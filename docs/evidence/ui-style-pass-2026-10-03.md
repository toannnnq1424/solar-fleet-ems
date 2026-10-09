# Detailed-reference UI continuation — 03/10/2026

## Scope

Continuation on `fix/real-data-engine-integration`, HEAD `af4f1b8`, dirty working tree. Preserved pre-existing backend/test changes. This batch edits frontend, browser tests and documentation only. The user's simple eight-panel SolarHub collage is explicitly **not** the style target. Reviewed all 35 local reference images; detailed SolarOne mockups guide shared typography, spacing, cards, tables and page compositions. Their sample values are never production data.

No Deye login, real credentials, physical command, deployment, commit or push. Test fixtures remain isolated from production. Previous evidence in `ui-reference-pass-2026-10-03.md` is historical; the results below supersede its suite counts for the current tree.

## Implemented and preserved

- Shared global styles: compact typography, 58px topbar, card/table/form spacing, SVG metric tiles, responsive grids and contained table scrolling. Fixed Vietnamese user-permissions overflow discovered during browser QA.
- Site overview: three-column desktop composition for the eleven existing data blocks, retaining all eleven site tabs. Compact energy flow/history and a self-use gauge using the actual API value. Missing values produce no filled gauge or fake curve; zero stays a valid value.
- Reports: actual daily PV/load/export bars and table, side-panel exports and self-use gauge. No synthetic bars for absent, negative or nonnumeric daily values. Market engineering calculator remains accessible in a collapsed section.
- Control: capability groups and current-readings sidebar; all 34 current capabilities remain discoverable with their existing gates and lock reasons. No backend control semantics changed.
- EMS and incidents: actual-record counts, compact filters and two-column arrangements. Counts do not imply operational success.
- Map: searchable actual plant directory, coordinate plot and selected-site details. Missing GPS generates no marker. Explicitly a coordinate view, not a street/satellite map. Selection and empty search states tested without commands.
- Settings: directory/permissions layout; grouped battery fields, ownership/operating shortcuts and saved-record panels; translated checklist keys/statuses and plain battery-level labels. Removed fabricated fallback audit IP. JSON price input still exists and remains a usability limitation, not a completed nontechnical setup wizard.
- Sources: actual configured/synchronized source counts and priority sidebar. A synchronization timestamp is not labelled proof of being online.
- Empty measurement charts retain grid/unit context without observations. Plant illustrations stay mapped to declared type with illustration captions; unknown type uses SVG. No image of a guessed inverter/logger model.

## Verification

Environment: local `work/ui-venv`, Python 3.14, Chromium, isolated `tests/ui_fixture.py`. Commands run from repository root.

| Check | Result |
|---|---|
| `python -m pytest -q tests --tb=short` | **1,788 passed, 1 failed**, 13 warnings, 308.39s |
| Focused `tests/test_ems_optimizer.py::TestEMSAPI::test_ems_optimization_route` | Same failure reproduced, 1 failed, 1.15s |
| Browser suite before final label/spacing polish | 47 passed, 89.09s |
| Final browser suite after label/spacing polish | **47 passed, 78.66s**, exit 0 |
| Ruff, every static JS syntax check, wheel/sdist build | Passed after final runtime changes |
| Desktop screenshots | 21 fleet routes + 11 site tabs, 1600px, no page errors/document overflow; contact sheets and representative full pages visually inspected |
| Responsive contracts | Existing 14-route checks at 1600/430px; seven new compositions at 1600/1024/430px; no document overflow |
| Final visual spot checks | Plant configuration desktop, reports mobile, data-history empty state; missing-data displays preserved |

New `ui_tests/test_reference_style.py` covers valid/unknown/zero chart semantics, page composition/reflow, translated saved-record labels, actual directory selection, absent GPS and no physical commands. Existing market-calculator test now explicitly opens its details section; no assertion was weakened to accept fake data or the backend failure.

The intermediate label test incorrectly searched hidden raw JSON as well as visible labels (46 passed / 1 failed). Corrected the test to assert translated checklist cells and keep technical keys only in the intentionally collapsed draft; the full rerun above passed. This is a test-scope correction, not removal of the translation requirement.

Screenshots are simulator-only QA artifacts under `/Users/toanlamsaoduocc/Documents/Codex/2026-09-30/users-toanlamsaoduocc-desktop/work/matrix/`, not shipped operational seed data. They are visual checks, not a pixel-diff certificate.

### Confirmed backend arithmetic inconsistency — deferred, not hidden

`tests/test_ems_optimizer.py:165` expects returned net savings to equal the difference of the returned baseline/optimized totals. Observed payload: baseline **1,868**, optimized **10,289**, net savings **−8,422 VND**, whereas the returned totals differ by **−8,421 VND**.

Source inspection: `ems_optimizer.py:333` computes the unrounded difference; lines 357–359 independently round all three returned fields. Independently rounded amounts need not satisfy the displayed accounting identity. This existing backend code was not modified; neither was the failing test. The fixture uses the current time, so the earlier pass is not proof this case is consistently green. The final tree cannot be called fully passing or production-ready.

## Remaining acceptance and next order

R10 remains IN_PROGRESS, not closed by screenshots or route presence. Shared style is applied broadly, but exact pixel/interaction acceptance, nested engineering/device workflows, accessible/mobile usability, nontechnical price entry, street/satellite map and richer chart/schedule-editor parity remain unfinished. No complete-feature or hardware acceptance claim.

Recommended sequence: finish UI/usability acceptance → user-entered Deye login with read-only observation → repair backend account/discovery/read/persistence/UI paths using those observations and regression tests → consolidated QA/pilot gates. Do not blindly overhaul the backend first or postpone all testing until its end. Do not collect credentials in chat, treat successful browser login as proof of connector support, or send device configuration commands during read-only discovery.
