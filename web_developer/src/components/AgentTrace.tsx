import { useEffect, useState } from "react";
import { API_BASE_URL } from "../api/investigations";
interface AgentState {
  phase?: string; status: string; iteration: number; max_iterations: number; elapsed_seconds: number; budget_seconds: number;
  finish_reason?: string; missing_evidence: string[]; questions?: string[]; uncertainties?: string[];
  tool_history: {step:number; tool:string; reason:string; arguments:Record<string,unknown>; status:string; summary:string; result?:{new_source_ids?:string[];[key:string]:unknown}}[];
  judge_decisions: {action:string;reason:string}[];
  hypothesis_history: {round:number;proposal:{summary:string;candidates:{id:string;name:string}[]};review:{review_summary:string};action:string}[];
}
export default function AgentTrace({id, revision}:{id:string;revision:number}) {
  const [state,setState]=useState<AgentState|null>(null);
  const [error,setError]=useState("");
  useEffect(()=>{
    const controller=new AbortController();
    fetch(`${API_BASE_URL}/api/investigations/${encodeURIComponent(id)}/agent`,{signal:controller.signal})
      .then(async response=>{if(response.status===404)return null;if(!response.ok)throw Error("Agent trace unavailable.");return response.json();})
      .then((data:AgentState|null)=>{setState(data);setError("");})
      .catch(e=>{if(!controller.signal.aborted)setError(e instanceof Error?e.message:"Trace unavailable.");});
    return()=>controller.abort();
  },[id,revision]);
  async function download() {
    const response=await fetch(`${API_BASE_URL}/api/investigations/${encodeURIComponent(id)}/agent`);
    if(!response.ok){setError("Report download failed.");return;}
    const data=await response.json();const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:"application/json"}));
    const anchor=document.createElement("a");anchor.href=url;anchor.download=`agrisleuth-agent-${id}.json`;anchor.click();URL.revokeObjectURL(url);
  }
  if(error)return <p role="status">{error}</p>;
  if(!state)return null;
  const unresolved = state.status === "investigating" ? state.missing_evidence : [...(state.questions ?? []), ...(state.uncertainties ?? [])];
  return <section className="panel" aria-labelledby="agent-trace-title"><p className="eyebrow">AUTONOMOUS INVESTIGATION</p><h2 id="agent-trace-title">Agent decisions &amp; tool execution</h2>
    <p>{state.status} · {state.phase ?? "agent"} · Action {state.iteration}/{state.max_iterations} · {state.elapsed_seconds}s / {state.budget_seconds}s budget</p>
    <p>Decision explanations below describe selected actions, not private model reasoning.</p>
    <ol className="result-list">{state.tool_history.map((step,i)=><li key={i}><strong>{step.tool} · {step.status}</strong><p>Selected because: {step.reason}</p><p>{step.summary}</p>
      {!!step.result?.new_source_ids?.length&&<small>New sources: {step.result.new_source_ids.join(", ")}</small>}
      {step.result&&<details><summary>Tool result summary</summary><pre style={{whiteSpace:"pre-wrap",overflowWrap:"anywhere"}}>{JSON.stringify(step.result,null,2)}</pre></details>}
      <details><summary>Validated tool inputs</summary><pre style={{whiteSpace:"pre-wrap",overflowWrap:"anywhere"}}>{JSON.stringify(step.arguments,null,2)}</pre></details>
    </li>)}</ol>
    {state.hypothesis_history.map((round,i)=><details key={i}><summary>Hypothesis revision {round.round} · {round.action}</summary><p>{round.proposal.summary}</p><p>Candidates: {round.proposal.candidates.map(c=>c.name).join(", ")}</p><p>Critic: {round.review.review_summary}</p></details>)}
    {state.judge_decisions.map((decision,i)=><p key={i}>Judge: {decision.action} — {decision.reason}</p>)}
    {!!unresolved.length&&<><h3>Unresolved evidence</h3><ul>{unresolved.map((text,i)=><li key={i}>{text}</li>)}</ul></>}
    {state.finish_reason&&<p><strong>Stopped because:</strong> {state.finish_reason}</p>}
    <button type="button" onClick={()=>void download().catch(()=>setError("Report download failed."))}>Download agent report JSON</button>
  </section>;
}
