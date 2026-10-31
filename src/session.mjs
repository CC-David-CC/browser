import {textError} from './policy.mjs';

/** One window owns one worker and its requests. No desktop-wide state. */
export class BrowserSession {
  constructor({workerURL, onEvent=()=>{}, startupTimeoutMs=120000, commandTimeoutMs=45000, workerFactory}) {
    this.workerURL=workerURL;this.onEvent=onEvent;
    this.startupTimeoutMs=startupTimeoutMs;this.commandTimeoutMs=commandTimeoutMs;
    this.workerFactory=workerFactory ?? ((u)=>new Worker(u, {name:'independent-gecko'}));
    this.worker=null;this.pending=new Map();this.seq=0;this.closed=false;this.state='new';
  }
  async start(init) {
    if(this.state!=='new') throw new Error('Session may be started only once.');
    this.state='starting';
    const w=this.worker=this.workerFactory(this.workerURL);
    w.onmessage=e=>this.receive(e.data);
    w.onerror=e=>this.fail(new Error(e.message || 'Browser worker failed.'));
    w.onmessageerror=()=>this.fail(new Error('Unreadable browser worker message.'));
    await this.request('init',init,this.startupTimeoutMs);
    if(this.closed) throw new Error('Session closed during startup.');
    this.state='ready';
  }
  receive(m) {
    if(this.closed || !m || typeof m!=='object') return;
    if(m.kind==='reply') {
      const p=this.pending.get(m.id);if(!p)return;
      clearTimeout(p.timer);this.pending.delete(m.id);
      m.ok ? p.resolve(m.value) : p.reject(new Error(m.error || 'Engine request failed.'));
    } else if(m.kind==='fatal') { this.fail(new Error(m.error)); }
    else if(m.kind==='event') { this.onEvent(m); }
  }
  request(type,payload={},timeout=this.commandTimeoutMs,transfer=[]) {
    if(this.closed || !this.worker) return Promise.reject(new Error('Session is closed.'));
    if(this.pending.size>=32) return Promise.reject(new Error('Too many pending browser operations.'));
    const id=++this.seq;
    return new Promise((resolve,reject)=>{
      const timer=setTimeout(()=>this.fail(new Error(`${type} timed out; instance terminated.`)),timeout);
      this.pending.set(id,{resolve,reject,timer});
      try { this.worker.postMessage({kind:'request',id,type,payload},transfer); }
      catch(e) { clearTimeout(timer);this.pending.delete(id);reject(e); }
    });
  }
  notify(type,payload={}) {
    if(!this.closed && this.worker) this.worker.postMessage({kind:'notice',type,payload});
  }
  fail(e) {
    if(this.closed)return;
    try { this.onEvent({kind:'event',type:'error',fatal:true,message:textError(e)}); }
    finally { this.dispose(e); }
  }
  dispose(reason=new Error('Browser window closed.')) {
    if(this.closed)return;
    this.closed=true;this.state='closed';
    for(const p of this.pending.values()){clearTimeout(p.timer);p.reject(reason);}
    this.pending.clear();
    const w=this.worker;this.worker=null;
    if(!w)return;
    // The native runtime may be stuck. A shutdown grace period is bounded and
    // never blocks mount/dispose. The fallback terminates the worker regardless.
    let timer,killed=false;
    const kill=()=>{if(killed)return;killed=true;clearTimeout(timer);w.onmessage=null;w.onerror=null;w.onmessageerror=null;w.terminate();};
    w.onmessage=e=>{if(e.data?.kind==='stopped')kill();};
    w.onerror=kill;
    timer=setTimeout(kill,250);
    try { w.postMessage({kind:'shutdown'}); } catch {kill();}
  }
}
