/** Device-local, account-scoped signed domain events. No URL paths or contents. */
const DB='codi-browser-domain-usage',VERSION=3,enc=new TextEncoder();
function open(){return new Promise((resolve,reject)=>{
  const request=indexedDB.open(DB,VERSION);
  request.onupgradeneeded=()=>{
    const db=request.result;
    if(!db.objectStoreNames.contains('keys'))db.createObjectStore('keys',{keyPath:'scope'});
    if(!db.objectStoreNames.contains('heads'))db.createObjectStore('heads',{keyPath:'scope'});
    if(!db.objectStoreNames.contains('events')){const store=db.createObjectStore('events',{keyPath:['scope','seq']});store.createIndex('scope','scope');}
    if(!db.objectStoreNames.contains('reported'))db.createObjectStore('reported',{keyPath:['scope','request']});
  };
  request.onsuccess=()=>resolve(request.result);request.onerror=()=>reject(request.error);
});}
function normalized(value){
  if(typeof value!=='string'||value.length>253)return null;
  try{const url=new URL('https://'+value);if(url.username||url.password||url.port||url.pathname!=='/'||url.search||url.hash)return null;return url.hostname.toLowerCase().replace(/\.$/,'');}catch{return null;}
}
function scopeFor(subject){if(typeof subject!=='string'||!subject.startsWith('user:')||subject.length>100)throw Error('Registered account required');return JSON.stringify([location.origin,subject]);}
function requestResult(request){return new Promise((resolve,reject)=>{request.onsuccess=()=>resolve(request.result);request.onerror=()=>reject(request.error);});}
function complete(tx){return new Promise((resolve,reject)=>{tx.oncomplete=resolve;tx.onerror=()=>reject(tx.error);tx.onabort=()=>reject(tx.error||Error('Storage transaction aborted'));});}
const hex=bytes=>[...new Uint8Array(bytes)].map(x=>x.toString(16).padStart(2,'0')).join('');
const fromHex=text=>Uint8Array.from(text.match(/../g).map(x=>parseInt(x,16)));
async function locked(scope,work){if(!navigator.locks)throw Error('Device usage recording needs Web Locks');return navigator.locks.request('codi-browser-domain-usage:'+scope,work);}
async function identity(db,scope){
  let tx=db.transaction('keys','readonly'),key=await requestResult(tx.objectStore('keys').get(scope));
  if(key)return key;
  const pair=await crypto.subtle.generateKey({name:'ECDSA',namedCurve:'P-256'},false,['sign','verify']);
  const publicKey=await crypto.subtle.exportKey('jwk',pair.publicKey);
  key={scope,privateKey:pair.privateKey,publicKey};tx=db.transaction('keys','readwrite');tx.objectStore('keys').add(key);await complete(tx);return key;
}
export async function recordDomain(subject,raw){
  const domain=normalized(raw);if(!domain)return;
  const scope=scopeFor(subject);
  await locked(scope,async()=>{const db=await open();try{
    const key=await identity(db,scope);
    const head=await requestResult(db.transaction('heads','readonly').objectStore('heads').get(scope));
    const seq=(head?.seq||0)+1,prev=head?.hash||'0'.repeat(64),at=Date.now();
    const payload=JSON.stringify({version:1,scope,seq,prev,domain,at});
    const hash=hex(await crypto.subtle.digest('SHA-256',enc.encode(payload)));
    const signature=hex(await crypto.subtle.sign({name:'ECDSA',hash:'SHA-256'},key.privateKey,fromHex(hash)));
    const tx=db.transaction(['events','heads'],'readwrite');
    tx.objectStore('events').add({scope,seq,prev,domain,at,hash,signature});tx.objectStore('heads').put({scope,seq,hash});await complete(tx);
  }finally{db.close();}});
}
export async function getDomainReport(subject){
  const scope=scopeFor(subject);
  return locked(scope,async()=>{const db=await open();try{
    const tx=db.transaction(['keys','events'],'readonly');
    const keyRequest=tx.objectStore('keys').get(scope),eventsRequest=tx.objectStore('events').index('scope').getAll(scope);
    const [key,events]=await Promise.all([requestResult(keyRequest),requestResult(eventsRequest)]);
    return {version:1,scope,publicKey:key?.publicKey||null,events:events.map(({seq,prev,domain,at,hash,signature})=>({seq,prev,domain,at,hash,signature}))};
  }finally{db.close();}});
}
export async function wasReportSent(subject,request){
  const scope=scopeFor(subject);if(typeof request!=='string'||!/^[A-Za-z0-9_-]{32}$/.test(request))throw Error('Invalid report request');
  return locked(scope,async()=>{const db=await open();try{return !!(await requestResult(db.transaction('reported','readonly').objectStore('reported').get([scope,request])));}finally{db.close();}});
}
export async function markReportSent(subject,request){
  const scope=scopeFor(subject);if(typeof request!=='string'||!/^[A-Za-z0-9_-]{32}$/.test(request))throw Error('Invalid report request');
  return locked(scope,async()=>{const db=await open();try{const tx=db.transaction('reported','readwrite');tx.objectStore('reported').put({scope,request});await complete(tx);}finally{db.close();}});
}
/** Verify content and signatures; a separately saved head detects truncation. */
export async function verifyDomainReport(report,expectedHead=null){
  if(!report||report.version!==1||typeof report.scope!=='string'||!Array.isArray(report.events)||!report.publicKey)throw Error('Invalid device report');
  const key=await crypto.subtle.importKey('jwk',report.publicKey,{name:'ECDSA',namedCurve:'P-256'},false,['verify']);
  let prev='0'.repeat(64),seq=0;const summary=new Map();
  for(const event of report.events){
    if(!event||event.seq!==++seq||event.prev!==prev||normalized(event.domain)!==event.domain||!Number.isSafeInteger(event.at)||event.at<0||!/^[0-9a-f]{64}$/.test(event.hash)||!/^[0-9a-f]{128}$/.test(event.signature))throw Error('Invalid device report event');
    const payload=JSON.stringify({version:1,scope:report.scope,seq,prev,domain:event.domain,at:event.at});
    const hash=hex(await crypto.subtle.digest('SHA-256',enc.encode(payload)));
    if(hash!==event.hash||!await crypto.subtle.verify({name:'ECDSA',hash:'SHA-256'},key,fromHex(event.signature),fromHex(hash)))throw Error('Device report signature or hash changed');
    prev=hash;summary.set(event.domain,(summary.get(event.domain)||0)+1);
  }
  if(expectedHead!==null&&prev!==expectedHead)throw Error('Device report differs from saved checkpoint');
  return {head:prev,count:seq,domains:[...summary].map(([domain,requests])=>({domain,requests}))};
}
