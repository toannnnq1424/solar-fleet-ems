# R03/R06/R08 — optional frozen observed-import estimates

Report generation accepts `include_import_estimate` (default false). The energy
summary and optional estimate inputs are captured in one SQLite transaction with
session revalidation. Persistence/audit is atomic and revalidates the session again.
Each site freezes site/device revisions, selected meter, all declared rate versions,
actual sample row bodies, accepted/excluded intervals, method and coverage. Report
artifacts remain immutable after changes to current tariffs or sample retention.

CSV/XLSX/HTML include estimate/disclaimer and per-item JSON provenance rows. The
Reports analytics screen exposes a bilingual opt-in using shared UI primitives.
No new screen, stylesheet, dependency, vendor control or hardware capability.

Limits: 30 days, 20 sites, 10,000 samples/site for the opt-in; explicit same-site
billing meter required. Ordinary counter-based reports retain their existing limits.
This estimate uses observed power, not counter totals or a utility bill; no interval
splitting, invented gap energy, implicit rates, taxes, demand/reactive charges or
savings. Missing prices yield null. Frozen row bodies are evidence, not new SQL
sample IDs or an externally anchored signature. Archive size/retention remains open.

Verification read from local synthetic artifacts:
- Focused backend: 38 passed, 1 warning, 15.26s (`/tmp/solar-snapshot-focused.log`).
- New browser export contract: 1 passed, 2.42s
  (`/tmp/solar-snapshot-browser-focused.log`): opt-in missing-meter error, retry with
  ordinary export, real download and request payload.
- Ruff passed; JS syntax/linkage and sdist/wheel build passed
  (`/tmp/solar-snapshot-{js,build}.log`).
- Full backend/browser pending final artifact read:
  `/tmp/solar-snapshot-{backend,browser}.{log,exit}`.

Backend tests use persisted sample rows (not a mocked successful cost calculation),
all three formats, immutable downloads, scoped access, null prices, rollback and
window/sample/meter failures. Broad visual/mobile acceptance is not claimed.
Rate correction/supersession remains unbuilt and is the next workflow; R03/R06/R08
remain open. No commit, push, deployment, real credentials or hardware actions.