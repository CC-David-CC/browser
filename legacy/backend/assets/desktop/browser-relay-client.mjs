/** Account-bound relay admission. The desktop retains the account private key. */
import {hash,signJws,inspectJws,verifyJws,sameKey,validateTimes,nowSeconds,requireThat} from '../../network/crypto.mjs';
import {verifyIdentity,PROOF_TYPE} from '../../network/identity.mjs';
const token=s=>typeof s==='string'&&/^[A-Za-z0-9_-]{43}$/.test(s);
export const relayUnavailable=status=>[502,503,504].includes(status)?'Browser network is temporarily unavailable. Select Reset engine to try again.':null;

const MAX_DOWNLOAD_BYTES=128*1024*1024;
const DOWNLOAD_TIMEOUT_MS=35*60*1000;
/** Consume a bounded response. The relay supplies Content-Length after its
 * private temporary-file fetch, so normally only one full-size buffer is held. */
export async function readDownloadBody(response){
  const raw=response.headers.get('content-length');let expected=null;
  if(raw!==null){
    if(!/^\d{1,9}$/.test(raw))throw Error('Invalid download length.');
    expected=Number(raw);if(expected>MAX_DOWNLOAD_BYTES)throw Error('Download is larger than 128 MiB.');
  }
  const reader=response.body?.getReader();if(!reader)throw Error('Download response has no body.');
  const result=expected===null?null:new Uint8Array(expected),chunks=[];let size=0;
  try{
    while(true){
      const {done,value}=await reader.read();if(done)break;
      if(!(value instanceof Uint8Array))throw Error('Invalid download data.');
      const next=size+value.length;
      if(next>MAX_DOWNLOAD_BYTES)throw Error('Download is larger than 128 MiB.');
      if(result){if(next>expected)throw Error('Download length does not match response.');result.set(value,size);}else chunks.push(value);
      size=next;
    }
    if(result){if(size!==expected)throw Error('Download ended before all bytes arrived.');return result;}
    const data=new Uint8Array(size);let at=0;for(const chunk of chunks){data.set(chunk,at);at+=chunk.length;}return data;
  }catch(error){await reader.cancel().catch(()=>{});throw error;}
  finally{reader.releaseLock();}
}

export async function openBrowserRelay(config,session,{valid=()=>true,onFailure=()=>{}}={}){
  const meta=config?.browserRelay,identity=config?.identity,api=identity?.apiBase;
  requireThat(identity?.mode==='server'&&identity.issuer===location.origin&&session?.public?.kind==='registered','Sign in to use Browser networking.');
  requireThat(typeof api==='string'&&/^\/(?:[A-Za-z0-9_-]+\/)*api\/v1$/.test(api),'Invalid issuer API.');
  const base=api.slice(0,-7)+'/browser-relay';
  requireThat(meta?.version==='codi-browser-relay/1'&&meta.basePath===base&&/^[a-f0-9]{64}$/.test(meta.policySHA256),'Browser networking is not configured.');
  const check=()=>requireThat(valid()&&session.public.kind==='registered','Account changed; reopen Browser.');
  const post=async(path,body,tokenValue=null,{timeoutMs=10000,maxResponse=16384}={})=>{
    check();const response=await fetch(path,{method:'POST',mode:'same-origin',credentials:'same-origin',redirect:'error',cache:'no-store',referrerPolicy:'no-referrer',headers:{'Content-Type':'application/json',...(tokenValue?{Authorization:'Codi '+tokenValue}:{})},body:JSON.stringify(body),signal:AbortSignal.timeout(timeoutMs)});
    const bytes=new Uint8Array(await response.arrayBuffer());requireThat(bytes.length<=maxResponse,'Browser relay response too large.');
    let result;try{result=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes));}catch{if(!response.ok)throw Error(relayUnavailable(response.status)||'Browser request failed ('+response.status+').');throw Error('Invalid Browser relay response.');}
    check();if(!response.ok)throw Error(relayUnavailable(response.status)||result.error||'Browser network connection failed ('+response.status+').');return result;
  };
  await verifyIdentity(session.public,identity);check();
  let challenge=await post(base+'/challenge',{}),id=challenge.connection_id,closed=false,timer=0;
  const downloadAbort=new AbortController();
  const reportRequestsEnabled=challenge.report_requests===true;
  requireThat(token(id)&&token(challenge.nonce)&&challenge.policy_sha256===meta.policySHA256,'Invalid Browser relay challenge.');
  const root=base+'/connection/'+id;
  async function authorize(ch){
    check();requireThat(ch.connection_id===id&&token(ch.nonce)&&ch.policy_sha256===meta.policySHA256,'Browser relay challenge changed.');
    const path=api+'/browser-relay/authorize';
    const issuerNonce=await post(api+'/browser-relay/challenge',{key:session.public.key,path});
    requireThat(token(issuerNonce.nonce),'Invalid issuer challenge.');
    const raw=JSON.stringify({nonce:ch.nonce,connection_id:id,policy_sha256:meta.policySHA256}),now=nowSeconds();
    const proof=await signJws({v:1,nonce:issuerNonce.nonce,iss:session.public.sid,aud:identity.issuer,method:'POST',path,iat:now,exp:now+60,request_sha256:await hash(raw)},session.privateKey,PROOF_TYPE);
    const result=await post(path,{request:raw,proof},session.token);
    const inspected=inspectJws(result.grant,'codi-browser-relay-identity+jwt',8192),authority=identity.authorityKeys.find(k=>k.kid===inspected.header.kid);
    requireThat(authority,'Unknown Browser relay issuer.');
    const c=await verifyJws(result.grant,authority.jwk,'codi-browser-relay-identity+jwt',8192);validateTimes(c,30);
    const audience=location.origin+base;
    requireThat(c.v===1&&c.iss===identity.issuer&&c.aud===audience&&c.sub===session.public.sub&&c.sid===session.public.sid&&c.kind==='registered'&&sameKey(c.cnf?.jwk,session.public.key)&&c.nonce===ch.nonce&&c.connection_id===id&&c.policy_sha256===meta.policySHA256,'Browser relay identity context changed.');
    check();
    const use=await signJws({v:1,iss:c.sid,aud:audience,nonce:ch.nonce,grant_sha256:await hash(result.grant),connection_id:id,policy_sha256:meta.policySHA256,method:'CONNECT',path:base,iat:c.iat,exp:c.exp},session.privateKey,'codi-browser-relay-use+jws');
    await post(root+'/authorize',{grant:result.grant,proof:use});
  }
  async function renew(){
    if(closed)return;
    try{challenge=await post(root+'/challenge',{});await authorize(challenge);if(!closed)timer=setTimeout(renew,12000);}
    catch(error){if(!closed){closed=true;downloadAbort.abort();onFailure(error);}}
  }
  try{await authorize(challenge);}catch(error){closed=true;throw error;}
  if(!valid()){closed=true;throw Error('Account changed; reopen Browser.');}
  timer=setTimeout(renew,12000);
  const url=new URL(root+'/wisp/',location.origin);url.protocol=url.protocol==='https:'?'wss:':'ws:';
  const reportId=value=>{requireThat(typeof value==='string'&&/^[A-Za-z0-9_-]{32}$/.test(value),'Invalid report request.');return value;};
  const reports=reportRequestsEnabled?Object.freeze({
    pending:()=>post(root+'/reports/pending',{}),
    role:()=>post(root+'/reports/role',{}),
    list:()=>post(root+'/reports/list',{}),
    submit:(request,report)=>post(root+'/reports/submit',{request:reportId(request),report},null,{timeoutMs:90000}),
    create:(seconds=3600)=>post(root+'/reports/create',{seconds}),
    summary:(request,subject=null)=>post(root+'/reports/summary',{request:reportId(request),subject},null,{maxResponse:1024*1024}),
    remove:request=>post(root+'/reports/remove',{request:reportId(request)}),
  }):null;
  return {url:url.href,sourceURL:root+'/sources/',reports,async download(source){
    check();requireThat(!closed,'Browser networking has disconnected.');
    const response=await fetch(root+'/download',{method:'POST',mode:'same-origin',credentials:'same-origin',redirect:'error',cache:'no-store',referrerPolicy:'no-referrer',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:source}),signal:AbortSignal.any([downloadAbort.signal,AbortSignal.timeout(DOWNLOAD_TIMEOUT_MS)])});
    if(!response.ok){let result;try{result=await response.json();}catch{}throw Error(relayUnavailable(response.status)||result?.error||'Download failed ('+response.status+').');}
    const data=await readDownloadBody(response);
    check();
    return {data,domains:(response.headers.get('X-Codi-Domain-Requests')||'').split(',').filter(Boolean)};
  },close(){if(closed)return;closed=true;clearTimeout(timer);downloadAbort.abort();void post(root+'/close',{}).catch(()=>{});}};
}
