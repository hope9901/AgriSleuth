import { API_BASE_URL } from "./investigations";
import type { Crop } from "../types/investigation";

export interface ReviewRequest {
  crop: Crop;
  observations: string;
  candidates: { id: string; name: string; claim: string; evidence_ids: string[] }[];
  evidence: { disease_id?: string | null; disease_name?: string | null; id: string; text: string; source: string; location: string }[];
  weather_summary?: string;
  review_round?: number;
}

export interface CriticIssue {
  code: "UNSUPPORTED_CLAIM" | "OBSERVATION_MISMATCH" | "MISSING_DIFFERENTIAL"
    | "WEATHER_CONTEXT_GAP" | "OVERCONFIDENT_CONCLUSION";
  severity: "blocking" | "advisory";
  candidate_id: string | null;
  reason: string;
  evidence_ids: string[];
  suggested_action: "retrieve_evidence" | "request_user_input" | "revise_conclusion";
  requested_information: string;
}

export interface ReviewResponse {
  review: { issues: CriticIssue[]; limitations: string[]; review_summary: string; scenario_id?: string; scenario_match?: string; scenario_reason?: string } | null;
  action: "finalize" | "finalize_with_limitations" | "request_user_input"
    | "retrieve_evidence" | "revise_conclusion" | "abstain";
  reason: string;
  review_round: number;
  trace: string[];
}

// For the separate review endpoint; intake does not automatically invoke this.
export async function submitReview(input: ReviewRequest): Promise<ReviewResponse> {
  const response = await fetch(`${API_BASE_URL}/api/reviews`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
    signal: AbortSignal.timeout(190_000),
  });
  if (!response.ok) {
    let message = `Critic review failed: HTTP ${response.status}`;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") message = body.detail;
    } catch { /* Preserve status for non-JSON responses. */ }
    throw new Error(message);
  }
  return response.json();
}
