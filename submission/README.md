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
- KMA recheck still returned HTTP 403. No world weather values are fabricated; weather is shown as unavailable. See weather-status.json.
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
