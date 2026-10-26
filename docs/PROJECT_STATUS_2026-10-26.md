# Project status — 2026-10-26 (Track 2)

## Implemented and observed
- React observation/photo intake, FastAPI validation and PostgreSQL atomic storage.
- Rice/maize evidence storage and real Zetaris read-only JDBC queries with source IDs.
- Local Qwen Controller selects validated tools; durable state, Critic/Judge, human clarification, freshness/duplicate/budget safeguards.
- Integrated upstream Meterless Markovian engine and checkpoints; Nightshift is not used.
- Actual separate supported and insufficient-information autonomous demonstrations (146.7 s / 151.5 s); constructed inputs, not diagnostic evaluation.
- Explain-why UI: tool selection reasons, source excerpts, limitations, review history, stopping reasons and JSON export.
- New KMA gts_bufr_syn1.php transport receives 8/8 timestamps on three Seoul dates. NOAA ISD provides station coordinates explicitly. No key is exported.
- A separate constructed test case verified actual HTTP weather POST, PostgreSQL save and HTTP GET equality (8 observations). See weather-live-2026-10-26.json.
- Weather offline checks, 11 API contract checks and disposable-schema weather storage checks passed after this change. Docker and API were restarted.

## Partial relative to the original D1–D6 plan
- Environmental evidence: samples of the observation day; autonomous tool can request bounded days. The originally planned pre-onset 7–14-day analysis and scientifically validated disease exposure windows are not complete.
- Image inputs: one uploaded image and tool-selected VLM; the planned multi-image evaluation and reliable Top-3 candidate evaluation are not established. The successful rice demo used typed symptoms rather than a selected image tool.
- Quantitative environment assessment: two source-gated maize temperature overlaps, not a validated infection probability. Collected weather-window files are not validated operational thresholds.
- Zetaris federates the disease evidence view; weather currently uses its own provider and application storage rather than a demonstrated joint federated weather query.
- Existing UI demo/video and GitHub submission package reflect the prior weather failure. New code and live weather records are local changes pending commit/push; video still needs a weather-inclusive segment.

## Remaining evidence/product work
1. Run a fresh full agent case in which an actual weather question causes get_weather and affects a source-linked explanation. Separate transport success does not prove this behavior.
2. Demonstrate an actual evidence conflict followed by a useful tool call and revised/withheld conclusion. Fixture coverage exists; broad real-model reproducibility does not.
3. Evaluate 5–10 labeled field examples and the planned A/B/C comparison. No accuracy gain or causal Critic benefit may be claimed yet.
4. Review source claims and image licensing; official management/registration links and regulated advice remain outside the implemented report.
5. Update video/submission evidence and submit the event form. No event submission has been performed.
6. International coverage, station metadata freshness, multi-user authentication, durable worker queue and backups require further work. Localhost prototype only.

Do not assign an arbitrary completion percentage: implemented functionality and demonstrated scientific validity are different measures.


## Environment reference follow-up
- Added 26 disease profiles and 67 windows as source-preserving PostgreSQL references, loaded from existing Korean data.
- Added window/input sufficiency assessment and rice-blast station sample overlap; full disease-specific infection models and all numeric threshold interpretations remain incomplete.
- Added live country-station API + web directory; KMA cc=1001 returned all 79 Russian stations. Names/IDs do not replace coordinate metadata.
- Single attributed rice sample was evaluated with constructed metadata; see environment-sample-latest.json and environment-sample-initial.json / environment-sample-context-failure.json / environment-sample-output-failure.json for preserved attempts. Never count retries as independent test cases or report an accuracy percentage.


### Actual one-sample result
The same sample/case was attempted five times while fixing integration issues. Initial behavior asked for unrelated disease inputs (45.5 s); then input context overflow (60.6 s), output truncation at 350 tokens (101.2 s), output truncation at 500 tokens (101.0 s), and a bounded-output-schema attempt (106.2 s) failed at verification. The last attempt selected cached weather, retrieved six real Zetaris excerpts, rejected incomplete model output and finished failed with no candidate. The original first attempt did perform a fresh KMA request. This demonstrates weather tool selection and retrieval, not a completed weather-inclusive diagnostic run. No accuracy percentage is reported. Full records: environment-integration-summary.json and environment-sample-*.json.

Current quantitative environment checks implement the explicitly gated rice-blast station temperature/RH overlaps; all 26 diseases preserve source conditions and assess window/input sufficiency. Fully operational infection models for all diseases remain unimplemented. Existing video has not been replaced. Current changes have not been pushed.


## English/scenario update — latest verification
- Working source, UI, reference data and documentation now use English. Original files and pretranslation DB snapshots are preserved outside the repository; translated historical exports are labeled.
- Critic: eight runtime-loaded scenarios, direct/nearest match, rationale, known-ID validation and visible review-history fields. Existing Judge/provenance safeguards retained.
- Verified LM Studio loaded context: 40,912. Application output budgets increased to 1,600 Diagnosis / 1,200 Critic; input context alone did not remove those old application caps.
- New real sample fd16b80e-f56f-4c82-9668-a2bbe4cdaeea: 156.6 s, fresh weather -> search -> verify -> finish, all tool actions completed. Rice blast leading tentative hypothesis; final status needs_more_evidence because infection-window information remains missing. This supersedes the earlier runtime-truncation blocker for this specific workflow; no general reliability or accuracy claim is established.
- Latest export is environment-sample-latest.json. Prior five attempts remain historical records; they are not independent evaluation cases.


Latest same-sample recheck after adding supplied case context: 141.2 s, all tool executions completed; WEATHER_WINDOW_GAP selected as a direct match; final status needs_more_evidence with Rice blast retained. This rerun reused the KMA snapshot collected in the preceding 156.6-second run. Records: docs/environment-sample-latest.json and docs/environment-English-first-live.json (relative to repository root). It is one attributed sample with constructed metadata, not independent ground truth. Critic remains conservative: the recorded question still asks for region/heading information despite supplied region and vegetative leaf context. Scenario selection is a review aid, not a guarantee of biological relevance. The old MP4 predates these changes.
