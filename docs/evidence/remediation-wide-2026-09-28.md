# Cross-R implementation batch — 28 September 2026

Scope: accumulated uncommitted working tree on `fix/real-data-engine-integration`, HEAD `567a9d0`;
no commit, push, deployment, credentials, external delivery or hardware actions.
All tests use synthetic fixtures. Python: `/tmp/solar-fleet-audit-8ec68fd/bin/python`.

## Implemented

- R06/R09/R10: advisory planning editor with scoped device selectors, explicit battery
  numbers and USD hourly input/source. Empty numbers cannot turn into zero. Clearing
  the advisory device clears its configuration, not control authority. Uses existing
  shell/style and VI/EN labels. Conflict keeps user inputs and blocks blind retry.
- Planning API now requires `expected_revision` from GET. Missing revision returns 422;
  stale/ABA site revision returns 409 before writes. API clients must GET then include
  this field on POST. This intentionally removes unsafe unversioned writes; no legacy
  command-plan digest/replay format is changed. Site-wide revision is conservative.
  Session and authority are checked again under the persistence transaction; mutation
  and audit commit together. Saved data remains advisory, not measured or commissioned.
- R02: alerts context is revalidated inside the persistence transaction. Four tests
  inject delete/restore via a second SQLite connection immediately before that lock.
  Corrected reproducer: 4 failures (200 instead of 409) before fix; 4 pass after.
  Earlier harness failures (missing JSON header, in-memory database) are not defect evidence.
- R04: reproducible read-only reconciliation script, 30/30 local folders; all 43 locked
  files match. OpenEMS file-count differs; Solis license absent. Historical tree hashing
  cannot be reproduced from missing original manifest/algorithm. No new reuse promoted.
- R11: backend and browser CI collection are separate; browser job installs Chromium
  and uses isolated fixture server. Ruff covers all code. Hosted CI has not run here.

## Verification

- Prior poll-capture artifacts independently read: 1646 backend passed, 12 warnings,
  exit 0; `/tmp/solar-poll-capture-backend.{log,exit}`. Not the new batch result.
- Focused planning/operational-input backend: 33 passed, 1 warning.
- New planning browser contracts: 2 passed, including actual save/reload and mocked 409.
- Alerts and reconciliation focused: 5 passed, 1 warning. The reconciliation test was
  authored after the full backend collection started and is separately verified.
- Full browser: 35 passed in 54.91s, exit 0, `/tmp/solar-wide-browser.{log,exit}`.
- Full backend: **1662 passed, 12 warnings in 268.45s, exit 0**, independently read
  at `/tmp/solar-wide-backend.{log,exit}`. The separately verified reconciliation test
  is not included in 1662; no 1663-case full run claimed.
- Ruff, static JavaScript syntax/import linkage, wheel/sdist build and diff whitespace
  passed locally; logs `/tmp/solar-wide-{js,build}.log`. Inventory regenerated with
  `python scripts/measure_code.py --update-doc`; JSON artifacts parsed successfully.
  Inventory is not a test. Full commands were `python -m pytest tests -q`,
  `python -m pytest ui_tests -q`, `python -m ruff check .`,
  `node --experimental-vm-modules scripts/check-ui.cjs`, `python -m build`,
  and `git diff --check`, from the repository root using the interpreter above.

## Not closed

No whole R is declared complete from this batch. Effective versioned billing, aligned
meter intervals, cost provenance, scalable recovery/backfill, notifications, transport
audit coverage, full UI/visual acceptance, hosted CI and multiprocess/crash/load acceptance
remain open. R12 needs separately authorized exact hardware acceptance. Historical
maintenance browser timeout remains unresolved; this successful run does not erase it.