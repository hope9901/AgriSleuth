# Sponsor technology explanation

**Zetaris:** AgriSleuth uses the Zetaris SQL API to query a read-only PostgreSQL JDBC evidence view. Disease/source IDs and citations are retained throughout retrieval and validation. Demo logs identify real Zetaris queries and returned source IDs.

**Meterless:** We integrated the Apache-2.0 Markovian Engine reference implementation, pinned in engines/meterless-markovian/UPSTREAM.md. It runs bounded Controller-selected tool actions with compressed checkpoints. PostgreSQL records each step and the web displays the actual trace. The upstream conformance suite passed 8/8; tests/check_autonomous.py checks revision, clarification, provenance and bounded abstention using real PostgreSQL/Meterless with explicitly mocked policy/provider responses. Nightshift is not used.

Token metrics are estimates. A passing software test is not evidence of agronomic accuracy. See live-validation.json for the current real-service demo results; no weather or diagnostic accuracy is implied beyond those records.
