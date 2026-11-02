import assert from 'node:assert/strict';
import { responseError, RuntimeApiError } from '../web_developer/src/api/errors.ts';

const error = await responseError(new Response(JSON.stringify({error:{message:'Server reason\nSeat Paint',code:'mesh_level_unavailable'},meterless:{fix:['Seat Paint'],chat_carrier:false}}),{status:409}), 'Fallback');
assert.ok(error instanceof RuntimeApiError);
assert.equal(error.message,'Server reason\nSeat Paint');
assert.equal(error.code,'mesh_level_unavailable');
assert.equal(error.status,409);
assert.deepEqual(error.fix,['Seat Paint']);
assert.equal(error.chatCarrier,false);
const legacy=await responseError(new Response(JSON.stringify({detail:'Legacy reason'}),{status:503}),'Fallback');
assert.equal(legacy.message,'Legacy reason');
const plain=await responseError(new Response('Unavailable',{status:503}),'Fallback');
assert.equal(plain.message,'Fallback');
const nested=await responseError(new Response(JSON.stringify({error:{message:'Reason',code:'class_no_route',meterless:{fix:[],chat_carrier:true}}}),{status:409}),'Fallback');
assert.equal(nested.chatCarrier,true);
assert.equal(nested.code,'class_no_route');
console.log('PASS web error message, code, status, fix and chatCarrier; legacy/non-JSON/nested metadata');
