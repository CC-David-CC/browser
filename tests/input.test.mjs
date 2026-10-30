import test from 'node:test';
import assert from 'node:assert/strict';
import {bindInput} from '../src/input.mjs';
class Surface extends EventTarget {
  constructor(){super();this.width=400;this.height=800;this.captured=new Set();this.value='';}
  getBoundingClientRect(){return {left:0,top:0,width:400,height:800};}
  focus(){} setPointerCapture(id){this.captured.add(id);} hasPointerCapture(id){return this.captured.has(id);} releasePointerCapture(id){this.captured.delete(id);}
}
function fire(target,type,fields={}){const e=new Event(type,{cancelable:true});for(const [key,value] of Object.entries(fields))Object.defineProperty(e,key,{value});target.dispatchEvent(e);return e;}
function fixture(){const canvas=new Surface(),keyboard=new Surface(),events=[],abort=new AbortController();bindInput(canvas,{notify:(type,data)=>events.push({type,...data})},abort.signal,{keyboard});return {canvas,keyboard,events,abort};}
const pointer=(x,y)=>({pointerType:'touch',pointerId:1,isPrimary:true,button:0,buttons:1,clientX:x,clientY:y,detail:1});
test('touch tap produces a matched mouse click',()=>{const {canvas,events}=fixture();fire(canvas,'pointerdown',pointer(10,20));fire(canvas,'pointerup',{...pointer(10,20),buttons:0});assert.deepEqual(events.map(e=>[e.op,e.evType,e.buttons]),[[1,1,1],[1,2,0]]);});
test('touch drag scrolls without clicking a page link',()=>{const {canvas,events}=fixture();fire(canvas,'pointerdown',pointer(15,200));fire(canvas,'pointermove',pointer(15,170));fire(canvas,'pointerup',{...pointer(15,170),buttons:0});assert.equal(events.length,1);assert.equal(events[0].op,3);assert.equal(events[0].deltaY,30);});
test('keyboard sends composed text and editing keys to Gecko',()=>{const {keyboard,events,abort}=fixture();keyboard.value='é';fire(keyboard,'input',{isComposing:false});assert.deepEqual(events.map(e=>[e.key,e.evType,e.charCode]),[['é',0,233],['é',1,233]]);assert.equal(keyboard.value,'');fire(keyboard,'beforeinput',{inputType:'deleteContentBackward',isComposing:false});assert.deepEqual(events.slice(-2).map(e=>[e.key,e.evType]),[['Backspace',0],['Backspace',1]]);abort.abort();fire(keyboard,'input',{isComposing:false});assert.equal(events.length,4);});
test('desktop mouse events remain immediate',()=>{const {canvas,events}=fixture();const p={pointerType:'mouse',pointerId:2,isPrimary:true,button:0,buttons:1,clientX:20,clientY:30,detail:1};fire(canvas,'pointerdown',p);assert.deepEqual(events.map(e=>e.evType),[1]);fire(canvas,'pointerup',{...p,buttons:0});assert.deepEqual(events.map(e=>e.evType),[1,2]);});
