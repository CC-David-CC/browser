/** Keep a registered Browser source lease alive only while its tab and account remain active. */
export function startBrowserSourcePage({popup,connect,valid,notify,origin,onStop=()=>{}}){
  let relay=null,stopped=false,timer=0;
  const stop=()=>{if(stopped)return;stopped=true;clearInterval(timer);relay?.close();onStop();};
  const alive=()=>!stopped&&!popup.closed&&valid();
  timer=setInterval(()=>{if(!alive())stop();},1000);
  const ready=(async()=>{
    try{
      const opened=await connect({onFailure:()=>{if(alive())notify('Source access disconnected. Open it again.');stop();}});
      if(!alive()){opened.close();stop();return;}
      relay=opened;
      const url=new URL(opened.sourceURL,origin);
      if(url.origin!==origin||!/^\/(?:[A-Za-z0-9_-]+\/)*browser-relay\/connection\/[A-Za-z0-9_-]{43}\/sources\/$/.test(url.pathname)||url.search||url.hash)throw Error('Invalid source page address.');
      popup.location.replace(url.href);
    }catch(error){if(alive()){popup.close();notify('Could not open licenses and source: '+(error?.message||'connection failed.'));}stop();}
  })();
  return {ready,stop};
}
