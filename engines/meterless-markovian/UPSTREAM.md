Meterless Markovian reference implementation, Apache-2.0.
Source: https://github.com/Meterless/Meterless/tree/1742dec56a66e58eef9dda2d2b865823758ca8cd/engines/markovian/reference/src
Vendored src files are unmodified. bridge.mjs is AgriSleuth integration code.
Uses the real runtime for bounded RESEARCH chunks, checkpoint extraction, compression, completion and config-snapshot accounting. Persistence is PostgreSQL in the host. The host applies Critic/Judge validation; the reference reflection call is disabled. Token metrics are estimates, not measured savings.
