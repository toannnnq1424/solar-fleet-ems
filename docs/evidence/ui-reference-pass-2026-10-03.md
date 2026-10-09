# UI reference and image pass — 03/10/2026

## Scope and baseline

- Branch `fix/real-data-engine-integration`, HEAD `af4f1b8`; remote fetched at the start of this pass. Existing uncommitted backend, tests, docs and frontend changes were preserved. This pass changes frontend/UI tests/documentation, not production backend or adapter semantics.
- Reviewed the 35 image files in `images/` as visual references. The simple SolarHub collage supplied by the user is a conceptual feature illustration, not the styling target or a reduced feature specification. Detailed mockups remain the reference; example customer/energy data is not application data.
- No commit, push, production deployment, customer login, or physical device command was performed.

## Implemented

- Shared navy sidebar, white header, pale background, compact cards/tables/actions and consistent outline SVG icons. Removed emoji from rendered primary navigation and screens; route checks cover Vietnamese at 1600px and 430px.
- Site overview keeps 11 tabs and actual API-backed blocks: energy flow, stored power observations, production/consumption, self-use, weather, equipment, alerts, command history, connectivity, location and site information. Removed fabricated curves/equipment/settings and false success feedback. Missing values stay unknown, not zero. All-plants scope no longer silently chooses the first plant.
- Portfolio search/vendor filter uses stored plants. Add-plant workflow preserves unspecified metadata; installation type is nullable. Steps distinguish current, completed and future. No sample owner phone/email is presented as actual contact information.
- Three user-provided plant photographs illustrate **declared** installation types: residential, commercial rooftop and ground mount. Reused in the type picker, portfolio/site surfaces through `plant-media.js`; visible illustration label and accessible description. Unknown types use an SVG fallback. No manufacturer image was downloaded or assigned from brand alone, and these assets are not customer site photographs.
- Deye and other forms that need additional credentials first explain the current connector requirement, without collecting a password at that stage. Users can view a request for their installer, defer setup, or enter supplied connection details. Saving a configuration is not reported as successful vendor authentication. Email/password-only Deye connection is **not implemented by this UI change**.
- All 34 current control capabilities remain discoverable in five groups, with readable labels and lock reasons. Engineering calculators are collapsed, not removed; existing safety gates remain. Unverified vendor tool screens clearly stop before pretending to offer live controls.
- Schedules display saved weekly slots with a 24-hour SVG timeline; gaps remain gaps, invalid geometry is skipped, and the chart is explicitly not execution status. Existing editor/compile/rollout ownership is retained.

## Verification actually executed

Environment: local Python 3.14 venv `work/ui-venv`, Playwright Chromium, isolated `tests/ui_fixture.py`. Tests use simulator-only accounts/devices. No real vendor credentials.

| Check | Observed result |
|---|---|
| `work/ui-venv/bin/python -m pytest -q tests` | 1,789 passed, 13 warnings, 295.91s; no backend source edits afterwards |
| Separate browser suite after nullable type fix | 43 passed, 69.12s |
| Added valid/invalid saved-slot timeline contract and focused rerun | 6 passed, 9.31s; includes five existing UI contracts |
| Final expanded browser suite | **44 passed, 71.01s**, after wizard progress-state polish; do not add rerun totals together |
| Ruff, all static JS syntax, sdist/wheel build, whitespace | Passed; Ruff/JS/build rerun after final runtime edits |
| Render matrix | 21 fleet routes + 11 site tabs at 1600px, no page errors, no document overflow; screenshots visually reviewed using contact sheets and representative full pages |
| Responsive contracts | 14 primary routes at 1600px/430px, no emoji or horizontal document overflow |

Browser tests include image/type matching, unselected type remaining blank, loaded local images, explicit illustration captions, email-only onboarding guidance, absent-data behavior, preserved capability count/no command on preview, and actual timeline geometry without synthesized slots. Existing wizard contracts caught a 422 for empty-string type; fixed by submitting null and rerun passed.

Local screenshot artifacts (simulator only): `work/qa-audit/` in the repository and `/Users/toanlamsaoduocc/Documents/Codex/2026-09-30/users-toanlamsaoduocc-desktop/work/matrix/` in this task workspace. The latter includes `plant-illustrations.png` and `deye-connection-guide.png`. These are QA artifacts, not production/sample assets.

## Still open — not a production or pixel-parity certificate

- Full reference-by-reference pixel/usability acceptance remains open, especially long engineering/settings pages, interactive chart parity and advanced device screens. Route rendering tests do not prove every nested workflow or accessibility requirement.
- Geographic view is a coordinate plot, not a finished street/satellite map. Drag-and-drop schedule editing, full multi-series accounting charts and model-specific device photography still need work. Existing 26-screen and estimate/code/unbuilt/acceptance matrices remain authoritative; no feature is marked complete because a tab exists.
- Do not revive the prior roadmap's absolute claims such as zero-knowledge credential handling, complete removal of every fake value, full hardware support or complete UI humanization. This pass found counterexamples in executable frontend code.
- User authorized a later visible Deye login with credentials entered directly by them and read-only inspection. It has **not** happened. Per their ordering, continue UI work before backend/core changes or that live account test; never request passwords in chat or automate physical configuration.
