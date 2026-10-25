# AgriSleuth

A rice and maize disease investigation prototype for South Korea.
The intended workflow is observation → evidence retrieval → hypotheses →
Critic → deterministic Judge → revision, additional questions, or a report.
**The full investigation workflow is not connected yet.**

## Current implementation

- React + TypeScript + Vite observation form and result panels.
- `POST /api/investigations`: multipart intake, image validation (JPEG/PNG/WEBP,
  up to 10 MB), required-observation checks and the UI response shape.
- Returned `ready` means inputs were validated and persisted to PostgreSQL, not
  that diagnosis or review ran. The UUID is a persisted investigation ID.
- Photos and observations are committed in one transaction. Photo bytes live in a
  separate PostgreSQL table for this small prototype (up to 10 MB each).
- GET `/api/investigations/{id}` restores the result; GET `/api/photos/{photoId}`
  returns the original validated photograph.
- `POST /api/reviews`: JSON candidates and evidence → LM Studio structured Critic
  response → Python Judge. Empty candidates/evidence request retrieval without
  invoking a model. Unconfigured review returns 503; model failure returns 502.
- English runtime prompt in `critic/prompts/clitic.md`.
- Disease JSON collections under `data/diseases/rice` and `data/diseases/corn`.
  Presence of a citation is not proof that every claim has been verified.

## Repository layout

```text
critic/                 FastAPI, intake/review graphs, schemas and Judge
  prompts/clitic.md     Runtime Critic instructions
functions/weather.py    Incomplete weather adapter; not imported by the API
struct/langgraph_main.py Legacy incomplete draft; do not use as an entry point
web_developer/          React + TypeScript + Vite
data/diseases/          Collected disease data
database/               Additive schema and idempotent JSON importer
docs/                   Earlier planning documents; may describe future features
```

## Run the API

Python 3.12 is recommended. Activate your existing Conda environment, then:

```bash
cd critic
python -m pip install -r requirements.txt
cp .env.example .env
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

If `.env` already exists, edit it instead of copying over it.
Set `LM_STUDIO_MODEL` to the exact ID returned by `GET /v1/models` on the LM Studio
server (typically `http://localhost:1234`). Start the server and load the intended
Qwen3.5-9B model before testing review. An empty model setting disables review
while leaving intake available. The prompt must exist and be nonempty.

- API docs: http://localhost:8000/docs
- Process health: http://localhost:8000/health (does not probe LM Studio)

Run from `critic/` because its modules currently use local imports.

## Run the web app

In another terminal:

```bash
cd web_developer
npm ci
cp .env.example .env
npm run dev -- --port 5173 --strictPort
```

Preserve any existing `.env`. Restart Vite after environment changes.
`VITE_API_BASE_URL` is a public server address, never a secret. Keep model and
service credentials on the Python side. CORS permits localhost/127.0.0.1:5173.

```bash
npm run build
npm run lint
```

## API contract

`POST /api/investigations` uses multipart fields:
`crop` (`rice` or `maize`), `region`, `observed_date` (YYYY-MM-DD),
`symptoms`, `growth_stage`, `affected_part`, and `photo`.
Do not manually set the multipart Content-Type boundary in browser code.
Growth stage and affected part are stored but are not used for analysis yet.

The result contains `id`, `photoId`, `status` (`ready` or `needs_input`), `summary`,
`questions`, empty `hypotheses`, `evidence`, `reviewIssues`, plus `nextAction`,
`limitations`, and actual intake `events`. The frontend understands `ready`.

`POST /api/reviews` uses the `ReviewRequest` JSON schema shown in `/docs`.
The web helper `src/api/reviews.ts` uses this same JSON contract and a 105-second
timeout, longer than the Critic call budget. It is not wired to the form yet.
It is a separate backend testing endpoint; submitting the web form does not
invoke it yet. Judge actions include finalize, finalize_with_limitations,
request_user_input, retrieve_evidence, revise_conclusion, and abstain.
Those actions are returned, not automatically executed. Finalize is not a
confirmed diagnosis. `review_round` is currently caller-supplied; server-side
case memory and a durable review budget are not implemented.
Old `/investigations` and `/reviews` paths have been replaced by `/api/...`.

## Next work and limitations

Not yet connected: image symptom extraction, disease retrieval, weather service,
repeat-review execution, investigation reasoning memory, and follow-up input.
The weather and legacy graph drafts contain incomplete code and are intentionally
left unchanged. They are not required to launch `critic/main.py`.

## Hackathon technology and disclosure

Based on the latest organizer update supplied by the participant, a working
feature must use Zetaris and a Meterless Engine. Cursor and NVIDIA are optional,
and event credits are not available. Zetaris and Meterless integration are
**not implemented in this repository yet**. Do not claim otherwise in submission.

Development is AI-assisted. The Critic is configured for a local LM Studio model;
record the exact model, quantization, runtime and actual tests before submission.
Data sources and limitations are included in collected JSON/Markdown, but source
verification and image licensing still need review. No pesticide recommendation
or definitive disease diagnosis is implemented.
Never commit `.env`, keys, tokens, or credentials.

## Offline API checks

After installing the Python requirements plus `httpx`, run from the project root:

```bash
python -m pip install httpx
python tests/check_api_contract.py
```

These 11 checks use an in-process HTTP client, tiny synthetic images and an
explicitly mocked reviewer. They cover multipart responses, missing observations,
invalid images/dates, size limits, CORS, unconfigured review, Judge routing,
evidence gating and prompt loading. They never call a live model or KMA.
The script temporarily sets `LM_STUDIO_MODEL` empty in its own process only.

## PostgreSQL setup and disease import

Use the project container `agrisleuth-postgres`, not Zetaris's internal PostgreSQL.
The existing local database is `agrisleuth` (PostgreSQL 18 at initial import).
Start Docker Desktop and the container before running import or submitting a case.

Credentials are read from environment variables or the existing ignored
`data/.env.postgres`. Do not commit that file. A server-side `DATABASE_URL` takes
precedence; otherwise `POSTGRES_HOST` defaults to 127.0.0.1 and `POSTGRES_PORT`
to 5432, with POSTGRES_USER/PASSWORD/DB from the local file or environment.
The importer uses environment/data-file settings directly; it does not load
`critic/.env`. The API loads `critic/.env` first. Keep these settings consistent.

From the project root, with critic requirements installed:

```bash
python database/import_diseases.py
```

The schema and import commit in one transaction. Re-running updates changed
source records without duplicating IDs or deleting unrelated records. Unchanged
records retain their original import timestamp. JSON is the canonical import
source; CSV and Markdown exports are not imported again as duplicate diseases.

| Table | Purpose |
| --- | --- |
| rice | 12 rice diseases; initial import contains 289 feature entries |
| maize | 14 maize diseases; initial import contains 301 feature entries |
| investigations | Crop, location, date, symptoms, growth stage, affected part, status and result |
| investigation_photos | Photo bytes, case foreign key, filename, MIME, size, dimensions and SHA-256 |

Disease IDs use `rice_001` / `maize_013` style identifiers derived from the source
record number. Features and research records are joined by that number, not by
potentially ambiguous common names. JSONB retains complete source records,
source locations, metadata, uncertainty labels and conflicts. Normalized name
columns and a GIN feature index support later retrieval. Import is not an audit
of the scientific, regulatory, or licensing claims. No source URL is fetched by
this importer. Review results are still separate and are not yet attached to cases.

The web helper exports `getInvestigation(id)` and `getPhotoUrl(photoId)` for later
history/preview UI. Intake persists data now, but no case-history screen is added.

For a real DB persistence/rollback test:

```bash
python tests/check_database.py
```

This creates a unique disposable schema, checks exact photo/result retrieval,
metadata and transaction rollback, and drops only that test schema afterward.
It requires local DB access and permission to create a schema. The offline API
checks mock persistence and do not require a running PostgreSQL server.

This is a local development API with no user authentication or ownership checks.
Run bound to 127.0.0.1; add authentication and access controls before public hosting.
Photo bytes increase DB/backup size; move large-scale storage to object storage
later. Docker volumes preserve data but are not backups; back up the DB separately.


## World weather evidence (KMA)

Set `KMA_AUTH_KEY` in the ignored `critic/.env` and restart FastAPI. The key must have permission for world GTS station metadata (`stn_gts1.php`) and structured SYNOP (`GtsInfoService/getSynop`). The attached saved page's example key returned HTTP 403 during setup; real weather responses and the station header still require verification with an authorized key. Keys are never sent to the browser or saved in weather snapshots.

Apply the additive schema with `python database/import_diseases.py` in the conda environment. It creates `investigation_weather` without dropping disease or upload data.

After submitting an observation, use **KMA world observations** to search and confirm a city. Geocoding uses Open-Meteo/GeoNames only; weather comes from KMA. The server resolves the selected location ID, converts the saved observation date from its IANA timezone to UTC, selects the nearest listed surface station within 100 km, and requests at most nine three-hourly timestamps for that local day. No future weather is fabricated. Requests have a 45-second overall deadline.

Routes:
- `GET /api/weather/locations?q=Seoul`
- `POST /api/investigations/{id}/weather` with JSON `{"location_id": 1835848}` (use a returned ID, not this illustrative value)
- `GET /api/investigations/{id}/weather` for the saved snapshot

PostgreSQL stores station identity/distance, location, requested period, retrieval time, normalized and raw observations, limitations and cited environment features from the selected crop's disease table. Upload handling remains separate and fast. Repeating collection replaces only that investigation's current weather snapshot.

Comparisons currently present source environment conditions beside measurements for researcher review. They do not automatically rank disease likelihood or infer undocumented thresholds. Station samples are not daily minima/maxima, canopy humidity, leaf wetness, long-term climate normals or evidence of pathogen presence. Missing values stay unknown; overlapping rain windows are never summed. Coverage is marked `partial` even when every requested timestamp is returned because these are sparse samples of a day. All-provider failures are saved as `unavailable`.

The original unfinished `functions/weather.py` ASOS draft is not imported by the world weather service. Zetaris and Meterless integration remain separate pending tasks.

Two source-specific temperature references (maize_013 CPN 18–27 °C and maize_014 Nongsaro 20–30 °C) can report counts of samples inside the source range. A rule activates only if its source name and exact range text still match and no source conflict is recorded. All other conditions remain researcher-reviewed. This count is not a disease score; leaf wetness/humidity requirements remain unverified. The key from the supplied saved page was placed only in ignored `critic/.env`; it returned HTTP 403, so its permission/validity must be checked in API Hub.

Weather verification (from project root, activated Python environment):
```bash
python tests/check_weather.py
python tests/check_weather_database.py
```
The first uses synthetic HTTP fixtures and tests UTC/local-date conversion, DST, sentinels, wrong-station rejection, source-gated comparison and provider failures. The second creates/removes its own temporary PostgreSQL schema. A real Open-Meteo search and selected-location lookup for Seoul were verified during setup. Live KMA observations remain unverified because the supplied key returned HTTP 403; do not present synthetic test data as real observations.
