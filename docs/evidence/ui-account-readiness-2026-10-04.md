# Account readiness, EMS draft editor and TOU — 04 October 2026

Repository: `/Users/toanlamsaoduocc/Desktop/solar-fleet-ems`, branch `fix/real-data-engine-integration`, HEAD `af4f1b8ab70d91e24ca0b44bc8b71d1c9f274be0` plus a pre-existing dirty working tree. This batch is uncommitted. Existing user changes were preserved; the full diff from HEAD is not attributable solely to this batch.

## Delivered and bounded

| Area / mock inventory | Implementation | Not claimed |
|---|---|---|
| Accounts / 21 | Password-free preflight reads actual Deye app configuration; GoodWe platform choice and SEMS+ warning; diagnostic account/vendor selection locked while in flight; actual counts including zero; clear partial-sample limits | GoodWe SEMS+ authentication, customer self-service/tenancy or Deye cross-customer grants |
| Synchronization / 17, 21 | Existing global `/sync` action now has a scope-confirmation dialog listing enabled accounts; cancel makes no sync request | A new account-scoped backend sync endpoint; success of every vendor inferred from HTTP success |
| EMS / 24 | One shared three-column editor for create/multi-condition/edit; observed metric/unit selection; explicit blank thresholds/actions; optional manual technical fields; async response fencing; boolean and work-mode parameters; actual draft persistence | Nested/OR logic, fully model-aware value schemas, automatic dispatch or all reference interactions |
| TOU / 09 | Empty weekly matrix preserved; pointer and keyboard resize; 15-minute snapping; touch-friendly choose-destination move; overlap/midnight validation and undo; save draft only | Freehand drawing, physical phone/tablet acceptance, per-model rollout semantics or running schedules on hardware |
| Documentation | Main [vendor access guide](../vendor-api-access-guide-vi.md) plus seven platform/OEM guides alongside existing Deye document; official sources and uncertainties separated | Contracts accepted, applications submitted, secrets acquired or all adapters made compatible |

No new production seed/telemetry, emoji or hardware capability. Structural time bands are axes, not simulated schedules. Fixtures and browser interactions use isolated test data only. Shared `app.css`, existing shell, 15 navigation owners and 26-screen inventory remain canonical.

## Consolidated checks actually executed

Use `work/ui-venv/bin/python` for Python commands below.

| Command | Observed result |
|---|---|
| `python -m pytest ui_tests -q` | Final **84 passed**, 133.92s; outbound-blocked fixtures, no real accounts |
| `python -m pytest tests -q` | **1,810 passed**, 13 warnings, 291.03s; executed before final pointer-Escape frontend fix; no backend code changed in this batch |
| `python -m ruff check src tests ui_tests scripts` | Passed |
| `node --experimental-vm-modules scripts/check-ui.cjs` | 50 modules parsed and linked; not application execution |
| `python -m build` | sdist and wheel built successfully |
| Wheel/source byte comparison | 50 JavaScript files plus `app.css` matched the built wheel |
| `git diff --check` | Passed |
| `python scripts/measure_code.py --update-doc` | Inventory regenerated; not counted as a test |

Initial consolidated browser run was 83 passed. The subsequently added pointer-negative test exposed a real bug: Esc during a resize propagated into native dialog cancellation. Fixed pointer focus and preventDefault only during an active resize; Esc outside resizing retains normal dialog dismissal. A later test assertion incorrectly expected draft validation in the form-save alert; corrected to the existing live-status region. Final 84-test run includes actual pointer resize, Esc cancellation, overlap refusal and persisted unchanged neighboring slot. Earlier failed attempts are not represented as passes.

Temporary logs: `/tmp/solar-readiness-ui.log`, `/tmp/solar-readiness-ui-final.log`, `/tmp/solar-readiness-be.log`, `/tmp/solar-readiness-build.log`, `/tmp/solar-readiness-visual-final.log`. Counts and boundaries are preserved here because `/tmp` is not durable evidence storage.

## Browser and visual evidence

New six regression cases cover preflight/platform gating, diagnostic locks/global-sync confirmation, actual rule draft creation/edit, late observation responses, keyboard/mobile-friendly TOU movement, and pointer resize/cancel/overlap. Existing whole-workspace contracts, including 31 genuinely empty installation routes, remain in the full suite.

Manual capture used a separately marked in-memory fixture at port 8879 (`ui-readiness-20261004`), with external browser traffic blocked. Captured VI and EN account list, preflight, GoodWe guide, blank EMS editor, mobile EMS editor and empty TOU editor: **12 states**, no page overflow or JavaScript page errors. Viewed both contact sheets and the underlying layouts. Responsive contract checks include 1600/1024/430px; this is not a real mobile-device test or pixel-diff acceptance.

Capture artifacts are local, outside the repository, under `/Users/toanlamsaoduocc/Documents/Codex/2026-09-30/users-toanlamsaoduocc-desktop/work/readiness/`; the capture script is adjacent as `work/ui_readiness_capture.py`. They contain explicitly labelled SIMULATOR accounts/plants, not customer data. They must not be used as production screenshots or seeds. The previous 66-state sweep remains historical evidence in [whole-workspace review](ui-whole-workspace-2026-10-04.md), not a fresh sweep for this slice.

## Readiness and next acceptance work

1. **Deye:** application credentials not configured in the reviewed setup; no real account QA yet. Existing managed-application flow must still prove exact region/account permissions and independent customer grants.
2. **GoodWe:** supplied logo crop does not identify app/version. Public SEMS Portal carries a migration/discontinuation notice; this alone does not prove all legacy regional APIs have stopped. Legacy connector plus plant IDs is not verified SEMS+ compatibility. Do not ask for a password to probe the wrong platform.
3. **Solis:** official customer OAuth consent contract differs from current `client_credentials` branch. Reconcile before live OAuth testing; documented, not silently patched as part of UI work.
4. **UI still incomplete:** exact phase/string/battery/latency chart definitions, deeper onboarding/network topology, geographic layers/clustering, nested rule UX, device-aware action inputs, complete translations/assistive-technology review and reference pixel/usability acceptance. These are engineering work, not merely missing customer data.

No real vendor credentials were entered, no email/application was sent, and no hardware command, deployment or Git push occurred. R10 and production/live acceptance remain open.
