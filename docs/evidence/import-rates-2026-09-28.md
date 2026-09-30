# Declared import-rate estimates — 28 September 2026

Accumulated uncommitted tree based on HEAD `567a9d0`. No credentials, live vendor
calls, hardware, commit, push or deployment. Synthetic local fixtures only.

## Implemented contract

- GET/POST `/api/sites/{site_id}/import-tariffs`: scoped reads; admin-only append,
  required whole-site `expected_revision`, session revalidation under write lock,
  atomic version + audit. Normalized UTC start/end, VND/kWh, explicit source;
  no overlaps, negative/nonfinite rates, implicit zero or naive timestamps.
  Up to 1000 versions per site. Append-only, no deletion/correction API yet.
- Existing tariff-analysis reads meter, site, revisions and samples in one transaction.
  It retains the 10,000-sample cap and 30-day window. Intervals require good canonical
  nonnegative W, one binding, no bad-sample barriers, maximum 15-minute separation.
- A trapezoid is priced only if entirely inside one version. No splitting across
  tariff changes, no gap filling, no extrapolation. Adjacent versions may meet at an
  observed endpoint. Price gaps/crossings are returned as excluded intervals.
- API returns estimated cost, priced seconds/coverage, interval UTC timestamps,
  endpoint W, kWh, rate/version/source, binding IDs and site revision. Unrounded
  float arithmetic for advisory calculations; no invoice rounding policy claimed.
  `total_active_bill_vnd`, solar savings and reactive penalties remain null.
- Settings editor saves/reloads versions; preserves inputs and disables retry on 409.
  EMS displays estimated VND cost, priced coverage and sources separately from bills.
  Prices are USER_DECLARED_NOT_UTILITY_VERIFIED, not catalogue or official EVN rates.

## Verification

Interpreter `/tmp/solar-fleet-audit-8ec68fd/bin/python` (Python 3.14.6).
Working directory `/Users/toanlamsaoduocc/Desktop/solar-fleet-ems`.

- Initial focused backend: 41 passed, 1 warning. Additional tests then added for
  audit rollback, adjacent version boundaries, role denial and site ABA.
- Initial browser: 3 passed, 1 failed. It exposed missing HTTP status on shared
  API errors; helper now preserves response.status so conflict disables retry.
- Final focused rate contracts: **17 passed**, 1 warning (5.68s).
- Full browser rerun: **37 passed in 57.33s, exit 0**; the 409 regression now passes.
- Full backend: **1680 passed, 12 warnings in 273.29s, exit 0**, read from
  `/tmp/solar-rates-backend.{log,exit}` after completion. Warnings concern existing
  Starlette/httpx and per-request cookie deprecations.
  Browser evidence: `/tmp/solar-rates-browser.{log,exit}`.
- Ruff, diff check, JS syntax/linkage and wheel/sdist build passed after that fix.
  Logs `/tmp/solar-rates-{js,build}.log`; inventory regenerated. No manual visual
  acceptance, hosted CI or multiprocess acceptance claimed.

Commands: `python -m pytest tests -q`, `python -m pytest ui_tests -q`,
`python -m ruff check .`, `git diff --check`,
`node --experimental-vm-modules scripts/check-ui.cjs`, `python -m build`.

## Still open

No whole R closed. Utility-verified tariff import, TOU recurring schedules,
export credits, tax/demand/reactive components, invoice precision/rounding,
rate correction/supersession, retention/rollups and reproducible report/export
snapshots are not implemented. Changed meter/binding provenance remains conservative;
this batch does not claim historic electrical-boundary continuity or acceptance.
The 30-day/10,000-row limit is deliberately explicit, not fleet-load acceptance.