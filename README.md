# AgriSleuth

Evidence-guided autonomous plant disease investigation agent for **Open Agent Hackathon 2026**.

The MVP targets **rice (벼)** and **corn (옥수수)** with structured symptom extraction (VLM), disease knowledge retrieval, weather evidence, and a **Diagnosis–Critic–Judge** verification loop. Disease JSON lives under `data/diseases/rice/` and `data/diseases/corn/` (curated sources you provide).

## Monorepo layout

```
apps/web/              Next.js (TypeScript, Tailwind)
services/api/          FastAPI HTTP API
services/agent/        Agent orchestrator & tools
data/diseases/         Curated disease JSON (official sources)
docs/                  Architecture & submission notes
scripts/               Seed & demo helpers
tests/                 Pytest (agent smoke tests)
```

## Quick start

### 1. Database (optional, D1+)

```bash
docker compose up -d db
cp .env.example .env
```

### 2. Backend

```bash
cd services
python3.12 -m venv .venv   # requires Python >= 3.11
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn api.app.main:app --reload --port 8000
```

- Health: http://localhost:8000/health  
- OpenAPI: http://localhost:8000/docs  

### 3. Frontend

```bash
cd apps/web
npm install
npm run dev
```

Open http://localhost:3000 — upload a photo to hit `POST /api/v1/investigations` (stub pipeline).

### 4. Tests

```bash
cd services && source .venv/bin/activate
pytest ../tests -q
```

## Hackathon roadmap (from plan)

| Day | Goal |
|-----|------|
| 10/22 | Repo scaffold, disease DB seeds, sponsor API checks — see `docs/D1-D6_실행_가이드.md` |
| 10/23 | VLM JSON + retrieval end-to-end |
| 10/24 | Weather API + environment evidence |
| 10/25 | Full verification loop + deterministic validation |
| 10/26 | Report UI, management links, test cases |
| 10/27 | Demo video, README, submission package |

## Safety

Outputs are **provisional** only. No pesticide recommendations without verified PSIS registration data. GPS is opt-in; precise coordinates are not shown on public report views by default.

## License

TBD — confirm hackathon submission requirements.
