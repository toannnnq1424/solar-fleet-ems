# Multi-vendor implementation addendum — 0.2.0

Research retrieved on 2026-09-13; implementation validated separately. This addendum updates the initial report and older source audit. It does not certify a customer account or inverter. The packaged and documentary registries contain the same 45 top-level evidence records.

## Implemented read connectors

| Connector | Implemented contracts | Authentication | Unresolved acceptance |
|---|---|---|---|
| Deye | Stations, devices, latest, history, alarms, configuration; existing native order transport remains guarded | Issued App ID/secret, SHA-256 password, account/region grants | Exact hardware identity, canonical metrics, configuration freshness, physical command verification |
| Solis | `userStationList`, `inverterList`, `inverterDetail` | Key ID/secret; exact UTF-8 request body, Base64 MD5, HMAC-SHA1, GMT date | Pagination contract, timestamp units, unit-field types, actual account grants |
| SOLARMAN | Token, station list, station devices, `currentData` | App ID/secret, SHA-256 password, email/username; optional Pro orgId | App grants, device OEM and protocol profile; history/alarms/control not implemented |

### Solis

[Authorization](https://developer.soliscloud.com/guide/authorization.html), [user data](https://developer.soliscloud.com/guide/data-access-user.html), [device control](https://developer.soliscloud.com/guide/device-control-v1.html) and [Modbus entry point](https://developer.soliscloud.com/guide/modbus.html) are primary manufacturer sources (`SOLIS_DEV_*_002`). Hashes are in the source registry. The newer portal describes owners and installers; the older support article's end-user-only restriction must not be treated as a universal current rule. Per-account grants still need confirmation. Third-party OAuth is a separate contract and is not implemented.

The HMAC implementation follows the documented signing formula and control example. The authorization example contains inconsistent whitespace before its content-type string; live acceptance must resolve that example discrepancy. The global user API host is fixed at `https://www.soliscloud.com:13333`; callers cannot supply arbitrary hosts or paths.

The portal labels list pagination/minId as pending. The adapter accepts only a complete list where returned row count equals the declared total; otherwise it reports incomplete discovery. It does not guess a cursor. `dataTimestamp` is retained natively because its unit is not stated. Consequently Solis samples have unknown measurement time and remain stale for control; no fabricated history or fresh readback. Unit fields are also retained only when their actual response value is a string. No Solis write path is shipped.

### SOLARMAN

[Official guide](https://doc.solarmanpv.com/en/Documentation%20and%20Quick%20Guide), [token contract](https://doc.solarmanpv.com/en/Account%20Interface/2.1Obtain%20Token.md), [station list](https://doc.solarmanpv.com/en/Power%20Station%20Interface/4.4Obtain%20Power%20Station%20List%20Under%20Account.md), [device list](https://doc.solarmanpv.com/en/Power%20Station%20Interface/4.2Obtain%20Power%20Station%20Device%20List.md), and [current data](https://doc.solarmanpv.com/en/Device%20interface/3.3Real-time%20device%20data.md) establish the implemented read contracts. The English token page omits a response example; the official [Chinese token page](https://doc.solarmanpv.com/账号接口/2.1获取Token) describes the response fields.

Global and China API hosts are fixed allowlists. Token lifetime is checked from `expires_in`; tokens stay in process memory. Pagination rejects repeated/incomplete responses. `currentData.collectionTime` is documented in epoch seconds. Samples retain native metric names, units, source and evidence, with `UNVERIFIED` quality until a model profile is accepted. SOLARMAN is the cloud/logger platform, not proof of the inverter's OEM.

## Other ecosystems and authorized reverse engineering

GoodWe, Sungrow, Huawei, Growatt, Eybond/SmartESS and Bluesun remain visible in the integration catalog with an explicit contract-pending state. Manufacturer documentation, local-driver options and community implementation leads are recorded in the original source audit. A blank adapter is not presented as a working connector.

When an authorized account is available, record the region, account role, visible model/logger/firmware and the exact read operation. Inspect the documented API first, then authorized web/app behavior where the public contract is insufficient. Keep private session material outside the repository; do not store browser cookies in the application or replay traffic against unrelated accounts. Do not assume a POST is a write or a GET is harmless: classify each observed endpoint by its effect.

For each observed contract, record request/response field schemas, success and error semantics, pagination, rate limits, token expiry, timestamp basis and unit/sign evidence. Replace all customer values with synthetic fixtures. A read adapter must pass auth, denied-permission, pagination, wrong-device, stale-time, redirect, quota and malformed-response cases before it becomes selectable. A control adapter additionally requires an exact commissioned identity, constraints, preview/diff, fresh device readback and reviewed acceptance. Reverse-engineered evidence is labeled as observation, not as an official API guarantee.

## Shared behavior and limits

All three connectors use one controller lifecycle and persistent discovery/bindings. Read loops share conservative budgets; 429 triggers bounded backoff and writes are never retried automatically. Current per-cycle telemetry batches are 50 Deye devices or 10 Solis/SOLARMAN devices, rotated between cycles; over-capacity fleets are reported explicitly. This is a single-process pilot, not a large-fleet SLA.

App management writes (incidents, profiles, schedules, rules and users) are transactional and audited. Physical control remains separately gated. The EMS evaluator accepts only fresh, verified measurements with exact units and an unambiguous source. Draft evaluation is deterministic and never creates a command.
