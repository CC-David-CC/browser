import test from 'node:test';
import assert from 'node:assert/strict';
import {navigationFeedback} from '../src/navigation-feedback.mjs';
const value=(state,result=0,httpStatus=0)=>({sequence:1,state,result,httpStatus});
test('reports a pending load and a completed HTTP response',()=>{
 assert.equal(navigationFeedback(value(1)),'Loading…');
 assert.equal(navigationFeedback(value(2,0,200)),'Page loaded.');
 assert.equal(navigationFeedback(value(2,0,404)),'The site returned HTTP 404.');
 assert.equal(navigationFeedback(value(2,0,503)),'The site returned HTTP 503.');
});
test('network failure stays general and normal redirect cancellation stays silent',()=>{
 assert.equal(navigationFeedback(value(2,0x804b0014)), 'Could not load the page. Check the address or connection.');
 assert.equal(navigationFeedback(value(2,0x804b0002,200)),null);
 assert.equal(navigationFeedback(value(0)),null);
});
test('rejects malformed and misleading native records',()=>{
 for(const record of [null,{},value(3),value(2,-1),value(2,0,1000),{...value(2),sequence:-1},{...value(2),result:1.5}])assert.throws(()=>navigationFeedback(record));
});
