/* Classic worker: raw Emscripten MODULARIZE glue uses importScripts.
 * No page DOM, iframe, remote renderer, or host service object exists here.
 */
let moduleInstance=null, mailbox=null, ready=false, dead=false, starting=false;
let hasDocument=false;
let config=null, width=960, height=640, visible=true, frameOutstanding=false;
let frameSeq=0, queue=[], pumping=false, timer=0, lastStatus=0, pageSeq=0;
let guestDownloads=null, downloadTimer=0, downloadScanFailed=false;
const abort=new AbortController(), connections=new Set(), blobURLs=[];
const libraries=Promise.all([import('./mailbox.mjs'),import('./policy.mjs'),import('./guest-downloads.mjs'),import('./download-resources.mjs')]);
libraries.catch(()=>{}); // Errors are reported by init, not left unhandled.
const event=(type,fields={},transfer=[])=>{if(!dead)postMessage({kind:'event',type,...fields},transfer);};
const reply=(id,ok,value)=>{
  if(dead)return;
  const message=ok?{kind:'reply',id,ok:true,value}:{kind:'reply',id,ok:false,error:String(value).slice(0,4000)};
  const data=value?.data;
  postMessage(message,ok&&data instanceof Uint8Array&&data.buffer instanceof ArrayBuffer?[data.buffer]:[]);
};
function shutdown(){
  if(dead)return;dead=true;ready=false;abort.abort();clearTimeout(timer);clearInterval(downloadTimer);guestDownloads=null;queue.length=0;
  for(const c of connections){try{c.close();}catch{}} connections.clear();
  try{moduleInstance?.PThread?.terminateAllThreads();}catch{}
  moduleInstance=null;mailbox=null;
  for(const u of blobURLs)URL.revokeObjectURL(u);
  postMessage({kind:'stopped'});self.close();
}
function fatal(e){
  if(dead)return;
  postMessage({kind:'fatal',error:String(e?.message??e).slice(0,4000)});shutdown();
}
function sri(hex){return 'sha256-'+btoa(String.fromCharCode(...hex.match(/../g).map(x=>parseInt(x,16))));}
async function verifiedResponse(asset){
  const r=await fetch(asset.url,{credentials:'omit',signal:abort.signal,integrity:sri(asset.sha256)});
  if(!r.ok)throw new Error(`Engine asset ${asset.file}: HTTP ${r.status}`);
  return r;
}
async function verifiedBytes(asset){
  const b=await (await verifiedResponse(asset)).arrayBuffer();
  if(b.byteLength!==asset.bytes)throw new Error(`${asset.file}: byte size mismatch.`);
  return b;
}
async function init(payload){
  if(starting)throw new Error('Already initialized.');starting=true;
  const [{Mailbox},policy,{GuestDownloads},{DOWNLOAD_RESOURCES}]=await libraries;
  if(!self.crossOriginIsolated || typeof SharedArrayBuffer==='undefined') {
    throw new Error('Gecko pthreads require cross-origin isolation (COOP/COEP).');
  }
  config=payload;
  const base=new URL(payload.manifestURL);
  if(base.origin!==self.location.origin)throw new Error('Manifest must be same-origin.');
  const response=await fetch(base,{credentials:'omit',signal:abort.signal});
  if(!response.ok)throw new Error('Engine not installed. Build and stage it using tools/build_engine.sh.');
  const assets=policy.validateManifest(await response.json(),base.href,self.location.href);
  const dims=policy.boundedSize(payload.width,payload.height);
  width=dims.width;height=dims.height;
  config.wispURL=policy.relayURL(payload.wispURL,self.location.href);
  if(!Number.isInteger(config.framesPerSecond) || config.framesPerSecond<1 || config.framesPerSecond>30)throw new Error('Bad frame limit.');
  if(!Number.isInteger(config.commandTimeoutMs) || config.commandTimeoutMs<1000 || config.commandTimeoutMs>120000)throw new Error('Bad command timeout.');
  if(!Number.isInteger(config.maxHTMLBytes) || config.maxHTMLBytes<1 || config.maxHTMLBytes>134217728)throw new Error('Bad input-file limit.');
  event('status',{message:'Loading the independent Gecko engine…'});
  const fontAssets=[
    {file:'arabic.ttf',bytes:244072,sha256:'504d7407d86875acf7d04dfaa0fd7524d0b8797723bc4aa18022f29db25b0b6e'},
    {file:'cjk.data',bytes:19484784,sha256:'b76b0433203017ca80401b2ee0dd69350349871c4b19d504c34dbdd80541690a'},
  ].map(asset=>({...asset,url:new URL('../engine-fonts/'+asset.file,base).href}));
  const [runtime,data,arabic,cjk]=await Promise.all([verifiedBytes(assets.runtime),verifiedBytes(assets.data),...fontAssets.map(verifiedBytes)]);
  const sourceURL=URL.createObjectURL(new Blob([runtime],{type:'text/javascript'}));blobURLs.push(sourceURL);
  let Connection;
  if(config.wispURL){
    const wispBytes=await verifiedBytes(assets.wisp);
    const wispBlob=URL.createObjectURL(new Blob([wispBytes],{type:'text/javascript'}));blobURLs.push(wispBlob);
    const {client}=await import(wispBlob);
    Connection=class extends client.ClientConnection {
      constructor(url,...rest){
        if(url!==config.wispURL)throw new Error('Unexpected relay URL.');
        // The controlled relay implements TCP-only Wisp v1; avoid automatic
        // protocol fallback and its extra connection attempt.
        super(url,{...(rest[0]||{}),wisp_version:1});connections.add(this);
      }
      create_stream(hostname,port,...rest){
        const stream=super.create_stream(hostname,port,...rest);
        stream.codiDestination=typeof hostname==='string'?hostname.slice(0,253):'';
        event('domain-use',{hostname});
        return stream;
      }
      close_stream(stream,reason){
        if(reason===0x48)event('network-blocked',{hostname:stream.codiDestination});
        else if(reason===0x49)event('network-throttled',{});
        return super.close_stream(stream,reason);
      }
    };
  }
  importScripts(sourceURL);
  if(typeof self.createGecko!=='function')throw new Error('Missing createGecko; raw glue is required.');
  let markReady, rejectReady;
  const nativeReady=new Promise((r,j)=>{markReady=r;rejectReady=j;});
  nativeReady.catch(()=>{});
  let logTokens=12,lastLog=performance.now();
  const log=(s,error=false)=>{
    if(typeof s!=='string')return;
    if(s.includes('READY cmd='))markReady();
    if(s.includes('xul_init FAILED'))rejectReady(new Error(s));
    const now=performance.now();if(now-lastLog>1000){logTokens=12;lastLog=now;}
    if(logTokens-->0)event('log',{message:s.slice(0,2000),error});
  };
  let engineMemory=null;
  const options={
    mainScriptUrlOrBlob:sourceURL,
    locateFile:name=>new URL(name,base).href,
    // Raw data package, not dist/gecko.js's compressed/inlined package.
    getPreloadedPackage:(_name,size)=>{
      if(size!==data.byteLength)throw new Error('Runtime and GRE data do not match.');return data;
    },
    print:s=>log(s),printErr:s=>log(s,true),
    onAbort:why=>{rejectReady(new Error(String(why)));fatal(new Error('Gecko aborted: '+why));},
    preRun:[m=>{
      m.ENV.GRE_DIR='/gre-baked';m.ENV.PROFILE_DIR='/profile';
      m.ENV.MOZ_FORCE_DISABLE_E10S='1';
      m.ENV.GECKO_NOWASMJIT='1'; // Upstream JIT is experimental; interpreter baseline.
      m.ENV.GECKO_SKIP_OPFS='1'; // Per-window, ephemeral private guest filesystem.
      m.ENV.GECKO_DARK='0';
      // Presence enables GPU/mirror flags: never set those flags to "0".
      m.geckoProviders={};
      if(Connection){m.WispClientConnection=Connection;m.wispUrl=config.wispURL;}
    }],
    // The headless engine scans this process-local directory during startup.
    // Install verified fonts before callMain(), not after font discovery.
    onRuntimeInitialized(){
      this.FS.writeFile('/gre-baked/fonts/NotoArabic.ttf',new Uint8Array(arabic));
      this.FS.writeFile('/gre-baked/fonts/NotoCJK.ttc',new Uint8Array(cjk));
    },
    instantiateWasm:(imports,success)=>{
      engineMemory=imports.env.memory;
      if(!(engineMemory instanceof WebAssembly.Memory))throw new Error('Engine shared memory is unavailable.');
      (async()=>{
        const r=await verifiedResponse(assets.wasm);
        // No silent fallback fetching a different file or disabling checks.
        const result=await WebAssembly.instantiateStreaming(r,imports);
        success(result.instance,result.module);
      })().catch(fatal);
      return {};
    },
  };
  moduleInstance=await self.createGecko(options);
  await nativeReady;
  if(dead)throw new Error('Window closed during engine initialization.');
  if(typeof moduleInstance.PThread?.terminateAllThreads!=='function')throw new Error('Missing lifetime export. Apply the supplied native patch.');
  if(typeof moduleInstance._browser_embed_abi!=='function' || moduleInstance._browser_embed_abi()!==2)throw new Error('Native browser ABI patch missing or incompatible.');
  mailbox=new Mailbox(moduleInstance,moduleInstance._xul_cmd_ptr(),config.commandTimeoutMs,engineMemory);
  // The upstream minimal GRE omits download modules. Restore the reviewed
  // exact-revision sources into this window's private, ephemeral guest FS.
  moduleInstance.FS.mkdir('/browser-downloads');
  moduleInstance.FS.mkdir('/browser-download-markers');
  for(const asset of DOWNLOAD_RESOURCES){
    const url=new URL('../engine-support/'+asset.name,base);
    if(url.origin!==base.origin)throw Error('Download module must be same-origin.');
    const bytes=await verifiedBytes({...asset,file:asset.name,url:url.href});
    const target='/gre-baked/modules/'+asset.name;
    // WasmFS writeFile does not reliably truncate an existing preloaded file.
    if(asset.name==='HelperAppDlg.sys.mjs')moduleInstance.FS.truncate(target,0);
    moduleInstance.FS.writeFile(target,bytes);
    if(moduleInstance.FS.stat(target).size!==bytes.byteLength)throw Error('Could not stage browser download module.');
  }
  guestDownloads=new GuestDownloads(moduleInstance.FS,event);
  downloadTimer=setInterval(()=>{
    if(dead||!guestDownloads)return;
    try{guestDownloads.scan();downloadScanFailed=false;}
    catch(error){if(!downloadScanFailed){downloadScanFailed=true;event('download-error',{message:'Could not inspect browser downloads: '+String(error?.message||error)});}}
  },500);
  moduleInstance.FS.mkdir('/browser-input');
  ready=true;scheduleTick();
  return {engine:'Gecko/WASM',profile:'ephemeral',network:!!Connection};
}
function showFrame(r){
  if(!r?.pixels || frameOutstanding || !visible || dead)return;
  frameOutstanding=true;
  const buffer=r.pixels.buffer;
  event('frame',{seq:++frameSeq,width:r.width,height:r.height,cursor:r.cursor,buffer},[buffer]);
}
function emitStatus(s){
  if(!s || typeof s.url!=='string' || typeof s.canGoBack!=='boolean' || typeof s.canGoForward!=='boolean')throw new Error('Malformed native navigation status.');
  event('navigation',{url:s.url.slice(0,16384),canGoBack:s.canGoBack,canGoForward:s.canGoForward});
}
async function native(c){
  const r=await mailbox.command(c,width,height,abort.signal);
  if(r.status)emitStatus(r.status);else showFrame(r);
  return r;
}
async function run(type,payload){
  const [{OP},policy]=await libraries;
  if(!ready)throw new Error('Engine is not ready.');
  switch(type){
    case 'navigate':{
      const url=policy.normalizeNavigation(payload.url);
      if(url!=='about:blank'&&!config.wispURL)throw new Error('No network relay configured. Use Home or Open HTML for offline pages.');
      await native({op:OP.load,url});hasDocument=true;return {};
    }
    case 'open-html':{
      const bytes=payload.data instanceof ArrayBuffer?new Uint8Array(payload.data):typeof payload.html==='string'?new TextEncoder().encode(payload.html):null;
      if(!bytes)throw new Error('HTML file data is invalid.');
      if(bytes.byteLength>config.maxHTMLBytes)throw new Error('HTML file exceeds the 128 MiB limit.');
      // Imports remain in the private guest filesystem for browser history.
      // Bound their combined size independently of the per-file limit.
      if((config.importedBytes??0)+bytes.byteLength>256*1024*1024)throw new Error('Imported pages have reached the 256 MiB window limit. Reset the engine to open more.');
      const path=`/browser-input/page-${++pageSeq}.html`;
      moduleInstance.FS.writeFile(path,bytes);
      config.importedBytes=(config.importedBytes??0)+bytes.byteLength;
      await native({op:OP.load,url:'file://'+path});hasDocument=true;return {};
    }
    case 'download-read':{
      if(!guestDownloads)throw Error('Downloads are unavailable.');
      return {data:guestDownloads.read(payload.id)};
    }
    case 'download-discard':{
      if(!guestDownloads)throw Error('Downloads are unavailable.');
      guestDownloads.discard(payload.id);return {};
    }
    case 'control':{
      const action={status:0,back:1,forward:2,reload:3,stop:4}[payload.action];
      if(action===undefined)throw new Error('Unknown navigation action.');
      const status=(await native({op:OP.control,evType:action})).status;
      if(status.ok!==true)throw new Error('Native navigation operation failed.');
      return status;
    }
    case 'resize':{
      const d=policy.boundedSize(payload.width,payload.height);width=d.width;height=d.height;
      if(hasDocument)await native({op:OP.paint});return {};
    }
    case 'input':{
      if(!hasDocument)return {};
      if(![OP.mouse,OP.key,OP.wheel].includes(payload.op))throw new Error('Invalid input opcode.');
      for(const k of ['evType','x','y','button','buttons','clicks','modifiers','keyCode','charCode','deltaX','deltaY']) {
        if(payload[k]!==undefined && (!Number.isInteger(payload[k]) || Math.abs(payload[k])>0x7fffffff))throw new Error('Invalid input field.');
      }
      if(payload.key!==undefined && (typeof payload.key!=='string'||new TextEncoder().encode(payload.key).length>63))throw new Error('Invalid key.');
      // Copy only permitted scalar fields. No arbitrary op, script, path or host API.
      const c={op:payload.op};
      for(const k of ['evType','x','y','button','buttons','clicks','modifiers','keyCode','charCode','deltaX','deltaY','key'])if(payload[k]!==undefined)c[k]=payload[k];
      await native(c);return {};
    }
    case 'tick':{
      if(!hasDocument)return {};
      if(visible&&!frameOutstanding)await native({op:OP.paint});
      if(performance.now()-lastStatus>1000){lastStatus=performance.now();await native({op:OP.control,evType:0});}
      return {};
    }
    default:throw new Error('Unknown browser operation.');
  }
}
function enqueue(item){
  // Only adjacent pointer moves or resizes are coalesced. Never cross a down/up/key.
  const last=queue[queue.length-1];
  const move=x=>x?.type==='input'&&x.payload.op===1&&x.payload.evType===0;
  if(item.kind==='notice'&&last?.kind==='notice'&&((move(last)&&move(item))||(last.type==='resize'&&item.type==='resize'))){queue[queue.length-1]=item;return;}
  if(queue.length>=96){fatal(new Error('Browser input backlog exceeded; reset instead of losing key/button releases.'));return;}
  queue.push(item);void pump();
}
async function pump(){
  if(pumping||dead)return;pumping=true;
  try{
    while(queue.length&&!dead){
      const item=queue.shift();
      try{const v=await run(item.type,item.payload??{});if(item.kind==='request')reply(item.id,true,v);}
      catch(e){
        if(item.kind==='request')reply(item.id,false,e.message);
        if(mailbox?.failed){fatal(e);break;}
        if(item.kind!=='request')event('error',{message:String(e.message)});
      }
    }
  }finally{pumping=false;}
}
function scheduleTick(){
  timer=setTimeout(()=>{
    if(dead)return;
    if(ready&&visible&&!pumping&&!queue.length)enqueue({kind:'notice',type:'tick'});
    scheduleTick();
  },Math.round(1000/config.framesPerSecond));
}
self.onmessage=e=>{
  const m=e.data;
  if(!m||typeof m!=='object'||dead)return;
  if(m.kind==='shutdown'){shutdown();return;}
  if(m.kind==='notice'&&m.type==='frame-ack'){if(m.payload?.seq===frameSeq)frameOutstanding=false;return;}
  if(m.kind==='notice'&&m.type==='visibility'){visible=m.payload?.visible===true;return;}
  if(m.kind==='request'&&m.type==='init'){
    void init(m.payload).then(v=>reply(m.id,true,v)).catch(e=>{reply(m.id,false,e.message);fatal(e);});return;
  }
  if(!ready){if(m.kind==='request')reply(m.id,false,'Engine is starting.');return;}
  if(m.kind==='request'&&m.type==='control'&&m.payload?.action==='stop') {
    // Cancel loads still waiting behind another native operation as well as an
    // active load. Otherwise immediate Stop can sit behind a queued navigation.
    for(let i=queue.length-1;i>=0;i--){
      const item=queue[i];
      if(item.kind==='request' && (item.type==='navigate'||item.type==='open-html')){
        queue.splice(i,1);reply(item.id,false,'Navigation stopped.');
      }
    }
    mailbox?.cancelLoad();
  }
  if(m.kind==='request'||m.kind==='notice')enqueue(m);
};
self.addEventListener('unhandledrejection',e=>{e.preventDefault();fatal(e.reason);});
