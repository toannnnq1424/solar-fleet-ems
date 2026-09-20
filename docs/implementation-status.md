# Implementation status — 0.2.0

Updated 2026-09-20. [26-screen coverage](mockup-coverage.md) is the detailed BE/FE inventory and sidebar specification. This is a local pilot, not the complete v1 product. No live hardware acceptance is claimed.

| Area | Implemented application behavior | Remaining |
|---|---|---|
| Shared UI | One shell, 13 sidebar destinations, global app.css, reusable forms/tables/dialogs, VI/EN; account layout follows mockup 21 | Complete visual/usability acceptance, accessibility and translation polish |
| Plants/devices | Metadata, customers, scoped inventory, manual assets, topology, coordinate map, bindings, readings/history | Real basemap/clusters, full plant dashboard, weather/forecast, hardware identity acceptance |
| Multi-vendor core | Plugin registry, observation DTOs, credential contracts, native descriptors, compiler; synthetic extra-vendor test | Five other ecosystem adapters; actual OEM/model acceptance |
| Cloud accounts | Deye/Solis/SOLARMAN read clients, encrypted setup, connection checks, cooldown, suspend, scoped read API keys | Live grants/data validation, other clouds, actual local-agent certificates |
| Telemetry/mapping | Native provenance, quality, source priority, discrepancy; draft editor/simulation/review/version; exact code-registered profiles | Shipping canonical profiles, cloud backfill, production time-series store |
| Realtime | Scoped authenticated WebSocket, durable bounded invalidations, cursor/reset/revocation; monitoring refresh | Detailed chart streaming, production fanout/cluster load acceptance |
| Collection | Per-integration interval/cap policies applied by polling, revision history, status/cursor inspection | Agent service configuration, distributed scheduling |
| Local Agent | Site/device token ingest, sequence/replay, SQLite outbox, upload CLI; optional SOLARMAN V5 read collector | mTLS/service/update lifecycle, auto discovery, hardware/profile acceptance |
| Control | Intent preview/diff/confirm, locks, persistent idempotency, fresh read, order/readback, audit; exact per-device/account acceptance registry with expiry, revocation and ambiguity rejection | Shipping hardware acceptance, model-specific native contracts and live readback; new profile code/tests not yet verified |
| Native UI | Adapter capabilities, nine groups and documentation | Actual native field schemas and model-specific grid/BMS/CT/generator control |
| TOU | Weekly editor/version/copy; compile API/UI with full-week gaps, timezone/DST, adapter translation, saved explanations, source digest and guarded rollout preparation | Shipping vendor translators, real device schedule acceptance, optimizer and unattended execution; new code/tests not yet run |
| EMS | Multiple AND conditions/actions, deterministic dry-run, unit/freshness checks; timed hold/notify monitor | Physical dispatch, optimizer, hysteresis/conflict policy, forecast planning |
| Bulk | Persistent rollout, compatibility, canary then remaining-device confirmation, cancellation, outcomes | Shipping profiles and scalable deployment scheduler |
| Incident center | BE/FE filters, triage, assignment, notes, append-only timeline, 24/7 SLA snapshots/escalation, versioned playbooks/checklist, linked work; adapter-neutral alarm correlation with duplicate/order/recovery handling | Actual vendor alarm decoders, model-specific playbooks, external notification, evidence uploads; new code/UI tests not yet executed |
| Maintenance execution | BE/FE plan versioning, checklist/evidence references, work time/overlap/void, independent review, digest/reviewer/evidence revalidation before closing, reopen workflow; observation health and service calendar; append-only execution history | Materials/procurement, service contracts, actual file storage, electrical health methods, firmware compatibility/OTA; new BE/browser tests authored, not executed |
| Commissioning | Manual checklist, diagnostics, six-check handover gate and report | Electrical tests, signatures, physical acceptance |
| Reports | CSV/XLSX, coverage/reset-aware counter analytics, printable global-style HTML | PDF templates, verified savings/CO2/yield, distribution |
| Administration | RBAC/site scope, users/session revoke, vault, scoped API keys, audit hash chain | Hosted multitenancy, SSO/MFA, backup/rotation UI, external checkpoints |
| Firmware/network | Persisted requests/network drafts with permissions | Firmware/network writes, certificates, recovery/rollback |

One controller, SQLite WAL, telemetry retention at most seven days / 200,000 points. Polling uses adapter caps and a 120-second base tick. These are pilot limits, not a fleet-scale SLA. Missing data is not populated with production fixtures.

Vendor logins enable contract verification; they do not complete the independent engineering above. See [core extension contract](core-extension-contract.md).

The separate estimate → implemented code → unbuilt scope → completion criteria table and reproducible BE/FE/test inventory are in [mockup coverage](mockup-coverage.md). Do not use route count or LOC as a completion percentage. Implementation and test authoring continue; final test/build/QA is deferred as requested.
