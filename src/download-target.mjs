// Select an account-bound target before consuming a temporary download.
export async function chooseDownloadTarget({storage,prompt,confirm,current,signal,suggested}){
 if(!storage?.mirrorFileContext)throw Error('Sign in to save downloads to My files.');
 const requested=prompt('Save download in My files as:',suggested);if(requested===null||!current())return null;
 const context=await storage.mirrorFileContext();if(!current()||!context.valid())return null;
 const name=context.name(requested);
 const folder=typeof storage.pickFolder==='function'?await storage.pickFolder({signal}):'/';
 if(folder===null||!current()||!context.valid())return null;
 const path=context.path((folder==='/'?'':folder)+'/'+name);let expected=null;
 try{const old=await context.files.stat(path);if(!current()||!context.valid())return null;if(old.status==='conflict')throw Error('Resolve the file conflict in Files first.');if(!confirm('Replace '+path+'?'))return null;expected=old.version;}
 catch(error){if(error.message!=='File not found.')throw error;}
 if(!current()||!context.valid())return null;
 return {context,path,expected};
}
