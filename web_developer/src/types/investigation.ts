export type Crop = "rice" | "maize";

export interface InvestigationInput {
  crop: Crop;
  region: string;
  observedDate: string;
  growthStage: string;
  affectedPart: string;
  symptoms: string;
  photo: File;
}

export type InvestigationStatus =
  | "ready"
  | "received"
  | "validating"
  | "researching"
  | "reviewing"
  | "needs_input"
  | "completed"
  | "abstained"
  | "failed";

export interface Evidence {
  id: string;
  title: string;
  excerpt: string;
  url?: string;
  location?: string;
}

export interface Hypothesis {
  id: string;
  name: string;
  reasoning: string;
  evidenceIds: string[];
}

export interface ReviewIssue {
  id: string;
  severity: "blocking" | "advisory";
  reason: string;
}

export interface ExecutionEvent {
  id: string;
  timestamp: string;
  node: string;
  summary: string;
}

export interface InvestigationResult {
  id: string;
  photoId?: string | null;
  status: InvestigationStatus;
  summary: string;
  hypotheses: Hypothesis[];
  evidence: Evidence[];
  reviewIssues: ReviewIssue[];
  questions: string[];
  nextAction: string | null;
  limitations: string[];
  events: ExecutionEvent[];
}

export type SubmitInvestigation = (
  input: InvestigationInput,
) => Promise<InvestigationResult>;
