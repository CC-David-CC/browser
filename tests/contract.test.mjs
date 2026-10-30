// Static source checks only. They do not mount a real DOM or execute Gecko.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
test('single synchronous desktop entrypoint',()=>{const s=read('index.mjs');assert.match(s,/export function mount\(host\)/);assert.doesNotMatch(s,/export async function mount/);assert.equal((s.match(/export /g)||[]).length,1);assert.match(s,/queueMicrotask/);assert.match(s,/return \{element:body,dispose\(/);});
test('host calls use the documented UI and account-file services',()=>{const s=read('index.mjs');assert.deepEqual([...new Set([...s.matchAll(/host\.\w+(?:\.\w+)?/g)].map(m=>m[0]))],['host.ui.make','host.storage','host.browserRelay','host.browserRelay.open','host.storage.pickFile','host.signal','host.storage.mirrorFileContext']);});
test('guest page not injected into outer DOM',()=>{const s=read('index.mjs');assert.doesNotMatch(s,/\.innerHTML\s*=|\.srcdoc\s*=|createElement\(['"]iframe|make\(['"]iframe|eval\s*\(/);assert.match(s,/putImageData/);});
test('build pin matches runtime pin',()=>{const lock=JSON.parse(read('upstream.lock.json'));assert.ok(read('src/policy.mjs').includes(lock.commit));assert.equal(lock.gecko_commit.length,40);});
test('no engine load on import, engine starts in worker',()=>{assert.doesNotMatch(read('index.mjs'),/createGecko\(/);assert.match(read('src/engine-worker.js'),/self\.createGecko\(options\)/);});
test('offline is the default, no public relay hardcoded',()=>{assert.match(read('config.mjs'),/wispURL: null/);assert.doesNotMatch(read('src/engine-worker.js'),/wss:\/\//);});
test('fresh worker does not paint a nonexistent first document',()=>{const s=read('src/engine-worker.js');assert.match(s,/if\(hasDocument\)await native\(\{op:OP.paint\}\)/);assert.match(s,/case 'tick':\{\s+if\(!hasDocument\)return/);});
