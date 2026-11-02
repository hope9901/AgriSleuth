export class RuntimeApiError extends Error {
  readonly code: string | null;
  readonly status: number;
  readonly fix: string[];
  readonly chatCarrier: boolean | null;

  constructor(message: string, status: number, code: string | null, fix: string[], chatCarrier: boolean | null) {
    super(message);
    this.name = "RuntimeApiError";
    this.status = status;
    this.code = code;
    this.fix = fix;
    this.chatCarrier = chatCarrier;
  }
}

export async function responseError(response: Response, fallback: string): Promise<RuntimeApiError> {
  const body = await response.json().catch(() => ({}));
  const error = body?.error;
  const metadata = body?.meterless ?? error?.meterless;
  const message = typeof error?.message === "string" ? error.message
    : typeof body?.detail === "string" ? body.detail : fallback;
  return new RuntimeApiError(message, response.status,
    typeof error?.code === "string" ? error.code : null,
    Array.isArray(metadata?.fix) ? metadata.fix.filter((item: unknown) => typeof item === "string") : [],
    typeof metadata?.chat_carrier === "boolean" ? metadata.chat_carrier : null);
}
