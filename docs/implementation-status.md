# Implementation status — 0.2.0 pilot

28 September follow-up: Reports analytics optionally freezes observed import-cost
inputs (actual sample rows, selected meter/site revisions, tariff versions and
interval provenance) into immutable CSV/XLSX/HTML artifacts. Not a utility bill;
30-day/20-site/10,000-sample-per-site limits. Rate correction and archive retention
remain open. [Verification](evidence/report-cost-snapshot-2026-09-28.md).

Updated **2026-09-27**, based on the source snapshot inspected before commit. This replaces earlier route-count and “completed flow” statements. The repository is **not yet a mature multi-vendor O&M/EMS product**. No customer hardware acceptance was performed in this audit.

The [26-screen coverage matrix](mockup-coverage.md) owns the feature inventory, sidebar responsibilities, estimate → existing code → unbuilt scope → completion criteria, and reproducible BE/FE/test LOC. The [multi-vendor contracts](multivendor-contracts.md) index the researched API differences and subsequent Eybond work. The [validation index](validation.md), including the latest [legacy reuse / flow record](legacy-validation-2026-09-27.md), distinguishes executed checks from pending acceptance. Return to the [documentation index](README.md) or [project README](../README.md).

## Current application boundaries

### 28 September follow-up: declared import-rate estimates

Settings now appends non-overlapping, UTC-normalized VND import-rate versions with
source, creator, whole-site optimistic revision and transactional audit. EMS prices
only accepted observed-power intervals wholly contained in one declared rate version;
returns interval endpoints/power/energy, version IDs, sources and priced coverage.
Missing or boundary-crossing prices do not become zero-cost energy. No legacy EVN
table is silently applied. This is not utility billing or a verified tariff: taxes,
demand/reactive charges, export credits, tariff correction/supersession and report
export integration remain unbuilt. See the [batch evidence](evidence/import-rates-2026-09-28.md).

The subsequent [Eybond read integration](eybond-read-integration.md) and [24 September validation](eybond-validation-2026-09-24.md) extend the original audit with DessMonitor/ShineMonitor account→collector→native telemetry workflows. They do not change the pilot or uncommissioned-hardware conclusion.

| Area | Connected application behavior | Still missing |
|---|---|---|
| Shared UI | One shell, 15 sidebar destinations, global app.css, VI/EN, shared forms/tables/dialogs; accounts include Eybond and Bluesun profiles | Full visual/usability/accessibility acceptance of all 26 references; translation, narrow tables, diagram and dashboard polish |
| Plants/devices | Scoped metadata, customers, inventory, topology records, coordinate view, device bindings | Physical discovery, cross-transport identity reconciliation, basemap, full electrical topology |
| Overview/history | Stored measurements with quality/time/source, nullable KPIs, counter deltas/reset/coverage, 11 site blocks; GPS-based Open-Meteo weather and forecast; shared animated site/device power flow with source/freshness gating | Long-term storage/backfill/rollups, complete energy accounting, verified electrical topology/source-to-load attribution and multi-axis charts |
| Accounts/adapters | Encrypted credentials and eight cloud read paths of different depth: Deye, Solis, SOLARMAN, GoodWe, Sungrow, Huawei, Growatt, Eybond/SmartESS. Eybond has explicit DessMonitor/ShineMonitor platforms, session signing/expiry, collector discovery and native reads | Eybond source timestamps/canonical mapping/history/alarms/control, scalable incremental discovery; Bluesun model-specific acceptance; complete refresh/history/alarm pipelines and native schemas across vendors |
| Mapping/sources | Native observations, exact profile matching, source priority/discrepancy; VI/EN mapping editor with scoped observed channels, unit/direction selection, simulation, revision history and independent review; identity/binding/account/agent revalidation; collection policy and polling limits | Shipping canonical profiles and activation/commissioning workflow, source failover acceptance across all views |
| Realtime | Authenticated scoped WebSocket invalidations, durable cursor/reset/revocation, monitoring refresh | Distributed fanout, clustered workers, load/soak acceptance and detailed streaming charts |
| Local Agent | Token enrollment/ingest, sequence/replay, SQLite outbox and Modbus TCP / SOLARMAN V5 model collector plus explicit HA sensor bridge; 41 pinned community profiles (913 decoders) | Service installation/discovery, RTU and full model protocol suite, mTLS/rotation, managed update, offline operation and diagnostics |
| Remote control | Capability → preview/diff → confirmation → lock/idempotency → native send/order → readback → journal/quarantine | Deye is the only registered intent compiler; most model-specific write contracts and actual hardware acceptance are absent. Guessed non-Deye mappings were removed |
| Native configuration | Vendor/OEM capability reasons, groups and documentation | Actual field schemas and supported CT/grid/BMS/generator/ATS/raw read/write per model |
| TOU/bulk | Versioned weekly drafts, compile artifacts, full-week/timezone/DST checks, source digest revalidation, canary/rollout outcomes | Per-vendor schedule semantics, accepted physical readback and unattended execution |
| EMS | Conditions/actions evaluator, unit/freshness validation, dry run and monitor-only hold/notify; history-trained hourly baseline (not optimizer) | Physical dispatch, optimizer, hysteresis, conflict arbitration and accepted offline policies |
| Incidents → maintenance | Correlation/dedup/order/recovery, assignment/notes/timeline/SLA/playbooks, linked jobs; versioned execution plans, time/void, independent review and closure | Actual vendor alarm decoders, channel delivery, evidence uploads, materials/service contracts |
| Commissioning | Manual checklist/evidence references, diagnostics and six-check handover gate | Electrical procedures, measurement-backed acceptance, uploaded evidence/signatures; manual PASS does not unlock writes |
| Reports/journal | Scope/date-bound immutable CSV/XLSX/HTML artifacts; actual command state/readback and audit history | PDF/email, verified tariff/CO₂/savings assumptions, scalable history and external audit anchoring |
| Administration | Local users, five roles/site scope, CSRF/session revoke, encrypted vault, API keys and audit; concurrent-session regression fix | SaaS tenancy, MFA/SSO, key rotation/restore UI and externally anchored audit |
| Firmware/network | Draft requests/configuration and permission checks | Package signature/compatibility/transfer, actual OTA/network writes, certificates, recovery and rollback |

## Scale and evidence limits

One controller process with SQLite WAL; telemetry retention is at most seven days / 200,000 points. The poller uses per-adapter caps and a 120-second base tick. The frontend uses JavaScript ES modules, not the React/TypeScript assumed in the user's mature-product estimate. These constraints are not fleet-scale service guarantees.

Successful authentication, a public endpoint, a community decoder, a rendered route or a passing fixture does not establish hardware support. Native history/alarm helpers still need canonical ingestion, persistence, quality, permissions and UI integration. Unsupported measurements and outcomes remain unknown; production routes must not fill them with simulator values.

The large LOC gap reflects substantial unbuilt engineering, in addition to reuse and the smaller deployment model. Vendor logins can supply contract evidence; they do not build the missing agent, native UI, EMS dispatch, OTA, tenancy, long-term storage or acceptance processes. Track completion using the coverage matrix's acceptance conditions, not line-count percentages.
