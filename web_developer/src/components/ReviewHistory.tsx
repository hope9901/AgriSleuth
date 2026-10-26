import { useEffect, useState } from "react";
import { API_BASE_URL } from "../api/investigations";
interface History {
  rounds: {round: number; action: string; reason: string; proposal: {summary: string}; review: {review_summary: string; scenario_id?: string; scenario_match?: string; scenario_reason?: string} | null; evidence_ids: string[]}[];
  engines: {status: string; tokenLabel: string; totalTokensUsed: number; durationMs: number; chunkConfig: {maxChunks: number; carryoverTokens: number}; chunks: {id: number; carryover: string; content: string}[]}[];
}
export default function ReviewHistory({ id, status }: { id: string; status: string }) {
  const [history, setHistory] = useState<History | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    fetch(`${API_BASE_URL}/api/investigations/${encodeURIComponent(id)}/history`, { signal: controller.signal })
      .then(async response => { if (!response.ok) throw Error("Review history unavailable."); return response.json(); })
      .then((data: History) => { setHistory(data); setError(""); })
      .catch(e => { if (!controller.signal.aborted) setError(e instanceof Error ? e.message : "History unavailable."); });
    return () => controller.abort();
  }, [id, status]);
  if (error) return <p role="status">{error}</p>;
  if (!history?.rounds.length && !history?.engines.length) return null;
  return <section className="panel"><h2>Critic &amp; Meterless run history</h2>
    {history.rounds.map((round,i) => <details key={i}><summary>Round {round.round}: {round.action}</summary>
      <p>{round.proposal.summary}</p><p>Critic: {round.review?.review_summary ?? "No supported candidates to review."}</p>
      {round.review?.scenario_id && <p>Critic scenario: {round.review.scenario_id} · {round.review.scenario_match}. {round.review.scenario_reason}</p>}
      <p>Judge: {round.reason}</p><small>Evidence: {round.evidence_ids.join(", ")}</small>
    </details>)}
    {history.engines.map((engine,i) => <details key={i}><summary>Meterless Markovian: {engine.status} · {engine.chunks.length} chunks</summary>
      <p>Budget: {engine.chunkConfig.maxChunks} chunks; carryover {engine.chunkConfig.carryoverTokens} estimated tokens. Runtime: {(engine.durationMs / 1000).toFixed(1)} s.</p>
      <p>Output tokens: {engine.totalTokensUsed} ({engine.tokenLabel}; not a measured cost or savings claim).</p>
      {engine.chunks.map(chunk => <details key={chunk.id}><summary>Chunk {chunk.id} checkpoint</summary><pre style={{whiteSpace:"pre-wrap",overflowWrap:"anywhere"}}>{chunk.carryover || "Initial chunk: no previous checkpoint."}</pre><p>{chunk.content}</p></details>)}
    </details>)}
  </section>;
}
