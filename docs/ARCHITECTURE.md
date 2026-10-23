# AgriSleuth Architecture (MVP skeleton)

## Repository layout

| Path | Role |
|------|------|
| `apps/web` | Next.js UI — intake, map/GPS, evidence panel, report |
| `services/api` | FastAPI — uploads, session API, OpenAPI |
| `services/agent` | Diagnosis–Critic–Judge orchestration and tools |
| `data/diseases` | Curated disease knowledge (source URLs required) |
| `tests/fixtures` | Demo cases (images, weather stubs, labels) |
| `scripts` | Seeding, evaluation, demo runners |

## Agent loop (v2)

```
INTAKE → OBSERVE (VLM) → RETRIEVE (DB) → CHECK_ENV (weather)
  → HYPOTHESIZE (Diagnosis) → CHALLENGE (Critic) → VERIFY (Judge)
  → ACT (re-query / more photos) → REPORT
```

Deterministic checks (D4+): disease IDs must exist in DB; sources must resolve; no unregistered pesticide names in output.

## D1 focus

1. HackOS / sponsor API smoke tests (Nemotron, Zetaris).
2. Add reviewed disease JSON under `data/diseases/rice/` and `data/diseases/corn/` (5–8 per crop or per schedule).
3. Replace stub `VisionTool` with real VLM JSON schema validation.
4. Optional: PostgreSQL + pgvector via `docker compose up db`.
