import {mount} from '../index.mjs';
let counter=0;
// Test sentinel: fixture JS should NOT see this outer JS global.
window.__DESKTOP_SENTINEL__='must-not-be-visible-inside-guest';
function open(){
  const w=document.createElement('section');w.className='window';
  const header=document.createElement('header'),label=document.createElement('span'),close=document.createElement('button'),slot=document.createElement('div');
  slot.className='slot';label.textContent=`Window ${++counter}`;close.textContent='Close';header.append(label,close);w.append(header,slot);
  document.querySelector('#windows').append(w);
  const app=mount({ui:{make(tag,cls){const e=document.createElement(tag);e.className=cls;return e;}}});
  if(app&&typeof app.then==='function')throw new Error('mount returned a Promise.');
  slot.append(app.element);
  close.onclick=()=>{app.dispose();app.dispose();w.remove();};
}
document.querySelector('#open').onclick=open;open();
