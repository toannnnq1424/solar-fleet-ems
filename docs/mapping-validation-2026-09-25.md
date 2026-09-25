# Mapping workspace — implementation and validation, 25 September 2026

This batch joins the existing mapping backend to the shared Data → Mapping UI. It consumes observed fields from the selected device and connection; it does not contain vendor-specific sample readings or automatic unit/sign guesses. No live vendor account or equipment was accessed. Validation was performed on the source snapshot before commit. See the [validation index](validation.md) and [documentation index](README.md).

## Connected behavior

- `GET /api/devices/{id}/mapping-context` checks site access and returns an allowlisted device identity, available cloud/local bindings, observed values/units/timestamps/quality, compatible dimensions and public evidence references. Unknown units remain visible but unavailable for canonical mapping. Connection credentials are excluded.
- The VI/EN editor selects only observed keys, offers compatible target dimensions, exposes independent positive/negative power transforms, retains absent fields from existing revisions for diagnosis, rejects duplicate outputs, and records evidence/notes. It uses the existing dialog/forms/tables/sidebar and `app.css`; no private stylesheet or copied navigation.
- Draft creation/editing uses optimistic revisions. Simulation displays the selected source beside the candidate output; it writes no telemetry. History shows each saved revision and review. An independent Senior Engineer can review the current draft; editing creates a new unreviewed revision.
- Backend save/simulate/review validates active bindings. Simulation/review also rechecks identity. A missing/disabled cloud integration, revoked binding or removed agent membership invalidates the draft's applicability. Stale/invalid values now produce no candidate; original observations remain diagnostic evidence.
- Review does not activate a profile, change a KPI or enable device control. Commissioned profiles still require the separate exact-identity acceptance path. This distinction is visible in every mapping dialog.

## Verification record

| Check | Result | Evidence |
|---|---|---|
| Entire backend suite | **450 passed**, 273.36 s, 13 existing deprecation warnings | `work/mapping-backend-tests.log` |
| Entire browser suite before navigation QA repair | **13 passed**, 66.01 s | `work/mapping-browser-tests.log` |
| Affected browser suite after navigation QA repair | **8 passed**, 102.02 s: mapping workflows, legacy/canonical navigation, all sidebar/site navigation and account/native readings regressions | `work/mapping-navigation-tests.log` |
| Ruff check + format check after changes | Passed; **116 Python files** formatted | `ruff check src tests ui_tests scripts`, `ruff format --check src tests ui_tests scripts` |
| JavaScript syntax and module linkage | **29 modules** passed; browser execution checked separately | `node --experimental-vm-modules scripts/check-ui.cjs` |
| Package | Wheel + sdist built successfully; **99 runtime files** byte-match source in both archives; MIT notice included; no work/fixture images/cache/DB/key files in runtime wheel | `work/mapping-build.log`, `work/mapping-package-verification.log` |
| Source inventory | BE **14,643**, FE **17,726**, tests/fixtures **9,020**, scripts **159** physical lines | `scripts/measure_code.py --update-doc`, per-file JSON inventory in `docs/evidence` |

The 8 browser cases are an affected rerun including one newly added route test. Do not add 13+8 as unique cases: the repository now contains 14 browser cases. No backend source changed after the full 450-case run. The 13 warnings concern Starlette's httpx/AnyIO compatibility and existing per-request cookie tests; none were suppressed.

Build uses isolated hatchling 1.32.4. Artifacts for this runtime snapshot:

- `dist/solar_fleet_ems-0.2.0-py3-none-any.whl`, 380,578 bytes, SHA256 `e677076fb6d77e8562ce529a6106095b5b32b08911952f6b691d9305bd200f78`.
- `dist/solar_fleet_ems-0.2.0.tar.gz`, 519,273 bytes, SHA256 `31cd3c6fe81fd796b47322336e69d77f16c87a8d88a3e5ccecb17d4353199432`.

Final validation results were recorded in this Markdown after the build. The subsequent pre-commit documentation refresh also removed one extra blank line at the end of `static/journal-workspace.js`; no runtime statement changed. The byte-match result, LOC above and artifact hashes refer to the original build snapshot, not to a rebuilt final commit. Current source counts are maintained in the [coverage inventory](mockup-coverage.md). These are local validation artifacts, not a deployed release.

## Visual QA finding and repair

Initially inspected the actual browser screenshots for mapping authoring and reviewed Viewer access. The Data screen rendered both legacy workbench tabs and a second Data tab row. Route ownership is now centralized in `data-workspace.js`: legacy `quality/mapping/sync/agents/cloud` and canonical `main/<tab>` routes use one tab row and the same forms, and the Measurements link reaches the stored-telemetry screen. No sidebar or CSS was duplicated.

After the repair, directly inspected `work/qa-audit/test_mapping_editor_simulation_revision_review_and_viewer_access.png` and `test_data_legacy_routes_share_one_tab_row_and_measurements_remain_reachable.png`. Both show one Data tab row, the shared sidebar, and correct VI labels; Viewer access exposes simulation/history without editing. The editor screenshot also demonstrates preserved input and a clear duplicate-output validation error. Long forms scroll within the shared dialog. This is desktop functional/visual QA of the changed workflows, not pixel matching or accessibility acceptance of all 26 screens.

## Remaining product gaps

Shipping canonical model profiles, field commissioning, profile activation/deployment/lifecycle UI, timestamped Eybond history, vendor alarm ingestion and cross-view failover acceptance are not completed by this editor. The source registry supplies documents for comparison; choosing a document does not prove it applies to a model or measurement. Draft review is a software workflow, not a hardware acceptance result.

The [26-screen matrix](mockup-coverage.md) remains the owning scope/LOC report. None of its 26 mockups has full product and hardware acceptance.
