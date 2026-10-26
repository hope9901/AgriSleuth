# Autonomous Agent implementation report

**Current submission: Track 2. Later real-service cases passed: see submission/README.md and submission/live-validation.json. Earlier failed trials below are historical and remain unchanged.**

## A. Existing structure and minimal change

The previous live executor was a bounded fixed workflow: retrieve, generate, Critic, Judge, then code-selected revision or retrieval. Existing agent-like components were structured hypothesis generation, semantic criticism, deterministic Judge, source-ID validation, durable rounds and the Meterless Markovian runtime. It did not let the LLM choose the next tool.

The live entry point now delegates to `agent_runtime.execute`. `pipeline.execute_fixed` is retained only for explicit regression/comparison of the previous path; it is not the run endpoint's executor. The existing React form/results, intake/review routes, PostgreSQL data, VLM, KMA adapter, Zetaris transport and upstream engine are reused.

## B. Changed implementation surfaces

| File | Change / reuse |
| --- | --- |
| critic/agent_controller.py, prompts/controller.md | Structured LLM tool policy; bounded state context and currently available-tool schema |
| critic/agent_tools.py | Registry, strict per-tool arguments, provenance, cache, photo ownership and finish guards; reuses existing analysis functions |
| critic/agent_runtime.py | Real select/validate/execute/update/replan loop, checkpoints, eight-minute/five-action defaults, partial-state preservation |
| critic/pipeline.py | Existing Diagnosis reused; live execute delegates to Controller runtime; previous fixed executor retained explicitly |
| critic/judge.py | Existing deterministic decisions with caller-configurable review cap; separate review endpoint retains default three |
| critic/vision.py | Reuses actual image input; accepts targeted inspection questions and explicit unknown/quality/extra-photo fields |
| critic/database.py, database/schema.sql | Additive Agent State and confirmed-location storage; no source-data deletion |
| critic/main.py | Redacted agent-trace and confirmed-location routes; existing API maintained |
| engines/meterless-markovian/bridge.mjs | Pass configured action cap to the unchanged upstream Markovian engine |
| AgentTrace.tsx, InvestigationResults.tsx, WeatherPanel.tsx | Actual tool decisions, validated inputs/outcomes, hypothesis history, report export and location confirmation |
| critic/evaluation.py, scripts/compare_agent_modes.py | Exploratory baseline/autonomous metrics with explicit unknown accuracy |
| tests/check_autonomous.py | Required A–G plus freshness guard, real DB/engine and synthetic policy/provider fixtures |

Existing user data edits and newly collected weather CSV/JSON files are retained. Existing management/pesticide or legal-reporting features were not found as verified working functions, so no such feature was invented or claimed complete.

## C. Actual reasoning loop and safeguards

At each Meterless chunk the LLM receives bounded evidence, candidate names/IDs, image observations, missing information, last Critic/Judge, recent tool outcomes and checkpoint. It chooses one tool and arguments. The host executes only allow-listed, schema-valid calls; the model cannot issue SQL, arbitrary paths or URLs.

Available-tool schemas exclude image inspection when no case image exists, verification when no source evidence exists, weather after failure, and searches that have already added no new evidence. This is a state/precondition guard, not a hard-coded order. The model still selects among eligible evidence gathering, verification and finishing actions. Duplicate arguments are normalized and rejected. Weather cache and a per-run Zetaris row cache avoid redundant external requests.

Only actual source records enter candidates. Canonical name/ID/source relationships are checked in code; cross-crop search IDs are rejected. Modified source pools or candidate claims invalidate completion. A passing verification fingerprint is mandatory for completed. Otherwise the model must request evidence or abstain. Time/action exhaustion abstains rather than fabricating a diagnosis. Raw images and precise coordinates are not copied into tool trace exports. Decision reasons are brief action explanations, not private chain-of-thought.

Diagnosis/Critic/Judge internal phases are persisted as actual events. After a blocking Critic finding the Controller receives the finding and chooses whether to research, inspect an image, collect weather, revise/verify, ask the user or abstain. The host does not preselect the next investigation tool.

## D. Tests and observed failures

`python tests/check_autonomous.py` covers:
- A: missing weather, selected get_weather, actual registered tool path and saved result;
- B: conflicting evidence, image reinspection chosen after Critic, then re-verification and Judge approval;
- C: sufficient verified evidence, immediate finish without extra tools;
- D: missing evidence, human question, trace export and follow-up;
- E: invented/cross-crop disease ID and unverified completion rejection;
- F: duplicate calls execute once; action exhaustion abstains;
- G: comparison reports steps/tools/time/flags and null accuracy without labels;
- modified previously reviewed claims cannot be completed without fresh verification.

These use mocked Controller/model/provider fixtures, real PostgreSQL in a disposable schema and the real Meterless runtime. They establish control/provenance behavior, not actual policy quality or diagnostic accuracy.

An initial real-model run searched repeatedly without adding evidence and exhausted the action budget; it was correctly marked abstained and produced no diagnosis. It was not counted as successful end-to-end verification. This exposed unclear search/verification semantics and missing canonical names in the Controller context. The prompt/context were clarified, explanations shortened, and no-progress tool eligibility enforced. Both the initial failure and revised live result are recorded separately when available.

Actual KMA access previously returned HTTP 403. Automated weather transport tests use fixtures; live station-header and data verification remain pending authorized access. No success is claimed for that blocker.

## E. Reproducible demonstrations

1. Maize differential investigation: use a clearly labeled synthetic symptom case, e.g. long gray/tan cigar-shaped lesions crossing leaf veins. Show actual Controller choices, retrieved source IDs, Diagnosis, Critic/Judge and final stopping reason. Exact choices are model-dependent; never replace them with staged UI events.
2. Missing observation case: provide an unclear image or an incomplete distinguishing description. Show targeted image inspection if selected, unobservable features, and a question or abstention. A fixture replay can demonstrate all branches deterministically, but must be labeled as a test rather than a live model demo.

For before/after exploration use `scripts/compare_agent_modes.py --investigation UUID`. Do not claim accuracy or quantified causal improvement without labels and an appropriate experimental design.

## F. Run and deployment

Preserve local `.env`. Set LM_STUDIO_MODEL / BASE_URL / API_KEY, Zetaris credentials/table, database settings and optional KMA_AUTH_KEY. Optional policy controls: AGENT_MAX_ITERATIONS=5, AGENT_DEADLINE_SECONDS=480, NODE_BINARY. Run `python database/import_diseases.py` for additive tables. Launch uvicorn from critic/ and Vite from web_developer/ as in README. Restart the local API to load Python changes.

Run the API, DB, weather, local-model, legacy pipeline and autonomous test scripts plus Meterless conformance. Build and lint the web with npm run build / npm run lint. Keep the app on localhost: authentication, public hosting, distributed execution, official management advice and agronomic accuracy evaluation remain outside this implementation. No production deployment is modified by this change.

A second live trial selected search then verify, but local Diagnosis exceeded the call timeout. It abstained without a report; repeated verification was rejected. Output targets were then reduced and provider failures made ineligible until material evidence changes. This unsuccessful trial is preserved in `autonomous-timeout-trial.json`. A separate compact Diagnosis call subsequently succeeded in 110.4 seconds with real Zetaris/Qwen.

Local-model runtime notes: LOCAL_MODEL_TIMEOUT_SECONDS defaults to 180 (allowed 10–180), still bounded by the 480-second whole-run deadline. Diagnosis output is compact and defaults to one leading hypothesis per verification; unresolved alternatives remain limitations. Targeted image requests containing known target disease names/IDs are rejected to reduce leading prompts. The current user-supplied field-photo preset UI is preserved; this implementation did not verify its source/license labels.

A later live trial reached actual Diagnosis and Critic but the Critic referenced an alternative disease ID outside the generated candidate list. The deterministic guard correctly rejected the review and the Controller requested more evidence instead of declaring success. Per-request structured-output enums now constrain candidate/evidence IDs during generation as well as checking them afterward. Supported alternative diseases can be discussed with candidate_id null.


## Final verification boundary

- Actual local LLM tool selection and real Zetaris tool execution were observed.
- Actual Controller re-planning after provider failure was observed, including an explicit request for more evidence instead of false completion (306.3 seconds; one transient storage read retry).
- That live run did not obtain a valid Critic/Judge result. It is not counted as successful verified diagnosis.
- After correcting reference enums and disease attribution, a separate real Critic/Judge call returned successfully in 26.0 seconds and requested more evidence. This still does not establish biological correctness; the request may be redundant with existing observations.
- The final complete revised end-to-end rerun was not executed because execution approval was declined. No such pass is claimed.
- A–G synthetic-policy/provider tests, API contract checks, local-model JSON/reference checks, attribution checks, DB persistence checks, and web build/lint passed during implementation. See the test scripts for exact scope.
- KMA live access and labeled agronomic accuracy remain unverified. Source/license checks and public deployment are not part of this completed code change.

Actual records: autonomous-initial-trial.json, autonomous-timeout-trial.json, autonomous-live-latest.json, autonomous-critic-attribution.json. Initial/failure runs remain visible; they are not replaced with staged successful actions.


## Subsequent Track 2 validation

A later explicitly authorized actual-service validation completed two cases: rice hypothesis 146.7 s (completed with limitations), insufficient information 151.5 s (needs_more_evidence, no disease candidate). See submission/live-validation.json and the full exports. These are constructed software inputs, not accuracy labels. This later evidence supersedes the earlier no-rerun boundary only for the two recorded cases. Historical failures remain unchanged.
