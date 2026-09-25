# Validation — Eybond read integration, 24 September 2026

Historical snapshot. [25 September mapping/navigation validation](mapping-validation-2026-09-25.md) supersedes the suite totals and fixes the duplicate Data tab rows observed below. See the [validation index](validation.md); earlier failures and reruns remain recorded here.

Working-tree scope: DessMonitor/ShineMonitor read connector, shared controller inventory/poll policy, Bluesun account form, native readings and regressions. No vendor account, customer browser or physical device was used. Contract tests block outbound HTTP; browser fixtures own their server/port and block external traffic.

## Executed checks

| Check | Evidence | Result |
|---|---|---|
| Complete BE suite | `python -m pytest -q`; `work/eybond-backend-tests.log` | **429 passed, 3 failed**, 355.90 s; all three repaired below |
| Affected BE rerun | DessMonitor adapter/workflow, extension/data-stream, data-connections and device-workspace modules; `work/eybond-backend-rerun.log` | **73 passed**, 21.62 s, including all three failures. Not a second full-suite run; do not add rerun counts to 432 total cases |
| Complete browser suite | `python -m pytest -q ui_tests`; `work/eybond-browser-tests.log` | **10 passed, 1 failed**, 83.71 s; new account test used an incorrect accessible button name |
| Affected browser rerun | `python -m pytest -q ui_tests/test_audit_workflows.py -k bluesun`; `work/eybond-browser-rerun.log` | **1 passed, 4 deselected**, 6.60 s after correcting the selector; no production UI change for this fix |
| Python static checks | Ruff check and format check on src/tests/ui_tests/scripts | Passed; **114 Python files** formatted |
| JavaScript module graph | `node --experimental-vm-modules scripts/check-ui.cjs` | **28 modules** parsed and imports/exports linked; browser suite separately executes the application |
| Package | `python -m build`; `work/eybond-build.log` | Passed: wheel and sdist for 0.2.0 built successfully. Subsequent mapping changes require their own final build; see the 25 September validation |
| Inventory | `python scripts/measure_code.py --update-doc` | BE **14,539**, FE **17,485**, tests/fixtures **8,633**, scripts **159** physical lines; per-file detail in coverage/inventory |

The complete BE run retains 13 existing dependency/test deprecation warnings; the affected rerun has two (Starlette httpx TestClient compatibility and AnyIO BlockingPortal alias). No warnings were suppressed. Initial failures remain in logs; the table does not claim a single green full-suite run.

## Findings and repairs

- Two new API workflow tests omitted `json={}` on POST sync/check. Existing JSON-only middleware correctly returned 415. Tests now follow the browser contract; middleware was unchanged.
- Per-adapter polling floors temporarily made saving a policy require a loaded adapter, although local configurations can outlive an extension. Reads/writes now consistently use the registered floor or conservative 120-second default when unloaded. Unknown adapters still cannot make network calls or device writes.
- The browser test requested `Add vendor account`; the accessible name was `+ Add vendor account`. The selector was corrected and the create workflow passed.
- Persistent discovery alone did not restore collector routes after restart or partial account diagnostics. Session inventory readiness now triggers full rediscovery before telemetry. Both cases pass in the workflow regression.
- Device inventory retained a fabricated 38°C temperature, a 0 kW table fallback, a hardcoded vendor filter missing Eybond/SOLARMAN and an offline label for unknown readings. Those paths now preserve missing values, filter observed brand/platform and show unknown state.

## Evidence exercised

Both platforms: selected host/auth action/source, ordered encoded signatures with Unicode/reserved characters, session token/secret order, expiry/concurrent refresh, HTTP errors/backoff, no redirect/alternate-host retry, malformed auth envelopes and clean public httpx URL/log context.

Discovery: collector pagination, repeated/scope/identity anomalies, partial discovery and unknown-device rejection. Native data: Wh/kWh/VA, text states, stable keys across ordering, no fabricated measurement time or canonical values.

API flow: encrypted credentials → actual adapter with synthetic HTTP transport → shared discovery/bindings/telemetry → device/source/history/site views. Tests verify declared Bluesun identity, null canonical KPI, no commissioned control, site isolation, 300-second collection floor, revision conflict and restart/check recovery.

Browser flow: Bluesun→SmartESS form, chosen platform, masked credential fields, brand persistence, administrator account identity and 300-second collection editor; inventory→native readings. Existing sidebar/site, permissions, incident and maintenance tests remain in the complete browser run.

## Visual review and limits

Directly inspected `work/qa-audit/test_device_native_values_readable_without_invented_temperature.png` and `test_bluesun_smartess_account_form_preserves_platform_and_brand.png`. The native table shows readable states/units; the collection form uses shared styles. Long details scroll inside the shared dialog. Inventory remains vertically spacious and Data still has two tab rows. This is not pixel/usability acceptance of all 26 mockups.

Still unverified/unbuilt: live grants/app identifier/company-key acceptance, hardware/OEM identity, timestamped history, canonical model profiles, alarms, native configuration/control/readback, incremental inventory under quotas and local Eybond protocols. See [integration boundary](eybond-read-integration.md) and the [26-screen matrix](mockup-coverage.md).
