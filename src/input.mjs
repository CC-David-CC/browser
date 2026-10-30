function modifiers(e){return (e.altKey?1:0)|(e.ctrlKey?2:0)|(e.shiftKey?4:0)|(e.metaKey?8:0);}
export function bindInput(canvas, session, signal) {
  const keys=new Map(); let pendingMove=null,raf=0;
  const send=p=>session.notify('input',p);
  const xy=e=>{
    const r=canvas.getBoundingClientRect();
    return {x:Math.round((e.clientX-r.left)*canvas.width/Math.max(r.width,1)),
            y:Math.round((e.clientY-r.top)*canvas.height/Math.max(r.height,1))};
  };
  const mouse=(e,evType)=>({op:1,evType,...xy(e),button:e.button,buttons:e.buttons,clicks:e.detail||1,modifiers:modifiers(e)});
  const listen=(t,f,options={})=>canvas.addEventListener(t,f,{...options,signal});
  function flushMove(){if(raf)cancelAnimationFrame(raf);raf=0;if(pendingMove){send(pendingMove);pendingMove=null;}}
  listen('pointermove',e=>{pendingMove=mouse(e,0);if(!raf)raf=requestAnimationFrame(flushMove);});
  listen('pointerdown',e=>{
    if(e.isPrimary===false)return;
    e.preventDefault();canvas.focus();flushMove();
    canvas.setPointerCapture(e.pointerId);send(mouse(e,1));
  });
  listen('pointerup',e=>{flushMove();send(mouse(e,2));if(canvas.hasPointerCapture(e.pointerId))canvas.releasePointerCapture(e.pointerId);});
  listen('pointercancel',e=>{flushMove();send({...mouse(e,2),buttons:0});});
  listen('contextmenu',e=>{e.preventDefault();send(mouse(e,3));});
  listen('wheel',e=>{
    e.preventDefault();flushMove();
    const factor=e.deltaMode===1?16:e.deltaMode===2?canvas.height:1;
    send({op:3,...xy(e),deltaX:Math.round(e.deltaX*factor),deltaY:Math.round(e.deltaY*factor),modifiers:modifiers(e)});
  },{passive:false});
  const key=(e,evType)=>({op:2,evType,key:e.key,keyCode:e.keyCode,
    charCode:[...e.key].length===1?e.key.codePointAt(0):0,modifiers:modifiers(e)});
  listen('keydown',e=>{
    if(e.isComposing)return; // IME/text-input support is an explicit remaining gate.
    e.preventDefault();e.stopPropagation();
    const k=key(e,0);keys.set(e.code,k);send(k);
  });
  listen('keyup',e=>{e.preventDefault();e.stopPropagation();keys.delete(e.code);send(key(e,1));});
  listen('blur',()=>{for(const k of keys.values())send({...k,evType:1,modifiers:0});keys.clear();});
  signal.addEventListener('abort',()=>{if(raf)cancelAnimationFrame(raf);keys.clear();},{once:true});
}
