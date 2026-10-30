function modifiers(e){return (e.altKey?1:0)|(e.ctrlKey?2:0)|(e.shiftKey?4:0)|(e.metaKey?8:0);}
export function bindInput(canvas, session, signal, {keyboard=null}={}) {
  const keys=new Map();let pendingMove=null,raf=0,touch=null;
  const send=p=>session.notify('input',p);
  const xy=e=>{
    const r=canvas.getBoundingClientRect();
    return {x:Math.round((e.clientX-r.left)*canvas.width/Math.max(r.width,1)),
            y:Math.round((e.clientY-r.top)*canvas.height/Math.max(r.height,1))};
  };
  const mouse=(e,evType)=>({op:1,evType,...xy(e),button:e.button,buttons:e.buttons,clicks:e.detail||1,modifiers:modifiers(e)});
  const listen=(t,f,options={})=>canvas.addEventListener(t,f,{...options,signal});
  function flushMove(){if(raf)cancelAnimationFrame(raf);raf=0;if(pendingMove){send(pendingMove);pendingMove=null;}}
  listen('pointermove',e=>{
    if(e.pointerType==='touch'){
      if(!touch||e.pointerId!==touch.id)return;
      const dx=e.clientX-touch.lastX,dy=e.clientY-touch.lastY;
      if(!touch.moved&&Math.hypot(e.clientX-touch.x,e.clientY-touch.y)>=8)touch.moved=true;
      if(touch.moved){
        e.preventDefault();const r=canvas.getBoundingClientRect();
        send({op:3,...xy(e),deltaX:Math.round(-dx*canvas.width/Math.max(r.width,1)),deltaY:Math.round(-dy*canvas.height/Math.max(r.height,1)),modifiers:0});
      }
      touch.lastX=e.clientX;touch.lastY=e.clientY;return;
    }
    pendingMove=mouse(e,0);if(!raf)raf=requestAnimationFrame(flushMove);
  });
  listen('pointerdown',e=>{
    if(e.isPrimary===false)return;
    e.preventDefault();canvas.focus();flushMove();canvas.setPointerCapture(e.pointerId);
    if(e.pointerType==='touch'){touch={id:e.pointerId,x:e.clientX,y:e.clientY,lastX:e.clientX,lastY:e.clientY,moved:false};return;}
    send(mouse(e,1));
  });
  listen('pointerup',e=>{
    if(e.pointerType==='touch'){
      if(!touch||touch.id!==e.pointerId)return;
      if(!touch.moved){const m=mouse(e,1);send({...m,button:0,buttons:1});send({...m,evType:2,button:0,buttons:0});}
      touch=null;
    }else{flushMove();send(mouse(e,2));}
    if(canvas.hasPointerCapture(e.pointerId))canvas.releasePointerCapture(e.pointerId);
  });
  listen('pointercancel',e=>{if(e.pointerType==='touch'){touch=null;return;}flushMove();send({...mouse(e,2),buttons:0});});
  listen('contextmenu',e=>{e.preventDefault();send(mouse(e,3));});
  listen('wheel',e=>{
    e.preventDefault();flushMove();
    const factor=e.deltaMode===1?16:e.deltaMode===2?canvas.height:1;
    send({op:3,...xy(e),deltaX:Math.round(e.deltaX*factor),deltaY:Math.round(e.deltaY*factor),modifiers:modifiers(e)});
  },{passive:false});
  const key=(e,evType)=>({op:2,evType,key:e.key,keyCode:e.keyCode,
    charCode:[...e.key].length===1?e.key.codePointAt(0):0,modifiers:modifiers(e)});
  listen('keydown',e=>{
    if(e.isComposing)return;
    e.preventDefault();e.stopPropagation();
    const k=key(e,0);keys.set(e.code,k);send(k);
  });
  listen('keyup',e=>{e.preventDefault();e.stopPropagation();keys.delete(e.code);send(key(e,1));});
  listen('blur',()=>{for(const k of keys.values())send({...k,evType:1,modifiers:0});keys.clear();});
  if(keyboard){
    const special=(name,code)=>{const event={op:2,key:name,keyCode:code,charCode:0,modifiers:0};send({...event,evType:0});send({...event,evType:1});};
    keyboard.addEventListener('keydown',e=>{
      if(e.isComposing)return;
      if(e.key==='Backspace'||e.key==='Enter'||e.key==='Tab'||e.key==='Escape'||e.key.startsWith('Arrow')){
        e.preventDefault();e.stopPropagation();special(e.key,e.keyCode);
      }
    },{signal});
    keyboard.addEventListener('beforeinput',e=>{
      if(e.isComposing)return;
      if(e.inputType==='deleteContentBackward'){e.preventDefault();special('Backspace',8);}
      else if(e.inputType==='insertLineBreak'||e.inputType==='insertParagraph'){e.preventDefault();special('Enter',13);}
    },{signal});
    keyboard.addEventListener('input',e=>{
      if(e.isComposing)return;
      for(const character of keyboard.value){const event={op:2,key:character,keyCode:0,charCode:character.codePointAt(0),modifiers:0};send({...event,evType:0});send({...event,evType:1});}
      keyboard.value='';
    },{signal});
  }
  signal.addEventListener('abort',()=>{if(raf)cancelAnimationFrame(raf);keys.clear();touch=null;},{once:true});
}
