import {recordDomain,getDomainReport,wasReportSent,markReportSent} from './src/domain-usage.mjs';
import {config} from './config.mjs';
import {BrowserSession} from './src/session.mjs';
import {normalizeNavigation,boundedSize,relayURL,textError} from './src/policy.mjs';
import {bindInput} from './src/input.mjs';
import {HOME_HTML} from './src/home.mjs';
import {styles} from './src/styles.mjs';

/** The only desktop-facing export. Each call returns synchronously. */
export function mount(host) {
  const body=host.ui.make('div','window-content');
  const doc=body.ownerDocument;
  const usageOwner=host.storage?.signedInSubject?.();
  // The desktop sizes window-content below its title bar. Overriding that
  // height with 100% clips the status and diagnostics at the window bottom.
  body.style.cssText='min-height:0;display:flex;flex-direction:column;';
  // Shadow DOM scopes OUR chrome styles only. It does not render guest content
  // and is not claimed as a security boundary.
  const root=body.attachShadow({mode:'open'});
  const make=(tag,cls,text)=>{const e=doc.createElement(tag);if(cls)e.className=cls;if(text!=null)e.textContent=text;return e;};
  const style=make('style');style.textContent=styles;
  const toolbar=make('div','toolbar'),form=make('form'),address=make('input');
  address.type='text';address.inputMode='url';address.autocomplete='off';address.placeholder='https://example.com';address.setAttribute('aria-label','Website address');
  const buttons={};
  for(const [name,label] of [['back','Back'],['forward','Forward'],['reload','Reload'],['stop','Stop'],['home','Home'],['keyboard','Keyboard'],['open','Upload HTML'],['download','Download URL'],...(host.storage?[['files','Open from My files']]:[]),['reset','Reset engine']]) {
    const b=make('button','',label);b.type='button';b.disabled=name!=='reset';buttons[name]=b;toolbar.append(b);
  }
  const go=make('button','','Go');go.type='submit';go.disabled=true;
  form.append(address,go);toolbar.insertBefore(form,buttons.home);
  const licenses=make('a','','Licenses & source');licenses.href='/browser-sources/';licenses.target='_blank';licenses.rel='noopener noreferrer';toolbar.append(licenses);
  const warning=make('div','warn','Experimental browser · temporary profile · audio is not available yet');
  const stage=make('div','stage'),canvas=make('canvas'),info=make('div','info');
  canvas.width=config.width;canvas.height=config.height;canvas.tabIndex=0;canvas.setAttribute('aria-label','Independent browser viewport');
  info.textContent='Preparing browser…';stage.append(canvas,info);
  const status=make('div','status','Preparing browser…'),details=make('details');
  details.append(make('summary','','Diagnostics'));const logs=make('pre','details');details.append(logs);
  const picker=make('input');picker.type='file';picker.accept='.html,.htm,text/html';picker.hidden=true;
  const keyboard=make('textarea','mobile-keyboard');keyboard.setAttribute('aria-label','Website keyboard input');keyboard.autocapitalize='off';keyboard.autocomplete='off';keyboard.spellcheck=false;
  stage.append(keyboard);root.append(style,toolbar,warning,stage,status,details,picker);
  const lifetime=new AbortController();
  let instance=null,runAbort=null,relay=null,disposed=false,generation=0,sizeTimer=0,reportTimer=0,reportPanel=null,seen=false,networkNotice='';
  const logLines=[];
  const log=s=>{logLines.push(String(s).slice(0,2000));if(logLines.length>60)logLines.shift();logs.textContent=logLines.join('\n');};
  const setStatus=s=>{if(!disposed)status.textContent=s;};
  const setControls=on=>{for(const [k,b]of Object.entries(buttons))if(!['reset','back','forward'].includes(k))b.disabled=!on;go.disabled=!on;if(!on){buttons.back.disabled=true;buttons.forward.disabled=true;}};
  const report=e=>{if(!disposed){setStatus(textError(e));log(textError(e));}};
  const current=(s,g)=>!disposed&&instance===s&&generation===g;
  async function sendRequestedReports(connection,g){
    if(!connection?.reports||!usageOwner||disposed||generation!==g)return;
    try{
      const requests=await connection.reports.pending();
      if(!Array.isArray(requests)||requests.length>16)throw Error('Invalid domain report requests.');
      for(const request of requests){
        if(disposed||generation!==g||host.storage?.signedInSubject?.()!==usageOwner)return;
        if(!request||typeof request.id!=='string'||!/^[A-Za-z0-9_-]{32}$/.test(request.id))throw Error('Invalid domain report request.');
        if(await wasReportSent(usageOwner,request.id))continue;
        const data=await getDomainReport(usageOwner);if(!data.publicKey||!data.events.length)continue;
        if(disposed||generation!==g||host.storage?.signedInSubject?.()!==usageOwner)return;
        await connection.reports.submit(request.id,data);
        if(disposed||generation!==g||host.storage?.signedInSubject?.()!==usageOwner)return;
        await markReportSent(usageOwner,request.id);log('A site administrator requested this device’s domain-usage report; it was sent.');
      }
    }catch(error){if(!disposed&&generation===g)log('Requested domain report could not be sent: '+textError(error));}
    finally{if(!disposed&&generation===g)reportTimer=setTimeout(()=>void sendRequestedReports(connection,g),30000);}
  }
  async function prepareReportAdmin(connection,g){
    if(!connection?.reports)return;
    try{
      const role=await connection.reports.role();if(disposed||generation!==g||role?.admin!==true)return;
      const panel=make('section','report-admin'),label=make('h3','','Domain usage reports'),note=make('p','','Requests collect signed domain-only records from browsers that are open during the request. Records can be incomplete and do not prove who used a device.'),select=make('select'),output=make('pre','details');
      select.setAttribute('aria-label','Domain usage report request');
      const request=make('button','','Request reports for one hour'),refresh=make('button','','Refresh requests'),show=make('button','','Show totals');
      for(const b of [request,refresh,show])b.type='button';
      const update=async()=>{const rows=await connection.reports.list();if(disposed||generation!==g)return;if(!Array.isArray(rows)||rows.length>100)throw Error('Invalid report request list.');select.replaceChildren();for(const item of rows){if(!item||!/^[A-Za-z0-9_-]{32}$/.test(item.id)||!Number.isSafeInteger(item.created))throw Error('Invalid report request.');const option=make('option','',new Date(item.created*1000).toLocaleString());option.value=item.id;select.append(option);}};
      const action=fn=>async()=>{try{await fn();}catch(error){if(!disposed&&generation===g)output.textContent=textError(error);}};
      request.addEventListener('click',action(async()=>{await connection.reports.create(3600);await update();output.textContent='Report requested. Open browsers can respond during the next hour.';}),{signal:lifetime.signal});
      refresh.addEventListener('click',action(update),{signal:lifetime.signal});
      show.addEventListener('click',action(async()=>{if(!select.value)throw Error('Choose a report request first.');const result=await connection.reports.summary(select.value);if(disposed||generation!==g)return;if(!result||!Number.isSafeInteger(result.devices)||!Array.isArray(result.domains))throw Error('Invalid report totals.');output.textContent=result.devices+' device(s)\n'+result.domains.map(row=>String(row.domain)+'  '+String(row.requests)).join('\n');}),{signal:lifetime.signal});
      panel.append(label,note,request,refresh,select,show,output);details.append(panel);reportPanel=panel;await update();
    }catch(error){if(!disposed&&generation===g)log('Domain report administration unavailable: '+textError(error));}
  }
  async function operation(type,payload={}) {
    const s=instance,g=generation;if(!s||s.state!=='ready')return;
    try{networkNotice='';setStatus('Loading…');await s.request(type,payload);if(current(s,g))setStatus(networkNotice||(payload.action==='stop'?'Stopped.':'Navigation requested.'));}
    catch(e){if(current(s,g))report(e);}
  }
  function applySize(){
    clearTimeout(sizeTimer);sizeTimer=0;
    const r=stage.getBoundingClientRect();if(r.width<1||r.height<1)return;
    const d=boundedSize(r.width,r.height,config.maxWidth,config.maxHeight);
    if(instance?.state==='ready')instance.notify('resize',d);
  }
  async function start(){
    if(disposed)return;const g=++generation;
    clearTimeout(reportTimer);reportPanel?.remove();reportPanel=null;runAbort?.abort();instance?.dispose();relay?.close();relay=null;setControls(false);info.hidden=false;
    info.textContent='Starting browser…';
    if(!globalThis.crossOriginIsolated||typeof SharedArrayBuffer==='undefined') {
      info.textContent='The browser could not start because this page is missing required isolation. Please contact the site administrator.';return;
    }
    let endpoint;
    try{
      if(host.browserRelay?.available()){
        const opened=await host.browserRelay.open({onFailure:error=>{if(generation===g&&!disposed){setStatus('Browser network disconnected: '+textError(error));instance?.dispose();setControls(false);info.hidden=false;info.textContent='Network connection ended. Use Reset engine to reconnect.';}}});
        if(disposed||generation!==g){opened.close();return;}
        relay=opened;void sendRequestedReports(opened,g);void prepareReportAdmin(opened,g);
      }
      endpoint=relayURL(relay?.url??config.wispURL,doc.location.href);
    }catch(e){report(e);info.textContent=textError(e);return;}
    const s=new BrowserSession({
      workerURL:new URL('./src/engine-worker.js',import.meta.url),
      startupTimeoutMs:config.startupTimeoutMs,commandTimeoutMs:config.commandTimeoutMs,
      onEvent:m=>{
        if(!current(s,g))return;
        if(m.type==='frame'){
          try{
            const {width:w,height:h,buffer}=m;
            if(!Number.isInteger(w)||!Number.isInteger(h)||w<1||h<1||w>config.maxWidth||h>config.maxHeight||!(buffer instanceof ArrayBuffer)||buffer.byteLength!==w*h*4)throw new Error('Invalid frame.');
            if(canvas.width!==w||canvas.height!==h){canvas.width=w;canvas.height=h;}
            const context=canvas.getContext('2d',{alpha:false});
            if(!context)throw new Error('Canvas unavailable.');
            context.putImageData(new ImageData(new Uint8ClampedArray(buffer),w,h),0,0);
            info.hidden=true;
          }catch(e){report(e);s.fail(e);}
          finally{s.notify('frame-ack',{seq:m.seq});}
        }else if(m.type==='network-blocked'){
          networkNotice='The site or one of its resources was blocked by the server network policy'+(m.hostname?' ('+String(m.hostname).slice(0,253)+').':'.');setStatus(networkNotice);
        }else if(m.type==='network-throttled'){
          networkNotice='Browser network connection limit reached. Try again shortly.';setStatus(networkNotice);
        }else if(m.type==='domain-use'){
          if(usageOwner&&host.storage?.signedInSubject?.()===usageOwner)void recordDomain(usageOwner,m.hostname).catch(error=>log('Domain usage could not be saved on this device: '+textError(error)));
        }else if(m.type==='navigation'){
          // Native nsIWebNavigation status, not a page-controlled JS location hook.
          if(root.activeElement!==address)address.value=m.url;
          buttons.back.disabled=!m.canGoBack;buttons.forward.disabled=!m.canGoForward;
        }else if(m.type==='log'){log(m.message);}
        else if(m.type==='status'){setStatus(m.message);}
        else if(m.type==='error'){report(m.message);if(m.fatal||s.closed){setControls(false);info.hidden=false;info.textContent=m.message;}}
      },
    });
    instance=s;runAbort=new AbortController();
    try{
      await s.start({...config,wispURL:endpoint});
      if(!current(s,g))return;
      setControls(true);bindInput(canvas,s,runAbort.signal,{keyboard});
      s.notify('visibility',{visible:seen&&!doc.hidden});
      applySize();
      await s.request('open-html',{html:HOME_HTML});
      if(current(s,g))setStatus(endpoint?'Ready':'Offline: websites are unavailable. You can still open an HTML file.');
    }catch(e){if(current(s,g)){setControls(false);info.hidden=false;info.textContent=textError(e);report(e);s.dispose();}}
  }
  root.addEventListener('keydown',e=>{
    if(e.ctrlKey&&!e.altKey&&!e.metaKey&&e.code==='Backquote'){
      e.preventDefault();e.stopPropagation();address.focus();address.select();
    }
  },{capture:true,signal:lifetime.signal});
  form.addEventListener('submit',e=>{e.preventDefault();try{void operation('navigate',{url:normalizeNavigation(address.value)});}catch(err){report(err);}},{signal:lifetime.signal});
  for(const name of ['back','forward','reload','stop'])buttons[name].addEventListener('click',()=>void operation('control',{action:name}),{signal:lifetime.signal});
  buttons.home.addEventListener('click',()=>void operation('open-html',{html:HOME_HTML}),{signal:lifetime.signal});
  buttons.keyboard.addEventListener('click',()=>{host.ui.enableKeyboard?.();keyboard.inputMode='text';keyboard.focus({preventScroll:true});},{signal:lifetime.signal});
  buttons.reset.addEventListener('click',()=>void start(),{signal:lifetime.signal});
  buttons.open.addEventListener('click',()=>picker.click(),{signal:lifetime.signal});
  buttons.download.addEventListener('click',async()=>{
    const s=instance,g=generation,connection=relay;
    try{
      if(!connection?.download)throw Error('Connect Browser networking before downloading.');
      const url=normalizeNavigation(address.value),parsed=new URL(url);
      if(!['http:','https:'].includes(parsed.protocol))throw Error('Enter an HTTP or HTTPS download URL.');
      let suggested=decodeURIComponent(parsed.pathname.split('/').pop()||'download').replace(/[\/\\\u0000-\u001f\u007f]/g,'_');
      if(!suggested||suggested==='.'||suggested==='..')suggested='download';
      const requested=doc.defaultView.prompt('Save download in My files as:',suggested.slice(0,120));
      if(requested===null)return;
      const context=await host.storage.mirrorFileContext();if(!current(s,g)||!context.valid())return;
      const name=context.name(requested);setStatus('Downloading…');
      if(usageOwner&&host.storage.signedInSubject?.()===usageOwner)void recordDomain(usageOwner,parsed.hostname).catch(error=>log(textError(error)));
      const result=await connection.download(url);if(!current(s,g)||!context.valid())return;
      for(const domain of result.domains.slice(1))if(usageOwner&&host.storage.signedInSubject?.()===usageOwner)void recordDomain(usageOwner,domain).catch(error=>log(textError(error)));
      await context.files.write('/'+name,result.data);if(current(s,g))setStatus('Saved to My files. Server synchronization may continue in the background.');
    }catch(error){if(current(s,g))report(error);}
  },{signal:lifetime.signal});
  buttons.files?.addEventListener('click',async()=>{
    const s=instance,g=generation;
    try{
      const path=await host.storage.pickFile({extensions:['.html','.htm'],signal:host.signal});
      if(!path||!current(s,g))return;
      const context=await host.storage.mirrorFileContext();if(!current(s,g)||!context.valid())return;
      const file=await context.files.read(path);if(!current(s,g)||!context.valid())return;
      if(file.data.byteLength>config.maxHTMLBytes)throw new Error('HTML file too large.');
      const html=new TextDecoder('utf-8',{fatal:true}).decode(file.data);
      await operation('open-html',{html});
    }catch(e){if(current(s,g))report(e);}
  },{signal:lifetime.signal});
  picker.addEventListener('change',async()=>{
    const f=picker.files?.[0];picker.value='';if(!f)return;
    const s=instance,g=generation;
    try{if(f.size>config.maxHTMLBytes)throw new Error('HTML file too large.');const html=await f.text();if(current(s,g))await operation('open-html',{html});}catch(e){report(e);}
  },{signal:lifetime.signal});
  const ro=new ResizeObserver(()=>{clearTimeout(sizeTimer);sizeTimer=setTimeout(applySize,100);});ro.observe(stage);
  const io=new IntersectionObserver(entries=>{
    seen=entries[0]?.isIntersecting===true;instance?.notify('visibility',{visible:seen&&!doc.hidden});
  });io.observe(body);
  doc.addEventListener('visibilitychange',()=>instance?.notify('visibility',{visible:seen&&!doc.hidden}),{signal:lifetime.signal});
  queueMicrotask(()=>{if(!disposed)void start();});
  return {element:body,dispose(){
    if(disposed)return;disposed=true;generation++;clearTimeout(sizeTimer);clearTimeout(reportTimer);
    lifetime.abort();runAbort?.abort();ro.disconnect();io.disconnect();
    instance?.dispose();instance=null;relay?.close();relay=null;canvas.width=1;canvas.height=1;
    // The desktop owns element removal. Do not close its Linux/network services.
  }};
}
