# Vendor adapter audit — 23 September 2026

Historical audit below. On 24 September, the Eybond/DessMonitor gap advanced to an implemented read-only connector with platform selection, session auth, collector discovery and native readings. See [current implementation and remaining gaps](eybond-read-integration.md) and [executed validation](eybond-validation-2026-09-24.md). Other claims here are scoped to the original audit.

This is a code/contract audit on the uncommitted working tree, not certification of live accounts or hardware. The core consumes device identity, observations, universal intents and capabilities; transport-specific field names and semantics belong inside adapters/profiles. Do not label a dependency or native group catalogue as full vendor support.

## Findings and corrections

| Ecosystem | Current implementation | Contract corrections / remaining limits |
|---|---|---|
| Deye | Existing read/configuration/order transport and guarded universal intent compiler | Exact profile/identity, evidence, grant and readback remain required. No live write acceptance in this audit. Deye is the only registered intent compiler; this is not full coverage of all Deye functions/models |
| Solis | User HMAC auth, complete-list discovery, inverter detail; native history/alarm helpers | Exact request bytes, Content-MD5/HMAC-SHA1; preserve declared units. Corrected day `money/timeZone`, month/year native keys and `alarmDeviceSn`. Pagination cannot invent a cursor; incomplete pages fail. Timestamp unit remains native/unknown where docs do not state it. Third-party OAuth/control not shipped |
| GoodWe | Classic SEMS CrossLogin and configured-plant MonitorForAppNew read path | JSON token from `data`, allowlisted returned API host, inverter nested `invert_full`; no guessed identity normalization. This is not the newer WEAPI/SEMS+ integration. Complete organization discovery/history/alarm/control still absent |
| Sungrow | OpenAPI read requests using appkey, access key, token, configured plants and point IDs | Correct sys_code/lang, success envelope and per-request credentials. Unknown point units are not scaled into canonical values. Full point catalogue, grants, other regions, native settings/control and history acceptance remain unresolved |
| Huawei | Northbound typed devIds/devTypeId discovery/latest and native history helpers | XSRF header, collectTime milliseconds, engineering values rather than Modbus scaling, 407 cooldown. Replaced invented getDevHistoryKpi with documented/maintainer getDevFiveMinutes. Alarm helper is not an accepted ingestion/decoder pipeline; no cloud or Modbus write compiler |
| Growatt | OpenAPI v1 token inventory and MIN/SPH family latest data | Token header, GET inventory versus POST form last_data, strict family/pagination handling. Not generic Shine/OSS/password-session compatibility. Other families/history/alarms/control unimplemented or unverified |
| SOLARMAN | D2 cloud read API and optional pysolarmanv5 local collector | D2 grants and OEM protocols are separate; not all tokens permit control. V5 length/control/RTU offset/CRC/identity checked; no generic register map or commissioned write path |
| Eybond / SmartESS | Platform/profile catalogue plus researched Dessmonitor implementation | Removed assumption that Eybond is SOLARMAN V5. No working production Dessmonitor cloud transport yet. Ordered query signing, company keys, hosts and token refresh differ by platform; PI17/PI18/SMG/OEM protocols must be handled independently |
| Bluesun | Brand/model profiles selecting actual OEM/platform/logger | BSM SmartESS, BSE cloud and BMS cloud cannot share an assumed protocol. Cloud branding is not endpoint evidence. No generic Bluesun adapter; model-specific transport/control/schema acceptance is missing |

Native methods that preserve payloads are **not** canonical historical ingestion or alarm correlation by themselves. They still need mapping, source time/units/quality, persistence, permissions, deduplication and UI integration.

The removed non-Deye compiler mappings guessed endpoint paths, enums, command IDs or TOU slot semantics. Their replacement explicitly reports an unresolved contract. Control widgets display capability reasons; compatibility is not inferred from brand name. Firmware/CT/grid/BMS/raw UI cannot unlock hardware without reviewed device contracts.

## Primary and maintainer sources inspected

| Source / version | Inspected contract | Applicability |
|---|---|---|
| [Solis user data API](https://developer.soliscloud.com/guide/data-access-user.html) | Authentication, inverter data/history, alarm filters and pagination notes | User HMAC API; does not imply control grants or stable undocumented timestamp units |
| [Solis user control API](https://developer.soliscloud.com/guide/device-control-v1.html) | Native command/order interface | Does not substantiate a universal cid=12/15 + three-slot schedule compiler |
| [Huawei login](https://info.support.huawei.com/enterprise/en/doc/EDOC1100307213/9e1a18d2/login-interface) | Northbound login/token contract | Regional/account grants remain specific. [Device data](https://support.huawei.com/enterprise/mx/doc/EDOC1100306384/2630ae1b/device-data-interfaces) was indexed; direct text retrieval failed in latest pass |
| [EnergieID/FusionSolar client](https://github.com/EnergieID/FusionSolar/blob/0ffcb7db3a47c466f85354536b45d03de8338087/fusionsolar/client.py) / MIT | Five-minute device endpoint, collectTime and engineering fields; LICENSE | Maintainer implementation. Its cookie-token behavior must not override the official header contract without account observation |
| [indykoning/PyPi_GrowattServer](https://github.com/indykoning/PyPi_GrowattServer/tree/6469d881462eaa4a3b3c6e3cfa6f17082e86eaf5/growattServer/open_api_v1) / MIT | base_api, v1 init, device abstract/MIN/SPH and LICENSE | v1 token API, not legacy web login or blanket family support |
| [yaleman/pygoodwe](https://github.com/yaleman/pygoodwe/tree/a8f636d23c9921681d9e0fb8c7e0f3e5943f37c6) / MIT | Classic SEMS login/session/monitor contracts, LICENSE | Separate from [WEAPI login](https://developers.we.goodwe.com/docs/main/02-%E6%8E%A5%E5%8F%A3%E6%96%87%E6%A1%A3/login). No claim to SEMS+ compatibility |
| [Sungrow practical guide, February 2026](https://sungrowacademy.com.br/wp-content/uploads/2026/02/Sungrow-API-Guia-Pratico-022026-2.pdf), [developer portal](https://developer-api.isolarcloud.com) | Auth fields, access-key and HK gateway/read examples | Configured point IDs and plants; units and writes require further evidence |
| [SOLARMAN account/capabilities](https://doc.solarmanpv.com/en/Public%20Information/12Account%20and%20Capabilities) | D2 access versus control/OEM privileges | No automatic write privilege from successful authentication |
| [pysolarmanv5](https://github.com/jmccrohan/pysolarmanv5/tree/8cfe84650f48f0803c32b3c4ca061364abd9cf49) / MIT, 3.0.6 | V5 framing, RTU payload, identity, disconnect; README/license | Optional read dependency, not a source of generic device registers |
| [andreas-glaser/ha-dessmonitor](https://github.com/andreas-glaser/ha-dessmonitor/tree/3b530bf34d91eef43ec2474d971019fa48c5ae16) / MIT | api.py, const.py, test_api_profiles.py, test_api_security.py, LICENSE | Research only: ordered query signatures, platform keys/hosts, session renewal. Credentials in query strings must never enter logs |
| [Bluesun BSM manual](https://www.bluesuneurope.eu/user/documents/upload/BSM-5500BLV-48DA%20%20User%20Manual%20V2.0.pdf), [ha-solarman](https://github.com/davidrapan/ha-solarman) | SmartESS monitoring and model-specific community profiles | Supports model/platform research, not “every Bluesun works via SOLARMAN” |

The exact inspected community revisions and local file digests are recorded in source-registry.json. Source visibility is not a license grant; the listed projects' MIT licenses were checked where revision-specific research is cited. No community source trees were vendored. The optional installed library carries upstream licensing; see THIRD_PARTY_NOTICES.md.

## Provenance repair

The two source registries now contain **57 unique IDs**, with identical documentary and packaged contents. A duplicate `SOLARMAN_LOCAL_001` was removed, preserving the original OpenData HTTP record. That record must not be confused with V5 TCP framing or cloud API.

Five post-baseline records asserted verified contracts without adequate evidence: `GROWATT_OPENAPI_001`, `SUNGROW_DEV_001`, `GOODWE_SEMS_001`, `HUAWEI_NB_001`, `SOLIS_CONTROL_001`. Their assertions are withdrawn, graded F, with digest UNKNOWN. Replacement scoped evidence is separate. The old digest strings are not retained as trustworthy hashes. Other baseline records are historical source observations, not a statement that every URL/schema has been recertified in this pass.

Grade A/B/C/D describes source type; F here explicitly includes unverified community applicability. Even an A source does not establish exact model/firmware/control acceptance. Evidence identity alone must not unlock capability.

## Next engineering required before claiming mature support

Per variant: document auth refresh/errors/region, inventory completeness, physical identity, timestamps, units/signs/enums, history paging/backfill, alarm state and recovery semantics; implement end-to-end ingestion; then native read/settings/control/readback with exact profiles and failure handling. Expand fixtures with actual sanitized account observations and perform hardware acceptance. Eybond transport, shipping mappings, native UI schemas and agent lifecycle are unfinished engineering, not work completed pending a login.
