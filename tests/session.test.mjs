// Fake worker verifies the transport/lifecycle state machine, not real pthreads.
import test from 'node:test';
import assert from 'node:assert/strict';
import {BrowserSession} from '../src/session.mjs';
class FakeWorker {
  sent=[];killed=0;ack=true;
  postMessage(m){this.sent.push(m);if(m.kind==='shutdown'&&this.ack)queueMicrotask(()=>this.emit({kind:'stopped'}));}
  emit(data){this.onmessage?.({data});}
  terminate(){this.killed++;}
  answer(last=this.sent.at(-1),value={}){this.emit({kind:'reply',id:last.id,ok:true,value});}
}
const tick=()=>new Promise(r=>setTimeout(r,0));
function make(options={}){const w=new FakeWorker(),events=[];const s=new BrowserSession({workerURL:'not-fetched',workerFactory:()=>w,onEvent:e=>events.push(e),...options});return {w,s,events};}
async function started(options){const f=make(options);const p=f.s.start({});f.w.answer();await p;return f;}
test('startup creates one worker and waits asynchronously',async()=>{const {s,w}=make();const p=s.start({});assert.equal(s.state,'starting');w.answer();await p;assert.equal(s.state,'ready');s.dispose();await tick();});
test('two sessions have independent pending requests and worker lifetimes',async()=>{const a=await started(),b=await started();const pa=a.s.request('navigate'),pb=b.s.request('navigate');a.w.answer(undefined,{a:1});assert.deepEqual(await pa,{a:1});assert.equal(b.s.pending.size,1);a.s.dispose();await tick();assert.equal(a.w.killed,1);assert.equal(b.w.killed,0);b.w.answer(undefined,{b:1});await pb;b.s.dispose();await tick();});
test('double disposal is harmless, pending work rejected',async()=>{const {s,w}=await started();const p=s.request('x');s.dispose();s.dispose();await assert.rejects(p,/closed/);await tick();assert.equal(w.killed,1);assert.equal(w.sent.filter(m=>m.kind==='shutdown').length,1);});
test('close during startup ignores late engine ready',async()=>{const {s,w}=make();const p=s.start({}),init=w.sent[0];s.dispose();w.answer(init);await assert.rejects(p,/closed/);await tick();assert.equal(s.state,'closed');});
test('out-of-order replies resolve their own calls',async()=>{const {s,w}=await started();const a=s.request('a'),ma=w.sent.at(-1),b=s.request('b'),mb=w.sent.at(-1);w.answer(mb,2);w.answer(ma,1);assert.deepEqual(await Promise.all([a,b]),[1,2]);s.dispose();await tick();});
test('worker failure marks event fatal and terminates',async()=>{const {s,w,events}=await started();w.emit({kind:'fatal',error:'broken'});await tick();assert.equal(s.closed,true);assert.equal(events[0].fatal,true);assert.equal(w.killed,1);});
test('request timeout closes the session',async()=>{const {s,w}=await started({commandTimeoutMs:8});await assert.rejects(s.request('blocked'),/timed out/);await tick();assert.equal(w.killed,1);});
test('bounded pending requests',async()=>{const {s,w}=await started();const requests=Array.from({length:32},()=>s.request('work'));const settled=Promise.allSettled(requests);await assert.rejects(s.request('excess'),/Too many/);s.dispose();assert.equal((await settled).filter(x=>x.status==='rejected').length,32);await tick();});
test('event callback failure still disposes after fatal failure',async()=>{const {s,w}=await started({onEvent:()=>{throw new Error('bad consumer');}});assert.throws(()=>s.fail(new Error('engine error')),/bad consumer/);await tick();assert.equal(s.closed,true);assert.equal(w.killed,1);});
test('missing graceful acknowledgment still terminates once',async()=>{const {s,w}=await started();w.ack=false;s.dispose();await new Promise(r=>setTimeout(r,280));assert.equal(w.killed,1);});
test('closed session neither sends input nor accepts requests',async()=>{const {s,w}=await started();s.dispose();await tick();const n=w.sent.length;s.notify('input',{});assert.equal(w.sent.length,n);await assert.rejects(s.request('x'),/closed/);});
test('session cannot start twice',async()=>{const {s}=await started();await assert.rejects(s.start({}),/only once/);s.dispose();await tick();});
