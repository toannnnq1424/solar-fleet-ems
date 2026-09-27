# Continuation: shared elapsed-time observations and EMS localization

## Verified baseline

- Branch `fix/real-data-engine-integration` initially clean at `5dc8d76`.
- Commits `727340a` and `5dc8d76` exist; `88676f3` is an ancestor.
- Previous Growatt logs and exit files confirm 1195 Python tests, 29 browser
  tests, and successful source/wheel build. These are software checks only.
- The local `/Users/toanlamsaoduocc/Downloads/before_project` contains 30 projects.
  Existing license/reuse decisions and hash inventory are in
  `legacy-project-audit.md` and `evidence/legacy-project-inventory.json`.
  This continuation did not rehash every project or verify all upstream revisions.

## Implemented

- Normalize aware observation windows and samples to UTC before ordering and
  elapsed-time arithmetic. This fixes coverage at daylight-saving transitions,
  including the repeated wall-clock hour, in the shared integration used by
  billing-meter observations and battery history. Naive windows are rejected.
- EMS import observations translate their explanation and known statuses in
  VI/EN, retain unknown bills, and disable the request button while loading.
- Three DST regression cases and two browser language/action contracts added.
  No new sidebar, vendor client, dependency, copied legacy code or hardware
  dispatch was introduced. Existing 503/409 containment remains unchanged.

## Executed validation

- Python: **1198 passed**, 12 dependency warnings; log
  `/tmp/solar-continuation-python.log`, exit file records zero.
- Browser, separately collected: **31 passed**; log
  `/tmp/solar-continuation-browser.log`, exit file records zero.
- Ruff, changed JavaScript syntax, whitespace and source/wheel build passed.
  Build log: `/tmp/solar-continuation-build.log`.
- Initial newly authored Vietnamese browser test failed because reload reapplied
  the fixture's English initialization. Corrected it to use the UI language
  selector; full browser suite then passed. No product guard was relaxed.

## Remaining scope

This is not completion of all issues or maximal legacy reuse. Per-project
revision/license/owner/contract reconciliation, additional live transport,
vendor-form localization, effective tariff configuration and aligned reactive
energy, broader interaction/visual review and hardware commissioning remain
open. No external-service or physical-device acceptance is claimed.