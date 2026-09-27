# Sidebar follow-up — 27 September 2026

## Consolidated continuation: confirmed fixes and acceptance boundaries

The cumulative suite was rerun rather than relying on earlier summaries. All 15
sidebar routes and site tabs are covered by the isolated browser smoke contract;
that does not certify every subtab or external integration.

- Devices: selected site now scopes inventory and firmware at the API, with
  explicit unauthorized-site denial. Firmware UI consumes `devices`,
  `current_firmware` and `latest_firmware`, not nonexistent response fields.
  Mixed missing/known firmware versions no longer break sorting. Firmware read
  failure surfaces an error with retry rather than a fabricated empty success.
- Native parameters: no invented fallback device ID or fake "request sent"
  acknowledgement; the action opens site-scoped commissioning records. Missing
  native values remain unknown. Maintenance navigation uses the canonical section.
- Reports: viewer role no longer receives a generate action that the API denies;
  existing authorized archive downloads remain available.
- Notifications: repaired incorrect persistence/audit calls, added typed partial
  input validation and global-admin checks. SMTP password, Telegram token and Zalo
  webhook are encrypted in the existing Vault, never returned as secret values.
  Existing plaintext secret fields migrate on the next successful configuration
  update; historical backups are not rewritten. This is backend configuration,
  not a completed notification editor or real delivery service.
- Catalogue bill scenarios require explicit tariff key, peak demand and exactly
  24 nonnegative finite hourly values in each direction. Partial/oversized profiles
  are rejected rather than silently truncated. Results identify themselves as
  unverified-effective-version advisory estimates, not billing-ready invoices.
- Alert severity/status filters no longer use the misleading "All plants" label.
- Maintenance KPI cards now use shared surface/ink tokens, repairing dark-on-dark
  heading contrast. Zero queued firmware requests no longer implies "Up to date";
  zero enabled preventive plans no longer claims "Active".

New contracts are in `tests/test_sidebar_contracts.py` and
`ui_tests/test_sidebar_contracts.py`. No credentials, real hardware, external
delivery, production writes or commissioning were used. Python's first cumulative
run: 1079 passed, one newly authored test failed because its POST omitted the JSON
body required by the existing HTTP guard. The test request was corrected; the
guard was not relaxed. Final full Python rerun: **1080 passed, 12 dependency
deprecation warnings in 132.76 seconds**. Final full browser rerun, including
maintenance contrast/labels assertions: **29 passed in 44.81 seconds**. Final
source distribution and wheel build succeeded.

Ruff, all static JavaScript syntax checks and whitespace checks passed. Final build
and Python logs: `/tmp/solar-overall-build.log` and
`/tmp/solar-overall-python-final.log`; browser log:
`/tmp/solar-overall-browser-final.log`. Code inventory was regenerated, not counted as QA.

Visual sampling reviewed firmware rows/unknown releases, viewer reports and mobile
alerts. A screenshot captured maintenance while loading; its test was strengthened
to wait for the destination heading before final capture; reviewing that image
identified and fixed the maintenance contrast and misleading firmware KPI. Remaining visual issues
include nested horizontally scrolling device tabs and a long empty report table.
This is not cumulative visual acceptance of every screen.

Still open: effective site-tariff selection/history, aligned active/reactive billing
intervals, trusted EV timestamp provenance and exact freshness boundaries, model/
decoder evidence review, full per-tab action/error/reload coverage and field
commissioning. The site tariff-analysis API deliberately returns unknown billing
amounts while these prerequisites are missing. No operational figures were invented.

Implementation has 15 sidebar entries, not 14. Route smoke coverage is not proof
that every workflow, calculation or permission is complete.

| Entry | Canonical route | Remaining review emphasis |
|---|---|---|
| Overview | overview/main | Partial telemetry coverage and stale responses |
| Plants | plants/main | Wizard metadata persistence; technical fields below |
| Topology / SLD | topology/main | Binding provenance and editing permissions |
| Map | plants/map | Unknown coordinates and site scope |
| Devices | devices/main | Vendor defaults and decoder provenance |
| Control | operations/main/control | Explicit inputs; verified command gates |
| Schedules / TOU | operations/main/schedules | Persistence and effective versions |
| EMS coordination | operations/main/rules | EV measurement freshness |
| Data & connections | reports/main | Collection errors and data provenance |
| Alerts | incidents/main | Site isolation and lifecycle actions |
| Reports | reports/analytics | Effective tariffs and aligned reactive energy |
| Maintenance | incidents/health | Action permissions and persistence |
| Journal | operations/main/journal | Filtering, export and site scoping |
| Users | settings/main/users | Role and site authorization |
| Settings & Vendors | settings/main/connections | Provider credentials and commissioning |

## Verified changes in this continuation

- Plant wizard preserves missing GPS and PV capacity as null rather than zero;
  explicit zero coordinates/capacity and fractional capacity remain valid.
- GPS pair/range and PV capacity validation run before advancing the wizard.
- Review displays missing GPS/capacity as an em dash, not `null`.
- Benchmark chart scales for yields above 5 kWh/kWp and excludes negative values.
- Four new isolated-browser contracts cover three metadata persistence cases and
  high-yield chart geometry. Full browser suite: **24 passed**.
- Ruff, changed JavaScript syntax, whitespace check and package build passed.
- Full Python suite: **1044 passed, 12 warnings** in 133.67 seconds;
  result recorded in `/tmp/solar-sidebar-python.log`.

## Confirmed unfinished engineering

The follow-up now persists installation type, battery capacity, vendor, grid
limit and tariff type under `declared_specs` in the site inventory/profile.
These declarations do not configure battery controllers, dispatch limits or
effective billing rates. UI warnings make that boundary explicit; operational
configuration remains a separate workflow. Unknown vendor/tariff and blank numeric
inputs stay missing; explicit zero and fractional capacity survive reload.

Benchmarking no longer invents ranking or equipment-health conclusions from
specific yield, formats absent summaries consistently, and opens the correct
site ID. Browser screenshot review caught an additional missing-count rendering
case in the sparse high-yield fixture, now also formatted as unknown.

Validation: **1054 Python tests passed, 12 warnings; 25 browser tests passed**.
Ruff, JavaScript syntax, whitespace checks and package build passed. Logs:
`/tmp/solar-sidebar2-python.log`, `/tmp/solar-sidebar2-browser.log`, and
`/tmp/solar-sidebar2-build.log`. Tests cover declaration persistence/read-back,
invalid values, non-admin denial, no dispatch side effects, and benchmarking
site navigation. Broader per-tab audit remains unfinished.

All 15 route smoke checks ran as part of the browser suite. Cumulative visual
review and full per-tab action/permission coverage remain open. No external
commissioning or hardware dispatch was performed.

## EV advisory freshness follow-up

- Site power observations and each charger accept optional timezone-aware
  `observed_at`. Missing timestamps explicitly produce `UNKNOWN` freshness.
- Supplied timestamps outside the preceding 300 seconds (including future dates)
  fail with 422 before allocation. This is an advisory sanity window, not an
  equipment-specific commissioned control policy. Recent user declarations are
  `USER_REPORTED_RECENT`, never verified telemetry.
- UI exposes a blank site timestamp input and charger timestamp documentation,
  displays the unknown/unverified distinction, and prevents overlapping button
  submissions. Vehicle column now shows vehicle identity rather than charger name.
- No persistence, site telemetry read, phase switching or hardware dispatch is
  introduced. Authenticated calculator inputs remain user-supplied scenarios.
  Trusted timestamp provenance and device-specific freshness acceptance remain open.
- Verified this batch: **56 targeted Python tests passed (1 dependency warning),
  3 browser tests passed**, Ruff, JS syntax, whitespace and package build passed.
  Logs: `/tmp/solar-sidebar3-python.log`, `/tmp/solar-sidebar3-browser.log`,
  `/tmp/solar-sidebar3-build.log`. Previous 1054/25 counts were checked against their
  logs; the full suites were not rerun for this batch.
- Effective tariff versions, aligned reactive-energy billing, vendor provenance
  and cumulative visual review are still unfinished; no assumed billing data added.