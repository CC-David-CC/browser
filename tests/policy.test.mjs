import test from 'node:test';
import assert from 'node:assert/strict';
import {normalizeNavigation as url,relayURL,boundedSize,trustedAssetURL,validateManifest,ENGINE_ABI,UPSTREAM_COMMIT,textError} from '../src/policy.mjs';
const parent='https://desktop.test/apps/browser/engine/manifest.json';
function manifest(){return {schema:1,abi:ENGINE_ABI,upstreamCommit:UPSTREAM_COMMIT,assets:Object.fromEntries(Object.entries({runtime:'gecko.js',wasm:'gecko.wasm',data:'gecko.data',wisp:'wisp-client.mjs'}).map(([k,file])=>[k,{file,bytes:1,sha256:'a'.repeat(64)}]))};}
for(const [input,expected] of [
  ['example.com','https://example.com/'],['example.com:8443?q=1','https://example.com:8443/?q=1'],
  [' [::1]:8080/ ','https://[::1]:8080/'],['http://localhost:8080','http://localhost:8080/'],
  ['about:blank','about:blank'],['https://example.com/a#b','https://example.com/a#b'],
])test('navigation normalization: '+input,()=>assert.equal(url(input),expected));
for(const input of ['',null,'javascript:alert(1)','data:text/html,test','file:///etc/passwd','chrome://settings','about:config','https://user:pass@a.test/','https://a.test/a\nb','https://a.test/space here','https://a.test/'+ 'x'.repeat(8200)])
  test('reject invalid or privileged navigation: '+String(input).slice(0,45),()=>assert.throws(()=>url(input)));
test('network is opt-in',()=>assert.equal(relayURL(null,parent),null));
test('approved relay form',()=>assert.equal(relayURL('wss://relay.test/wisp/',parent),'wss://relay.test/wisp/'));
for(const v of ['ws://relay.test/wisp/','https://relay.test/wisp/','wss://u:p@relay.test/','wss://relay.test/path','wss://relay.test/?token=x','wss://relay.test/#x'])
  test('reject relay: '+v,()=>assert.throws(()=>relayURL(v,parent)));
test('viewport scales as one unit',()=>assert.deepEqual(boundedSize(4000,2000),{width:1920,height:960}));
test('invalid viewport rejected',()=>{for(const v of [0,-1,NaN,Infinity])assert.throws(()=>boundedSize(v,100));});
test('asset resolution is local',()=>assert.equal(trustedAssetURL('gecko.js',parent),'https://desktop.test/apps/browser/engine/gecko.js'));
for(const n of ['../gecko.js','https://bad.test/x','/gecko.js','.hidden','a/b','x?token=1'])
  test('reject artifact path: '+n,()=>assert.throws(()=>trustedAssetURL(n,parent)));
test('recognized manifest accepted',()=>assert.equal(validateManifest(manifest(),parent,parent).runtime.file,'gecko.js'));
for(const [name,change] of [
  ['wrong ABI',m=>m.abi='other'],['wrong pin',m=>m.upstreamCommit='bad'],['missing asset',m=>delete m.assets.data],
  ['bad digest',m=>m.assets.wasm.sha256='x'],['zero size',m=>m.assets.data.bytes=0],
  ['UI bundle substituted',m=>m.assets.runtime.file='index.js'],
])test('reject manifest: '+name,()=>{const m=manifest();change(m);assert.throws(()=>validateManifest(m,parent,parent));});
test('reject cross-origin manifest',()=>assert.throws(()=>validateManifest(manifest(),parent,'https://other.test/worker.js')));
test('errors bounded as text',()=>assert.equal(textError(new Error('x'.repeat(5000))).length,4000));
