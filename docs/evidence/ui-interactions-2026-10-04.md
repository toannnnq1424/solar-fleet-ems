# Visual TOU, reports and explicit market inputs — 04/10/2026

## Scope

Continuation across 03–04 October, on the existing dirty `fix/real-data-engine-integration` tree, HEAD `af4f1b8`. No backend, adapter, login or commissioning changes in this batch. Prior user/backend edits are preserved. No commit, push, production deployment, real credentials, exchange orders or hardware commands.

Detailed SolarOne references `images/Screenshot 2026-09-13 132441.png` and `132542.png` guide schedule/report layout. The simple SolarHub collage is not a style target. No reference customer, plant, price, schedule or performance values were copied into runtime data. Synthetic values occur only in isolated tests and browser-only QA responses.

## Implemented

- `schedule-editor.js` replaces the old linear row editor through the existing shared schedule entry point. Seven-day calendar and side inspector remain present when empty; selecting an empty cell supplies only that explicitly selected time range, not a mode, power or battery target. Manual Add starts with blank times and values.
- Click/keyboard slot editing; desktop drag to another calendar cell; copy one day to explicitly checked target days; opt-in replacement; remove; undo. All modify local drafts until Save. Shared POST/edit/revision contracts remain unchanged. Overlap, overnight boundaries, whole SOC percentages, power bounds and 168-slot limit are checked. Copy is atomic, conflicts preserve the draft, unapplied edits block Save, and viewer controls remain absent. No automatic compile, deployment or command.
- The editor uses the shared modal, global CSS, SVG icons, responsive inspector and contained horizontal calendar scrolling. Tablet/mobile selection scrolls to the inspector. Fixed a visibly clipped modal footer found during QA.
- Reports have a main chart and four compact panels: self-use, battery cycles, grid import/export and daily incident counts. Existing API channels only; missing channels keep empty axes/gauges, not estimated data. Incident axes use whole counts. Production and consumption use line/point series, self-use/export use bars; missing observations break lines. Legend toggles and keyboard/pointer values are interactive, with an expandable complete daily data table.
- Export/archive form a right column. Archives use compact file rows and a real empty state, with accessible download actions. Report scope, permissions, formats and actual download endpoints remain unchanged. No fabricated PDF/email delivery or report categories. Vietnamese cost-estimate wording no longer exposes snapshot/revision terminology in the normal form.
- New `market-scenario-editor.js` removes the report calculator's raw JSON input. Optional engineering panel contains labeled capacity, scenario name, market, direction, delivery hour, quantity, bid price and assumed clearing-price fields. Rows/values start empty, prices and units are explicit, and no exchange/date/timezone is inferred. Same-hour price conflicts, duplicate names, missing values and capacity over-allocation are rejected before requests. Explicit zero/negative prices are retained. Inputs lock during calculation; changed inputs clear old results; failed requests preserve entries. Result cards show the API's advisory result, not a trading success claim.

## Verification

Commands use the ignored `work/ui-venv` environment:

```sh
work/ui-venv/bin/python -m pytest tests -q
work/ui-venv/bin/python -m pytest ui_tests -q
work/ui-venv/bin/python -m pytest tests/test_explicit_calculations.py tests/test_ev_fleet_and_market.py -q
work/ui-venv/bin/ruff check .
for module in src/solar_fleet/static/*.js; do node --check "$module" || exit 1; done
work/ui-venv/bin/python -m build --no-isolation --outdir /tmp/solar-ui-interactions-dist
work/ui-venv/bin/python scripts/measure_code.py --update-doc
git diff --check
```

Backend: **1,791 passed, 13 deprecation warnings, 284.81s**. Backend source stayed unchanged through subsequent UI refinements; the explicit-calculation/market subset also passed **38 tests, 2 warnings, 10.47s**. Final full UI rerun: **64 passed, 98.82s**. A subsequent mobile-modal padding/scroll-margin correction passed all **9 affected schedule/report/market browser tests, 16.91s**, with fresh targeted screenshots. Ruff, all JS syntax, package build, inventory and whitespace checks passed; build/inventory repeated after the final CSS correction.

Initial browser batch: 61 passed, 1 test timeout. The new test attempted desktop-sidebar logout after resizing to mobile; corrected it to open the actual Account menu before Sign out. Subsequent full runs passed 62, then 64 cases. No assertions removed to hide a UI defect. New contracts cover copy/collision/replace/undo/native drag, save/reload/edit, stale revision retention, unapplied edits, keyboard/mobile/viewer behavior, report toggles/unknown values/gaps, archived downloads, market inputs/errors/negative prices and absence of device commands.

Visual QA: recaptured 32 primary fleet/site views, 29 deep desktop views and 5 mobile views. Automated sweep found no document overflow, browser exceptions or caught-error text in tested views. These broad captures preceded the final market form/CSS refinements; targeted captures were repeated afterwards. Additional targeted screenshots cover schedule dialogs and report/market panels in desktop/mobile, VI/EN and empty/browser-only synthetic response states. Full-size inspection found and corrected the modal footer, content showing above its mobile sticky heading, and tiny mini-chart labels. Final mobile slot selection shows the inspector and both Update/Cancel slot controls unobscured. This is sampled visual QA, not pixel-diff acceptance of every state.

Scripts/captures reside locally under `/Users/toanlamsaoduocc/Documents/Codex/2026-09-30/users-toanlamsaoduocc-desktop/work/`: `ui_interaction_capture.py`, `interactions/`, `ui_matrix.py`, `matrix/`, `ui_deep_capture.py`, `deep/`. Fixture uses `tests/ui_fixture.py` on loopback 8879, isolated from production and real credentials. Targeted/deep capture scripts block non-loopback browser traffic. No screenshots with real customer records are committed.

## Remaining work / acceptance

R10 remains IN_PROGRESS. Calendar drag moves existing whole slots to visible boundaries; freehand painting/resizing and touch drag are not implemented (touch uses the inspector). Per-vendor schedule semantics and physical readback remain separate backend/hardware gates. Reports lack PDF/email, additional report workflows and full analytics parity; unknown cycles/financial KPIs cannot be made real through styling. Several EMS engineering calculators still use JSON, and map basemap, phase/multi-axis measurements, exact-model native forms and richer network/onboarding/rollout layouts remain open.

Next UI slice: simplify remaining EMS engineering forms, then continue measurement and network/onboarding detail parity with empty/error/populated states. After UI acceptance, perform the authorized Deye read-only baseline with user-entered credentials, repair observed backend contracts with regression tests, and run end-to-end QA. No production readiness or overall pixel-perfect claim follows from these local tests.
