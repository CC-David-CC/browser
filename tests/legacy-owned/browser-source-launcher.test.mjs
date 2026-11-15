import assert from 'node:assert/strict';
import {startBrowserSourcePage} from '../../legacy/backend/assets/desktop/browser-source-launcher.mjs';
const origin='https://ksu.codes',url=origin+'/browser-relay/connection/'+'A'.repeat(43)+'/sources/';
function stub(){const result={closed:false,destination:null,location:{replace(v){result.destination=v}},close(){result.closed=true}};return result;}
let closes=0, notices=[], stopped=0, popup=stub();
let page=startBrowserSourcePage({popup,origin,valid:()=>true,notify:v=>notices.push(v),onStop:()=>stopped++,connect:async()=>({sourceURL:url,close(){closes++}})});
await page.ready;assert.equal(popup.destination,url);page.stop();page.stop();assert.equal(closes,1);assert.equal(stopped,1);
popup=stub();page=startBrowserSourcePage({popup,origin,valid:()=>true,notify:v=>notices.push(v),connect:async()=>({sourceURL:'https://evil.example/sources/',close(){closes++}})});await page.ready;assert.equal(popup.closed,true);assert.equal(popup.destination,null);assert.match(notices.at(-1),/Invalid source page/);assert.equal(closes,2);
let resolve,connected=new Promise(r=>resolve=r);popup=stub();let valid=true;page=startBrowserSourcePage({popup,origin,valid:()=>valid,notify:v=>notices.push(v),connect:()=>connected});valid=false;resolve({sourceURL:url,close(){closes++}});await page.ready;assert.equal(popup.destination,null);assert.equal(closes,3);
let fail;popup=stub();page=startBrowserSourcePage({popup,origin,valid:()=>true,notify:v=>notices.push(v),connect:async({onFailure})=>{fail=onFailure;return {sourceURL:url,close(){closes++}}}});await page.ready;fail();assert.match(notices.at(-1),/disconnected/);assert.equal(closes,4);
console.log('PASS source page lease lifecycle, origin validation, cancellation and failure');
