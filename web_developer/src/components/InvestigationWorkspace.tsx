import { useState } from "react";

import ObservationForm from "./ObservationForm";
import InvestigationResults from "./InvestigationResults";

import type {
  InvestigationInput,
  InvestigationResult,
  SubmitInvestigation,
} from "../types/investigation";

interface InvestigationWorkspaceProps {
  onSubmit: SubmitInvestigation;
}

export default function InvestigationWorkspace({
  onSubmit,
}: InvestigationWorkspaceProps) {
  const [result, setResult] = useState<InvestigationResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(input: InvestigationInput) {
    setBusy(true);
    setError("");
    setResult(null);

    try {
      const response = await onSubmit(input);
      setResult(response);
    } catch {
      setError(
        "The investigation could not be submitted. Please try again.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      {error && (
        <p className="error-banner" role="alert">
          {error}
        </p>
      )}

      <div className="workspace-grid">
        <ObservationForm busy={busy} onSubmit={handleSubmit} />
        <InvestigationResults result={result} busy={busy} />
      </div>
    </>
  );
}
