// Per-window bridge from completed Gecko downloads to explicit desktop saves.
// Gecko's privileged transfer hook writes completion markers in a separate
// guest-only directory after its file saver closes the target.
export const MAX_DOWNLOAD_BYTES=128*1024*1024;
const FILE_ROOT='/browser-downloads/',MARKER_ROOT='/browser-download-markers/';
const uuidPattern=/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const markerPattern=/^\{[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\}\.json$/i;
const validName=name=>typeof name==='string'&&name.length>0&&name.length<=255&&name!=='.'&&name!=='..'&&!/[\/\\\x00-\x1f\x7f]/.test(name);
const regular=mode=>Number.isInteger(mode)&&(mode&0xf000)===0x8000;

export class GuestDownloads {
  constructor(fs,emit){this.fs=fs;this.emit=emit;this.pending=new Map();this.active=new Map();this.badMarkers=new Map();}
  cleanup(id,name){
    if(!uuidPattern.test(id)||!validName(name))return;
    try{this.fs.unlink(FILE_ROOT+id+'/'+name)}catch{}
    try{this.fs.rmdir(FILE_ROOT+id)}catch{}
  }
  scan(now=Date.now()){
    const markers=[];
    for(const marker of this.fs.readdir(MARKER_ROOT)){
      if(!markerPattern.test(marker))continue;
      const markerPath=MARKER_ROOT+marker;let data;
      try{
        const stat=this.fs.stat(markerPath);
        if(!regular(stat.mode)||stat.size>4096)throw Error('Invalid download marker');
        data=JSON.parse(this.fs.readFile(markerPath,{encoding:'utf8'}));
      }catch(error){
        // A marker may be observed while the guest is still writing it.
        const first=this.badMarkers.get(marker)??now;this.badMarkers.set(marker,first);
        if(now-first<5000)continue;
        this.badMarkers.delete(marker);try{this.fs.unlink(markerPath)}catch{}
        this.emit('download-error',{message:'Could not read the completed download.'});continue;
      }
      this.badMarkers.delete(marker);this.fs.unlink(markerPath);markers.push(data);
    }
    // Very small transfers can finish between scans. Show starts before their
    // completions even when both markers were observed together.
    markers.sort((a,b)=>Number(b?.phase==='start')-Number(a?.phase==='start'));
    for(const data of markers){
      if(data?.version!==1){this.emit('download-error',{message:'Invalid download notification.'});continue;}
      const {id,name}=data,valid=typeof id==='string'&&uuidPattern.test(id)&&validName(name);
      if(data.phase==='start'){
        if(!valid){this.emit('download-error',{message:'The download filename is not supported.'});continue;}
        if(!this.active.has(id)&&!this.pending.has(id)){
          this.active.set(id,name);this.emit('download-start',{id,name});
        }
        continue;
      }
      if((data.phase!==undefined&&data.phase!=='complete')||typeof data.success!=='boolean'){
        this.emit('download-error',{message:'Invalid download completion.'});continue;
      }
      const message=data.reason==='queue'?'Save or discard a waiting download before starting another.':data.reason==='size'?'This download exceeds the 128 MiB limit.':'The download did not finish.';
      if(data.success!==true){
        if(valid){
          // Duplicate late failure notifications cannot remove a completed file.
          if(this.pending.has(id))continue;
          this.active.delete(id);this.cleanup(id,name);
        }
        this.emit('download-error',{message,...(valid?{id}: {})});continue;
      }
      if(!valid){this.emit('download-error',{message:'The download filename is not supported.'});continue;}
      if(this.active.has(id)&&this.active.get(id)!==name){this.emit('download-error',{id,message:'Invalid download completion.'});continue;}
      this.active.delete(id);
      const file=FILE_ROOT+id+'/'+name;
      try{
        const stat=this.fs.stat(file);
        if(!regular(stat.mode)||!Number.isSafeInteger(stat.size)||stat.size<0||stat.size>MAX_DOWNLOAD_BYTES){
          this.cleanup(id,name);throw Error('The download exceeds the 128 MiB limit or is not a regular file.');
        }
        if(this.pending.has(id))continue;
        if(this.pending.size>=3){this.cleanup(id,name);throw Error('Too many downloads are waiting to be saved.');}
        this.pending.set(id,{name,file,size:stat.size});this.emit('download-ready',{id,name,size:stat.size});
      }catch(error){this.emit('download-error',{id,message:String(error?.message||error)});}
    }
  }
  read(id){
    const item=this.pending.get(id);if(!item)throw Error('Download is no longer available.');
    const stat=this.fs.stat(item.file);
    if(!regular(stat.mode)||stat.size!==item.size||stat.size>MAX_DOWNLOAD_BYTES)throw Error('Download changed before saving.');
    const data=this.fs.readFile(item.file);
    if(!(data instanceof Uint8Array)||data.byteLength!==item.size)throw Error('Download size changed.');
    return data;
  }
  discard(id){
    const item=this.pending.get(id);if(!item)throw Error('Download is no longer available.');
    this.fs.unlink(item.file);this.pending.delete(id);
    try{this.fs.rmdir(FILE_ROOT+id)}catch{}
  }
}
