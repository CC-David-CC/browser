// A synthetic memory protocol peer, NOT Gecko, not an engine smoke test.
import test from 'node:test';
import assert from 'node:assert/strict';
import {Mailbox,EngineCommandError,OFF,OP} from '../src/mailbox.mjs';
const base=16,result=12000;
function fixture(timeout=200){const buffer=new SharedArrayBuffer(65536);const m={HEAPU8:new Uint8Array(buffer),HEAP32:new Int32Array(buffer)};m.HEAP32[base/4]=10;return {m,box:new Mailbox(m,base,timeout)};}
function finish(m,bytes,state=3){m.HEAPU8.set(bytes,result);m.HEAP32[(base+OFF.result)/4]=result;m.HEAP32[(base+OFF.length)/4]=bytes.length;Atomics.store(m.HEAP32,base/4,state);}
const tick=()=>new Promise(r=>setTimeout(r,6));
test('ABI offsets match inspected wasm32 struct',()=>{assert.equal(OFF.op,8212);assert.equal(OFF.key,8260);assert.equal(OFF.cursor,8324);});
test('BGRA copied to RGBA, not shared with engine',async()=>{const {m,box}=fixture();const p=box.command({op:OP.paint},1,1);finish(m,new Uint8Array([10,20,30,0]));const r=await p;assert.deepEqual([...r.pixels],[30,20,10,255]);m.HEAPU8[result+2]=0;assert.equal(r.pixels[0],30);});
test('native control result parsed',async()=>{const {m,box}=fixture();const p=box.command({op:OP.control},1,1);const status={url:'https://a.test/',canGoBack:false,canGoForward:true,ok:true};finish(m,new TextEncoder().encode(JSON.stringify(status)));assert.deepEqual((await p).status,status);});
test('reject parallel mailbox command, allow later completed operation',async()=>{const {m,box}=fixture();const p=box.command({op:OP.paint},1,1);await assert.rejects(box.command({op:OP.paint},1,1),/busy/);finish(m,new Uint8Array(4));await p;const p2=box.command({op:OP.paint},1,1);finish(m,new Uint8Array(4));await p2;});
test('page evaluation and DOM mirroring opcodes not exposed',async()=>{const {box}=fixture();for(const op of [5,6,7,8,9,11])await assert.rejects(box.command({op},1,1),/Disallowed/);});
test('oversized UTF8 rejected before submission without poisoning mailbox',async()=>{const {box,m}=fixture();await assert.rejects(box.command({op:OP.key,key:'é'.repeat(40)},1,1),/capacity/);assert.equal(box.failed,false);assert.equal(m.HEAP32[base/4],10);});
test('timeout poisons mailbox; no uncertain reuse',async()=>{const {box}=fixture(8);await assert.rejects(box.command({op:OP.paint},1,1),/timed out/);assert.equal(box.failed,true);await assert.rejects(box.command({op:OP.paint},1,1),/failed/);});
test('completed native failure is recoverable',async()=>{const {box,m}=fixture();const p=box.command({op:OP.load,url:'https://a.test'},1,1);finish(m,new Uint8Array(),-1);await assert.rejects(p,EngineCommandError);assert.equal(box.failed,false);const p2=box.command({op:OP.paint},1,1);finish(m,new Uint8Array(4));await p2;});
test('malformed frame poisons mailbox',async()=>{const {box,m}=fixture();const p=box.command({op:OP.paint},2,2);finish(m,new Uint8Array(4));await assert.rejects(p,/Expected/);assert.equal(box.failed,true);});
test('out-of-bounds native memory rejected',async()=>{const {box,m}=fixture();const p=box.command({op:OP.paint},1,1);m.HEAP32[(base+OFF.result)/4]=65535;m.HEAP32[(base+OFF.length)/4]=4;Atomics.store(m.HEAP32,base/4,3);await assert.rejects(p,/outside/);});
test('shared heap views reacquired after growth',async()=>{const {box,m}=fixture();const p=box.command({op:OP.paint},1,1);const fresh=new SharedArrayBuffer(131072);new Uint8Array(fresh).set(m.HEAPU8);m.HEAPU8=new Uint8Array(fresh);m.HEAP32=new Int32Array(fresh);finish(m,new Uint8Array([1,2,3,4]));assert.deepEqual([...(await p).pixels],[3,2,1,255]);});
test('reads a frame allocated after shared Wasm memory grows without refreshing Module views',async()=>{
 const memory=new WebAssembly.Memory({initial:1,maximum:2,shared:true});const stale=memory.buffer;
 const m={HEAPU8:new Uint8Array(stale),HEAP32:new Int32Array(stale)};m.HEAP32[base/4]=10;
 const box=new Mailbox(m,base,200,memory),pending=box.command({op:OP.paint},1,1);
 memory.grow(1);const fresh=new Uint8Array(memory.buffer);fresh.set([10,20,30,0],70000);
 const words=new Int32Array(memory.buffer);words[(base+OFF.result)/4]=70000;words[(base+OFF.length)/4]=4;Atomics.store(words,base/4,3);
 assert.equal(m.HEAPU8.byteLength,65536);assert.deepEqual([...(await pending).pixels],[30,20,10,255]);assert.equal(box.failed,false);
});
test('abort before submission does not change state',async()=>{const {box,m}=fixture();const a=new AbortController();a.abort();await assert.rejects(box.command({op:OP.paint},1,1,a.signal),/disposed/);assert.equal(m.HEAP32[base/4],10);});
test('abort in flight fails instance',async()=>{const {box}=fixture();const a=new AbortController();const p=box.command({op:OP.paint},1,1,a.signal);a.abort();await assert.rejects(p,/disposed/);assert.equal(box.failed,true);});
test('reject impossible mailbox pointers without wraparound',()=>{const {m}=fixture();for(const ptr of [0,-1,1,0x100000000,65530,1.5,NaN])assert.throws(()=>new Mailbox(m,ptr));});
test('non-shared memory rejected',()=>assert.throws(()=>new Mailbox({HEAPU8:new Uint8Array(20000),HEAP32:new Int32Array(5000)},16),/shared/));
test('malformed control JSON fails instance',async()=>{const {box,m}=fixture();const p=box.command({op:OP.control},1,1);finish(m,new TextEncoder().encode('not JSON'));await assert.rejects(p);assert.equal(box.failed,true);});
test('UTF8 URL and key stored without truncation',async()=>{const {box,m}=fixture();const p=box.command({op:OP.key,url:'https://a.test/é',key:'é'},1,1);const read=(off)=>{const s=m.HEAPU8.subarray(base+off);return new TextDecoder().decode(s.subarray(0,s.indexOf(0)));};assert.equal(read(OFF.url),'https://a.test/é');assert.equal(read(OFF.key),'é');finish(m,new Uint8Array(4));await p;});
