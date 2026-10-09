# UI refinement and VND rounding — 03/10/2026

## Scope and evidence boundary

Working tree on `fix/real-data-engine-integration`, baseline HEAD `af4f1b8`, already dirty. Existing adapter/control/optimizer changes were preserved. The only new backend change in this batch is the explicitly authorized monetary-rounding correction; no connector, authentication or hardware gate was changed. No commit, push, Deye login or production deployment.

The 35 files in `images/` were reviewed as reference sheets, with individual detailed images opened for layout inspection. The simple SolarHub collage is excluded as a style target. Reference values were not copied into operational data. Browser captures use the isolated `tests/ui_fixture.py` server and are visibly labeled SIMULATOR; those records are not production seeds.

## Implemented

- Global design system: consistent card/field/table rhythm, 216px navy sidebar, compact typography, blue actions, responsive columns and contained scrolling. Fixed the actual 1024px planning-layout overflow found by browser tests. No route stylesheet or inline CSS.
- Planning settings: replaced hourly-price JSON with 24 editable rows, explicit USD/kWh import/export units, blank initial values, user-triggered bulk fill and saved-value reload. Start time is explicitly Vietnam UTC+7; conversion is independent of browser timezone. Invalid dates, incomplete prices and non-whole-hour starts are rejected. Effective VND import-rate dates also use explicit Vietnam time. Battery efficiency is entered as a percentage and converted to the existing fractional API contract; no currency conversion or invented default rates.
- TOU: seven-day matrix persists even with zero schedules (42 empty cells, structural time bands only). Actual saved boundaries/modes/targets are used when present; overlapping slots are identified. Empty-cell action opens the shared blank draft editor, not a fabricated schedule. Saving/compilation and hardware rollout remain distinct.
- Control: compact function-card grid and readings sidebar. All 34 current API intents remain selectable exactly once, including less common electrical/native controls. Every preview uses the existing shared form and exact-capability/role gates. No universal settings or preset values are inferred.
- Alerts: three actual-count charts, full-width eight-column list, filters/pagination and separate detail/assignment panels. Empty alerts keep chart axes, list headers and detail structure. Retained create → assignment → notes → timeline → maintenance workflow. Fixed a detail-reload race that could replace a form while the user began typing; stale detail responses are ignored.
- Linking equipment: four-step navigation, manufacturer/type filters, separate cloud/local guidance and observed-binding review. Navigation is not presented as successful discovery or commissioning. No fake serials, topology or successful diagnostics.
- Sources: actual-source table, priority/collection cards, explicitly conceptual data-flow diagram, diagnostic counts and synchronization events. Accepted/received sample counts are not mislabeled as seconds of latency. Collection/diagnostic statuses are translated. An unpolled local collector no longer claims an active reading state.
- Site overview: all eleven blocks remain, with smaller flow/chart cards, non-clipped generation/consumption period facts and compact self-use gauge. Missing values stay unknown.
- Journal: empty list retains all twelve columns and detail panel. Removed invented fallback actor, vendor, source and notes; real zero before/after values no longer become dashes. Pagination buttons are genuinely disabled at bounds, and selection clears when a filter removes the selected command.
- Deeper screens: localized native-group title objects instead of `[object Object]`; regional summaries no longer display `null%` or a fixed-width fake distribution bar; unknown customer capacities stay unknown. Documents/network/policies/local-device/maintenance-plan/firmware lists retain table headers without records. Work orders retain empty detail structure. Firmware prerequisites use neutral requirement styling, not green passed checks; preliminary API checks are not called complete OTA readiness.

## Monetary correction

`ems_optimizer.py` rounds returned baseline and optimized whole-VND totals before deriving savings and the displayed savings percentage. Dispatch uses unchanged full-precision calculations. Profit derives from the same returned savings and degradation cost. A deterministic 2.4 → 1.6 VND case now returns 2 − 2 = 0, instead of independently rounding 0.8 to 1. Additional tariff/load cases check returned arithmetic identities, zero and negative savings. This is not utility billing certification or a change to per-slot cost allocation.

## Verification

Commands use the ignored local environment `work/ui-venv`:

```sh
work/ui-venv/bin/python -m pytest tests -q
work/ui-venv/bin/python -m pytest ui_tests -q
work/ui-venv/bin/python -m ruff check .
for module in src/solar_fleet/static/*.js; do node --check "$module" || exit 1; done
work/ui-venv/bin/python -m build --no-isolation --outdir /tmp/solar-ui-refinement-dist
work/ui-venv/bin/python scripts/measure_code.py --update-doc
git diff --check
```

Final runs: **1,791 backend tests passed, 13 dependency deprecation warnings, 289.81s**; **56 browser tests passed, 87.70s**. Ruff, all JavaScript syntax checks, sdist/wheel build and whitespace checks passed. The subsequent CSS edit only combined identical cascading declarations, with no effective style change. Earlier QA found and corrected planning overflow, a test fixture brand mismatch, a missing region-render helper, control-test readiness and incident-detail form replacement. Assertions were not lowered to hide arithmetic or UI failures.

Visual review: 32 primary fleet/site routes at 1600×1000, plus 29 deeper desktop views and five 430px mobile views. VI primary/mobile and EN deep views. Scripts/captures are local artifacts under `/Users/toanlamsaoduocc/Documents/Codex/2026-09-30/users-toanlamsaoduocc-desktop/work/`: `ui_matrix.py`, `ui_deep_capture.py`, `matrix/`, `deep/`. Final route sweep reported no document overflow or browser exceptions; corrected deep sweep also checked caught runtime-error text. Contact sheets supplement, not replace, full-size inspection. Old dialog/mobile captures in `matrix/` are not counted as fresh captures.

## Remaining acceptance, not hidden as credential blockers

R10 stays IN_PROGRESS. This is not pixel-perfect acceptance for every screen, dialog, responsive breakpoint and populated/error state. Street/satellite basemap, multi-metric/phase/MPPT chart sets, direct drag/copy TOU editing, exact-model advanced field schemas, richer rollout/network/onboarding interactions and some engineering JSON calculators remain unfinished. The prototype images include features not yet connected to product workflows; a well-styled locked card does not implement those features. No production-readiness percentage is inferred from LOC, screenshots or passing simulator tests.

Next: keep UI-first priority and work through those interaction/layout gaps with empty and actual-data states. Once UI acceptance is reached, perform an authorized Deye read-only baseline with the user entering credentials directly; then repair observed backend contracts with regression tests and rerun end-to-end QA. Do not delay all testing until after backend work or claim email/password-only support from a redesigned form.
