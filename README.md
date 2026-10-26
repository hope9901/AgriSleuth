# AgriSleuth

**Submission: Track 2 — The Agent That Can Explain Why.**

Research support for rice and maize disease investigation. It returns tentative hypotheses, source excerpts, Critic findings and questions. It does not provide confirmed diagnoses or pesticide recommendations.

## Working workflow

1. Save photo and typed observations using the existing form. PostgreSQL stores them atomically.
2. Optionally confirm the growing location with **Use location for agent** or collect weather manually.
3. Click **Start evidence investigation**. The Controller reads case evidence, missing observations, Critic findings and Judge decisions and selects ONE allowed tool with validated arguments.
4. The backend validates the tool/arguments, provenance, duplicate-call signature and budget, then executes it. Tool outcomes update durable Agent State and the next Controller decision.
5. Tools reuse existing Zetaris search, KMA observations, photo VLM, Diagnosis, Critic and Judge. Only `verify_evidence` generates/revises hypotheses and runs Critic/Judge; search itself does not diagnose.
6. The Controller may inspect different image features, compare diseases, obtain weather, reverify, ask the researcher, finish a verified tentative report or abstain. It is not required to call every tool.
7. Meterless Markovian controls at most five action chunks by default. Web polling displays actual action reasons, inputs, outcomes, revised hypotheses and the stopping reason. Download a redacted Agent JSON report from the trace panel.

`completed` requires current source-linked hypotheses and a passing Critic/Judge result, with no subsequent change to material inputs or candidate claims. `needs_more_evidence` requests human observations; `abstained` withholds a conclusion. None means confirmed disease. No pesticide or regulatory recommendation is implemented.

No automatic action is taken in a field. No data is sent to a hosted model by the default configuration.

## Actual sponsor use

**Zetaris:** `critic/retrieval.py` logs in through the installed platform UI proxy and executes SQL against `AGRISLEUTH.disease_evidence`. The JDBC source uses `agrisleuth_reader`, granted SELECT only on the evidence view. There is no silent direct-PostgreSQL fallback for disease retrieval. PostgreSQL remains the application's upload/state store.

**Meterless Engine:** unmodified upstream Markovian runtime source is vendored in `engines/meterless-markovian/src`, Apache-2.0, pinned to commit `1742dec56a66e58eef9dda2d2b865823758ca8cd`. The Node bridge injects Python's analysis work as steps. Runtime config, chunks, incoming checkpoints and estimated metrics are persisted and visible in the web history. Native reference reflection is disabled; host Critic/Judge performs validation. The upstream conformance suite passes 8/8. Token estimates are not measured savings claims. See `UPSTREAM.md` and the preserved license.

Based on the organizer update supplied by the participant, Zetaris and a Meterless Engine must be used in a working feature; Cursor/NVIDIA are optional. Implementation evidence is documented here; acceptance is determined by the organizers.

## Run locally

Requirements: existing Python 3.12 Conda environment, Docker PostgreSQL and Zetaris, LM Studio, Node with `--experimental-transform-types` support (verified on Node 23.5.0).

```bash
conda activate agrisleuth
python -m pip install -r critic/requirements.txt
python database/import_diseases.py
python database/setup_zetaris.py
```

`setup_zetaris.py` expects Zetaris credentials in ignored `critic/.env`; initial setup can instead use `--platform-env /absolute/path/to/zetaris-platform/.env`. It creates a scalar evidence view and a read-only source role and registers the JDBC source. The provided local setup uses `host.docker.internal:5432/agrisleuth` from Docker Desktop. Other installations need an appropriate database host. It never resets an existing reader password.

Edit `critic/.env` using `critic/.env.example` as the template. **Preserve existing settings; do not copy over an existing `.env`.** Database credentials come from `DATABASE_URL` or POSTGRES variables / ignored `data/.env.postgres`. Set Zetaris credentials, `LM_STUDIO_MODEL=qwen/qwen3.5-9b`, model URL (default `http://localhost:1234/v1`), and optional KMA key. Never commit credentials.

Current verified model: Qwen3.5-9B Q4_K_M, LM Studio, loaded context 4096. The model's advertised maximum context is not the loaded context. Large descriptions/evidence can exceed the active model budget and must be reduced or configured appropriately.

```bash
cd critic
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

In a separate terminal:

```bash
cd web_developer
npm ci
npm run dev -- --port 5173 --strictPort
```

Vite uses `VITE_API_BASE_URL`, default `http://localhost:8000`. API docs: http://localhost:8000/docs. `/health` checks the process only. Load the Qwen model and start LM Studio's local server before analysis. The strict JSON adapter handles the observed LM Studio Qwen channel quirk only when the entire returned alternate channel is a schema-valid JSON object; it never extracts JSON from prose or displays private reasoning.

The local app runs one analysis at a time, by default five action chunks and an eight-minute overall budget. Set `AGENT_MAX_ITERATIONS` (1–10) and `AGENT_DEADLINE_SECONDS` (30–600) to adjust these host-enforced limits. Individual model calls default to 180 seconds (LOCAL_MODEL_TIMEOUT_SECONDS, range 10–180); the total agent deadline still applies. Server shutdown cancels active jobs and marks them failed while retaining partial records. Jobs abandoned by a hard crash can be reclaimed by an explicit retry after ten minutes. This is a local background-task runner, not a distributed job queue; run one API worker.

## API

| Endpoint | Purpose |
| --- | --- |
| POST `/api/investigations` | Multipart crop, region, observed_date, symptoms, growth_stage, affected_part, photo; persist validated input |
| GET `/api/investigations/{id}` | Current durable result/progress |
| GET `/api/photos/{id}` | Original validated image |
| POST `/api/investigations/{id}/run` | Start bounded investigation; HTTP 202 |
| POST `/api/investigations/{id}/observations` | Add typed symptoms after a paused/finished investigation |
| GET `/api/investigations/{id}/history` | Round and Meterless records |
| GET `/api/investigations/{id}/agent` | Current redacted Agent State and actual tool trace |
| POST `/api/investigations/{id}/location` | Confirm a geocoding location_id before agent execution |
| POST `/api/reviews` | Separate structured candidate-review endpoint |
| GET `/api/weather/locations?q=Seoul` | Open-Meteo/GeoNames location search |
| POST `/api/investigations/{id}/weather` | Collect weather for selected location_id and saved date |
| GET `/api/investigations/{id}/weather` | Saved weather snapshot |

`ready` means input saved, not analyzed. `researching` / `reviewing` are active. `completed` means the workflow ended without a blocking issue, not disease confirmation. `needs_input` / `needs_more_evidence` request observations; `abstained` withholds a conclusion; `failed` records an execution failure.

## Data and storage

- `rice`: 12 diseases / 289 feature entries; `maize`: 14 / 301 at initial import.
- `disease_evidence`: scalar view for Zetaris JDBC; provenance retained per feature.
- `investigations`, `investigation_photos`: observations, status/result and photo bytes with MIME/size/hash metadata.
- `investigation_weather`: current raw/normalized weather evidence per case.
- `investigation_rounds`, `engine_runs`: durable review and Meterless history.
- `agent_runs`: per-run plan/actions, tool inputs/results, hypotheses, Critic/Judge and finish reason.
- `investigation_locations`: user-confirmed location for autonomous weather lookup.

The importer preserves raw JSON, uncertainty/conflict labels and sources. It is idempotent and does not delete unrelated rows. Collected citations are not proof of scientific, regulatory or licensing verification. Photos up to 10 MB are stored in PostgreSQL for this prototype. Volumes are not backups.

## Weather scope and current blocker

KMA world GTS provides weather observations, not long-term climate normals. Location search uses Open-Meteo/GeoNames; weather comes from KMA. The saved local observation date is converted via the selected location's IANA timezone. The nearest listed surface station within 100 km is selected and three-hourly snapshots are requested. Missing values remain unknown and overlapping rainfall intervals are never summed.

The supplied KMA key returned HTTP 403 during initial setup. Live station-header parsing and observation results remain unverified pending API permissions/key/IP checks. Failures are saved as unavailable and do not invent weather. Configure permission for `stn_gts1.php` and `GtsInfoService/getSynop`. The Controller can request weather when a specific uncertainty warrants it. It reuses existing observations where possible. Without a confirmed location, only an unambiguous geocoding result can be used; ambiguous regions require human confirmation. Failed weather requests are blocked from repeated attempts within the run.

Disease environment conditions are presented with sources. Two source-gated maize temperature references can count sampled values inside the cited range. This is not a disease probability; canopy humidity, leaf wetness and the infection period are not established.

## Verification

```bash
python tests/check_api_contract.py
python tests/check_database.py
python tests/check_weather.py
python tests/check_weather_database.py
python tests/check_pipeline.py
python tests/check_local_model.py
python tests/check_autonomous.py
python tests/check_critic_attribution.py
MARKOVIAN_IMPL="$PWD/engines/meterless-markovian/src/index.ts" node --experimental-transform-types engines/meterless-markovian/conformance/runner.ts
cd web_developer
npm run build
npm run lint
```

Database checks create and remove only their own disposable schemas. Pipeline checks use real PostgreSQL and the real Meterless runtime with explicitly synthetic model/retrieval fixtures. They cover revision/checkpoint persistence, human clarification, three-round abstention, empty evidence, service failures and citation provenance. Offline checks do not establish live model or weather behavior.

A previous fixed-executor real-service smoke test on 2026-10-26 used synthetic maize symptoms with actual Zetaris, Qwen and Meterless. It took 248.5 seconds across two chunks: revise conclusion, then ask for human clarification. This verifies software integration, not diagnostic accuracy. Details: `docs/verification-2026-10-26.json`.

## Limits and submission

No labeled field-image accuracy evaluation or agronomic outcome study has been completed. Researcher confirmation and possibly laboratory tests remain necessary. The app has no user authentication or ownership checks: keep it bound to localhost, not public hosting. Production deployment requires authentication, durable workers and storage/backup design.

`metadata.json` records sponsor roles, model and limitations. Development is AI-assisted; `docs/agent_using.md` records the tools. Demo presets currently use separately supplied field-photo samples with source labels. Their licensing/source claims still require verification. Any synthetic test inputs must be identified as synthetic, never field validation. Older `functions/weather.py` and `struct/langgraph_main.py` drafts are not entry points and are not imported by the application.


## Autonomous Agent Controller and comparison

See `docs/AUTONOMOUS_AGENT_IMPLEMENTATION.md` for the fixed-workflow analysis, changed files, safeguards, evidence of actual execution and remaining limitations. `tests/check_autonomous.py` covers A–G with real PostgreSQL/Meterless and clearly mocked policy/model/provider responses. A separate live Controller selection and autonomous end-to-end smoke test are recorded independently; fixture results are never presented as actual model behavior.

To compare a single-pass Diagnosis + DB + saved-weather baseline against an existing autonomous run:

```bash
python scripts/compare_agent_modes.py --investigation UUID --output /tmp/agrisleuth-comparison.json
```

This executes a real baseline model call and reads the saved autonomous trace. It reports actions, tool calls, duration, candidate/claim changes, Critic flags and abstention. With no ground-truth labels, diagnostic accuracy and the baseline's unknown unsupported-claim count remain null. Available data and additional tools can differ, so this is exploratory, not a controlled causal estimate of Critic benefit.

Unfinished product features: field-image accuracy evaluation, source-claim verification, official registration/management advice, public deployment authentication, distributed workers, and live KMA verification pending access. Collected `data/diseases/weather_windows*` files are retained but are not automatically translated into validated disease-risk thresholds.

Local demo performance: Diagnosis is prompted to return one leading tentative candidate per verification, with plausible alternatives retained as limitations. The schema still supports up to three, but broad multi-candidate reports and clinical accuracy are not claimed. Actual local throughput declined during testing; failed/timeout trials are preserved separately, not counted as successful verification. The eight-minute overall budget remains in force even with a 180-second per-call limit.

Local storage connection timeout defaults to 10 seconds (POSTGRES_CONNECT_TIMEOUT, range 1–30). The web retries progress polling after a read failure; no missing response is interpreted as successful analysis. A live smoke test observed a transient storage-read failure under concurrent local inference, which is recorded rather than omitted.

Final autonomous verification boundary: actual action selection/search/re-planning and a separate corrected Critic/Judge call were observed. The final revised complete live rerun was not performed because execution approval was declined. Do not present earlier failed/rejected trials as a completed verified run. Records and full details are in docs/AUTONOMOUS_AGENT_IMPLEMENTATION.md.


## Track 2 final submission evidence

The later real-service demonstrations are now recorded in [submission/README.md](submission/README.md): a source-supported rice hypothesis completed with limitations in 146.7 seconds; an insufficient-information case requested observations without producing a disease candidate in 151.5 seconds. Both used real local services. These supersede the earlier “final rerun not performed” verification boundary for these two specific cases; the earlier failed trials are retained as historical records. They do not establish agronomic accuracy or general reliability.

See the sponsor explanation, captioned edited demo MP4, actual run exports and weather-access record under submission/. Track 2 is the selected submission category. The event form has not been submitted automatically.
