# Validation record — audit of 23–24 September 2026

Scope: the working-tree snapshot inspected on 23–24 September, including additions after the preceding commit. Local synthetic contracts and workflows only; no vendor credentials, logged-in customer browser, physical writes or hardware acceptance. This historical record does not certify a mature release. Later results are indexed in [validation records](validation.md), including [25 September](mapping-validation-2026-09-25.md).

## Consolidated checks

Executed on 24 September after the shared-session fix. The full BE run found two authorization regressions; they were repaired and the affected five test modules were rerun. Do not add the rerun count to the full suite count or describe this as a single green full-suite run.

| Check | Command / evidence | Final result |
|---|---|---|
| BE contracts and workflows | `python -m pytest -q --tb=short`; `work/audit-pytest-2026-09-24.txt` | 396 passed, 2 failed in 273.47 s; both failures were the same missing-await authorization defect described below |
| Affected BE regression rerun | `python -m pytest tests/test_security_app.py tests/test_workspaces.py tests/test_session_concurrency.py tests/test_report_workspace.py tests/test_settings_and_admin_workspace.py -q --tb=short -W error::RuntimeWarning`; `work/audit-affected-2026-09-24.txt` | 51 passed in 138.41 s after repair, including both failed cases; no RuntimeWarning. No further full BE run after the one-line repair |
| Browser workflows | `python -m pytest ui_tests -q --tb=short`; `work/audit-browser-2026-09-24.txt` | 9 passed in 58.51 s; shared session fix included. Ran before the subsequent security-audit await repair, which was covered by BE regressions |
| Python lint / formatting | `python -m ruff check src tests ui_tests scripts`; `python -m ruff format --check src tests ui_tests scripts` | Passed; 110 Python files formatted |
| JavaScript module graph | `node --experimental-vm-modules scripts/check-ui.cjs` | 28 modules parsed; all local imports/exports linked. Does not execute the application |
| Source distribution / wheel | `python -m build`; `work/audit-build-2026-09-24.txt` | Passed. All 95 package source/assets/data files match the working tree byte-for-byte; source archive has 192 entries without mockup images, work/cache/database/private-key files |
| Whitespace / inventory | `git diff --check`; `python scripts/measure_code.py --update-doc` | Passed; inventory includes uncommitted source and excludes assets/dependencies/generated/build output |

There are 13 remaining deprecation warnings in the affected BE run: Starlette's httpx TestClient compatibility, an AnyIO BlockingPortal alias, and per-request cookies in an existing admin-session test. They are recorded, not hidden. Dependency migration and that test-fixture cleanup remain follow-up work; no runtime-coroutine warning remains in the affected rerun.

Previous runs are retained as diagnostic evidence, not reported as the final result: BE 395 passed / 1 failed (obsolete hard-coded source count); browser 8 passed / 1 failed (intermittent session loss), then the affected navigation test passed after the session fix. Those failures were not suppressed.

## Defects reproduced and repaired

- **Concurrent valid sessions could disappear or return inconsistent rows.** On Python 3.12, the same SQLite connection was read by concurrent sync dependencies. A local probe produced 375 incorrect results out of 1,200 reads. Disabling its statement cache produced zero incorrect results in the same probe; auth dependencies now run on the async request path. The new regression verifies three identities, distinct site scopes and CSRF tokens across eight threads / 1,200 reads, and rejects an invalid token. This matches the documented [CPython shared-connection statement-cache issue](https://github.com/python/cpython/issues/118172). It does not establish multi-process or distributed transaction support.
- **A pending form save could consume or overwrite subsequent input.** Shared form submission now disables existing controls and restores their original state; browser tests verify a completed transition before note entry and check the saved note/timeline/job relationship.
- **Engineer report generation was incorrectly blocked.** The shared operator dependency now includes the Engineer role. Regression checks own-site creation/download and rejection for a viewer and a different-site operator.
- **The async-auth refactor temporarily bypassed a direct permission call.** The security-audit route called `admin(who)` without awaiting it. Two existing tests exposed a viewer/scoped administrator receiving HTTP 200 instead of 403. The call is now awaited; all other direct calls to these dependencies were searched, and both rejection cases pass in the 51-test affected rerun. This defect was introduced during this audit and fixed before delivery.
- **Unmeasured values appeared as operational results.** Removed synthetic overview curves, default self-use percentages, invented financial/environmental metrics, fabricated health scores and electrical commissioning PASS values. Tests assert null/unknown, stored counter boundaries, immutable artifact bytes and permissions.
- **Native vendor contracts were treated as interchangeable.** Corrected auth/envelopes, physical IDs, units/timestamps, Solis history keys/alarm filters, Huawei five-minute history, Growatt family methods, SEMS session host/token and SOLARMAN frame identity. Guessed non-Deye write compilers now reject unsupported mappings. See the vendor audit for exact applicability limits.
- **Provenance and documentation overstated support.** Repaired duplicate source IDs, withdrew five unsupported evidence claims, synchronized the packaged registry, and replaced subjective completion statements with per-screen gaps. The catalogue test now verifies required sources and uniqueness instead of freezing an obsolete source count.
- **The source archive included development mockup images.** Added an sdist-only exclusion for `/images`; the repository's reference images remain intact. The source package fell from approximately 83.6 MB to 0.49 MB. The runtime wheel still contains the global UI, all adapter modules and packaged evidence; no runtime source was omitted.

## Browser and visual QA boundaries

The isolated fixture starts its own process/port, verifies an ownership marker, blocks external browser requests and outbound vendor HTTP, and collects uncaught JS exceptions and HTTP failure metadata. It uses only simulator accounts. A failed/offline API must show an error rather than a success placeholder.

Browser scenarios cover sidebar/site navigation, global stylesheet/sidebar reuse and VI/EN, account display, collection revision saving, API failure, viewer restrictions, incident assignment/transition/note/history/linked maintenance, execution plan/time/independent review, and a narrow incident view. Route traversal checks 21 route states plus ten site subtabs; it is a navigation check, not acceptance of every control in those screens.

Representative images were inspected directly: `work/qa-audit/accounts-vi.png`, `site-overview.png`, and the mobile incident screenshot. Accounts follow the main table + right diagnostics + lower summary cards of mockup 21 and show Bluesun/Eybond without fabricating connected accounts or certificates. The site page displays missing measurements explicitly; mobile incident content stacks without page-wide horizontal overflow.

Visual gaps remain: the site overview is too vertical, two tab rows are present, energy flow lacks the full inverter hub/topology/arrows, narrow tables need refinement, and technical labels/translations need consistency. **No claim of pixel matching or full usability acceptance for all 26 screens.** Review links and completion conditions are in `mockup-coverage.md`.

## Not covered by this audit

Live region/account grants, model/logger/firmware identity, actual native settings/readback, electrical commissioning, vendor alarms/backfill, outages/soak/load at fleet scale, tenant isolation/SSO/MFA, managed agent lifecycle, real OTA, notification delivery, long-term backup/restore, and comprehensive accessibility/security/visual acceptance remain unfinished or unverified. Passing local tests must not be relabeled as those outcomes.
