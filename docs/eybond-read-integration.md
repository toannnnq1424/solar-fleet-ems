# Eybond / SmartESS cloud reads — 24 September 2026

Implemented code and synthetic validation are separate from account/hardware acceptance. This is a read-only pilot connector, not complete Eybond or Bluesun support.

## Sources and applicability

- [Eybond SmartESS operating manual](https://fms.eybond.com/fms/api/auth/web/doc/html/previewOnline/72/2), registry `EYBOND_GUIDE_001`: manufacturer platform/onboarding evidence only; it does not document these HTTP contracts.
- [ha-dessmonitor at 3b530bf34d91eef43ec2474d971019fa48c5ae16](https://github.com/andreas-glaser/ha-dessmonitor/tree/3b530bf34d91eef43ec2474d971019fa48c5ae16), registry `EYBOND_DESSMONITOR_AUDIT_001`: inspected `custom_components/dessmonitor/api.py`, `const.py`, `tests/test_api_profiles.py`, `tests/test_api_security.py`, synthetic devcode 518/2477 last-data fixtures and LICENSE. Community evidence grade F remains F. The new connector independently implements the observed wire contract; the MIT notice accompanies the package.
- Upstream fixtures show model-specific field names and units. They do not identify every Bluesun inverter/OEM/logger or establish safe control mappings. Our contract tests use independently authored SIMULATOR values.

## Implemented contract

| Platform selection | HTTPS host | Authentication | Source |
|---|---|---|---|
| DessMonitor / SmartESS | api.dessmonitor.com | authSource | 1 |
| ShineMonitor / SmartClient for Solar | ios.shinemonitor.com | auth | 0 |

The fixed path is `/public/`. These are explicit account-platform selections, not interchangeable geographic regions. There is no failed-login fallback to another host, redirect following or arbitrary URL input. ShineMonitor here is not the Growatt Shine/OpenAPI connector.

Ordered query values use UTF-8 `quote_plus`. Login signs SHA1(salt + SHA1(password) + action string); session requests sign SHA1(salt + secret + token + action string). Token and secret remain in memory, expire/refresh under a single auth lock, and are not returned by application APIs. Signed query bytes are attached only inside the network transport through task-local context; public httpx request URLs/hooks/logs contain no query. Wire traffic necessarily contains credentials/signatures protected by TLS.

The connector identifies itself as `solar-fleet-ems`, version 0.3.0, client web. The form defaults to the public company key observed in upstream source; users can supply their platform's issued company key. App identifier/company-key acceptance in a real account remains unverified. No application key is evidence of control authority.

Only these reads are reachable:

1. `queryPlants`: plant IDs/names, at most 50; an unprovable full page or total mismatch fails explicitly.
2. `webQueryCollectorsEs`: per-plant collector pagination, page size 50, bounded at 1,000 collectors; reject repeated PN, changing totals, or plant mismatch.
3. `queryCollectorDevices`: bind exact PN + devcode + devaddr + serial; reject duplicate/ambiguous routes; bounded at 1,000 devices per response and 10,000 per plant.
4. `queryDeviceLastData`: at most ten devices per cycle, at most 1,000 points per device. Preserve native title/value/unit. A title-derived stable key avoids merging names when order changes.

The controller repeats discovery after process restart or an account check invalidates session inventory. A stored DB discovery timestamp is insufficient to prove that an adapter still has its collector routes.

## Connected product behavior

- Accounts → Bluesun → SmartESS saves `equipment_brand=Bluesun`, `vendor=Eybond / SmartESS` and the actual selected platform. No model-to-cloud inference.
- Credentials are encrypted by the existing vault. Administrator account rows may show username, never password/company key/token/secret.
- Check access uses read calls; successful access never means commissioned control.
- Synchronize uses the shared controller, bindings, native samples, source status and local retention. Collection defaults to a **300-second minimum**, enforced in BE and UI. The 120-second controller tick means periodic execution may occur later than 300 seconds. Global/account budgets can further defer work.
- Device filters use observed platform and declared brand. Device detail displays readable native numeric values and string states with original units, using the same shell/styles and VI/EN.
- Source CONNECTED means the read operation succeeded. It does not mean the equipment is online, measurements are recent, or canonical energy accounting is verified.

## Explicit gaps

The inspected last-data response has no established source measurement timestamp. `received_at` is recorded separately; source timestamp stays null, samples remain UNVERIFIED/stale, and unknown state is not rendered as confirmed offline. Timestamp-less points replace the latest unknown sample per metric/binding rather than creating a fabricated time series. No energy KPI is inferred from native title alone.

Still unbuilt: timestamp-bearing history ingestion, alarms, exact canonical/model profiles, native configuration schema retrieval/editing, control/order/readback, refresh on a documented vendor error code, incremental discovery across exhausted call budgets, local PI17/PI18/SMG protocols and device acceptance. Large initial inventories can exhaust the conservative shared call budget before discovery completes; that is an explicit error, not an asserted full fleet import. Unsupported plant pagination fails rather than silently importing only 50.

SOLARMAN V5 framing lives in `adapters/solarman_v5.py`; it is not used for Eybond. `eybond.py` only keeps compatibility imports for the separate cloud and framing modules.

See [24 September validation](eybond-validation-2026-09-24.md) for executed results and remaining acceptance conditions.
