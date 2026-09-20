# Core extension contract — 20 September 2026

Controller and command engine dispatch through `IntegrationRegistry`. Integration names, HTTP paths, credential transformations and response dialects belong to `adapters/`. Core accepts `PlantObservation`, `DeviceObservation`, `MeasurementObservation` and universal intents. `adapters/plugins.py` is the composition root.

## Adding an ecosystem

1. Implement a bounded authenticated transport and synthetic contract tests. The transport must allowlist network addresses; the application API is not a proxy.
2. Register an `IntegrationPlugin` with factory, observation decoders, namespace, provenance, credential contract and registration manifest. Common onboarding and provider discovery consume this manifest.
3. Supply feature declarations and translated native groups. Device UI checks these declarations without branching on vendor names. Empty groups are visibly unavailable, not fabricated support.
4. Supply a compiler only for reviewed intent semantics. The engine still checks commissioned capability, identity, ranges, role, fresh pre-read, preview digest, idempotency and post-write readback. Registration never unlocks control.
5. Supply code-reviewed `CommissionedTelemetryProfile` instances after hardware acceptance. Exact identity includes inverter, logger, firmware, protocol, account, privilege and region. Duplicate matches fail closed; native readings remain alongside canonical copies.

`tests/test_extension_data_stream.py` registers a synthetic tenth ecosystem with a different response shape, discovers and polls it, and exercises onboarding without changing core. That fixture is not a shipping adapter. Candidate Deye mappings now live in `adapters/deye_control.py`; shared budgets live in `budgets.py`.

GoodWe/Sungrow/Huawei/Growatt/Eybond still require concrete contracts, adapters and acceptance. Bluesun remains a brand with model-specific transport profiles.

## Data workspace

Collection policies have optimistic revisions, versions, bounded intervals and per-cycle caps. The 120-second controller tick and stricter adapter cap still apply. They do not change equipment sample configuration.

Mapping drafts pin identity and binding. UI supports observed-channel selection, units, direction, canonical target, evidence IDs, edits, simulation, versions and independent engineering review. Simulation never stores canonical samples or sends commands. Review does not install a profile. Firmware changes and revoked bindings reject simulation. Directional power, units, SOC bounds and signed temperatures are explicit.

UI separates fresh channels from verified channels. Fresh native telemetry does not become EMS input merely because it arrived recently.

## Realtime delivery

`/api/stream` is a read-only WebSocket with Host/Origin checks, existing session cookie, site filtering, four connections per user / 64 per process, and session/scope revalidation. Revocation closes the stream. It accepts no device commands.

SQLite retains up to 20,000 invalidations atomically with entity updates. Cursor gaps/excessive catch-up request a reset. Events contain only topic/site identifiers. A five-second send deadline disconnects slow consumers; clients reconnect with capped backoff. UI refreshes fleet/device monitoring while preserving open forms; management workspaces refresh explicitly.

This feed reduces ingestion-to-UI delay. It does not change cloud freshness, stream every detailed chart, increase equipment polling speed or establish a production fleet SLA. Clustering and production time-series storage remain outstanding.
