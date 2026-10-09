# GoodWe native-read pilot and UI findings — 08/10/2026

## Scope and evidence

The user entered and linked their own SEMS+ account through SolarOne, then authorized
read QA and fixes. The account uses hk; no app keys or browser-session extraction were
used. Only one controller accessed the real database. Temporary manual diagnostics
held the same process lock while the web controller was stopped, used its existing
encrypted vault and printed schema/counts only. Automated tests used isolated fixtures
with synthetic accounts, never the real account. No physical writes or alarm acknowledgments.

Primary community reference remains the MIT ioBroker commit pinned in the previous
[connector evidence](goodwe-semsplus-connector-2026-10-07.md). The scoped E-grade live
observation is registered as `GOODWE_SEMSPLUS_HK_READ_OBS_20261008` in both registries.
No customer identifiers, raw values/payloads, credentials, tokens or screenshots are included.

## Findings and implementation

1. **Whole read batch failed on inventory types without telemetry.** Discovery returned
   one plant, two INVERTER, one DATA_LOGGER, one SMART_METER and two related BATTERY_BANK
   records. These six API objects do not prove six independent physical devices.
   Two inverter responses contained 98 factors each; meter contained 24 factors.
2. The initial diagnostic used `response.get('data')`, conflating omitted and null data.
   The first fix handled explicit null and therefore did **not** resolve the live failure.
   Follow-up envelope inspection confirmed `code=00000`, `description`, `traceId` and
   **no data key** for logger and BATTERY_BANK telemetry. This correction supersedes the
   initial interpretation; it is not an intermittent successful trial.
3. `GoodWePlus.read` now tolerates omitted data only on the telemetry endpoint of those
   two already-discovered kinds. `latest` returns an empty observation, not synthetic
   zero or offline. Missing station/inverter data, malformed lists, errors and throttling
   still fail closed. Explicit null also remains no-data. Discovery/identity guards,
   five-device rotation, call budgets and the shared ingestion owner are preserved.
4. After the final transport fix, the actual controller completed a read cycle at
   **2026-10-07T23:23:30Z**: five selected records stored, three with factors, **220 native
   points**. State `PILOT_CAPACITY_EXCEEDED` reflects five-device rotation across six
   inventory records, not a vendor auth failure. This is read-path evidence, not every
   field/physical value or six-device end-to-end acceptance. Missing timestamps remain
   unknown and unverified; no backfilled clock, energy chart, billing or control promotion.
5. Native aliases/group labels are display metadata only. A shared searchable/grouped
   native inspector now appears early in device detail and realtime monitoring. It
   preserves zero, missing values and original units, escapes text, separates received
   time from measurement time, and keeps an explicit empty state on telemetry-less devices.
6. Real UI review exposed a second tri-state loss: `OperationalViews.equipment` coerced
   unknown connectivity to false. It now preserves unknown when there are no recent
   samples, and distinguishes true/false otherwise. Inventory uses the actual connectivity
   counter, not the separate measurement-quality counter. Type filters are built from
   returned types; logger/meter/vendor battery records have VI/EN labels and nonblank titles.
7. Inventory no longer reports hardcoded zero active warnings without complete alarm
   coverage. Site equipment read summaries distinguish received native points from fresh
   verified measurements. The overview adds an entry point to inspect those readings.
8. Account screen: one primary add action, secondary setup/help toolbar; sample-read
   success explicitly covers one plant/device only; last-cycle error or rotation is not
   labelled a fully synchronized fleet. Shared shell and app.css remain the only owners.

## Portal control observation, not implementation permission

Read-only opening of the selected inverter's work-mode panel exposed self-use, backup,
TOU, peak shaving and smart charging, plus a current mode. No switch or submit was used.
The portal also exposed AC-port/backup/on-off/remote-grid controls. A menu does not prove
a third-party write contract, fresh readback or commissioned ranges. SolarOne writes stay
disabled; exact model/logger/firmware, authority and per-action acceptance remain unresolved.

## Verification status

- Initial implementation: 1,852 backend tests / 100 browser tests passed. Live QA then
  found the omitted-data distinction and the shared operational-view coercion above.
  Those initial totals must not be presented as final-tree acceptance.
- Focused revised GoodWe/device suite: **53 passed**, two dependency warnings, 11.69s.
- Native-read slice final consolidated backend/browser: **1,860 / 100 passed**;
  ruff/JS syntax/build passed. Superseded by the station-report slice below for new code.
- Manual empty-data UI navigation: all 15 sidebar owners at 1600px, no observed page
  overflow or page-error placeholder. Account two-column layout visually inspected.
  Automated browser contracts cover empty/deep routes and 1600/1024/430px layouts.
  This is not an all-screen pixel-diff certification.
- After the user's sign-in, live inverter 98 / meter 24 / logger no-data panels were
  inspected; all 15 sidebar owners opened. A manual fixture initially used the same
  hostname on another port and replaced the host cookie; fixed by moving that fixture
  to localhost. No password reset or session bypass. Keep cookies host-isolated.

## Follow-up: overview still blank — station reporting

The user's complaint was correct: native factor visibility did not complete overview
integration. The connector omitted station-level flow/statistics reads. MIT upstream
`TimSoethout/goodwe-sems-home-assistant@72c06c72caf0600272ca2ac17db6474af60d59ae`
was inspected (implementation, API examples, tests, release notes, LICENSE); notices
and both registries now include `GOODWE_SEMSPLUS_STATION_001`.

Manual authorized hk read confirmed flow includes pSystem/pAc/pBat/pGrid/pConsum/soc
and a timezone-less refreshTime. Day statistics returned scalar energy summaries and
dated kWh series. Basic-info request was rejected; no timezone inferred. No raw user
payload persisted in this document or test fixtures. Monitoring report timestamps are
not retroactively assigned to inverter/meter telemetry.

Initial implementation (cadence superseded by the follow-up below): optional shared StationReport/ReportedEnergy interface; adapter owns
field/unit/sign conversion; guarded poll persists one oldest selected station per cycle
at >=15-minute intervals. Scoped readers recheck account, revision and enabled binding.
Vendor reports are a separate presentation channel, never GOOD samples, EMS/billing or
command evidence. Site KPI fallback is explicitly labelled; energy flow has static
values/no moving arrows; fleet shows per-site numbers without summing unknown coverage;
reports show the vendor section separately from verified calculations/exports.

Station slice initial suite: 1,879 backend / 101 browser passed; live QA then found
the statistics fixture too broad. With four selected items, hk omits flat summaries;
month/year return YYYY-MM / YYYY buckets, not daily rows. Corrected decoder reads
one matching dated kWh bucket; separate dimension=day fetch supplies the month chart.
No summing partial curves. Regression: 67 focused tests passed after correction.
Real persistence at 2026-10-08T01:47:11Z: all five flow fields, four energy fields in
each today/month/year period, eight daily rows, no unavailable period. These are
source-reported snapshots, not billing-grade. Live UI: all six site KPI populated,
24 energy bars (three metrics × eight days), no animated unverified flow branches.

## Per-inverter follow-up to the user's 11 screenshots

Added optional DeviceReport / DeviceEnergyReport to MeasurementObservation. Existing
GoodWe latest additionally reads telecounting for discovered INVERTER records only;
field+unit+uniqueness guard, serial checked before persist and during latest read.
AC and DC stay distinct. Do not infer device SOC from the station or undocumented
related battery values. Device report never emits GOOD samples or commissioning.
Shared device panel in detail/realtime: rated-output gauge, AC/DC/temperature,
generation/charge/discharge with day/week/month/year/lifetime selector. Inventory and
site equipment table explicitly label AC vendor-reported fallback. Native inspector
remains available. Icon is generic SVG, not a claimed photograph/model match.

Manual account read 2026-10-08T04:40:43Z: both inverter reports match their own serial;
AC/DC/rated values present and all five periods available. Browser observed both
devices with different serials and different AC values, three energy values each;
month switch preserved three energy values. No horizontal overflow at observed
viewport. Screenshot retained locally outside repo, no customer data in evidence.

Consolidated device-slice results: backend **1,890 passed**, browser **102
passed**, focused backend **75 passed**, ruff/JS syntax/build passed. These results
precede the freshness follow-up below. Full power/MPPT history,
runtime ring, battery-parent metrics, alarm history, AC-port/backup/control remain
unfinished; screenshots-to-functions matrix is in vendor-feature-backlog-2026-10-05.md.

## Freshness and manual-refresh follow-up — 08/10/2026

User correctly observed mismatched values. Same-inverter browser comparison found
SolarOne's open dialog retained its 11:40 receipt while SEMS+ had changed. Code skipped
all live invalidations while a dialog was open, station reports had a 900s extra cache,
and 120s scheduler ticks rounded a 300s account minimum toward 360s. The “Live updates”
label described a UI WebSocket, not inverter sampling; it was misleading.

Implemented shared read-only device-live-monitor: local GET every 15s, visible receipt
age/cadence, preserved period/native filters, no replacement while editing a filter,
stop when removed, clear readings on failed/scope-revoked refresh. Both detail dialog
and monitoring tab use it. Controls/configuration forms remain untouched.

Shared POST /readings/refresh uses the existing controller lock/budgets, enabled
account scope, optional preferred device, no physical writes; organization-admin-only
like existing sync. Returns UPDATED/PARTIAL/FAILED/WAITING/BUSY/NO_SOURCE, never a
fake successful update on cooldown. Common shell and device monitor provide buttons.
Plant selectors show name + vendor + account identity for org admins; other roles
only receive the connection name, not vault login identities.

SEMS+ minimum now 60s based on pinned maintainer const.py, not an official quota.
Classic SEMS stays 300s; slower user collection policies remain intact. Controller
checks due work every 15s; station report uses account cadence rather than extra 15min
cache. No claim that a fresh HTTP receipt is a new physical measurement. Source-time
semantics still unresolved. Automatic/background calls keep shared budget/429 backoff.

Intermediate freshness tests
found two defects and led to fixes: restoring selects by aria-label failed because
shared fields use aria-labelledby; cadence metadata polluted rejected empty payloads.
After fixes, 107 guard tests and 103 browser tests passed. The subsequent 60s/manual
refresh/account-label slice passed 139 focused backend tests.

Final combined software verification on the uncommitted working tree based on
HEAD af4f1b8: **1,894 backend passed, 13 dependency warnings (331.25s)**;
**104 browser passed (198.40s)**; wheel and sdist built successfully.
Commands: `work/ui-venv/bin/python -m pytest tests -q`, separate
`work/ui-venv/bin/python -m pytest ui_tests -q`, and
`work/ui-venv/bin/python -m build`. Logs observed in
`/tmp/solar-nearlive-python.log`, `/tmp/solar-nearlive-ui.log`,
`/tmp/solar-nearlive-build.log`; the summarized results here survive temporary-log
cleanup. Automated tests use isolated fixtures, not customer credentials/hardware.
These counts do not certify the future DE/AI plan or full pixel/live acceptance.

An existing open browser dialog showed the upper report/native panel advancing to
a new receipt while the lower original readings table retained its opening snapshot.
Record BUG-LIVE-02 for reproduction on the newly loaded client and a single-snapshot
read-only render fix; do not rebuild control forms with a timer. Latest-client manual
refresh/account-label and multi-cycle live acceptance remain open, not silently
promoted by the passing fixture suite. See the resumable backlog checkpoint.

Storage read-only audit: samples currently hold 220 rows across 220
device/metric/binding channels, all source_ts UNKNOWN; six latest and one station_report
entities. Store.put overwrites current bodies, and add_samples overwrites same-key
values including UNKNOWN. Entity revision counters are safety fences, not historical
values. The backlog now plans bounded receipt/correction history; it is not implemented.

## Remaining work

Verify the remaining rotating inventory record and repeated native persistence, then
compare the native UI with the portal after user sign-in. Resolve source timestamps,
model/firmware and canonical semantics before trusted KPIs. History/alarms/recovery and
control/readback remain unimplemented or unaccepted for this transport. Continue the
26-screen detailed-mock styling/interaction backlog (not the conceptual SolarHub collage),
especially dense engineering/native and network/EMS workflows. Do not call them merely
waiting for credentials. No commit, push, deployment or physical capability unlock.
