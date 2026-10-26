# Historical D1–D6 Implementation Guide (English edition)

This is an English planning summary, not a claim that the original plan was fully delivered. Current implementation and measured results are in README.md, PROJECT_STATUS_2026-10-26.md and submission/README.md. The original Korean plan is preserved separately.

## Original scope and schedule
Solo six-day MVP, October 22–27. Rice and maize. Target investigation loop: 5–10 minutes; video: 1–4 minutes. Initial architecture proposed Next.js, Python/FastAPI, PostgreSQL/pgvector and an agent workflow. The delivered app instead uses React/Vite and the documented local services.

1. D1: install tools, configure private keys, establish the application skeleton and prove sponsor access.
2. D2: photo to tentative visible symptoms, source-backed disease retrieval and up to three candidate hypotheses.
3. D3: location-to-station mapping and 7–14 days of pre-observation weather with distance, missingness and source provenance. Do not equate station weather with canopy exposure.
4. D4: Diagnosis–Critic–Judge revisions; reproduce an evidence conflict, retain checkpoints, bound iterations and request human clarification where necessary.
5. D5: explainable report UI and three to five example cases. Plan five to ten labeled photographs only when ground truth is available. Compare A: image only, B: observations plus DB/weather, C: added Critic loop. Do not infer accuracy from unlabeled samples.
6. D6: package a reproducible local demonstration, English README, metadata, sponsor explanation and one-to-four-minute video; finish event submission.

## Original data requirements
Each disease feature retains crop, canonical identity, symptoms, visible/laboratory requirements, growth stage, source name, URL, location in source and conflicts. Separate confirmed occurrence from missing reports. Foreign regulation or occurrence is not evidence of Korean status. Weather requires observation dates, confirmed locations, valid station distance and missing-value handling. Growth-stage/event anchors are required for source-specific infection windows.

## Sponsor and product requirements
Zetaris should provide meaningful governed data access. A Meterless Engine should perform a working role demonstrated by tests/logs. Nightshift is a separate product and is not required by this implementation. Planned official management links and registered-product advice require independent live verification and were not implemented as pesticide recommendations.

## Evaluation boundaries
The implemented one-photo intake, one-leading-candidate local demo, bounded autonomous Controller, separate weather transport, environment references and synthetic fixture tests are not equivalent to all planned biological validation, multi-image analysis, full infection models or international coverage. See current status before making submission claims.
