// Select an account-bound target before consuming a temporary download.
export async function chooseDownloadTarget({storage,prompt,confirm,current,signal,suggested}){
 if(!storage?.mirrorFileContext)throw Error('Sign in to save downloads to My files.');
 const requested=await prompt('File name',{
  title:'Save download to My files',value:suggested,confirmLabel:'Choose file',cancelLabel:'Cancel',signal,
 });if(requested===null||!current())return null;
 const context=await storage.mirrorFileContext();if(!current()||!context.valid())return null;
 const name=context.name(requested);
 const folder=typeof storage.pickFolder==='function'?await storage.pickFolder({signal}):'/';
 if(folder===null||!current()||!context.valid())return null;
 const path=context.path((folder==='/'?'':folder)+'/'+name);let expected=null,old=null;
 try{old=await context.files.stat(path);}
 catch(error){if(error.message!=='File not found.')throw error;}
 if(!current()||!context.valid())return null;
 if(old){
  if(old.status==='conflict')throw Error('Resolve the file conflict in Files first.');
  const replace=await confirm('Replace '+path+'?',{
   title:'Replace existing file?',confirmLabel:'Replace file',cancelLabel:'Keep existing',danger:true,signal,
  });
  if(!replace||!current()||!context.valid())return null;
  let latest;
  try{latest=await context.files.stat(path);}
  catch(error){if(error.message==='File not found.')throw Error('The file changed while you were deciding. Review it in Files and try again.');throw error;}
  if(!current()||!context.valid())return null;
  if(latest.status==='conflict')throw Error('Resolve the file conflict in Files first.');
  if(latest.version!==old.version)throw Error('The file changed while you were deciding. Review it in Files and try again.');
  expected=latest.version;
 }
 if(!current()||!context.valid())return null;
 return {context,path,expected};
}
