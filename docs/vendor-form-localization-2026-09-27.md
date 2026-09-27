# Vendor account form localization follow-up

## Scope

Existing account workflow only: no new sidebar, transport, dependency or imported
legacy implementation. This addresses a remaining VI/EN gap, not completion of
the broader before_project reuse programme.

- Added shared VI/EN labels for vendor account, username/password, application
  key, system code, access token and explicit plant/point selections.
- Localized Australia and the Growatt `server` option without changing their
  request values or claiming the two Growatt hosts are interchangeable.
- Replaced generic API-key-only instructions with credential-neutral guidance:
  saving configuration does not verify connectivity or authorize control.
- GoodWe and Sungrow setup guidance now reflects the existing adapters' explicit
  comma-separated plant scope (up to 100 distinct IDs). Sungrow additionally
  requires numeric point selection (up to 200 IDs). No automatic model mapping
  or discovery of all account plants is implied.

## Tests and boundaries

Two new isolated browser contracts visit all eight implemented provider forms
in VI and EN, checking meaningful accessible field labels, required inputs and
password masking. They close forms without saving or contacting a vendor.
Initial test assumptions about native HTML labels and optional organization
inputs were corrected to follow the shared aria-labelledby form primitive.

Full Python: **1198 passed**, 12 dependency warnings. Focused browser: **2 passed**.
Ruff, all static JavaScript syntax checks, whitespace and source/wheel build
passed. Full isolated browser suite: **33 passed in 50.62 seconds**; exit zero.

Logs: `/tmp/solar-vendor-form-python.log`,
`/tmp/solar-vendor-form-browser.log`, `/tmp/solar-vendor-form-build.log`.

No hardware acceptance, remote authentication, new vendor protocol evidence or
additional legacy-code reuse is claimed. Existing read/command containment and
secret masking remain intact. Full per-form submission/error/permission and
visual acceptance across all vendors remain broader work.