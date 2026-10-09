# Observation inspector UI — 07/10/2026

## Scope

Continued gate U from the interface plan: frontend only, not the post-QA backend refactor.
Changed `static/device-history.js`, `measurement-chart.js`, shared `app.css`, canonical labels in `i18n.js`; added `ui_tests/test_observation_inspector.py`. Accumulated dirty worktree remains preserved; unrelated changes are not attributed to this slice.

Features: compare two selected channels of identical unit without aggregation; loaded-history time ranges; explicit native UNVERIFIED opt-in with hollow markers; primary-channel min/max/count/latest-time; latest 100 table rows with quality/source/binding. Channel identity includes device ID, metric, unit, binding and source. Four mini-charts retain empty frames. Single-series renderer rejects numeric strings/booleans/wrong units/INVALID data instead of coercing them into measurements. Canonical labels use backend-defined meanings; no inferred vendor aliases.

Filters and quality options affect display only. Historical GOOD samples may legitimately be old; history does not claim they are current realtime readings. Missing/future/invalid timestamps are excluded by the inspector, and no continuity or interpolation is fabricated. Loaded archive is not the complete cloud history.

## Verification

Commands use `work/ui-venv/bin/python` in the repository. Consolidated runs were followed by focused regression after final labels/identity refinements. Exact final results are recorded below when completed; no old test count represents a new pass.

- Full UI suite: **89 passed**, 150.50s. Ran across the frontend refinement period; not claimed as solely the final tree.
- Final affected UI suite (`test_observation_inspector.py`, `test_ui_whole_workspace.py`): **10 passed**, 17.31s.
- Backend regression (`python -m pytest tests -q`): **1,810 passed**, 13 deprecation warnings, 310.88s; no backend source changes in this slice.
- Final Ruff passed. All **51 JS modules** parsed/linked. Final sdist/wheel built; byte comparison matched **52 assets** (51 JS + app.css). `git diff --check` passed; source inventory regenerated, not counted as a test.

Browser tests cover explicit zero, same-unit-only comparison, different-device/binding separation, invalid/future/missing-quality values, native opt-in, time filtering, comparison reset, responsive bounds, empty whole-workspace layouts and no commands. All synthetic observations stay under tests/intercepted loopback responses, never production seed files.

## Visual QA

Marked isolated fixture: `ui-observation-20261007`, port 8879, backend outbound HTTP blocked and browser restricted to this loopback origin. Eight VI/EN device-inspector captures at 1600/1024/430 widths, plus one realtime screen; no page errors, page-level horizontal overflow or commands. Viewed desktop/mobile and realtime images. Source table capture from the synthetic regression was also inspected. An initial capture script used the wrong Vietnamese button text and timed out; corrected to the existing label and reran, not counted as a product failure or successful capture.

Artifacts: `work/qa-observation-20261007/` and `work/qa-audit/observation-inspector-desktop.png`, ignored local SIMULATOR screenshots. They are not production/customer evidence. Diagram/control mocks and the existing shared layout remain references; these captures do not establish whole-product pixel parity.

Owned port-8879 fixture was stopped after QA; unrelated servers were untouched. Temporary logs: `/tmp/solar-observation-ui.log`, `solar-observation-focused-final.log`, `solar-observation-be.log`, `solar-observation-js-final.log`, `solar-observation-build-final.log`. Counts and limitations are retained here independently of those temporary files.

## Remaining gaps

The UI cannot safely label generic voltage/current as phase A/B/C or MPPT/string without a supported mapping. Specialized AC/DC/battery/latency panels, network topology, nested EMS/action-schema UX, map layers and overall accessibility/pixel acceptance remain open. Canonical translations do not create new backend mappings. No Deye/GoodWe live login in this slice; prerequisites remain unchanged. No hardware writes, deployment or Git push.
