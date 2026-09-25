# Multi-vendor contracts — current implementation, 25 September 2026

[Project README](../README.md) · [Documentation index](README.md) · [Implementation status](implementation-status.md) · [Validation](validation.md)

There are **eight cloud read integrations of different depth**, plus Bluesun brand/model routing. None is certified for all models or accepted on customer hardware by the recorded verification. The [source registry](evidence/source-registry.json) has 57 unique records, including withdrawn claims; this is an evidence inventory, not 57 proven capabilities.

## Implemented boundaries

| Integration / code | Authentication and discovery | Semantics and outstanding work |
|---|---|---|
| [Deye](../src/solar_fleet/adapters/cloud.py) | Issued app ID/secret, SHA-256 password, identity/account/region grants; station/device discovery | Latest/history/alarms/configuration/order transport. Cached getters do not prove fresh configuration. Exact canonical and write/readback acceptance remain required |
| [Solis](../src/solar_fleet/adapters/solis.py) | Key ID/secret; exact UTF-8 body, Base64 MD5, HMAC-SHA1, GMT date; complete-list discovery | Detail/history/alarm helpers preserve native fields. Incomplete list fails rather than guessing a cursor; undocumented timestamp units remain unknown. No control compiler or third-party OAuth |
| [SOLARMAN](../src/solar_fleet/adapters/solarman.py) | App ID/secret, SHA-256 password, identity and optional orgId; global/China hosts; paged station/device lists | D2 current data, documented collection time, native key/unit provenance. OEM/logger and token privileges remain separate; no universal register map/control |
| [GoodWe](../src/solar_fleet/adapters/goodwe.py) | Classic SEMS CrossLogin JSON token and allowlisted returned API host; configured plant IDs | MonitorForAppNew/nested inverter reads. Not WEAPI/SEMS+, complete organization discovery, history/alarm pipeline or write support |
| [Sungrow](../src/solar_fleet/adapters/sungrow.py) | OpenAPI appkey/access key, user token; configured plant and point IDs | Exact request credentials/envelope. No guessed scaling for unknown point units; full regional/point catalogue/native control remains absent |
| [Huawei](../src/solar_fleet/adapters/huawei.py) | Northbound account/system code, XSRF header; typed device ID/type discovery and latest | collectTime milliseconds, engineering values without Modbus rescaling, quota cooldown; native history helper. No accepted alarm pipeline or cloud/local write compiler |
| [Growatt](../src/solar_fleet/adapters/growatt.py) | OpenAPI v1 token header; GET inventory, POST form latest for MIN/SPH | Explicit device family/pagination. Not generic legacy Shine/OSS sessions or every family; history/alarm/control incomplete |
| [Eybond / SmartESS](../src/solar_fleet/adapters/dessmonitor.py) | Explicit DessMonitor or ShineMonitor platform; ordered query signing/session expiry; plant → collector → device | Preserve native labels/string states/units. Source measurement time remains unknown; minimum polling 300 seconds. History, alarms, canonical profiles and control are unbuilt |
| [Bluesun profiles](../src/solar_fleet/adapters/bluesun.py) | Declared brand selects actual SOLARMAN or Eybond account transport where applicable | No generic Bluesun API. BSE/BSM/BMS/OEM/logger variants need exact evidence and acceptance |

The [23 September audit](vendor-adapter-audit-2026-09-23.md) records official/maintainer sources, corrections and scoped applicability for the first seven paths. The later [Eybond contract](eybond-read-integration.md) supersedes its Eybond transport gap. [Bluesun research](bluesun-integration.md) covers brand/platform boundaries and the optional local collector.

Native history/alarm helper methods do not by themselves provide canonical ingestion, persistence, recovery/deduplication or an end-to-end UI workflow. Those missing parts remain in the [coverage matrix](mockup-coverage.md).

## Shared core, separate protocol contracts

[Integration plugins](../src/solar_fleet/adapters/plugins.py) are the composition root; [provider manifests](../src/solar_fleet/providers.py) declare setup fields and selectable regions/platforms. The [extension contract](core-extension-contract.md) defines observations, telemetry profiles, capabilities and compiler interfaces. The controller does not translate one vendor's field name, command ID or unit directly into another vendor's value.

Setup → encrypted account → discovery/binding → native samples → scoped views is a shared workflow. HTTP methods, payload fields, signing, token renewal, pagination, errors, timestamp units and rate limits remain adapter-specific. Redirects/arbitrary user-supplied API destinations are not fallback mechanisms.

Read loops use conservative budgets and adapter-specific caps. A 120-second controller tick does not promise a 120-second measurement age; Eybond enforces at least 300 seconds and can run later. Unknown source time is not replaced by receipt time to claim freshness.

The [mapping workspace](mapping-validation-2026-09-25.md) lets engineers inspect observed fields and simulate unit/direction transforms with versioned independent review. Review does not install a profile, mark a native value GOOD, or make it EMS/control input.

## Control and vendor-native UI

Only [Deye's intent compiler](../src/solar_fleet/adapters/deye_control.py) is currently registered. Guessed non-Deye paths/enums/TOU commands were removed. A vendor-native group or disabled form is discoverability, not implemented parameter read/write.

Universal intents pass through capability/profile identity, role/range/freshness, preview/diff, digest confirmation, idempotency, device serialization, native order and readback verification. Neither successful authentication nor the write environment flag supplies missing acceptance. See [candidate control mapping](universal-control-mapping.md) and [hardware acceptance](hardware-acceptance.md).

## Public sources and authorized observation

Continue research through manufacturer developer portals/manuals and comparable public applications. Record exact upstream revision/path/license, distinguish official contracts from community observations and preserve notices; public visibility alone is not a copying license. [Source audit](vendor-source-audit.md), [registry](evidence/source-registry.json), [third-party notices](../THIRD_PARTY_NOTICES.md) and [repository workflow](../AGENTS.md) own these obligations.

For an authorized account, record region/role/model/logger/firmware and the exact operation. Classify effects instead of assuming POST means write or GET means harmless. Keep secrets/cookies/customer payloads out of the repository; derive sanitized fixtures. Do not infer protocol compatibility from a brand, logo, similar field name or available endpoint.

Per variant, complete contract/error/permission/pagination/quota tests, actual history/alarm ingestion, model normalization, native schemas and accepted control/readback. Passing synthetic cases or adding a dependency does not finish that engineering.
