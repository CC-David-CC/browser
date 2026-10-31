import test from 'node:test';
import assert from 'node:assert/strict';
import {chooseDownloadTarget} from '../src/download-target.mjs';

function fixture(){
 let active=true,valid=true,record=null,folder='/Course',statCalls=0;
 const asked=[];
 const context={
  valid:()=>valid,
  name:n=>{if(!n||n.includes('/'))throw Error('Invalid filename.');return n;},
  path:p=>p,
  files:{stat:async()=>{statCalls++;if(!record)throw Error('File not found.');return {...record};}},
 };
 const args={
  storage:{mirrorFileContext:async()=>context,pickFolder:async()=>folder},
  prompt:async(label,options)=>{asked.push({kind:'prompt',label,options});return 'report.pdf';},
  confirm:async(message,options)=>{asked.push({kind:'confirm',message,options});return true;},
  current:()=>active,
  signal:new AbortController().signal,
  suggested:'report.pdf',
 };
 return {
  args,context,asked,
  setRecord:value=>{record=value;},setFolder:value=>{folder=value;},
  setActive:value=>{active=value;},setValid:value=>{valid=value;},
  statCalls:()=>statCalls,
 };
}

test('new file selects a folder and carries an absent expected version',async()=>{
 const f=fixture();
 assert.deepEqual(await chooseDownloadTarget(f.args),{context:f.context,path:'/Course/report.pdf',expected:null});
 assert.equal(f.asked[0].kind,'prompt');
 assert.equal(f.asked[0].options.title,'Save download to My files');
 assert.equal(f.asked[0].options.value,'report.pdf');
 assert.equal(f.statCalls(),1);
});

test('existing file requires themed confirmation and rechecks its version',async()=>{
 const f=fixture();f.setRecord({version:'v1',status:'synced'});
 assert.deepEqual(await chooseDownloadTarget(f.args),{context:f.context,path:'/Course/report.pdf',expected:'v1'});
 assert.equal(f.statCalls(),2,'the existing target is read again after confirmation');
 const confirmation=f.asked.find(x=>x.kind==='confirm');
 assert.equal(confirmation.message,'Replace /Course/report.pdf?');
 assert.equal(confirmation.options.title,'Replace existing file?');
 assert.equal(confirmation.options.danger,true);
 f.args.confirm=async()=>false;
 assert.equal(await chooseDownloadTarget(f.args),null);
});

test('cancellations and invalid names do not select a download target',async()=>{
 const f=fixture();f.args.prompt=async()=>null;
 assert.equal(await chooseDownloadTarget(f.args),null);
 f.args.prompt=async()=> 'bad/name';
 await assert.rejects(chooseDownloadTarget(f.args),/Invalid filename/);
 f.args.prompt=async()=> 'ok';f.setFolder(null);
 assert.equal(await chooseDownloadTarget(f.args),null);
});

test('a file changed or removed while replacement confirmation is open is protected',async()=>{
 const f=fixture();f.setRecord({version:'v1',status:'synced'});
 f.args.confirm=async()=>{f.setRecord({version:'v2',status:'synced'});return true;};
 await assert.rejects(chooseDownloadTarget(f.args),/file changed while you were deciding/i);
 assert.equal(f.statCalls(),2);

 const removed=fixture();removed.setRecord({version:'v1',status:'synced'});
 removed.args.confirm=async()=>{removed.setRecord(null);return true;};
 await assert.rejects(chooseDownloadTarget(removed.args),/file changed while you were deciding/i);
});

test('conflicts and account changes stop the operation',async()=>{
 const f=fixture();f.setRecord({version:'v2',status:'conflict'});
 await assert.rejects(chooseDownloadTarget(f.args),/Resolve the file conflict/);
 f.setRecord(null);f.args.storage.pickFolder=async()=>{f.setValid(false);return '/';};
 assert.equal(await chooseDownloadTarget(f.args),null);
 f.setValid(true);f.args.storage.pickFolder=async()=>{f.setActive(false);return '/';};
 assert.equal(await chooseDownloadTarget(f.args),null);
});
