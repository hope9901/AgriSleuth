import { useEffect, useState } from "react";
import ObservationForm from "./ObservationForm";
import InvestigationResults from "./InvestigationResults";
import { getInvestigation, startInvestigation, addObservations } from "../api/investigations";
import type { InvestigationInput, InvestigationResult, SubmitInvestigation } from "../types/investigation";

export default function InvestigationWorkspace({ onSubmit }: { onSubmit: SubmitInvestigation }) {
  const [result, setResult] = useState<InvestigationResult | null>(null);
  const [submittedRegion, setSubmittedRegion] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [followup, setFollowup] = useState("");
  const active = result?.status === "researching" || result?.status === "reviewing";
  const id = result?.id;
  useEffect(() => {
    if (!active || !id) return;
    let disposed = false;
    let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      try {
        const next = await getInvestigation(id);
        if (disposed) return;
        setResult(next); setError("");
        if (next.status === "researching" || next.status === "reviewing") timer = setTimeout(() => void poll(), 2000);
      } catch (e) {
        if (disposed) return;
        setError(e instanceof Error ? e.message : "Unable to refresh investigation.");
        timer = setTimeout(() => void poll(), 5000);
      }
    };
    timer = setTimeout(() => void poll(), 1000);
    return () => { disposed = true; clearTimeout(timer); };
  }, [active, id]);

  useEffect(() => {
    const requested = new URLSearchParams(window.location.search).get("investigation");
    if (!requested || !/^[0-9a-f-]{36}$/i.test(requested)) return;
    let disposed = false;
    getInvestigation(requested).then(next => { if (!disposed) setResult(next); })
      .catch(e => { if (!disposed) setError(e instanceof Error ? e.message : "Saved investigation unavailable."); });
    return () => { disposed = true; };
  }, []);

  async function handleSubmit(input: InvestigationInput) {
    setBusy(true); setError(""); setResult(null);
    try { const next = await onSubmit(input); setSubmittedRegion(input.region); setResult(next); }
    catch (e) { setError(e instanceof Error ? e.message : "Submission failed."); }
    finally { setBusy(false); }
  }
  async function run() {
    if (!result) return;
    setBusy(true); setError("");
    try { await startInvestigation(result.id); setResult({ ...result, status: "researching", summary: "Searching source evidence through Zetaris…" }); }
    catch (e) { setError(e instanceof Error ? e.message : "Unable to start investigation."); }
    finally { setBusy(false); }
  }
  async function respond() {
    if (!result) return;
    setBusy(true); setError("");
    try { setResult(await addObservations(result.id, followup)); setFollowup(""); }
    catch (e) { setError(e instanceof Error ? e.message : "Unable to save observations."); }
    finally { setBusy(false); }
  }
  return <>
    {new URLSearchParams(window.location.search).get("demo") === "1" && <p className="boundary-note">Recorded software demonstration. Inputs are constructed examples, not labeled clinical validation. All displayed results and actions come from saved backend runs.</p>}
    {error && <p className="error-banner" role="alert">{error}</p>}
    {result && <section className="panel" aria-label="Investigation controls">
      <p>Optional: retrieve weather evidence below before starting. Analysis uses your symptom description and attempts tentative image observations. Review visual findings in execution history.</p>
      <button type="button" onClick={() => void run()} disabled={busy || active || result.status === "needs_input"}>
        {active ? "Investigation running…" : result.status === "ready" ? "Start evidence investigation" : "Run investigation again"}
      </button>
      {(result.status === "needs_input" || result.status === "needs_more_evidence" || result.status === "abstained") && <div>
        <label htmlFor="followup">Additional symptom observations</label>
        <textarea id="followup" value={followup} maxLength={3000} onChange={e => setFollowup(e.target.value)} />
        <button type="button" disabled={busy || !followup.trim()} onClick={() => void respond()}>Save additional observations</button>
      </div>}
    </section>}
    <div className="workspace-grid">
      <ObservationForm busy={busy || active} onSubmit={handleSubmit} />
      <InvestigationResults result={result} busy={busy} region={submittedRegion} />
    </div>
  </>;
}
