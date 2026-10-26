# AgriSleuth implemented architecture

React/TypeScript/Vite -> FastAPI intake and persisted observations -> explicit start -> local LLM Controller -> one validated tool -> durable Agent State -> evaluate/replan -> finish, ask for more evidence, abstain or fail.

The Controller chooses among search_diseases, get_weather, reanalyze_image, verify_evidence and finish_investigation. Their existing implementations are reused: Zetaris read-only JDBC evidence, KMA world observations, LM Studio VLM, source-linked Diagnosis, Critic and deterministic Judge. No hard-coded tool sequence drives the live run. State-conditioned eligibility, normalized duplicate detection, provenance and freshness guards remain deterministic.

The unmodified Meterless Markovian reference runtime controls bounded action chunks and checkpoints. Default limits: five actions, 480 seconds overall. The Python host persists state before/after tools; reference reflection is disabled because validation is performed by host Critic/Judge. LangGraph remains in intake and the separate review endpoint. The previous fixed executor is retained explicitly as execute_fixed for regression, not the live run route.

PostgreSQL stores inputs/photos, optional weather, round/engine history, agent_runs and confirmed locations. Web polling shows real backend events and tool traces; report export redacts precise location and raw weather/images. It does not generate simulated agent actions.

See README and AUTONOMOUS_AGENT_IMPLEMENTATION.md for setup, new routes, exact test scope, actual failed trials, successful isolated checks and remaining limitations. Final complete revised live replay was not performed after execution approval was declined.
