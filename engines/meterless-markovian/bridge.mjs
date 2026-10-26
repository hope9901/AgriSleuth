import { createInterface } from "node:readline";
import { Markovian } from "./src/index.ts";
const lines = createInterface({ input: process.stdin })[Symbol.asyncIterator]();
const receive = async () => { const item=await lines.next(); if(item.done) throw Error("Host disconnected"); return JSON.parse(item.value); };
const config = await receive();
const engine = new Markovian({chunkConfig:{chunkSize:4000,maxChunks:config.maxChunks ?? 3,carryoverTokens:512,overlapTokens:0}});
const run = await engine.run({goal:config.goal,mode:"RESEARCH",reflect:false,stepFn:async ({step,carryover,prompt})=>{
  process.stdout.write(JSON.stringify({type:"step",step:step+1,carryover,prompt})+"\n");
  const reply = await receive();
  if(reply.error) throw Error(reply.error);
  return {content:reply.content};
}});
process.stdout.write(JSON.stringify({type:"done",run})+"\n");
process.exit(0);
