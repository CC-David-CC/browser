// Protocol facts checked against pinned upstream embed-xul.h/index.ts.
// This is an independent driver of that ABI, not a substitute HTML renderer.
export const OFF = Object.freeze({
  state:0, width:4, height:8, result:12, length:16, url:20,
  op:8212, evType:8216, x:8220, y:8224, button:8228, buttons:8232,
  clicks:8236, modifiers:8240, keyCode:8244, charCode:8248,
  deltaX:8252, deltaY:8256, key:8260, cursor:8324,
});
export const OP = Object.freeze({load:0, mouse:1, key:2, wheel:3, paint:4, control:10});
const ALLOWED = new Set(Object.values(OP));
const encoder = new TextEncoder();
const decoder = new TextDecoder('utf-8', {fatal:true});
const pause = ms => new Promise(r=>setTimeout(r, ms));

// A native -1 reply is completed failure, not an unknown in-flight state.
export class EngineCommandError extends Error { constructor(message){super(message);this.name='EngineCommandError';} }
export class Mailbox {
  constructor(module, pointer, timeoutMs=45000, memory=null) {
    this.module = module;
    if(memory!==null&&(!(memory instanceof WebAssembly.Memory)||!(memory.buffer instanceof SharedArrayBuffer)))throw new Error('Expected shared engine memory.');
    this.memory=memory;this.viewBuffer=null;this.viewBytes=null;this.viewWords=null;
    if(!Number.isInteger(pointer)||pointer<4||pointer>0xffffffff)throw new Error('Invalid mailbox pointer.');
    if(typeof SharedArrayBuffer==='undefined'||!(module.HEAPU8?.buffer instanceof SharedArrayBuffer))throw new Error('Expected shared engine memory.');
    this.pointer = pointer;
    this.timeoutMs = timeoutMs;
    this.active = false;
    this.failed = false;
    this.assertRange(this.pointer, 8328);
    if (this.pointer % 4) throw new Error('Unaligned engine mailbox.');
  }
  refreshViews() {
    if(!this.memory)return;
    // A pthread can grow shared WebAssembly memory without refreshing this
    // worker's Emscripten HEAP views. The old SharedArrayBuffer remains valid
    // but does not cover newly allocated bytes; reacquire from Memory itself.
    const buffer=this.memory.buffer;
    if(buffer!==this.viewBuffer){this.viewBuffer=buffer;this.viewBytes=new Uint8Array(buffer);this.viewWords=new Int32Array(buffer);}
  }
  get bytes() { if(!this.memory)return this.module.HEAPU8;this.refreshViews();return this.viewBytes; }
  get words() { if(!this.memory)return this.module.HEAP32;this.refreshViews();return this.viewWords; }
  assertRange(p,n) {
    if (!Number.isSafeInteger(p) || !Number.isSafeInteger(n) || p < 0 || n < 0 || p+n > this.bytes.byteLength) {
      throw new Error('Engine buffer outside WASM memory.');
    }
  }
  integer(offset,value) {
    if (!Number.isFinite(value)) throw new Error('Non-finite command number.');
    this.words[(this.pointer+offset)>>>2] = value|0;
  }
  string(offset,capacity,text) {
    const b=encoder.encode(text);
    if (b.length >= capacity) throw new Error('Text exceeds command capacity; not truncated.');
    this.bytes.fill(0,this.pointer+offset,this.pointer+offset+capacity);
    this.bytes.set(b,this.pointer+offset);
  }
  async command(c, width, height, signal) {
    if (this.active || this.failed) throw new Error('Mailbox is busy or failed. Reset this window.');
    if (!ALLOWED.has(c.op)) throw new Error('Disallowed engine opcode.');
    if (signal?.aborted) throw new Error('Engine disposed.');
    this.active=true;
    let submitted=false;
    try {
      this.assertRange(this.pointer,8328);
      const prev=Atomics.load(this.words,this.pointer>>>2);
      if (![0,3,10,-1].includes(prev)) throw new Error(`Unexpected mailbox state ${prev}.`);
      for (const k of ['width','height','op','evType','x','y','button','buttons','clicks','modifiers','keyCode','charCode','deltaX','deltaY']) {
        const v = k==='width' ? width : k==='height' ? height : c[k] ?? (k==='buttons' ? -1 : 0);
        this.integer(OFF[k], v);
      }
      this.string(OFF.url,8190,c.url ?? '');
      this.string(OFF.key,64,c.key ?? '');
      Atomics.store(this.words,this.pointer>>>2,1);
      Atomics.notify(this.words,this.pointer>>>2,1);
      submitted=true;
      const end=performance.now()+this.timeoutMs;
      let state;
      do {
        if (signal?.aborted) throw new Error('Engine disposed.');
        state=Atomics.load(this.words,this.pointer>>>2);
        if (state===3 || state===-1) break;
        if (performance.now()>end) throw new Error('Engine command timed out; mailbox cannot be reused. Reset the window.');
        await pause(4); // Yield so Emscripten runtime proxy callbacks can run.
      } while (true);
      if (state===-1) throw new EngineCommandError(`Gecko failed command ${c.op}.`);
      const ptr=this.words[(this.pointer+OFF.result)>>>2]>>>0;
      const len=this.words[(this.pointer+OFF.length)>>>2]>>>0;
      this.assertRange(ptr,len);
      if (c.op===OP.control) {
        if (len>65536) throw new Error('Oversized engine status.');
        // TextDecoder rejects SharedArrayBuffer-backed views in Chrome.
        // Copy the bounded response while the native mailbox is idle.
        return {status:JSON.parse(decoder.decode(this.bytes.slice(ptr,ptr+len)))};
      }
      const expected=width*height*4;
      if (len!==expected || !ptr) throw new Error(`Expected ${expected} BGRA bytes; engine returned ${len}.`);
      // Copy while the mailbox is idle. Never expose the engine's shared heap.
      const pixels=new Uint8ClampedArray(len);
      const src=this.bytes;
      for (let i=0;i<len;i+=4) {
        pixels[i]=src[ptr+i+2]; pixels[i+1]=src[ptr+i+1];
        pixels[i+2]=src[ptr+i]; pixels[i+3]=255;
      }
      return {pixels, width, height, cursor:this.words[(this.pointer+OFF.cursor)>>>2]};
    } catch(e) {
      // Once submitted, uncertain completion must not be patched over by sending
      // another command into the same native mailbox.
      if (submitted && !(e instanceof EngineCommandError)) this.failed=true;
      throw e;
    } finally { this.active=false; }
  }
}
