# Whole-workspace UI finishing and verification — 04/10/2026

## Scope and evidence boundary

- Repository: `solar-fleet-ems`, branch `fix/real-data-engine-integration`, base HEAD `af4f1b8ab70d91e24ca0b44bc8b71d1c9f274be0`.
- Working tree already contained substantial previous application/test/documentation work. This is **uncommitted working-tree evidence**, not a release attestation or a clean-commit diff.
- Current request: continue UI across all screens/deep tabs, follow detailed mockups, no fabricated operational data; the conceptual SolarHub collage is not the visual target.
- No production backend/adapter/control changes in this UI pass. No vendor/customer login, hardware commands, push or deployment. Existing backend changes in the dirty tree belong to earlier work and were preserved.
- All test accounts/data are isolated, in-memory fixtures under `tests/`; outbound HTTP is blocked. The new empty fixture creates local test users only, with no plants, devices, integrations or samples. It is not a production startup mode.

## Implemented in this pass

| Area / mockup rows | Changes in actual code | Remaining boundary |
|---|---|---|
| Shared shell / all 26 | Consistent heading/card/field/table spacing, designed empty table rows, SVG menu icon, mobile drawer with Escape/focus, plant scope stored per signed-in user and validated after reload | No claim of exhaustive screen-reader, contrast, translation or pixel acceptance |
| Forms and live refresh | Submit can retry after validation failure; pre-existing disabled states preserved. Background refresh checks render epoch and avoids replacing specialist forms/drafts | Full live/concurrent action matrix remains broader than these regressions |
| Devices / 07, 16 | Removed legacy protocol panels that manufactured measurements/session outcomes; retained 15 protocol entries with real synchronized inventory and links to model/account/collector/control owners | No new live probe, scanner or write capability. Old standalone demo builders were removed rather than presented as operational tools |
| Model and collection / 07, 14, 17 | Two-column profile list/detail; register rows with explicit function/address/value validation; model/HA collection settings entered as labeled fields, not JSON | Requires registered agent/profile/evidence. Configuration validation/download does not prove hardware connectivity |
| Bulk / 18 | Five-stage guide, three-column blank target/settings/review editor, actual draft save, explicit values including valid zero, 1–20 target validation | Multi-vendor commissioning and unattended rollout remain unaccepted; saving a draft sends no command |
| Realtime / 26 | Six KPI tiles, energy-flow/chart/status layout, status column beside main and mini-charts, source-bound observed metric picker, four exact-unit mini-charts, retained empty frames | Mini-charts are V/A/Hz/°C observations, **not full AC-phase/DC-string/battery/latency parity**. No unverified sample is promoted to plotted telemetry |
| Geographic map / 05, 22 | Natural Earth public-domain land geometry, Mercator projection, finite actual GPS markers, zoom/pan/fit, keyboard selection, filter/list/detail, no pins for missing GPS | Coarse physical land only; no satellite/street tiles, province borders or full marker-cluster UX. Antimeridian/polar UX not accepted |
| Engineering input / 24 | Optional timestamp inputs use local date/time controls with displayed browser timezone, then serialize to UTC | Advisory fields are not a device control path |
| Handover, maintenance, incidents / 20, 23, 25 | Two-column handover structure before site selection, clearer maintenance filter grouping, SLA 2×2 desktop and single-column mobile | No electrical test, OTA, external escalation or signature/storage acceptance |

No operational seed was added. Map geometry is a geographic asset, not plant locations; provenance/revision/license are in `THIRD_PARTY_NOTICES.md`. Generated `map-land.js` is excluded from handwritten-code inventory. Generic SVG equipment glyphs do not claim a particular inverter model photograph.

## Consolidated automated verification

Commands run from repository root using `work/ui-venv/bin/python` / `work/ui-venv/bin/pytest`:

| Check | Observed result |
|---|---|
| `pytest tests -q` | **1,810 passed**, 13 warnings, 297.77 s, exit 0; full backend run earlier in this pass, before final UI-only refinements and empty-fixture harness addition |
| `pytest ui_tests -q` final | **78 passed**, 120.63 s, exit 0, after final production UI changes |
| `pytest ui_tests/test_ui_whole_workspace.py -q` before final monitoring layout tweak | 8 passed, 12.13 s; all included again in final full run |
| `ruff check src tests ui_tests scripts` | Passed, exit 0 |
| `node --experimental-vm-modules scripts/check-ui.cjs` | 48 modules parsed/linked, exit 0; syntax/linkage is not visual acceptance |
| `python -m build --no-isolation --outdir /tmp/solar-ui-whole-dist-final` | sdist + wheel built, exit 0 |
| Wheel inspection | New geographic/map/collection/history modules present; no `tests/` or `ui_tests/` paths; every packaged static file byte-matches current source |
| Emoji scan of production static tree | No U+1F300–U+1FAFF matches; visual controls use SVG icons. This scan alone is not a complete Unicode glyph audit |
| `git diff --check` | Passed |

Execution history is not hidden: initial browser run had 71 passes/4 failures; next had 74 passes/2 failures. Fixed unstable collection scroll/live rerender, disabled submit after validation, select readiness, hidden mobile account menu, mobile login wait and the rollout test's wrong expected status (actual creation is HTTP 201). An interrupted run ended with dots and no summary and is **not counted as passed**. New empty-installation test initially called an absent collection endpoint; corrected to the real `/api/fleet` contract. Final lint caught and fixed import order before the successful final run.

Final logs: `/tmp/solar-ui-whole-backend.log`, `/tmp/solar-ui-whole-browser-final.log`, `/tmp/solar-ui-whole-js.log`, `/tmp/solar-ui-whole-build-final.log`. These temporary logs can expire; the observed counts/commands/limits are preserved here.

### Added browser contracts

`ui_tests/test_ui_whole_workspace.py` verifies:

1. Plant scope survives reload; closed mobile drawer opens, navigates, closes with Escape and restores focus.
2. Valid GPS including 0/0 is plotted, invalid latitude is excluded, selection preserves zoom, filters remove markers, no command is created.
3. Realtime retains six KPI/three main cards/four mini-charts and no page overflow at 1600, 1024 and 430 px.
4. Rollout fields start blank; missing targets fail visibly; retry accepts an explicit zero in a real HTTP 201 draft; no commands are created.
5. All 15 protocol panels remain discoverable without legacy fabricated telemetry/session markers or JSON input.
6. Empty device history retains four chart frames and no plotted observations; responsive widths remain bounded.
7. A genuinely empty fixture traverses 31 main/deep routes, checks no page error or invented records, then verifies empty realtime/mobile layout.
8. Map HTTP 503 shows the actual failure, exposes retry and recovers without fabricated locations.

These are meaningful selected contracts, not every button in every permission/error combination.

## Visual review

Authenticated only against owned fixture port 8879, with its unique marker verified and browser requests restricted to that origin. Existing unrelated port 8767 was not used or stopped.

- **32 primary/site states**: 21 fleet views (overview, plants/list/map, topology, devices, control, TOU, EMS, data, incidents, reports, health, journal, users, accounts, site config, onboarding, security, rollout, handover, sources) and 11 site tabs.
- **29 deep desktop states**: customers, regions, add plant, benchmarking; model/native/health/firmware; realtime/audit/sync journal; seven source/data tabs; jobs/plans/firmware/playbook/SLA; schedule compiler/handover; network profile/document; source/notification policy.
- **5 mobile VI states** at 430×932: site config, control, schedules, sources, site overview. Desktop includes VI primary/site and EN deep views at 1600×1000.
- Final capture logs report no document overflow, page-level error text or browser exceptions in those 66 states. Full-size monitoring, rollout and empty-installation mobile captures were also inspected; composite sheets were used for the broad review.
- Captures and local review scripts remain under the task workspace's `work/matrix`, `work/deep`, and `work/qa-audit` in the repository. All contain fixture-only identities, never customer sessions. Temporary visual artifacts are not screenshot-regression baselines.

## Honest acceptance status

This pass reaches across the whole screen inventory, but **does not close R10 or certify pixel-perfect UI**. Specific remaining work includes exact phase/string/battery/latency chart semantics, complete EMS rule-builder/reference interaction parity, detailed onboarding/network topology, touch/resize calendar editing, full geographic layers, and broad accessibility/usability acceptance. Existing map/TOU/chart frames must not be populated with example data to hide these gaps.

Backend/product gates remain independent: tenant/customer self-service, Deye cross-customer application grants, GoodWe platform/discovery, real read-only account/device comparisons, production operations and per-profile hardware acceptance. Passing this fixture suite does not mean Deye/GoodWe login has been tested or the system is production-ready.
