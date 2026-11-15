import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {DOWNLOAD_RESOURCES} from "../../src/download-resources.mjs";
const root=new URL("../../",import.meta.url),hash=b=>createHash('sha256').update(b).digest('hex');
test('download modules are pinned, declared assets from the exact Gecko revision',async()=>{
 const source=JSON.parse(await readFile(new URL('engine-support/SOURCES.json',root))),app=JSON.parse(await readFile(new URL('app.json',root))),lock=JSON.parse(await readFile(new URL('upstream.lock.json',root)));
 assert.equal(source.geckoCommit,lock.gecko_commit);assert.equal(DOWNLOAD_RESOURCES.length,12);assert.deepEqual(Object.keys(source.files).sort(),DOWNLOAD_RESOURCES.map(x=>x.name).sort());
 for(const item of DOWNLOAD_RESOURCES){const metadata=source.files[item.name],raw=await readFile(new URL('engine-support/'+item.name,root));assert.ok(app.assets.includes('engine-support/'+item.name));assert.equal(raw.length,item.bytes);assert.equal(hash(raw),item.sha256);assert.equal(hash(raw),metadata.packagedSHA256);assert.equal(metadata.modified,['HelperAppDlg.sys.mjs','DownloadLegacy.sys.mjs'].includes(item.name));if(!metadata.modified)assert.equal(metadata.upstreamSHA256,metadata.packagedSHA256)}
 assert.ok(app.assets.includes('engine-support/SOURCES.json'));
});
