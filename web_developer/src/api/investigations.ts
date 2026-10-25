import type {
  InvestigationInput,
  InvestigationResult,
} from "../types/investigation";

export const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000"
).replace(/\/$/, "");

export async function submitInvestigation(
  input: InvestigationInput,
): Promise<InvestigationResult> {
  const formData = new FormData();

  formData.append("crop", input.crop);
  formData.append("region", input.region);
  formData.append("observed_date", input.observedDate);
  formData.append("growth_stage", input.growthStage);
  formData.append("affected_part", input.affectedPart);
  formData.append("symptoms", input.symptoms);
  formData.append("photo", input.photo);

  const response = await fetch(`${API_BASE_URL}/api/investigations`, {
    method: "POST",
    body: formData,
    signal: AbortSignal.timeout(30_000),
  });

  // Do not set Content-Type manually when sending FormData.
  if (!response.ok) {
    let message = `Investigation submission failed: HTTP ${response.status}`;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") message = body.detail;
    } catch { /* Preserve the HTTP error for non-JSON responses. */ }
    throw new Error(message);
  }

  const result: InvestigationResult = await response.json();
  return result;
}

export async function getInvestigation(id: string): Promise<InvestigationResult> {
  const response = await fetch(`${API_BASE_URL}/api/investigations/${encodeURIComponent(id)}`, {
    signal: AbortSignal.timeout(10_000),
  });
  if (!response.ok) throw new Error(`Investigation lookup failed: HTTP ${response.status}`);
  return response.json();
}

export function getPhotoUrl(photoId: string): string {
  return `${API_BASE_URL}/api/photos/${encodeURIComponent(photoId)}`;
}
