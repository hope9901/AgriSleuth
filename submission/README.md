# AgriSleuth — Track 2 submission package

## Positioning
An agent that explains why a crop hypothesis is supported, what remains uncertain, and what the researcher should verify next. This is research support, not confirmed diagnosis.

## Actual real-service demonstrations

| Case | Outcome | Wall-clock time | Actual actions |
| --- | --- | --- | --- |
| Constructed rice symptom case | completed with Critic/Judge limitations | 146.7 s | search_diseases → verify_evidence → finish_investigation |
| Synthetic low-information image | needs_more_evidence; no candidate | 151.5 s | reanalyze_image → rejected finish → search_diseases → finish_investigation |

Both use the actual local Qwen, PostgreSQL, Zetaris and Meterless runtime. No model or provider mock was used in these two runs. They are software demonstrations with constructed inputs, not diagnostic accuracy validation. The normal case used typed observations and evidence; the Controller did not select image interpretation. The low-information case did use the VLM. The rejected finish argument is retained in the second trace rather than hidden.

Local viewers (the saved DB records must exist):
- [Rice case](http://127.0.0.1:5173/?investigation=2721acac-22d4-4e06-a4b0-fff3bef21f4c&demo=1)
- [Insufficient observation case](http://127.0.0.1:5173/?investigation=df655389-45b2-4112-94f4-fe5bbd7bdd36&demo=1)

Portable evidence: `live-validation.json`, the two case JSON exports, actual UI screenshots and `AgriSleuth-Track2-demo.mp4`. Viewers are local-only; the repository does not imply a hosted public application. Fresh installations reproduce runs with `python scripts/validate_submission.py --case all`; new case IDs and policy choices may differ.

## Sponsor explanation
See SPONSOR_TECH.md. Zetaris performs actual read-only JDBC evidence queries. The integrated Meterless Markovian reference implementation controls bounded action chunks/checkpoints. Nightshift is not used. Software fixture checks and actual model runs are identified separately.

## Video
The approximately 98-second MP4 is a captioned edited replay of actual saved results and UI screenshots, not an unedited live recording. Waiting times are omitted; actual wall-clock times are displayed. No fictional action has been inserted. DEMO_SCRIPT.md provides the spoken presentation outline; the video contains no generated narration.

## Current limitations
- The recorded video predates the weather transport fix and accurately shows its historical HTTP 403. The new KMA SYNOP transport now receives live observations (8/8 timestamps on three tested Seoul dates), with explicit NOAA station metadata. See weather-status.json and ../docs/weather-live-2026-10-26.json. A fresh autonomous weather-inclusive demonstration and updated video remain outstanding.
- Biological accuracy, source claim completeness and treatment/regulatory advice are not established.
- Local model behavior is variable. One positive and one insufficient-information demonstration do not establish reliability across all crops/images.
- No authentication/public hosting; run only on localhost.
- Earlier failed trials remain in docs and are not counted as successful runs.

## Submission checklist
- [x] Track 2 positioning and metadata
- [x] Real positive and insufficient-information cases, portable actual logs
- [x] Explicit weather-access limitation
- [x] Sponsor explanation and attribution
- [x] Captioned edited demo video and presentation outline
- [ ] Upload the chosen video/link on the event submission form and complete the final event submission yourself; no event account submission has been made by this agent.


## Later environment integration check
The existing Korean environment report is imported as 26 profiles / 67 windows. The country-station API and web directory received all 79 Russian entries for cc=1001. A one-sample check selected real weather and Zetaris tools but did not complete Diagnosis/Critic/Judge because structured model output was truncated. See ../docs/environment-integration-summary.json. This new check does not replace the two prior demonstrations or establish diagnostic accuracy. The existing video still shows the historical weather access failure.


## Latest English and Critic-scenario verification
The working project and reference data are English. Historical export translations are labeled and originals preserved separately. The Critic now selects one of eight scenarios, records direct/nearest fit and rationale, and keeps the deterministic Judge and citation checks.

A later weather-inclusive run completed all tool executions in 156.6 seconds with real KMA, Zetaris, Qwen and Meterless, ending needs_more_evidence with Rice blast as a tentative candidate. It did not fail at model output generation and does not establish diagnostic accuracy. See ../docs/environment-sample-latest.json. Prior failed development attempts remain historical; the existing MP4 still predates the weather/scenario update.


Latest same-sample recheck after adding supplied case context: 141.2 s, all tool executions completed; WEATHER_WINDOW_GAP selected as a direct match; final status needs_more_evidence with Rice blast retained. This rerun reused the KMA snapshot collected in the preceding 156.6-second run. Records: docs/environment-sample-latest.json and docs/environment-English-first-live.json (relative to repository root). It is one attributed sample with constructed metadata, not independent ground truth. Critic remains conservative: the recorded question still asks for region/heading information despite supplied region and vegetative leaf context. Scenario selection is a review aid, not a guarantee of biological relevance. The old MP4 predates these changes.


## Final narrated pitch and configuration
Use the repository-root `AgriSleuth_3min_Pitch.mp4` for the current three-minute English narrated pitch with burned-in captions. It explains Critic roles, scenario review, Judge separation and a measured 43.6-second Critic phase within the 141.2-second recorded run. These are edited presentation scenes with synthetic narration, not an unedited live demo or a diagnostic accuracy evaluation. The older 98-second MP4 remains a historical artifact.

All application configuration now uses the ignored repository-root `.env` and the single `.env.example` template. Direct HTTP/SQL tools implement the working sponsor integrations. No MCP server is required for the current architecture.
