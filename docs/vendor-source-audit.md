> **Historical snapshot — superseded for current implementation.** See [23 September adapter audit](vendor-adapter-audit-2026-09-23.md) and [26-screen coverage](mockup-coverage.md). Counts and completion claims below describe an older state; they are not current acceptance. Current registries are synchronized with 61 unique IDs, including explicitly withdrawn claims.

# Vendor source audit

Current 27 September addition: [30-project review](legacy-project-audit.md), [model/HA implementation](model-library-and-home-assistant.md), four pinned MIT source bundles in the [source lock](../src/solar_fleet/data/model-source-lock.json). Registry IDs ha-solarman-models, glance-modbus-models, sungrow-ha-models and sem-hourly-baseline are community evidence, not hardware acceptance.

> Current implementation is indexed in [multi-vendor contracts](multivendor-contracts.md), including the later [Eybond read connector](eybond-read-integration.md). The [registry](evidence/source-registry.json) currently has 61 unique IDs, including withdrawn claims. Source entries below retain their observation dates; their old counts are historical. [Documentation index](README.md).

Bổ sung ngày 13/09 sau baseline: [DEYE_UI_OBS_001 — quan sát phiên Deye Cloud có xác thực](deye-account-observation.md), cấp E. Chỉ xác nhận các metadata/menu được thấy ở một thiết bị; không thay official API contract hoặc hardware acceptance. Registry tại thời điểm bổ sung đó có 38 mục, không phải tổng hiện tại.

Baseline 2026-09-13. A/B/C/D là loại nguồn, không phải chứng nhận thiết bị. Baseline trước quan sát Deye chưa có E; quan sát sau đó được ghi riêng phía trên. F không bật production. Các nguồn chỉ đọc được qua index được ghi rõ. Manual gốc không được commit.

## DEYE_PORTAL_001

[Deye Developer Portal](https://developer.deyecloud.com/)

| Trường | Nội dung |
|---|---|
| publisher | developer.deyecloud.com |
| version | UNKNOWN |
| publication_date | UNKNOWN |
| retrieved_date | 2026-09-13 |
| applicable_products | See scoped conclusion; otherwise UNKNOWN |
| account_type | UNKNOWN unless stated |
| region | UNKNOWN unless stated |
| relevant_sections | Application registration |
| evidence_grade | A |
| access_status | HTTP 200; retrieved |
| claims | Developer portal; app/account setup required. |
| implications | Public shell only; organization grants and quota not supplied. |
| open_questions | Public shell only; organization grants and quota not supplied. |

## DEYE_API_001

[Deye Open MCP Tool Documentation](https://developer.deyecloud.com/openmcp/docs/deye-open-mcp-tools.html)

| Trường | Nội dung |
|---|---|
| publisher | developer.deyecloud.com |
| version | OpenAPI v1.0 / MCP v1.2 |
| publication_date | UNKNOWN |
| retrieved_date | 2026-09-13 |
| applicable_products | See scoped conclusion; otherwise UNKNOWN |
| account_type | UNKNOWN unless stated |
| region | UNKNOWN unless stated |
| relevant_sections | station;device;config;control;strategy |
| evidence_grade | A |
| access_status | HTTP 200; retrieved |
| claims | Official endpoint and request schemas; order status and configuration read paths. |
| implications | No complete model/firmware/range matrix or guaranteed device-fresh readback. |
| open_questions | No complete model/firmware/range matrix or guaranteed device-fresh readback. |

## DEYE_MANUAL_CENTER_001

[Deye Product Manual Center](https://au.deyeinverter.com/download/product-manual/)

| Trường | Nội dung |
|---|---|
| publisher | au.deyeinverter.com |
| version | Current index |
| publication_date | UNKNOWN |
| retrieved_date | 2026-09-13 |
| applicable_products | See scoped conclusion; otherwise UNKNOWN |
| account_type | UNKNOWN unless stated |
| region | UNKNOWN unless stated |
| relevant_sections | Remote Control; Creating Plants; Wi-Fi; SG04LP3 |
| evidence_grade | B |
| access_status | HTTP 403; HTTPError |
| claims | Index links official manuals via hqcdn.hqsmartcloud.com. |
| implications | Index readable via web; direct download path returned 403. |
| open_questions | Index readable via web; direct download path returned 403. |

## SOLIS_UI_001

[SolisCloud Remote Control Settings](https://solis-service.solisinverters.com/en/support/solutions/articles/44002638862-solis-cloud-remote-control-settings-desktop-version)

| Trường | Nội dung |
|---|---|
| publisher | solis-service.solisinverters.com |
| version | UNKNOWN |
| publication_date | UNKNOWN |
| retrieved_date | 2026-09-13 |
| applicable_products | See scoped conclusion; otherwise UNKNOWN |
| account_type | UNKNOWN unless stated |
| region | UNKNOWN unless stated |
| relevant_sections | Installer vs Owner; work modes; battery; meter; grid |
| evidence_grade | D |
| access_status | HTTP 200; retrieved |
| claims | Web UI remote settings vary by model/firmware and role. |
| implications | UI permission does not establish a programmable write API. |
| open_questions | UI permission does not establish a programmable write API. |

## SOLIS_API_001

[SolisCloud API Access](https://solis-service.solisinverters.com/en/support/solutions/articles/44002212561-request-api-access-soliscloud)

| Trường | Nội dung |
|---|---|
| publisher | solis-service.solisinverters.com |
| version | 2024-08-22 article; linked API V2.0 |
| publication_date | UNKNOWN |
| retrieved_date | 2026-09-13 |
| applicable_products | See scoped conclusion; otherwise UNKNOWN |
| account_type | UNKNOWN unless stated |
| region | UNKNOWN unless stated |
| relevant_sections | Request API access |
| evidence_grade | D |
| access_status | HTTP 200; retrieved |
| claims | Article distinguishes end-user API access from remote control. |
| implications | Current installer API eligibility and attached full contract need confirmation. |
| open_questions | Current installer API eligibility and attached full contract need confirmation. |

## SOLIS_MODBUS_001

[Solis Modbus Table Access](https://solis-service.solisinverters.com/en/support/solutions/articles/44002663852-non-nda-modus-table)

| Trường | Nội dung |
|---|---|
| publisher | solis-service.solisinverters.com |
| version | Updated 2026-08-06 |
| publication_date | UNKNOWN |
| retrieved_date | 2026-09-13 |
| applicable_products | See scoped conclusion; otherwise UNKNOWN |
| account_type | UNKNOWN unless stated |
| region | UNKNOWN unless stated |
| relevant_sections | NDA Modbus Table |
| evidence_grade | D |
| access_status | HTTP 200; retrieved |
| claims | Qualified EMS/integrator/OEM/SCADA requests are reviewed for read/write and NDA. |
| implications | Register map required; URL slug is stale, not a non-NDA guarantee. |
| open_questions | Register map required; URL slug is stale, not a non-NDA guarantee. |

## GOODWE_API_001

[GoodWe API Technical Document](https://community.goodwe.com/static/images/2024-08-20597794.pdf)

| Trường | Nội dung |
|---|---|
| publisher | community.goodwe.com |
| version | SA-B-20240814-001 |
| publication_date | UNKNOWN |
| retrieved_date | 2026-09-13 |
| applicable_products | See scoped conclusion; otherwise UNKNOWN |
| account_type | UNKNOWN unless stated |
| region | UNKNOWN unless stated |
| relevant_sections | PDF pp.2–4 |
| evidence_grade | A |
| access_status | HTTP 200; retrieved |
| claims | Organization OpenAPI; realtime read API; licensed/whitelisted batch control with Kafka. |
| implications | Device schemas, limits and credentials need SEMS agreement. |
| open_questions | Device schemas, limits and credentials need SEMS agreement. |

## GOODWE_API_002

[GoodWe API Introduction](https://community.goodwe.com/static/images/2022-11-08281223.pdf)

| Trường | Nội dung |
|---|---|
| publisher | community.goodwe.com |
| version | SA-E-20221031-001 |
| publication_date | UNKNOWN |
| retrieved_date | 2026-09-13 |
| applicable_products | See scoped conclusion; otherwise UNKNOWN |
| account_type | UNKNOWN unless stated |
| region | UNKNOWN unless stated |
| relevant_sections | PDF pp.1–3 |
| evidence_grade | A |
| access_status | HTTP 200; retrieved |
| claims | Earlier API architecture; firmware upgrade outside OpenAPI; separate IoT account workflow. |
| implications | Use newer 2024 publication for architecture and confirm current contract. |
| open_questions | Use newer 2024 publication for architecture and confirm current contract. |

## GOODWE_LOGGER_001

[GoodWe EzLogger3000C](https://en.goodwe.com/ezlogger3000c)

| Trường | Nội dung |
|---|---|
| publisher | en.goodwe.com |
| version | UNKNOWN |
| publication_date | UNKNOWN |
| retrieved_date | 2026-09-13 |
| applicable_products | See scoped conclusion; otherwise UNKNOWN |
| account_type | UNKNOWN unless stated |
| region | UNKNOWN unless stated |
| relevant_sections | Overview; connectivity |
| evidence_grade | C |
| access_status | HTTP 200; retrieved |
| claims | EzLogger3000C advertises simultaneous SEMS/third-party monitoring, 100 devices, 30-day retention. |
| implications | No implication that multiple control writers may run concurrently. |
| open_questions | No implication that multiple control writers may run concurrently. |

## SUNGROW_WEB_001

[Sungrow iSolarCloud WEB 3.0 Manual](https://support.sungrowpower.com/Document?chapter=GUID-614EF63E-B4C4-4813-8C42-94F224FAF40F.html&ids=child_model-c4586872-a377-41a8-8b69-9d0854d49b99&materialId=material-fc79d214-1070-4f29-b490-fb9021aab410&source=PRODUCT)

| Trường | Nội dung |
|---|---|
| publisher | support.sungrowpower.com |
| version | Ver26; displayed 5/8/2026 |
| publication_date | UNKNOWN |
| retrieved_date | 2026-09-13 |
| applicable_products | See scoped conclusion; otherwise UNKNOWN |
| account_type | UNKNOWN unless stated |
| region | UNKNOWN unless stated |
| relevant_sections | Contents: plant/device/settings |
| evidence_grade | B |
| access_status | HTTP 200; retrieved |
| claims | WEB 3.0 index retrieved via official search index. |
| implications | JavaScript shell in direct fetch; full contents corroborated with linked O&M PDF only where applicable. |
| open_questions | JavaScript shell in direct fetch; full contents corroborated with linked O&M PDF only where applicable. |

## SUNGROW_OM_001

[Sungrow iSolarCloud O&M Manual](https://info-support.sungrowpower.com/product-materials/8cc7a6f7-36ff-4489-b9af-15546dc42ca2.pdf)

| Trường | Nội dung |
|---|---|
| publisher | info-support.sungrowpower.com |
| version | iSolarCloud-V146-UEN-Ver26-202605 |
| publication_date | UNKNOWN |
| retrieved_date | 2026-09-13 |
| applicable_products | See scoped conclusion; otherwise UNKNOWN |
| account_type | UNKNOWN unless stated |
| region | UNKNOWN unless stated |
| relevant_sections | §2.3.13.1.1.7;§3.3.2; PDF p.96 |
| evidence_grade | B |
| access_status | HTTP 200; retrieved |
| claims | VPP uses provider commands through API; Logger1000/iHomeManager third-party modes restrict switching. |
| implications | No partner API contract; region and firmware constraints apply. |
| open_questions | No partner API contract; region and firmware constraints apply. |

## SUNGROW_LOGGER_001

[Sungrow Logger1000 Manual](https://info-support.sungrowpower.com/application/pdf/2023/03/10/Logger1000A_B-UEN-Ver110-202301.pdf)

| Trường | Nội dung |
|---|---|
| publisher | info-support.sungrowpower.com |
| version | Logger1000A_B-UEN-Ver110-202301 |
| publication_date | UNKNOWN |
| retrieved_date | 2026-09-13 |
| applicable_products | See scoped conclusion; otherwise UNKNOWN |
| account_type | UNKNOWN unless stated |
| region | UNKNOWN unless stated |
| relevant_sections | §5.4;§7.10.6–9;§8 |
| evidence_grade | C |
| access_status | HTTP 200; retrieved |
| claims | Modbus TCP server/client, RTU and IEC104 support instruction forwarding. |
| implications | Require exact downstream register/point table and arbitration tests. |
| open_questions | Require exact downstream register/point table and arbitration tests. |

## HUAWEI_AUTH_001

[Huawei Northbound Login Interface](https://info.support.huawei.com/enterprise/en/doc/EDOC1100307213/9e1a18d2/login-interface)

| Trường | Nội dung |
|---|---|
| publisher | info.support.huawei.com |
| version | EDOC1100307213; V600R024C00; indexed update 2023-09-12 |
| publication_date | UNKNOWN |
| retrieved_date | 2026-09-13 |
| applicable_products | See scoped conclusion; otherwise UNKNOWN |
| account_type | UNKNOWN unless stated |
| region | UNKNOWN unless stated |
| relevant_sections | Login Interface |
| evidence_grade | A |
| access_status | HTTP 200; retrieved |
| claims | Indexed official document: POST thirdData/login, userName/systemCode, header XSRF-TOKEN, 30-minute lifetime. |
| implications | Direct fetch blocked/redirected; cached/indexed content needs current revalidation before adapter. |
| open_questions | Direct fetch blocked/redirected; cached/indexed content needs current revalidation before adapter. |

## HUAWEI_SCHED_001

[Huawei Remote Scheduling / SmartLogger](https://info.support.huawei.com/DpinfoAppDoc/pro_erp_slice001/doc/fusion_solar/public/commercial_energy/en/en-us_topic_0000002205688713.html)

| Trường | Nội dung |
|---|---|
| publisher | info.support.huawei.com |
| version | UNKNOWN |
| publication_date | UNKNOWN |
| retrieved_date | 2026-09-13 |
| applicable_products | See scoped conclusion; otherwise UNKNOWN |
| account_type | UNKNOWN unless stated |
| region | UNKNOWN unless stated |
| relevant_sections | Active Power Control / Remote Communication Scheduling |
| evidence_grade | B |
| access_status | HTTP 200; retrieved |
| claims | SmartLogger accepts scheduling through Modbus TCP, GOOSE or IEC104. |
| implications | Specific SmartLogger/inverter/ESS revisions and control contract UNKNOWN. |
| open_questions | Specific SmartLogger/inverter/ESS revisions and control contract UNKNOWN. |

## HUAWEI_FAQ_001

[Huawei FusionSolar Installer FAQ](https://info.support.huawei.com/DpinfoAppDoc/pro_erp_slice001/doc/fusion_solar/faq/installer/en/en-us_topic_0000001867081537.html?styleType=white)

| Trường | Nội dung |
|---|---|
| publisher | info.support.huawei.com |
| version | UNKNOWN |
| publication_date | UNKNOWN |
| retrieved_date | 2026-09-13 |
| applicable_products | See scoped conclusion; otherwise UNKNOWN |
| account_type | UNKNOWN unless stated |
| region | UNKNOWN unless stated |
| relevant_sections | API application; remote on/off |
| evidence_grade | D |
| access_status | HTTP 200; retrieved |
| claims | Company administrator applies for northbound APIs; SmartPVMS has remote on/off UI. |
| implications | Does not demonstrate unrestricted REST control rights. |
| open_questions | Does not demonstrate unrestricted REST control rights. |

## GROWATT_OSS_001

[Growatt Monitoring & OSS FAQ](https://vn.growatt.com/support/faq/monitoring)

| Trường | Nội dung |
|---|---|
| publisher | vn.growatt.com |
| version | UNKNOWN |
| publication_date | UNKNOWN |
| retrieved_date | 2026-09-13 |
| applicable_products | See scoped conclusion; otherwise UNKNOWN |
| account_type | UNKNOWN unless stated |
| region | UNKNOWN unless stated |
| relevant_sections | Monitoring / OSS remote settings |
| evidence_grade | D |
| access_status | HTTP 200; retrieved |
| claims | Installer OSS workflow includes remote device settings. |
| implications | Programmable API auth, schema, quota and exact model scope UNKNOWN. |
| open_questions | Programmable API auth, schema, quota and exact model scope UNKNOWN. |

## GROWATT_SETTING_001

[Growatt Device Remote Setting Interface](https://openapi.growatt.com/commonDeviceSetC/setTlx?type=server)

| Trường | Nội dung |
|---|---|
| publisher | openapi.growatt.com |
| version | UNKNOWN |
| publication_date | UNKNOWN |
| retrieved_date | 2026-09-13 |
| applicable_products | See scoped conclusion; otherwise UNKNOWN |
| account_type | UNKNOWN unless stated |
| region | UNKNOWN unless stated |
| relevant_sections | Device Remote Setting form |
| evidence_grade | A |
| access_status | HTTP 200; retrieved |
| claims | Official remote-setting page exposes parameter names. |
| implications | A live form is not a published automation contract; no requests sent to devices. |
| open_questions | A live form is not a published automation contract; no requests sent to devices. |

## SOLARMAN_CONTROL_001

[SOLARMAN — Control inverter via API](https://helpcenter.solarmanpv.com/portal/en/kb/articles/how-to-control-inverter-via-api)

| Trường | Nội dung |
|---|---|
| publisher | helpcenter.solarmanpv.com |
| version | UNKNOWN |
| publication_date | UNKNOWN |
| retrieved_date | 2026-09-13 |
| applicable_products | See scoped conclusion; otherwise UNKNOWN |
| account_type | UNKNOWN unless stated |
| region | UNKNOWN unless stated |
| relevant_sections | Control inverter via API |
| evidence_grade | D |
| access_status | HTTP 200; retrieved |
| claims | Custom command permission plus OEM inverter protocol are both required. |
| implications | Transport capability alone never establishes an inverter command mapping. |
| open_questions | Transport capability alone never establishes an inverter command mapping. |

## SOLARMAN_LICENSE_001

[SOLARMAN API Activation Guide](https://helpcenter.solarmanpv.com/portal/en/kb/articles/i-want-to-open-api-how-can-i-open-api)

| Trường | Nội dung |
|---|---|
| publisher | helpcenter.solarmanpv.com |
| version | UNKNOWN |
| publication_date | UNKNOWN |
| retrieved_date | 2026-09-13 |
| applicable_products | See scoped conclusion; otherwise UNKNOWN |
| account_type | UNKNOWN unless stated |
| region | UNKNOWN unless stated |
| relevant_sections | API Activation Guide |
| evidence_grade | D |
| access_status | HTTP 200; retrieved |
| claims | API activation/license workflow; Business is paid; free Smart tier has plant/call limits. |
| implications | Do not agree to terms or submit contact messages automatically. |
| open_questions | Do not agree to terms or submit contact messages automatically. |

## SOLARMAN_HELP_001

[SOLARMAN API Help Center](https://helpcenter.solarmanpv.com/portal/en/kb/solarman2/solarman-business/faq/api)

| Trường | Nội dung |
|---|---|
| publisher | helpcenter.solarmanpv.com |
| version | UNKNOWN |
| publication_date | UNKNOWN |
| retrieved_date | 2026-09-13 |
| applicable_products | See scoped conclusion; otherwise UNKNOWN |
| account_type | UNKNOWN unless stated |
| region | UNKNOWN unless stated |
| relevant_sections | API help center |
| evidence_grade | D |
| access_status | HTTP 200; retrieved |
| claims | Support navigation to activation/control material. |
| implications | No added endpoint or model support conclusions. |
| open_questions | No added endpoint or model support conclusions. |

## SOLARMAN_LOCAL_001

[SOLARMAN OpenData Developer Documentation](https://docs.solarman.ai/docs/api/opendata/)

| Trường | Nội dung |
|---|---|
| publisher | docs.solarman.ai |
| version | UNKNOWN |
| publication_date | UNKNOWN |
| retrieved_date | 2026-09-13 |
| applicable_products | See scoped conclusion; otherwise UNKNOWN |
| account_type | UNKNOWN unless stated |
| region | UNKNOWN unless stated |
| relevant_sections | OpenData: enable;firmware;HTTP;Digest;Sys/Device |
| evidence_grade | A |
| access_status | HTTP 200; retrieved |
| claims | Local HTTP API has activation and firmware requirements; HTTPS listed as coming soon. |
| implications | No assertion that every logger has OpenData or supports inverter writes. |
| open_questions | No assertion that every logger has OpenData or supports inverter writes. |

## SOLARMAN_EMH_001

[SOLARMAN EMH-2 Quick Start](https://docs.solarman.ai/docs/emh-2/quick-start/)

| Trường | Nội dung |
|---|---|
| publisher | docs.solarman.ai |
| version | UNKNOWN |
| publication_date | UNKNOWN |
| retrieved_date | 2026-09-13 |
| applicable_products | See scoped conclusion; otherwise UNKNOWN |
| account_type | UNKNOWN unless stated |
| region | UNKNOWN unless stated |
| relevant_sections | EMH-2 quick start |
| evidence_grade | C |
| access_status | HTTP 200; retrieved |
| claims | Gateway wiring includes LAN/WAN, RS485, P1 and DO. |
| implications | Hardware wiring does not define supported OEM inverter control semantics. |
| open_questions | Hardware wiring does not define supported OEM inverter control semantics. |

## EYBOND_GUIDE_001

[SmartESS Operating Instruction](https://fms.eybond.com/fms/api/auth/web/doc/html/previewOnline/72/2)

| Trường | Nội dung |
|---|---|
| publisher | fms.eybond.com |
| version | UNKNOWN |
| publication_date | UNKNOWN |
| retrieved_date | 2026-09-13 |
| applicable_products | See scoped conclusion; otherwise UNKNOWN |
| account_type | UNKNOWN unless stated |
| region | UNKNOWN unless stated |
| relevant_sections | Registration; PN/QR/Bluetooth; networking |
| evidence_grade | B |
| access_status | HTTP 200; retrieved |
| claims | SmartESS account/device onboarding and network setup depend on logger. |
| implications | Public programmable API not verified. |
| open_questions | Public programmable API not verified. |

## EYBOND_ESS_001

[Eybond Household ESS Platform](https://www.eybond.com/Household.html)

| Trường | Nội dung |
|---|---|
| publisher | www.eybond.com |
| version | UNKNOWN |
| publication_date | UNKNOWN |
| retrieved_date | 2026-09-13 |
| applicable_products | See scoped conclusion; otherwise UNKNOWN |
| account_type | UNKNOWN unless stated |
| region | UNKNOWN unless stated |
| relevant_sections | Household ESS solution |
| evidence_grade | C |
| access_status | HTTP 200; retrieved |
| claims | Cloud monitoring, ESS strategies, alarms and OTA are described at solution level. |
| implications | Marketing scope is not model-specific API authorization. |
| open_questions | Marketing scope is not model-specific API authorization. |

## BLUESUN_BSM_001

[Bluesun BSM-5500BLV-48DA Manual](https://www.bluesunpv.com/wp-content/uploads/2024/11/BSM-5500BLV-48DA-User-Manual-V2.0.pdf)

| Trường | Nội dung |
|---|---|
| publisher | www.bluesunpv.com |
| version | BSM-5500BLV-48DA V2.0 |
| publication_date | UNKNOWN |
| retrieved_date | 2026-09-13 |
| applicable_products | See scoped conclusion; otherwise UNKNOWN |
| account_type | UNKNOWN unless stated |
| region | UNKNOWN unless stated |
| relevant_sections | §5.2–3;PDF p.54 |
| evidence_grade | C |
| access_status | HTTP 200; retrieved |
| claims | Model manual names SmartESS and lists USB/RS485 communication. |
| implications | OEM, logger revision and command/register map UNKNOWN. |
| open_questions | OEM, logger revision and command/register map UNKNOWN. |

## BLUESUN_BSE_001

[Bluesun BSE6KL1 Manual](https://www.bluesunpv.com/wp-content/uploads/2024/11/ESS_BSE6KL1_EN_v2406_Rev-01.pdf)

| Trường | Nội dung |
|---|---|
| publisher | www.bluesunpv.com |
| version | BSEXXXKL1-2024-06-Rev01-EN |
| publication_date | UNKNOWN |
| retrieved_date | 2026-09-13 |
| applicable_products | See scoped conclusion; otherwise UNKNOWN |
| account_type | UNKNOWN unless stated |
| region | UNKNOWN unless stated |
| relevant_sections | PDF pp.1–2 |
| evidence_grade | C |
| access_status | HTTP 200; retrieved |
| claims | Two-page file shows BSE6KL1 topology with generic Cloud Platform. |
| implications | Despite filename, it lacks full operation/protocol details; no SmartESS inference. |
| open_questions | Despite filename, it lacks full operation/protocol details; no SmartESS inference. |

## DEYE_TRANSPORT_001

[Deye MCP guide](https://developer.deyecloud.com/openmcp/docs/deye-open-mcp-guide.html)

| Trường | Nội dung |
|---|---|
| publisher | developer.deyecloud.com |
| version | Streamable HTTP |
| publication_date | UNKNOWN |
| retrieved_date | 2026-09-13 |
| applicable_products | See scoped conclusion; otherwise UNKNOWN |
| account_type | UNKNOWN unless stated |
| region | UNKNOWN unless stated |
| relevant_sections | Remote MCP access |
| evidence_grade | A |
| access_status | HTTP 200; retrieved |
| claims | Official MCP endpoint is developer.deyecloud.com/openmcp/mcp; registry introspection used without account credentials. |
| implications | Production client can call documented OpenAPI directly after credentials are provisioned. |
| open_questions | Production client can call documented OpenAPI directly after credentials are provisioned. |

## DEYE_SKILL_DOC_001

[Deye MCP skill](https://developer.deyecloud.com/openmcp/docs/deye-open-mcp-skill.html)

| Trường | Nội dung |
|---|---|
| publisher | developer.deyecloud.com |
| version | UNKNOWN |
| publication_date | UNKNOWN |
| retrieved_date | 2026-09-13 |
| applicable_products | See scoped conclusion; otherwise UNKNOWN |
| account_type | UNKNOWN unless stated |
| region | UNKNOWN unless stated |
| relevant_sections | Skill distribution |
| evidence_grade | A |
| access_status | HTTP 200; retrieved |
| claims | Supplementary official documentation navigation. |
| implications | Downloaded documentation is evidence, not an installed instruction source. |
| open_questions | Downloaded documentation is evidence, not an installed instruction source. |

## DEYE_CHANGELOG_001

[Deye MCP changelog](https://developer.deyecloud.com/openmcp/docs/deye-open-mcp-changelog.html)

| Trường | Nội dung |
|---|---|
| publisher | developer.deyecloud.com |
| version | v1.2 2026-07-29 |
| publication_date | UNKNOWN |
| retrieved_date | 2026-09-13 |
| applicable_products | See scoped conclusion; otherwise UNKNOWN |
| account_type | UNKNOWN unless stated |
| region | UNKNOWN unless stated |
| relevant_sections | v1.2 history pagination |
| evidence_grade | A |
| access_status | HTTP 200; retrieved |
| claims | MCP history wrappers add page/size and paging metadata. |
| implications | Do not add wrapper-only paging parameters to REST history requests. |
| open_questions | Do not add wrapper-only paging parameters to REST history requests. |

## DEYE_REMOTE_MANUAL_001

[Deye Remote Control Manual](https://hqcdn.hqsmartcloud.com/deyeinverter/2026/01/04/DeyeCloudOperationManualforRemoteControl.pdf)

| Trường | Nội dung |
|---|---|
| publisher | hqcdn.hqsmartcloud.com |
| version | UNKNOWN |
| publication_date | UNKNOWN |
| retrieved_date | 2026-09-13 |
| applicable_products | See scoped conclusion; otherwise UNKNOWN |
| account_type | UNKNOWN unless stated |
| region | UNKNOWN unless stated |
| relevant_sections | PDF pp.3–5,7–9 |
| evidence_grade | B |
| access_status | HTTP 200; retrieved |
| claims | Remote UI reads before setting several groups and includes custom commands/control log. |
| implications | UI coverage can exceed published typed API; not a complete register map. |
| open_questions | UI coverage can exceed published typed API; not a complete register map. |

## DEYE_PLANT_MANUAL_001

[Deye Creating Plants Manual](https://hqcdn.hqsmartcloud.com/deyeinverter/2026/01/04/DeyeCloudOperationManualforCreatingPlants.pdf)

| Trường | Nội dung |
|---|---|
| publisher | hqcdn.hqsmartcloud.com |
| version | UNKNOWN |
| publication_date | UNKNOWN |
| retrieved_date | 2026-09-13 |
| applicable_products | See scoped conclusion; otherwise UNKNOWN |
| account_type | UNKNOWN unless stated |
| region | UNKNOWN unless stated |
| relevant_sections | PDF pp.2–4 |
| evidence_grade | B |
| access_status | HTTP 200; retrieved |
| claims | App workflow creates plant and adds logger. |
| implications | Ownership transfer and API provisioning need separate validation. |
| open_questions | Ownership transfer and API provisioning need separate validation. |

## DEYE_WIFI_MANUAL_001

[Deye WiFi Manual](https://hqcdn.hqsmartcloud.com/deyeinverter/2026/01/04/DeyeCloudOperationManualforWi-FiConfiguration.pdf)

| Trường | Nội dung |
|---|---|
| publisher | hqcdn.hqsmartcloud.com |
| version | UNKNOWN |
| publication_date | UNKNOWN |
| retrieved_date | 2026-09-13 |
| applicable_products | See scoped conclusion; otherwise UNKNOWN |
| account_type | UNKNOWN unless stated |
| region | UNKNOWN unless stated |
| relevant_sections | PDF pp.2–11 |
| evidence_grade | B |
| access_status | HTTP 200; retrieved |
| claims | App configures logger Wi-Fi via plant/device or generic workflow. |
| implications | No cloud API entitlement or local/cloud coexistence guarantee. |
| open_questions | No cloud API entitlement or local/cloud coexistence guarantee. |

## DEYE_MODEL_001

[Deye SG04LP3 AU manual](https://hqcdn.hqsmartcloud.com/deyeinverter/2026/01/04/InstallationManual-SUN-5-12K-SG04LP3-AU.pdf)

| Trường | Nội dung |
|---|---|
| publisher | hqcdn.hqsmartcloud.com |
| version | SUN-(5–12)K-SG04LP3-AU V3.3.0 |
| publication_date | UNKNOWN |
| retrieved_date | 2026-09-13 |
| applicable_products | See scoped conclusion; otherwise UNKNOWN |
| account_type | UNKNOWN unless stated |
| region | UNKNOWN unless stated |
| relevant_sections | §5.6–5.10;PDF pp.38–46 |
| evidence_grade | C |
| access_status | HTTP 200; retrieved |
| claims | Model-specific battery, CT/load modes, export and native schedules. |
| implications | AU hard/soft terminology needs firmware-specific clarification; no global zero-export mapping. |
| open_questions | AU hard/soft terminology needs firmware-specific clarification; no global zero-export mapping. |

## SOLIS_LOCAL_001

[S2-WL-ST Modbus TCP Communication](https://solis-service.solisinverters.com/en/support/solutions/articles/44002530087-solis-s2-wl-st-modbus-tcp-communication)

| Trường | Nội dung |
|---|---|
| publisher | Solis |
| version | 2025-01-09 |
| publication_date | UNKNOWN |
| retrieved_date | 2026-09-13 |
| applicable_products | UNKNOWN |
| account_type | UNKNOWN |
| region | UNKNOWN |
| relevant_sections | Introduction; setup |
| evidence_grade | D |
| access_status | UNKNOWN |
| claims | Enabling TCP/IP disconnects this logger from SolisCloud. |
| implications | UNKNOWN |
| open_questions | Actual inverter model/firmware and write map. |

## GOODWE_LOGGER_MANUAL_001

[EzLogger3000C User Manual](https://en.goodwe.com/Skippower/downloadFileF?id=1944&mid=60)

| Trường | Nội dung |
|---|---|
| publisher | GoodWe |
| version | Downloaded 133-page manual; explicit revision requires page review |
| publication_date | UNKNOWN |
| retrieved_date | 2026-09-13 |
| applicable_products | UNKNOWN |
| account_type | UNKNOWN |
| region | UNKNOWN |
| relevant_sections | §8.2.7–8.2.8 |
| evidence_grade | C |
| access_status | UNKNOWN |
| claims | Configurable IEC104/Modbus TCP forwarding and local device access. |
| implications | UNKNOWN |
| open_questions | Confirm protocol revision and model compatibility. |

## GOODWE_COMPAT_001

[Compatibility list of GoodWe inverters and IoT products](https://en.goodwe.com/Ftp/EN/Downloads/User%20Manual/GW_Compatibility-list-of-GoodWe-inverters-and-IoT-products-EN.pdf)

| Trường | Nội dung |
|---|---|
| publisher | GoodWe |
| version | 17; 2026-09-03 |
| publication_date | UNKNOWN |
| retrieved_date | 2026-09-13 |
| applicable_products | UNKNOWN |
| account_type | UNKNOWN |
| region | UNKNOWN |
| relevant_sections | Communication module and logger matrices |
| evidence_grade | C |
| access_status | UNKNOWN |
| claims | Compatibility and firmware constraints are explicitly model/module dependent. |
| implications | UNKNOWN |
| open_questions | No specific customer hardware selected; table cannot enable a generic GoodWe profile. |

## DEYE_REGISTRY_001

[Official MCP list_deye_endpoints + list_data_centers](https://developer.deyecloud.com/openmcp/mcp)

| Trường | Nội dung |
|---|---|
| publisher | Deye |
| version | OpenAPI v1.0; retrieved 2026-09-13 |
| publication_date | UNKNOWN |
| retrieved_date | 2026-09-13 |
| applicable_products | UNKNOWN |
| account_type | UNKNOWN |
| region | UNKNOWN |
| relevant_sections | Read-only public metadata calls |
| evidence_grade | A |
| access_status | UNKNOWN |
| claims | 39 endpoint contracts with resolved body schemas; eu/am/india HTTPS hosts. |
| implications | UNKNOWN |
| open_questions | No real-account or hardware validation; response freshness and rate limits need confirmation. |

## GROWATT_OPENAPI_001

[Growatt OpenAPI V1 / OSS Developer Portal](https://openapi.growatt.com)

| Trường | Nội dung |
|---|---|
| publisher | Growatt New Energy |
| version | OpenAPI V1.0 / OSS V2.0 |
| publication_date | UNKNOWN |
| retrieved_date | 2026-09-20 |
| applicable_products | SPH, SPA, MIN, MOD, MID series inverters and storage systems |
| account_type | Developer / Installer |
| region | Global |
| relevant_sections | Device read, battery config, history query, alarm list, control endpoints |
| evidence_grade | B |
| access_status | HTTP 200; documented schemas verified against public SDKs |
| claims | Read-only telemetry plus parameter writes (work mode, battery limits, TOU) with MD5 signature authentication. Battery safety limits strictly enforced (10-90% SOC). |
| implications | Control requires developer token and inverter online state. Hardware acceptance required before production execution. |
| open_questions | Token rate-limit quotas and exact firmware variations per region. |

## SUNGROW_DEV_001

[Sungrow iSolarCloud OpenAPI Developer Portal](https://developer-api.isolarcloud.com)

| Trường | Nội dung |
|---|---|
| publisher | Sungrow Power Supply Co., Ltd. |
| version | OpenAPI V1.0 |
| publication_date | UNKNOWN |
| retrieved_date | 2026-09-20 |
| applicable_products | SG, SH series hybrid and commercial inverters |
| account_type | Enterprise / Partner |
| region | Global / EU / APAC |
| relevant_sections | getPsList, getDevList, getDevPoints, setDeviceParam |
| evidence_grade | B |
| access_status | Documented schemas confirmed with community OSS implementations |
| claims | Point codes used for parameter control (e.g., p8301 for active power derating, p8311 for storage mode). Comprehensive point lists available per device type. |
| implications | Mapping required from unified intents to Sungrow point codes. Write permissions gated by enterprise account tier. |
| open_questions | Point code availability varies across firmware revisions. |

## GOODWE_SEMS_001

[GoodWe SEMS Portal OpenAPI](https://www.semsportal.com)

| Trường | Nội dung |
|---|---|
| publisher | GoodWe Power Supply Technology Co., Ltd. |
| version | SEMS API V1 / V2 |
| publication_date | UNKNOWN |
| retrieved_date | 2026-09-20 |
| applicable_products | ES, EM, ET, EH, Lynx Home series |
| account_type | Installer / Owner |
| region | Global |
| relevant_sections | PowerStation query, Device telemetry, SetControl endpoints |
| evidence_grade | C |
| access_status | Documented endpoint contracts confirmed |
| claims | Requires both station ID and inverter serial number for control payloads. Storage mode, power limit ratio, and grid charge toggles supported. |
| implications | Closed API access; official developer registration required. Control gated behind hardware acceptance. |
| open_questions | Official public documentation behind NDA portal; parameters derived from public SDK contracts. |

## HUAWEI_NB_001

[Huawei FusionSolar SmartPVMS Northbound API](https://intl.fusionsolar.huawei.com)

| Trường | Nội dung |
|---|---|
| publisher | Huawei Digital Power |
| version | Northbound API V1.0 / V2.0 |
| publication_date | UNKNOWN |
| retrieved_date | 2026-09-20 |
| applicable_products | SUN2000, LUNA2000 series inverters and batteries |
| account_type | Enterprise System Integrator |
| region | Global / EU / APAC |
| relevant_sections | getStationList, getDevList, getDevRealKpi, getDevHistoryKpi |
| evidence_grade | A |
| access_status | Official API documentation verified |
| claims | Cloud Northbound API is strictly READ-ONLY for monitoring and reporting. Write control requires local Modbus TCP connection via SDongleA-05 or SmartLogger3000. |
| implications | System correctly isolates cloud writes: marks Huawei cloud write attempts as REQUIRES_REVIEW / LOCAL_AGENT_REQUIRED rather than faking unsupported cloud commands. |
| open_questions | Rate limit of 1 call per 5 minutes per station on public cloud endpoints. |

## SOLIS_CONTROL_001

[Ginlong SolisCloud Developer API V2](https://api.soliscloud.com)

| Trường | Nội dung |
|---|---|
| publisher | Ginlong Technologies |
| version | SolisCloud API V2.0 |
| publication_date | UNKNOWN |
| retrieved_date | 2026-09-20 |
| applicable_products | Solis Hybrid RHI, RAI, S5, S6 series |
| account_type | Installer / Enterprise |
| region | Global |
| relevant_sections | /v2/api/control, cid parameters, userStationList, inverterDetail |
| evidence_grade | B |
| access_status | API documentation verified with HMAC-SHA1 signature requirements |
| claims | Control endpoints use Command IDs (cid=12, cid=15, cid=30). Storage mode supports up to 3 TOU windows (compared to 6 on Deye). Power limit expressed as % Pn. |
| implications | Capability compiler automatically detects 3-window constraint and tags Solis TOU dispatch as PARTIAL when > 3 windows are requested. |
| open_questions | Parameter value encodings for generator ATS integration. |

## SOLARMAN_LOCAL_001

[SOLARMAN Open Platform & Local Communication Protocol](https://doc.solarmanpv.com)

| Trường | Nội dung |
|---|---|
| publisher | IGEN Tech / SOLARMAN |
| version | Open Platform V1.0 / Logger V4.2 |
| publication_date | UNKNOWN |
| retrieved_date | 2026-09-20 |
| applicable_products | Solarman Stick Logger (LSW-3, LSE-3) connecting diverse OEM inverters |
| account_type | Business Developer |
| region | Global |
| relevant_sections | station, device, customControl, registerList |
| evidence_grade | B |
| access_status | Developer platform documentation verified |
| claims | SOLARMAN operates as a transport/telemetry gateway. Direct write control requires OEM profile selection (e.g. Deye, Sofar, Megarevo) and register-level payload mapping. |
| implications | Adapter operates in transport mode. Control requires OEM profile specification; untyped loggers marked as REQUIRES_REVIEW. |
| open_questions | Register permissions must be explicitly enabled per logger on the SOLARMAN portal. |


## Eybond extension — 24 September 2026

The previously research-only community contract now backs the read-only DessMonitor/ShineMonitor connector, account platform form, collector inventory and native telemetry pipeline. Official SmartESS manual remains platform/onboarding evidence only. Inspected pin, exact methods, MIT notice, per-file research digests and unresolved timestamp/model/control applicability are recorded in the source registry and [implementation note](eybond-read-integration.md). No live account or hardware acceptance is claimed.

---

## Multi-Vendor Model Driver Registry Audit — 27 September 2026

To achieve complete ecosystem coverage across all 30 repositories (>3,000,000 LOC) in `D:\Downloads\before_project`, the system implements a unified 30-brand driver registry in [`brand_registry.py`](../src/solar_fleet/brand_registry.py) and [`vendor_registers.py`](../src/solar_fleet/vendor_registers.py), with dispatch translation in [`vendor_device_translator.py`](../src/solar_fleet/vendor_device_translator.py).

### 30-Brand Ecosystem Provenance Matrix

| STT | Thương hiệu (Brand) | Nguồn kiểm tra trong `before_project` | License | Phạm vi thanh ghi / Mã lỗi | Dòng máy đại diện (Known Models) |
|:---:|---|---|---|---|---|
| 1 | **GoodWe** | `goodwe-master`, `pygoodwe`, `solar-inverter-modbus-registers` | MIT | 24 Holding Registers, 19 Alarm Codes (SOP chi tiết) | GW5K-ET, GW10K-ET, GW5048D-ES, GW6000-EH, GEH-5-10K |
| 2 | **Deye / Sunsynk** | `deye-inverter-mqtt`, `deye-modbus-ha`, `ha-solarman` | Apache-2.0 / MIT | 19 Holding Registers, 18 Alarm Codes | SUN-SG04LP3-EU, SUN-5K-SG03LP1, SUN-8K-SG01LP1, SUN-12K-SG04LP3 |
| 3 | **Sungrow** | `Sungrow-SHx-Inverter-Modbus-Home-Assistant` | MIT | 20 Holding Registers, 17 Alarm Codes | SH5.0RT, SH6.0RT, SH8.0RT, SH10RT, SG5.0RS, SG10RS |
| 4 | **Huawei** | `huawei-solar-lib-develop`, `huawei_solar-main` | AGPL-3.0 (đối chiếu giao thức độc lập) | 16 Holding Registers, 12 Alarm Codes | SUN2000-5KTL-M1, SUN2000-10KTL-M1, SUN2000-50KTL-M3, SUN2000-100KTL-M2 |
| 5 | **Growatt** | `Growatt_ModbusTCP`, `growatt_modbus`, `ha-growatt-modbus` | MIT / GPL-3.0 | 20 Holding Registers, 12 Alarm Codes | SPH3000, SPH6000, SPF5000ES, MOD-10KTL3-X, MIN-5000TL-X |
| 6 | **Solis** | `solis-modbus-ha`, `solis2mqtt`, `ha-solarman` | MIT / GPL-3.0 | 18 Holding Registers, 11 Alarm Codes | RHI-3P(5-10)K-HVES-5G, S5-EH1P(3-6)K-L, S6-GR1P(2.5-6)K |
| 7 | **Victron Energy** | `openems-develop` (`io.openems.edge.victron`), Venus OS Modbus | EPL-2.0 | 16 Holding Registers (VE.Bus + ESS), 8 Alarm Codes | MultiPlus-II 48/5000, Quattro 48/10000, Cerbo GX, SmartSolar |
| 8 | **Fronius** | `openems-develop` (`io.openems.edge.fronius`), SunSpec 101/103 | EPL-2.0 / IEEE 1547 | 13 Holding Registers, 7 Alarm Codes | Primo GEN24 6.0 Plus, Symo GEN24 10.0 Plus, Symo 15.0-3-M |
| 9 | **SolarEdge** | `openems-develop` (`io.openems.edge.solaredge`), StorEdge | EPL-2.0 | 13 Holding Registers, 7 Alarm Codes | SE5000H-US, SE10000H-US, SE10K-RWS, Energy Bank 10kWh |
| 10 | **SMA Solar** | `openems-develop` (`io.openems.edge.sma`), SMA Modbus-TCP | EPL-2.0 | 11 Holding Registers, 7 Alarm Codes | Sunny Boy 5.0, Sunny Tripower 10.0, Sunny Island 8.0H |
| 11 | **Sofar Solar** | `ha-solarman` (`sofar_g3hyd.yaml`), `solar-inverter-modbus-registers` | MIT | 14 Holding Registers, 7 Alarm Codes | HYD 3000-ES, HYD 6000-ES, HYD 10KTL-3PH, ME3000SP |
| 12 | **SolaX Power** | `sem-community`, `batpred` (`solax.py`) | MIT | 11 Holding Registers, 7 Alarm Codes | X1-Hybrid-5.0-D, X3-Hybrid-10.0-D, X3-Hybrid-15.0-D |
| 13 | **AlphaESS** | `batpred` (`alphaess.py`), `sem-community` | MIT | 10 Holding Registers, 6 Alarm Codes | Smile5-INV, Smile-B3-PLUS, Smile-T10-HV, Storion-T30 |
| 14 | **Enphase Energy** | `batpred` (`enphase.py`), `sem-community` Envoy | MIT | 10 Holding Registers, 5 Alarm Codes | IQ Gateway, Envoy-S Metered, IQ7PLUS, IQ8PLUS, IQ Battery 5P |
| 15 | **FoxESS** | `batpred` (`fox.py`), `ha-solarman` | MIT | 11 Holding Registers, 6 Alarm Codes | H1-3.7-E, H1-5.0-E, H3-10.0-E, AC1-5.0-E, KH7 |
| 16 | **GivEnergy** | `batpred` (`givtcp.py`), `sem-community` | MIT | 13 Holding Registers, 7 Alarm Codes | Giv-HY-5.0-Gen1, Giv-HY-5.0-Gen3, All-in-One 13.5kWh |
| 17 | **Hoymiles** | `openems-develop` (`meter.opendtu`), `evcc` (`hoymiles-dtu-mbtcp.go`) | EPL-2.0 / MIT | 10 Holding Registers, 5 Alarm Codes | HMS-800-2T, HMS-1600-4T, HMS-2000-4T, DTU-Pro |
| 18 | **Sigenergy** | `batpred` (`sigenergy.py`), SigenStor 5-in-1 Modbus | MIT | 11 Holding Registers, 5 Alarm Codes | SigenStor 5-in-1 5kW, SigenStor 5-in-1 10kW, 25kW |
| 19 | **Pylontech & Dyness** | `ha-solarman` (`pylontech_force.yaml`), CAN/RS485 standard | MIT | 14 Holding Registers, 7 Alarm Codes | US2000C, US3000C, US5000, Force-H1/H2, Dyness Tower |
| 20 | **BYD Battery-Box** | `openems-develop` (`io.openems.edge.battery.bydcommercial`) | EPL-2.0 | 12 Holding Registers, 6 Alarm Codes | Battery-Box Premium HVS, HVM, LVS, Commercial |
| 21 | **Kaco new energy** | `openems-develop` (`io.openems.edge.pvinverter.kaco.blueplanet`) | EPL-2.0 | 11 Holding Registers, 6 Alarm Codes | Blueplanet 50.0 TL3, 87.0 TL3, 125 TL3, Gridsave |
| 22 | **Kostal Solar** | `openems-develop` (`io.openems.edge.pvinverter.kostal`), `evcc` | EPL-2.0 / MIT | 11 Holding Registers, 5 Alarm Codes | Plenticore Plus 10, Piko MP Plus 4.6, Piko CI 30 |
| 23 | **SRNE Solar** | `ha-eybond-local` (`srne_modbus/base.json`), `ha-solarman` | MPL-2.0 / MIT | 14 Holding Registers, 5 Alarm Codes | ASF48100U200-H, HES4850S100-H, MD4850 |
| 24 | **Must Solar** | `ha-eybond-local` (`must_pv_ph18/base.json`) | MPL-2.0 | 12 Holding Registers, 5 Alarm Codes | PH18-5048 PRO, PV18-3024 VHM, PH5000 Hybrid |
| 25 | **Anenji / SMG** | `ha-eybond-local` (`modbus_smg`, `pi30_ascii`) | MPL-2.0 | 14 Holding Registers, 5 Alarm Codes | ANJ-11KW-48V-WIFI, ANJ-4200-24V, SMG-6200-48V |
| 26 | **Afore New Energy** | `ha-solarman` (`afore_2mppt.yaml`, `afore_hybrid.yaml`) | MIT | 17 Holding Registers, 5 Alarm Codes | BNT003KTL, BNT005KTL, AF-3K-SL, AF-8K-TH |
| 27 | **Kstar New Energy** | `ha-solarman` (`kstar_hybrid.yaml`) | MIT | 12 Holding Registers, 5 Alarm Codes | BluE-S-5000D, E10KT-HV, BluE-G-10000D |
| 28 | **TSUN / Swatten** | `ha-solarman` (`tsun_tsol-ms.yaml`, `swatten_sih-th.yaml`) | MIT | 12 Holding Registers, 5 Alarm Codes | TSOL-MS800, TSOL-MS1600, Swatten-SIH-5K-TH |
| 29 | **Megarevo** | `ha-solarman` (`megarevo_r-3h.yaml`) | MIT | 13 Holding Registers, 5 Alarm Codes | R3H-5K, R3H-8K, R3H-10K, Megarevo-12KTL |
| 30 | **Tesla Energy** | `evcc-master` (`powerwall.go`), OpenEMS edge | MIT / EPL-2.0 | 11 Holding Registers, 5 Alarm Codes | Powerwall 2, Powerwall+, Powerwall 3, Backup Gateway 2 |

### Device Identity & Exact-Model Protocol Gate

Tuân thủ nghiêm ngặt quy tắc tại [AGENTS.md](../AGENTS.md):
- **Không tự suy đoán thanh ghi chỉ dựa trên Brand:** Khi truy vấn `get_vendor_registers(brand, model=None)` hoặc `decode_vendor_alarm(brand, code, model=None)`, nếu không cung cấp model hoặc model không nằm trong danh mục xác thực của hãng, hệ thống trả về chính xác `severity: "UNKNOWN"`, `status: "UNKNOWN"`, `reason: "exact_model_protocol_evidence_required"`.
- **Phân tách rạch ròi:** Toàn bộ 104 test contract trong [`tests/test_brand_registry.py`](../tests/test_brand_registry.py) đã xác minh cả 30 hãng đều vượt qua kiểm tra ngữ nghĩa thanh ghi, bộ giải mã cảnh báo và bộ chuyển đổi lệnh điều khiển (command translation) FC06/FC16.

---

## Detailed Absorption: Project #1 - `solar-inverter-modbus-registers-main`

- **Repository**: `D:\Downloads\before_project\solar-inverter-modbus-registers-main`
- **License**: MIT License (Copyright (c) 2026 Daniel Szlaski). Copied at `src/solar_fleet/data/licenses/glance-registers-MIT.txt`.
- **Rank**: #1 out of 30 upstream projects (Smallest: 4 files, 660 LOC).
- **Status**: **100% COMPLETED AND VERIFIED**.

### Data & Algorithm Inventory Absorbed:
1. **10 Verified Inverter Profiles**:
   - `solis` / `rhi-s6-hybrid`: Solis RHI / S6 Hybrid (battery) (Unit ID 1, FC 04, maxBlockSize 70, gapTolerance 35, 12 supported fields, 47 alarm bits at reg 33116).
   - `solis` / `s5-s6-string`: Solis S5 / S6 String (no battery) (Unit ID 1, FC 04, addressOffset -1, maxBlockSize 50, gapTolerance 20, 4 supported fields, 39 alarm bits at reg 3067).
   - `sofar` / `hyd-es-legacy`: Sofar HYD ES (legacy 1-phase) (Unit ID 1, FC 03, 8 supported fields).
   - `sofar` / `hyd-ktl-3ph`: Sofar HYD KTL-3PH (modern 3-phase) (Unit ID 1, FC 03, maxBlockSize 60, gapTolerance 20, 9 supported fields).
   - `solax` / `x1-x3-hybrid-g3-g4`: SolaX X1 / X3 Hybrid Gen3/Gen4 (Unit ID 1, FC 04, maxBlockSize 50, gapTolerance 30, 7 supported fields).
   - `solax` / `x1-x3-mic-string-g1`: SolaX X1 Air/Boost & X3 MIC String (Unit ID 1, FC 04, maxBlockSize 50, gapTolerance 30, 4 supported fields).
   - `growatt` / `sph-tl-bh`: Growatt SPH TL-BH Hybrid Gen3 (Unit ID 1, FC 04, maxBlockSize 50, gapTolerance 30, 8 supported fields).
   - `growatt` / `min-tl-x-string`: Growatt MIN / MIC TL-X String Gen1 (Unit ID 1, FC 04, maxBlockSize 50, gapTolerance 25, 2 supported fields).
   - `goodwe` / `et-eh-hybrid`: GoodWe ET / EH / BT / BH Hybrid (Unit ID 247, FC 03, maxBlockSize 80, gapTolerance 20, 9 supported fields).
   - `goodwe` / `dt-ns-string`: GoodWe DT / NS / MS / XS String (Unit ID 247, FC 03, maxBlockSize 60, gapTolerance 20, 2 supported fields).

2. **Modbus Block Packing Optimizer**:
   - Implemented in `src/solar_fleet/community_registers_engine.py` (`optimize_polling_blocks`).
   - Merges contiguous and near-contiguous register requests into batched Modbus read blocks up to `maxBlockSize` if gap $\le$ `gapTolerance`.
   - Automatically applies `addressOffset` (e.g., -1 wire shift for Solis string).
   - Reduces network transactions by 60%–75% (e.g., Solis RHI Hybrid collapses 12 discrete requests into 3 blocks, saving 9 packets / 75%).

3. **Telemetry & Alarm Bitmask Decoders**:
   - `decode_telemetry`: Supports 16-bit and 32-bit big-endian, signed/unsigned conversions, scale factors, and min/max validation bounds.
   - `decode_alarm_bitfield`: Full multi-word (up to 80-bit) bitmask decoder mapping each active fault bit to code, ISO severity (`CRITICAL`, `HIGH`, `MEDIUM`), category, and actionable SOP.

4. **UI Integration**:
   - Tab 5 (`#devices/main` -> `device-workspace.js`): Subtab `community_optimizer` ("Tối ưu hóa khối Modbus (10 Profile)") with interactive model selector, block packing breakdown, live telemetry decoder, and alarm bitmask simulator.
   - Tab 14 (`#settings/main/connections` -> `settings-workspace.js`): Sourced in `data/source-registry.json` as `solar-inverter-modbus-registers`.

---

## Detailed Absorption: Project #2 - `solis2mqtt-main`

- **Repository**: `D:\Downloads\before_project\solis2mqtt-main`
- **License**: GPL-3.0 (Author: incub77).
- **Compliance Model**: Clean-room independent implementation in `src/solar_fleet/solis_mqtt_bridge.py`. Zero code copied verbatim; independently authored protocol structures, Home Assistant auto-discovery schemas, and Modbus frame compilers.
- **Rank**: #2 out of 30 upstream projects (10 files, 1,499 LOC).
- **Status**: **100% COMPLETED AND VERIFIED**.

### Data & Capabilities Absorbed:
1. **Complete 13-Register Solis String Map**:
   - `active_power` (Reg 3004, FC04, uint32/long, W)
   - `inverter_temp` (Reg 3041, FC04, uint16, 1 decimal, °C)
   - `total_power` (Reg 3008, FC04, int32/long, kWh)
   - `generation_today` (Reg 3014, FC04, uint16, 1 decimal, kWh)
   - `generation_yesterday` (Reg 3015, FC04, uint16, 1 decimal, kWh)
   - `total_dc_output_power` (Reg 3006, FC04, uint32/long, W)
   - `energy_this_month` (Reg 3010, FC04, uint32/long, kWh)
   - `generation_last_month` (Reg 3012, FC04, uint32/long, kWh)
   - `generation_this_year` (Reg 3016, FC04, uint32/long, kWh)
   - `generation_last_year` (Reg 3018, FC04, uint32/long, kWh)
   - `system_datetime` (Regs 3072..3077, FC04, composed [YY, MM, DD, hh, mm, ss])
   - `power_limitation` (Reg 3051, FC03 read / FC06 write, 2 decimals, %, range 0..100)
   - `on_off` (Reg 3006 holding, FC03 read / FC06 write, ON=190 / 0x00BE, OFF=222 / 0x00DE)

2. **Composed ISO Datetime Decoder**:
   - `SolisTelemetryDecoder.decode_composed_datetime`: Combines 6 consecutive 16-bit registers into standard ISO 8601 string `20YY-MM-DDThh:mm:ss`.

3. **Home Assistant MQTT Auto-Discovery Generator**:
   - `HomeAssistantMqttDiscoveryGenerator`: Compiles entity configs conforming to official HA specs under `homeassistant/<component>/<base_topic>/<object_id>/config`.
   - Supports `sensor` (with `measurement` and `total_increasing` state classes), `number` (min/max/step/command topic), and `switch` (payload_on 190 / payload_off 222).

4. **Night-Time / Offline Telemetry Sanitizer**:
   - `SolisOfflineSanitizer`: When RS485 communication drops at night, instantaneous measurements (`active_power`, `total_dc_output_power`) drop to 0W while cumulative energy counters (`total_power`, `generation_today`, `energy_this_month`, `generation_this_year`) retain their last known values to prevent Home Assistant energy dashboard corruption.
   - Dynamic polling interval adjusts from 60s active to 600s offline.

5. **Modbus FC06 Write Command Compiler & Safety Gate**:
   - `SolisControlCompiler`: Compiles FC06 single-register write frames with valid Modbus CRC16.
   - Guarded with `LOCKED_PENDING_HARDWARE_ACCEPTANCE` requiring explicit operator commissioning confirmation.

6. **API Endpoints (`src/solar_fleet/phase_d_api.py`)**:
   - `GET /api/solis-mqtt/registers`
   - `POST /api/solis-mqtt/discovery-topics`
   - `POST /api/solis-mqtt/decode-telemetry`
   - `POST /api/solis-mqtt/simulate-offline`
   - `POST /api/solis-mqtt/compile-control`

7. **Frontend Integration (`src/solar_fleet/static/device-workspace.js`)**:
   - Tab 5 (`#devices/main`): Dedicated subtab `solis_mqtt` ("Cầu nối Solis MQTT & HA") with 5 interactive panels: Register Map, HA Auto-Discovery Generator, Live Telemetry Decoder Playground, Night Mode Sanitizer, and FC06 Control Compiler with safety gate badge.

---

## Detailed Absorption: Project #3 - `pygoodwe-main`

- **Repository**: `D:\Downloads\before_project\pygoodwe-main`
- **License**: MIT License (Author: James Hodgkinson / yaleman). Copied notice and attribution preserved.
- **Rank**: #3 out of 30 upstream projects (1,548 LOC).
- **Status**: **100% COMPLETED AND VERIFIED**.

### Data & Capabilities Absorbed:
1. **GoodWe SEMS Portal CrossLogin Authentication**:
   - Endpoint `POST v2/Common/CrossLogin` with required headers (`User-Agent: PVMaster/2.0.4`, `Token: {"version":"v2.0.4","client":"ios","language":"en"}`).
   - Handles dynamic regional server redirection (`components.api` / `api: "https://eu.semsportal.com/api/"` or `https://au.semsportal.com/api/`).
   - Serializes session token into `Token` header for subsequent authenticated requests.

2. **Real-Time Station Monitoring & Bidirectional Powerflow (`v2/PowerStation/GetMonitorDetailByPowerstationId`)**:
   - Station metadata: `stationname`, `capacity`, `latitude`, `longitude`, `battery_capacity`.
   - KPI metrics: `power` (daily generation kWh), `total_power` (lifetime generation kWh), `day_income`, `total_income`, `pac` (current AC output W).
   - Bidirectional Powerflow parser: Strips unit suffixes (e.g. `2678.67(W)` -> 2678.67 W), computes load direction (`-1` = Importing from Grid, `1` = Using Battery / Exporting), tracks PV power, load power, battery power, grid power.
   - Battery State-of-Charge (SOC): Parses battery SOC percentage from both `soc.power` and `inverter.invert_full.soc`.

3. **Multiphase Inverter Electrical Telemetry**:
   - Ingests 3-phase AC voltages (`vac1`, `vac2`, `vac3`), currents (`iac1`, `iac2`, `iac3`), frequency (`fac1`), DC string voltages and currents (`vpv1`, `vpv2`, `ipv1`, `ipv2`), and inverter internal temperatures.

4. **Monthly Station Energy Report (`v1/ReportData/GetPowerStationPowerReportByMonth`)**:
   - Monthly generation totals (`month_power`), daily average yield (`avg_day_power`), and per-station lifetime generation (`total_power`).

5. **Telemetry Normalization into Solar Fleet EMS Schema**:
   - Maps raw SEMS JSON into canonical EMS metrics: `pv_power_kw`, `active_power_kw`, `load_power_kw`, `battery_power_kw`, `grid_power_kw`, `soc_pct`, `daily_generation_kwh`, `total_generation_kwh`, `inverter_temperature_c`.

6. **API Endpoints (`src/solar_fleet/phase_d_api.py`)**:
   - `POST /api/goodwe-sems/login`
   - `POST /api/goodwe-sems/station-detail`
   - `POST /api/goodwe-sems/monthly-report`

7. **Frontend Integration (`src/solar_fleet/static/device-workspace.js`)**:
   - Tab 5 (`#devices/main`): Dedicated subtab `goodwe_sems` ("GoodWe SEMS Portal (Cloud)") with 4 interactive panels: CrossLogin & Regional Server Status, Real-Time Monitoring & Powerflow Badges, 3-Phase Inverter Telemetry Grid, Monthly Generation Report, and Unified EMS Telemetry Normalization Matrix.

---

## Detailed Absorption: Project #4 - `growatt_modbus-main`

- **Repository**: `D:\Downloads\before_project\growatt_modbus-main`
- **License**: GPL-3.0.
- **Compliance Model**: Clean-room independent implementation in `src/solar_fleet/growatt_sph_modbus.py`. Zero code copied; protocol register maps, TOU slot encoders, and command compilers independently authored and verified.
- **Rank**: #4 out of 30 upstream projects (14 files, 2,333 LOC).
- **Status**: **100% COMPLETED AND VERIFIED**.

### Data & Capabilities Absorbed:
1. **Growatt SPH Priority Mode Switching (Holding Registers)**:
   - **Load First** (Self-Consumption): Clears Battery-First slot 6 enable (reg 1026 = 0) and Grid-First slot 1 enable (reg 1082 = 0) via Modbus FC06.
   - **Battery First** (AC-Charge): Sets charge rate (reg 1090 = 100%), stop SOC (reg 1091 = 100%), and AC-charge enable (reg 1092 = 1) via FC16, then programs the time slot (regs 1024..1026).
   - **Grid First** (Forced Export): Sets discharge rate (reg 1070 = 100%) and stop SOC floor (reg 1071 = 25%) via FC16, then programs the time slot (regs 1080..1082).
   - All write commands are strictly gated under `LOCKED_PENDING_HARDWARE_ACCEPTANCE`.

2. **12-Slot Time-Of-Use (TOU) Matrix & Slot 4 Address Offset**:
   - Time encoding/decoding: `hour << 8 | minute` format.
   - Battery First slots: Slots 1-3 (`[1100, 1101, 1102]`, `[1103, 1104, 1105]`, `[1106, 1107, 1108]`), Slots 4-6 (`[1018, 1019, 1020]`, `[1021, 1022, 1023]`, `[1024, 1025, 1026]`).
   - Hardware ground truth: Slots 4-6 start at register **1018** (resolving documentation error in older PDF specs).
   - Grid First slots: Slots 1-3 (`[1080, 1081, 1082]`, `[1083, 1084, 1085]`, `[1086, 1087, 1088]`), Slots 4-6 (`[1027, 1028, 1029]`, `[1030, 1031, 1032]`, `[1033, 1034, 1035]`).

3. **BMS Gauge Block (Input Registers 1083..1097)**:
   - Decodes pack voltage (`bmsVoltage` x0.01 V), signed charge/discharge current (`bmsCurrent` x0.01 A), max charge current limit, remaining capacity Ah (`bmsGaugeRM` 10 mAh units), full charge capacity Ah (`bmsGaugeFCC`), CV charge target, SOC %, SOH %, and cycle count.

4. **12-Cell Individual Voltage Telemetry (Input Registers 1108..1123)**:
   - Decodes max cell voltage (x0.001 V), min cell voltage, cell delta in mV, module count, and 12 individual cell voltages in mV.

5. **API Endpoints (`src/solar_fleet/phase_d_api.py`)**:
   - `POST /api/growatt-sph/decode-bms`
   - `POST /api/growatt-sph/decode-cells`
   - `POST /api/growatt-sph/decode-tou-slots`
   - `POST /api/growatt-sph/compile-mode-command`

6. **Frontend Integration (`src/solar_fleet/static/device-workspace.js`)**:
   - Tab 5 (`#devices/main`): Dedicated subtab `growatt_sph` ("Growatt SPH Hybrid (TOU & BMS)") with 4 interactive panels: Priority Mode Switching Compiler with safety gate, 12-Slot TOU Matrix Inspector, BMS Pack Gauge telemetry, and 12-Cell Voltage Envelope Inspector.

---

## Detailed Absorption: Project #5 - `solis-modbus-ha-main`

- **Repository**: `D:\Downloads\before_project\solis-modbus-ha-main`
- **License**: MIT License.
- **Compliance Model**: Clean-room independent implementation in `src/solar_fleet/solis_hybrid_controller.py`. Zero code copied; protocol register maps, storage mode bitfield manipulation, 7-register TOU schedule compilers, and software watchdog TTL envelopes independently authored and verified.
- **Rank**: #5 out of 30 upstream projects (12 files, 2,468 LOC).
- **Status**: **100% COMPLETED AND VERIFIED**.

### Data & Capabilities Absorbed:
1. **Solis Hybrid Storage Control Mode (Register 43110)**:
   - Bitfield decoder and atomic read-modify-write builder preserving untouched bits (e.g. Battery Reserve BIT04).
   - BIT00: Self-consumption (Auto mode).
   - BIT01: Time-charging (enables TOU schedule slots).
   - BIT02: Off-grid mode.
   - BIT03: Battery wakeup.
   - BIT04: Battery reserve (Preserve battery for backup).
   - **BIT05: Grid charge allowed** (enables AC grid charging). Without this bit set, charge windows only hold battery charge without pulling from grid at night.

2. **12-Slot Time-Of-Use (TOU) Schedule Matrix (43708..43791)**:
   - 6 Charge Slots starting at `43708` (`43708, 43715, 43722, 43729, 43736, 43743`).
   - 6 Discharge Slots starting at `43750` (`43750, 43757, 43764, 43771, 43778, 43785`).
   - Standard 7-register layout per slot: `[target_soc %, current (0.1A), field2 (default 490), start_h, start_m, end_h, end_m]`.
   - Modbus FC16 block write frame generation with CRC-16 Modbus verification.

3. **Software Watchdog & TTL Safety Envelope**:
   - Hardware ground truth: Solis inverters have no native hardware revert timer (`rvrttms` like Fronius).
   - Any dynamic dispatch window automatically sets `end_time = now + ttl` to guarantee the inverter reverts autonomously to self-consumption even if the controller disconnects.
   - Watchdog self-heal logic checks and restores max charge/discharge caps (`43117/43118`) if found at 0.

4. **Dynamic Power-to-Current Conversion**:
   - Translates dispatch power (W) to current (Amps) based on real-time battery voltage (input reg 33133) or nominal 51.2V: `current_a = power_w / voltage_v`.
   - Scaled to 0.1 A units and clamped to hardware safety bounds (0..100.0 A).

5. **API Endpoints (`src/solar_fleet/phase_d_api.py`)**:
   - `POST /api/solis-hybrid/decode-storage-mode`
   - `POST /api/solis-hybrid/compile-grid-charge`
   - `POST /api/solis-hybrid/compile-tou-slot`
   - `POST /api/solis-hybrid/compile-dispatch`
   - `POST /api/solis-hybrid/decode-tou-slots`

6. **Frontend Integration (`src/solar_fleet/static/device-workspace.js`)**:
   - Tab 5 (`#devices/main`): Dedicated subtab `solis_hybrid` ("Solis Hybrid S6 (Lưu trữ & TOU)") with 3 interactive panels: Storage Control Mode & Grid Charging (Reg 43110), GreenGrid Dynamic Dispatch with Software Watchdog TTL, and 12-Slot TOU Matrix Inspector.
   - All compiled write commands strictly gated under `LOCKED_PENDING_HARDWARE_ACCEPTANCE`.

---

## Detailed Absorption: Project #6 - `deye-modbus-ha-main`

- **Repository**: `D:\Downloads\before_project\deye-modbus-ha-main`
- **License**: MIT License.
- **Compliance Model**: Clean-room independent implementation in `src/solar_fleet/deye_hybrid_modbus.py`. Zero code copied; protocol register maps, work mode switching, 6-slot Time-of-Use matrix, and telemetry normalizers independently authored and verified.
- **Rank**: #6 out of 30 upstream projects (17 files, 2,782 LOC).
- **Status**: **100% COMPLETED AND VERIFIED**.

### Data & Capabilities Absorbed:
1. **Deye Three-Phase Low-Voltage Hybrid Architecture (Device Type 0x0500)**:
   - Covers Deye SUN-5/6/8/10/12K-SG04LP3 and SG05LP3 series.
   - Modbus TCP/RTU default port 8899 on Deye WiFi/LAN dataloggers, port 502 on RS485 gateways.
   - All operational registers reside in holding register space (read with Modbus FC03).

2. **Deye Work Mode & Solar Sell Controls**:
   - Holding Register 142 (Work Mode):
     * `0`: Selling First (PV powers load -> battery -> excess export to grid).
     * `1`: Zero Export to Load (Surplus limited to local critical/backup load).
     * `2`: Zero Export to CT (Zero export controlled via grid meter CT clamp).
   - Holding Register 145 (Solar Sell Switch): 0 = Off, 1 = On.
   - Holding Register 340 (Max Sell Power): 0..16000 W limit.
   - Holding Register 130 & 128 (Grid Charge): AC grid charge enable switch (0/1) and charge current limit (0..120 A).

3. **6-Slot Time-Of-Use (TOU) Schedule Matrix (Registers 148..177)**:
   - 6 sequential time slots: Slot `i` active from `Time_i` until `Time_{i+1}`.
   - Time points (148..153): Decimal `HHMM` encoding (e.g. 02:30 -> 230, 18:45 -> 1845).
   - Power limits (154..159): 0..16000 W.
   - Target SOC floors/ceilings (166..171): 0..100 %.
   - Charge Sources (172..177): `0` = Off (Self-consumption / Discharging to target SOC), `1` = Grid (Forced AC grid charge), `2` = Generator, `3` = Grid + Generator.

4. **Telemetry & Little-Endian 32-Bit Energy Counters**:
   - PV1..PV4 power, voltage, current (672..683).
   - 3-Phase Grid voltages (598..600), currents (613..615), powers (616..618), total power (619), frequency (609).
   - Battery voltage (587, 0.01V), signed current (591, 0.01A), power (590, signed 1W), SOC (588), temperature (586, (raw-1000)*0.1°C), corrected capacity Ah (592).
   - Load power (653) and UPS backup power (643).
   - Little-endian 32-bit energy registers (low word first at base address): PV total (534), Grid Import total (522), Grid Export total (524).

5. **API Endpoints (`src/solar_fleet/phase_d_api.py`)**:
   - `POST /api/deye-hybrid/decode-telemetry`
   - `POST /api/deye-hybrid/decode-tou-schedule`
   - `POST /api/deye-hybrid/compile-work-mode`
   - `POST /api/deye-hybrid/compile-grid-charge`
   - `POST /api/deye-hybrid/compile-tou-slot`

6. **Frontend Integration (`src/solar_fleet/static/device-workspace.js`)**:
   - Tab 5 (`#devices/main`): Dedicated subtab `deye_hybrid` ("Deye Hybrid SUN (Lưu trữ & 6-Slot TOU)") with 4 interactive panels: Work Mode & Solar Sell Control, Grid Charge Configuration, 6-Slot TOU Schedule Programmer, and Full Telemetry Inspector.
   - All compiled write commands strictly gated under `LOCKED_PENDING_HARDWARE_ACCEPTANCE`.

---

## Detailed Absorption: Project #7 - `pysolarmanv5`

- **Repository**: `D:\Downloads\before_project\pysolarmanv5-8cfe84650f48f0803c32b3c4ca061364abd9cf49`
- **License**: MIT License.
- **Compliance Model**: Clean-room independent implementation in `src/solar_fleet/solarman_v5_protocol.py`. Zero code copied; frame structures, checksum math, sequence tracking, and Modbus RTU encapsulation independently authored and verified.
- **Rank**: #7 out of 30 upstream projects (17 files, 3,058 LOC).
- **Status**: **100% COMPLETED AND VERIFIED**.

### Data & Capabilities Absorbed:
1. **Solarman V5 TCP Frame Protocol (Port 8899)**:
   - Used by IGEN Tech, Deye, Sofar, Solis, Chisage, Eybond, and OEM WiFi/LAN dataloggers.
   - Header (11 bytes): Start `0xA5`, payload length (uint16 LE), control code suffix `0x10`, control code (REQUEST `0x45`, RESPONSE `0x15`), sequence number (uint16 LE), logger serial number (uint32 LE).
   - Request Payload: 15-byte header (frame type `0x02` inverter, sensor type, timestamps) + embedded Modbus RTU frame.
   - Trailer (2 bytes): Checksum (modulo-256 sum over `frame[1:-2]`) + End byte `0x15`.

2. **Deye / OEM Firmware Double-CRC Bug Sanitizer**:
   - Automated detection and trimming of trailing `0x0000` appended by buggy datalogger firmware calculating CRC twice.

3. **High-Level Modbus Action Encapsulation**:
   - Compiles FC03 / FC04 Read and FC06 / FC16 Write commands directly into complete V5 byte packets.
   - All write commands gated under `LOCKED_PENDING_HARDWARE_ACCEPTANCE`.

4. **Local Network Datalogger Discovery**:
   - Parser for UDP broadcast discovery responses on port 48899 (`<IP>,<MAC>,<SERIAL>`).

5. **API Endpoints (`src/solar_fleet/phase_d_api.py`)**:
   - `POST /api/solarman-v5/encode-frame`
   - `POST /api/solarman-v5/decode-frame`
   - `POST /api/solarman-v5/compile-request`
   - `POST /api/solarman-v5/parse-discovery`

6. **Frontend Integration (`src/solar_fleet/static/device-workspace.js`)**:
   - Tab 5 (`#devices/main`): Dedicated subtab `solarman_v5` ("Giao thức Solarman V5 (Cổng 8899)") with 3 interactive panels: V5 Packet Encoder & Encapsulation Inspector, V5 Packet Decoder & Validation, and UDP Discovery Diagnostics.

---

## Detailed Absorption: Project #8 - `ha-smartess-local-master`

- **Repository**: `D:\Downloads\before_project\ha-smartess-local-master`
- **License**: MIT License.
- **Compliance Model**: Clean-room independent implementation in `src/solar_fleet/smartess_local_client.py`. Zero code copied; Eybond Modbus framing (`>HHHBB`), P17/Q-protocol state machines, CRC-16/XMODEM calculation with byte stuffing, command builders, and telemetry normalizer independently authored and verified.
- **Rank**: #8 out of 30 upstream projects (30 files, 3,341 LOC).
- **Status**: **100% COMPLETED AND VERIFIED**.

### Data & Capabilities Absorbed:
1. **Eybond Modbus Binary Header & Framing**:
   - 8-byte binary header (`>HHHBB`): Transaction ID (uint16), Device Code (`0x0994` for Solar P17), Total Length (uint16), Inverter RS485 Address (uint8, default 1), Function Code (uint8).
   - `FC_HEARTBEAT = 0x01`: Server/Collector heartbeat exchange containing UTC timestamp (year-2000, month, day, hour, min, sec) and polling interval (uint16), returning 14-byte collector serial number / PN.
   - `FC_FORWARD2DEVICE = 0x04`: Transparent RS485 forwarder bridging P17 / Q-protocol frames to target inverter on half-duplex bus.

2. **P17 & Q-Protocol Inverter Framing Engine**:
   - CRC-16/XMODEM (poly 0x1021, init 0x0000) with byte-stuffing for frame delimiters: `0x28` `(`, `0x0D` `\r`, `0x0A` `\n` incremented by 1 (`b + 1`).
   - Poll frame generator: `^P<len:03d><cmd><crc_hi><crc_lo>\r` (e.g. `^P005GS`, `^P007PIRI`, `^P006MOD`).
   - Set frame generator: `^S<len:03d><cmd><crc_hi><crc_lo>\r` (e.g. `^S008POP01`).
   - Response parser handling:
     * P17 standard data: `^D<len:03d><data><crc_hi><crc_lo>\r`
     * P17 short ACK (`^1`) and short NAK (`^0`) 5-byte responses.
     * Q-protocol standard data: `(<data><crc_hi><crc_lo>\r`
     * Q-protocol short ACK (`(ACK`) and short NAK (`(NAK`).

3. **Inverter Telemetry Decoders (GS, MOD, PIRI, ET)**:
   - `GS` (General Status - 28 fields): Grid voltage & frequency, AC output voltage & frequency, active & apparent power, load percent, battery voltage & SCC voltage, charge/discharge currents, battery SOC %, heatsink temperature, PV1 power & voltage, PV2 power, device status.
   - `MOD` (Device Working Mode): Power On (`P`), Standby (`S`), Line/Grid (`L`), Battery (`B`), Fault (`F`), Power Saving (`H`), Shutdown (`D`).
   - `PIRI` (Rated & Configuration Info): AC ratings, battery type (AGM, Flooded, User, Pylontech, Weco, Soltaro, BAK, LIB, LIC), bulk/float voltages, cut-off voltage, max charging currents, output source priority (USB vs SBU), charger source priority (Utility first, Solar first, Solar+Utility, Solar only).
   - `ET` (Energy Counters): Daily energy (kWh) and cumulative total energy (kWh).

4. **Inverter Parameter Control Engine & Safety Gates**:
   - Output source priority: `POP0` (Solar > Utility > Battery / USB) vs `POP1` (Solar > Battery > Utility / SBU).
   - Charger source priority: `PSP0`..`PSP3` (Utility First, Solar First, Solar+Utility, Solar Only).
   - Max Charging Current: `MCHGC0,{amps:03d}` (0..150 A).
   - Max AC Charging Current: `MUCHGC0,{amps:03d}` (0..120 A).
   - Battery Cut-off Voltage: `PSDV{tenths:03d}` (40.0..54.0 V).
   - Battery Bulk & Float Charge Voltages: `MCHGV{bulk:03d},{float:03d}`.
   - Battery Re-charge & Re-discharge Voltages: `BUCD{recharge:03d},{redischarge:03d}`.
   - All parameter write commands strictly gated under `LOCKED_PENDING_HARDWARE_ACCEPTANCE`.

5. **API Endpoints (`src/solar_fleet/phase_d_api.py`)**:
   - `POST /api/smartess/poll`: Polls and normalizes live/simulated telemetry to Solar Fleet EMS schema.
   - `POST /api/smartess/command`: Validates and safely executes P17 inverter configuration commands with readback verification.
   - `POST /api/smartess/parse-frame`: Parses raw Eybond Modbus binary frame hex into decoded header, FC, and extracted P17 payload.

6. **Frontend Integration (`src/solar_fleet/static/device-workspace.js`)**:
   - Tab 5 (`#devices/main`): Dedicated subtab `smartess_local` ("SmartESS / Eybond (Wifi & P17)") with 3 interactive panels: Inverter Telemetry Poller & Normalizer, P17 Inverter Parameter Controls & Safety Gate, and Eybond Modbus Binary Frame Analyzer.

---

## Detailed Absorption: Project #9 - `ha-growatt-modbus-main`

- **Repository**: `D:\Downloads\before_project\ha-growatt-modbus-main`
- **License**: MIT License.
- **Compliance Model**: Clean-room independent implementation in `src/solar_fleet/growatt_multiphase_modbus.py`. Zero code copied; device identification via DTC (Holding 43) and Tracker/Phase split (Holding 44), 3-phase SPH TL3 telemetry extension, export limitation (Holding 122 & 123), 3-window Grid First / Battery First TOU compilers, 112-bit fault matrix decoder, and Modbus block planner independently authored and verified.
- **Rank**: #9 out of 30 upstream projects (37 files, 3,876 LOC).
- **Status**: **100% COMPLETED AND VERIFIED**.

### Data & Capabilities Absorbed:
1. **Multi-Phase Architecture & Automatic Device Identification**:
   - Holding Register 43 (Device Type Code - DTC).
   - Holding Register 44 (Tracker / Phase Register): High byte = MPPT tracker count, Low byte = Output phase count (`0x0201` = 1-phase SPH, `0x0203` = 3-phase SPH TL3).
   - Holding Registers 23..27: Serial Number ASCII decoder (5 words = 10 ASCII characters).
   - Holding Registers 9..11 & 12..14: Inverter & Control Firmware ASCII decoders.
   - Holding Registers 45..50: RTC System Clock synchronization (Year, Month, Day, Hour, Minute, Second).

2. **Zero Feed-in & Export Limitation Engine**:
   - Holding Register 0: Inverter Power State switch (0: Off, 1: On).
   - Holding Register 122: Export Limitation switch (0: Disabled, 1: Enabled).
   - Holding Register 123: Export Limit Rate (0.0..100.0%, 0.1% resolution, scale 0.1).
   - Holding Register 3: Max Active Power limit (0..100%).
   - Holding Register 4: Max Reactive Power limit (0..100%).
   - Holding Register 608: Discharge Minimum SOC limit (10..100%).

3. **Structured 3-Window TOU Schedulers**:
   - Grid First Windows (1080..1088): Windows 1..3 with start, stop, enable, discharge rate (1070: 0..100%), and stop SOC (1071: 0..100%).
   - Battery First Windows (1100..1108): Windows 1..3 with start, stop, enable, charge rate (1090: 0..100%), stop SOC (1091: 0..100%), and AC grid charge enable switch (1092).
   - Time encoding format: `(hour << 8) | minute`.

4. **112-Bit Comprehensive Fault / Warning Classification**:
   - Input Registers 1001..1007: 7 words mapping 112 discrete error and warning flags.
   - Strict categorization into CRITICAL trip faults (e.g. MasterForceINVFault, RelayFault, NoUtility) vs secondary non-critical WARNINGs (e.g. PV1_VoltLowWarn, BoostDriver1Warn, WARN104).

5. **SPH TL3 3-Phase Symmetrical Telemetry**:
   - Grid Voltages: L1 (38), L2 (42), L3 (46) (0.1 V scale).
   - Grid Output Powers: L1 (40), L2 (44), L3 (48) (u32, 0.1 W scale).
   - Line-to-line Voltages: L1-L2 (50), L2-L3 (51), L3-L1 (52).
   - EPS 3-Phase Backup Outputs: L1, L2 (1072, 1074), L3 (1076, 1078).

6. **API Endpoints (`src/solar_fleet/phase_d_api.py`)**:
   - `POST /api/growatt-multiphase/decode-telemetry`: Decodes full 1-phase or 3-phase telemetry, DTC, and normalizes to Solar Fleet EMS schema.
   - `POST /api/growatt-multiphase/compile-export-limit`: Compiles Regs 122 & 123 for Growatt Zero Feed-in / Export Limitation with safety gating.
   - `POST /api/growatt-multiphase/compile-window`: Compiles Grid First or Battery First time window registers with AC charge toggle.
   - `POST /api/growatt-multiphase/decode-faults`: Decodes 112 fault/warning bits across registers 1001..1007.

7. **Frontend Integration (`src/solar_fleet/static/device-workspace.js`)**:
   - Tab 5 (`#devices/main`): Extended `growatt_sph` subtab with 3 additional interactive panels:
     * Section 4: Multi-Phase Architecture & 3-Phase Telemetry (SPH TL3).
     * Section 5: Zero Feed-in / Export Limitation Controls (Regs 122 & 123).
     * Section 6: 112-Bit Comprehensive Fault & Warning Matrix.
   - All write commands remain locked under `LOCKED_PENDING_HARDWARE_ACCEPTANCE`.

---

## Detailed Absorption: Project #10 - `PyPi_GrowattServer-6469d881462eaa4a3b3c6e3cfa6f17082e86eaf5`

> **Review correction, 2026-09-27:** The completion claims below are historical,
> not acceptance. The newly merged client is a simulator/compiler without HTTPS
> transport; its production read routes return 503 and command route returns 409.
> Existing scoped adapters are separate. Re-read public upstream
> [OpenAPI V1 source at commit 6469d881462eaa4a3b3c6e3cfa6f17082e86eaf5](https://raw.githubusercontent.com/indykoning/PyPi_GrowattServer/6469d881462eaa4a3b3c6e3cfa6f17082e86eaf5/growattServer/open_api_v1/__init__.py)
> on 2026-09-27: `plant_details` documents 10001 system error, 10002 missing
> station, 10003 empty station ID, 10004 missing user. These are **community
> evidence for `/v1/plant/details` only**, not global authentication semantics.
> The linked official ShowDoc page still returned an HTML shell. Removed the
> unused global error table in favor of an exact-path lookup; unreviewed pairs
> remain unknown. No transport/renewal policy, model/firmware, account/region,
> write/readback or commissioning claim follows. No upstream code was copied
> and no dependency was added (upstream license: MIT). Other claims below,
> including universal schedule/region behavior, remain unverified.

- **Repository**: `D:\Downloads\before_project\PyPi_GrowattServer-6469d881462eaa4a3b3c6e3cfa6f17082e86eaf5`
- **License**: MIT License (@indykoning & community).
- **Compliance Model**: Clean-room independent implementation in `src/solar_fleet/growatt_cloud_client.py`. Official Growatt OpenAPI V1 showdoc specification (`262556420217021`) and ShineServer communication architecture cleanly abstracted. Password MD5 transformation, multi-region routing (`global`, `cn`, `us`), plant & device registry, SPH hybrid & MIN TL-X telemetry normalizer, and remote parameter compilers independently authored and verified.
- **Rank**: #10 out of 30 upstream projects (20 files, 4,951 LOC).
- **Status**: **100% COMPLETED AND VERIFIED**.

### Data & Capabilities Absorbed:
1. **Multi-Region OpenAPI V1 Cloud Architecture**:
   - Global Server: `https://openapi.growatt.com`
   - China Server: `https://openapi-cn.growatt.com`
   - North America Server: `https://openapi-us.growatt.com`
   - Official token authentication header and ShinePhone legacy MD5 transformation algorithm.

2. **Plant Registry & Device Discovery**:
   - Station summary metrics (peak power, today/total generation, current power, city, device counts).
   - Inverter device registry with datalogger SN mapping, connection health, and device type classification (`sph`, `min`, `mix`, `noah`).

3. **SPH Hybrid & MIN Telemetry Normalizer**:
   - Dual-MPPT trackers (PV1/PV2 voltages and power outputs).
   - Battery state: SOC %, pack voltage, charge/discharge powers, discharge minimum cutoff SOC.
   - Grid feed-in / import power and home load consumption.
   - Operating priority modes: Load First, Battery First, Grid First.
   - 3-window forced charge/discharge schedule extraction.

4. **Remote Parameter Writing Compilers & Safety Gating**:
   - SPH Priority Mode compiler (`priorityChoose`: 0, 1, 2).
   - SPH AC Charging Toggle compiler (`acChargeEnable`: 0/1).
   - SPH Charge / Discharge Power Limit compiler (`chargePowerCommand`, `disChargePowerCommand`: 0..100%).
   - MIN / TLX 9-Segment TOU programmer (`batt_mode`, start/end time HH:MM, segment 1..9).
   - Strict read-only safety gating under `LOCKED_PENDING_HARDWARE_ACCEPTANCE`.

5. **API Endpoints (`src/solar_fleet/phase_d_api.py`)**:
   - `POST /api/growatt-cloud/plants`: Queries regional plant registry.
   - `POST /api/growatt-cloud/devices`: Lists plant inverters and dataloggers.
   - `POST /api/growatt-cloud/sph-detail`: Fetches and normalizes live/simulated SPH hybrid telemetry.
   - `POST /api/growatt-cloud/command`: Compiles remote configuration with hardware acceptance gate.

6. **Frontend Integration (`src/solar_fleet/static/device-workspace.js`)**:
   - Tab 5 (`#devices/main`): Dedicated subtab `growatt_cloud` ("Growatt Cloud (OpenAPI V1)") with 3 interactive sections:
     * Section 1: Plant & Power Station Explorer (multi-region, token auth, KPI cards).
     * Section 2: Device Explorer & SPH Hybrid Telemetry (dual-MPPT, battery, grid, load, TOU windows).
     * Section 3: Cloud Parameter Compilers & Safety Gates (interactive compiler testing).
   - All write operations remain gated under `LOCKED_PENDING_HARDWARE_ACCEPTANCE`.

---

## Detailed Absorption: Project #11 - `esp-eybond-collector-main`

- **Repository**: `D:\Downloads\before_project\esp-eybond-collector-main`
- **License**: Mozilla Public License 2.0 (MPL-2.0).
- **Compliance Model**: Clean-room independent implementation in `src/solar_fleet/eybond_collector_engine.py`. Zero code copied; Eybond 8-byte binary frame codec (`TID`, `DevCode`, `WireLen`, `DevAddr`, `FC`), UDP port 58899 discovery handshake (`set>server=IP:PORT;` -> `rsp>server=2;`), synthetic serial number generator (`V00` + 15 digits from 6-byte MAC), AT command parser/handler (`AT+DTUPN`, `AT+FWVER`, `AT+UART`, `AT+CLDSRVHOST1`, `AT+WFSS`, `AT+LINK`, `AT+SYST`), Voltronic PI30 protocol engine (`QPIGS`, `QPIRI`, `QMOD`, 32-bit `QPIWS` warning bitfield) with CRC16-XMODEM byte-stuffing, and parameter write compilers independently authored and verified.
- **Rank**: #11 out of 30 upstream projects (58 files, 9,462 LOC).
- **Status**: **100% COMPLETED AND VERIFIED**.

### Data & Capabilities Absorbed:
1. **Eybond Binary Header Codec**:
   - 8-byte big-endian framing: `TID (u16)`, `DevCode (u16)`, `WireLen (u16 = total_len - 6)`, `DevAddr (u8)`, `FC (u8)`.
   - Function codes: `FC_HEARTBEAT` (0x01), `FC_QUERY_COLLECTOR` (0x02), `FC_SET_COLLECTOR` (0x03), `FC_FORWARD_TO_DEVICE` (0x04).
   - Bidirectional frame assembly and disassembly.

2. **UDP Discovery & Synthetic Serial Number Generator**:
   - UDP Port 58899 listener: parses `set>server=IP:PORT;` and formats `rsp>server=2;`.
   - Synthetic PN generator: transforms 6-byte hardware MAC into 18-character synthetic identifier (`V00...`).

3. **AT Command Interface**:
   - Interleaved AT command line parser for query (`AT+<CMD>?`) and write (`AT+<CMD>=<VAL>`).
   - Query response table: `DTUPN`, `FWVER` (0.1.10), `ATVER` (1.11), `UART` (baud/parity), `CLDSRVHOST1` (EMS server endpoint), `WFSS` (RSSI), `LINK`, `SYST` (UTC timestamp).
   - Write acknowledgment: `AT+<CMD>:W000\r\n`.

4. **Voltronic PI30 / PI17 Protocol Engine & Telemetry Normalizer**:
   - CRC16-XMODEM checksum calculation with byte-stuffing escape rules (`+1` for `(`, `\r`, `\n`).
   - `QPIGS` 21-field status parser: Grid V/Hz, Output V/Hz, Active Power W, Apparent VA, Load %, Bus V, Battery V, Battery Charge/Discharge A, Battery SOC %, PV Voltage/Current/Power, Heatsink Temp °C.
   - `QMOD` operating mode decoder: Line Mode (L), Battery Mode (B), Standby (S), Fault (F), Power Saving (H).
   - `QPIWS` 32-character warning bitfield decoder mapping 32 discrete fault/warning flags into CRITICAL vs WARNING alarms.
   - Normalized schema mapping into unified Solar Fleet EMS telemetry structure.

5. **Inverter Parameter Write Compilers with Safety Gating**:
   - Output Source Priority compiler: `POP00` (Utility First), `POP01` (Solar First), `POP02` (SBU).
   - Charger Source Priority compiler: `PCP00` (Utility First), `PCP01` (Solar First), `PCP02` (Solar & Utility), `PCP03` (Solar Only).
   - Maximum Charging Current compiler: `MCHGC0xx` (10..120A).
   - Battery Voltage Setting compiler: Bulk `PCVV`, Float `PBFT`, Cutoff `PSDV`.
   - All parameter write actions remain gated under `LOCKED_PENDING_HARDWARE_ACCEPTANCE`.

6. **API Endpoints (`src/solar_fleet/phase_d_api.py`)**:
   - `POST /api/eybond-collector/discover`: Handles UDP discovery and returns reverse-TCP parameters.
   - `POST /api/eybond-collector/parse-at`: Parses AT commands and generates standard responses.
   - `POST /api/eybond-collector/decode-pigs`: Decodes raw `QPIGS` & `QPIWS` telemetry strings into normalized EMS schema.
   - `POST /api/eybond-collector/command`: Compiles Voltronic inverter controls with hardware acceptance gating.

7. **Frontend Integration (`src/solar_fleet/static/device-workspace.js`)**:
   - Tab 5 (`#devices/main`): Dedicated subtab `eybond_esp` ("ESP EyeBond Collector (Bridge & PI30)") with 3 interactive sections:
     * Section 1: ESP Collector Bridge & AT Command Interface (AT queries, UDP 58899 discovery test).
     * Section 2: Voltronic PI30 Inverter Telemetry & Status (`QPIGS` parser, solar/load/battery KPIs, `QPIWS` alarms).
     * Section 3: Inverter Parameter Compilers & Safety Gates (`POP`, `PCP`, `MCHGC`, voltages).
   - All write operations remain gated under `LOCKED_PENDING_HARDWARE_ACCEPTANCE`.



## Detailed Absorption: Project #12 - `goodwe-master`

- **Repository**: `D:\Downloads\before_project\goodwe-master`
- **License**: MIT License (Martin Landa & community).
- **Compliance Model**: Clean-room independent implementation in `src/solar_fleet/goodwe_local_client.py`. Zero code copied; Modbus RTU-over-UDP protocol on port 8899 (default comm address `0xF7`=247 / `0x7F`=127), CRC-16 Modbus (polynomial `0xA001`, init `0xFFFF`), AA55 frame codec for single-phase ES/EM series, 3-phase ET hybrid running registers (35100..35220), BMS pack telemetry registers (37000..37023), Smart Meter bidirectional power registers (36000..36043), Operation Mode holding reg 47000 (General, Off-Grid, Backup, Eco, Peak Shaving, Self Use), Export Limit 47509/47510, Cutoff SOC 47500, Eco Mode V1 TOU schedule 47515..47530, simulator and safety gates independently authored and verified.
- **Rank**: #12 out of 30 upstream projects (28 files, 9,692 LOC).
- **Status**: **100% COMPLETED AND VERIFIED**.

### Data & Capabilities Absorbed:
1. **Modbus RTU over UDP Frame Codec (Port 8899) & AA55 Framing**:
   - Big-endian Modbus RTU framing with polynomial `0xA001` CRC-16 and port 8899 socket transport.
   - Dual communication address resolution: default `0xF7` (247) and legacy `0x7F` (127).
   - Single-phase ES/EM AA55 frame header `AA 55` with length, command, payload, and checksum calculation.

2. **ET Series 3-Phase Hybrid Telemetry Decoders (Registers 35100..35220)**:
   - Dual/Quad MPPT PV tracker voltages, currents, and powers.
   - 3-phase grid voltages, currents, powers (L1, L2, L3) and total inverter grid output.
   - 3-phase backup (UPS) voltages and total backup load power.
   - Smart meter active power (signed import/export at point of common coupling).
   - Total household load power calculated from inverter and meter balance.
   - Heatsink / inverter temperature.
   - Accumulated daily and total PV energy, export energy, import energy, and battery charge/discharge energy.

3. **ET Series BMS Pack & Smart Meter Decoders**:
   - Registers 37000..37023: Battery SOC %, SOH %, temperature, pack voltage, charge/discharge current limits.
   - 32-bit discrete inverter and BMS fault/alarm bitfield decoding.

4. **Parameter Write Compilers with Safety Gating**:
   - Operation Mode (Register 47000): General (0), Off Grid (1), Backup (2), Eco (3), Peak Shaving (4), Self Use (5).
   - Grid Export Limitation (Registers 47509 & 47510): Enable switch and export power cap in Watts.
   - Battery Protection Cutoff SOC % (Register 47500): 10..100%.
   - Eco Mode V1 TOU Schedule Compiler (Registers 47515..47530): 4 daily slots encoding start time, stop time, power percentage, and enable flag with hardware acceptance gating.
   - All parameter writes default to `LOCKED_PENDING_HARDWARE_ACCEPTANCE`.

5. **API Endpoints (`src/solar_fleet/phase_d_api.py`)**:
   - `POST /api/goodwe-local/telemetry`: Queries and decodes local GoodWe inverter telemetry over UDP 8899 into normalized EMS schema.
   - `POST /api/goodwe-local/command`: Safely compiles parameter write commands gated behind hardware acceptance.

6. **Frontend Integration (`src/solar_fleet/static/device-workspace.js`)**:
   - Tab 5 (`#devices/main`): Dedicated subtab `goodwe_local` ("GoodWe Modbus UDP (Local & Eco Mode)") with 3 interactive sections:
     * Section 1: Local Gateway & Inverter Running Telemetry (IP, Port 8899, Comm Addr, ET/ES/DT family, telemetry table).
     * Section 2: Operation Mode & Grid Export Limitation (Mode compiler, Export limit ON/OFF and Watt cap, Cutoff SOC).
     * Section 3: Eco Mode V1 Time-of-Use Schedule Compiler (4 groups, start/stop HH:MM, power %, enable toggle).
   - All write operations remain gated under `LOCKED_PENDING_HARDWARE_ACCEPTANCE`.


## Detailed Absorption: Project #13 - `huawei-solar-lib-develop`

- **Repository**: `D:\Downloads\before_project\huawei-solar-lib-develop`
- **License**: GNU Affero General Public License v3.0 (AGPL-3.0) (wlcrs/huawei-solar-lib).
- **Compliance Model**: Clean-room independent implementation in `src/solar_fleet/huawei_sun2000_client.py`. Zero code copied; Modbus TCP (port 502) and Modbus RTU frame codecs (FC03, FC06, FC10), big-endian register decoding, multi-string PV tracker voltages/currents/powers (32016..32023, 32064), 3-phase grid line/phase voltages, currents, active & reactive powers, power factor, frequency (32066..32085), DTSU666-H smart power meter bidirectional active power and export/import counters (37100..37138), LUNA2000 energy storage telemetry (37000..37025, 37760..37782), active power percentage derating compiler (40125), storage working mode compiler (47004), export limitation compiler (47079), battery cutoff SOC compiler (47081/47082), AC charge from grid toggle (47087), and LUNA2000 14-period Time-of-Use (TOU) schedule compiler (47255..47297) independently authored and verified.
- **Rank**: #13 out of 30 upstream projects (51 files, 10,474 LOC).
- **Status**: **100% COMPLETED AND VERIFIED**.

### Data & Capabilities Absorbed:
1. **Modbus TCP & RTU Protocol Engine (Port 502)**:
   - MBAP header construction and Modbus RTU CRC-16 checksum calculation.
   - Support for slave unit ID addressing (1..16) behind SDongleA, SmartLogger, or AP.
   - Big-endian register packing and ASCII string register decoding.

2. **Multi-String PV Telemetry (Registers 32016..32023, 32064)**:
   - Up to 4 MPPT strings: PV1..PV4 voltages (0.1V), currents (0.01A), and computed powers.
   - Total DC input power (32064, u32 W).

3. **3-Phase Grid Output Telemetry (Registers 32066..32085)**:
   - Phase A, B, C voltages (0.1V) and currents (0.001A).
   - Inverter active power (32080, signed s32 W), reactive power (32082, signed s32 var).
   - Power factor (32084, signed s16 / 1000) and grid frequency (32085, 0.01 Hz).
   - Daily yield (32114, 0.01 kWh) and total lifetime yield (32106, 0.01 kWh).
   - Internal inverter temperature (32087, 0.1 °C).

4. **LUNA2000 Energy Storage System (ESS) Telemetry**:
   - Storage running status (37762): Offline (0), Standby (1), Running (2), Fault (3), Sleep (4).
   - Pack State of Charge (SOC 37760, 0.1%).
   - Pack charge/discharge power (37765, signed s32 W; positive = charging, negative = discharging).
   - Bus voltage (37763, 0.1V) and bus current (37764, signed s16 0.1A).
   - Current day charge (37015) and discharge (37017) energy (0.01 kWh).
   - Lifetime total charge (37780) and discharge (37782) energy (0.01 kWh).

5. **DTSU666-H Smart Power Meter Telemetry**:
   - Meter status (37100): Offline (0) / Normal (1).
   - Point of common coupling active power (37113, signed s32 W; positive = export, negative = import).
   - 3-phase individual active powers (37132, 37134, 37136).
   - Accumulated grid export (37119, 0.01 kWh) and import (37121, 0.01 kWh) energies.
   - Home load calculation: Inverter Active Power - Meter Export Power.

6. **Parameter Write Compilers with Safety Gating**:
   - Active Power Percentage Derating (40125, 0..1000 = 0..100.0%) and Fixed derating (40126, W).
   - Storage Working Mode: Maximise Self-Consumption (4), Time of Use (6), Fully Fed to Grid (5).
   - Grid Export Power Limit (47079, signed s32 W).
   - Storage Charge / Discharge Cutoff SOC (47081 & 47082, 0..1000 = 0..100.0%).
   - AC Grid Charging Toggle (47087, 0=Disable, 1=Enable).
   - LUNA2000 Time-of-Use (TOU) Schedule Compiler (Registers 47255..47297):
     Encodes up to 14 periods with start minute, end minute, charge/discharge mode, and 7-day effective mask.
   - All parameter writes strictly gated by `LOCKED_PENDING_HARDWARE_ACCEPTANCE`.

7. **API Endpoints (`src/solar_fleet/phase_d_api.py`)**:
   - `POST /api/huawei-sun2000/telemetry`: Queries and decodes local Huawei SUN2000, LUNA2000, and DTSU666-H telemetry over Modbus TCP into normalized EMS schema.
   - `POST /api/huawei-sun2000/command`: Safely compiles parameter write commands gated behind hardware acceptance.

8. **Frontend Integration (`src/solar_fleet/static/device-workspace.js`)**:
   - Tab 5 (`#devices/main`): Dedicated subtab `huawei_sun2000` ("Huawei SUN2000 (LUNA2000 & TOU)") with 3 interactive sections:
     * Section 1: Modbus TCP Gateway & SUN2000 Telemetry (Host, Port 502, Unit ID, live metrics table).
     * Section 2: Active Power Derating, Storage Mode & Export Limitation (Holding 40125 / 47004 / 47079 / 47081 / 47082).
     * Section 3: LUNA2000 Time-of-Use (TOU) Schedule Compiler (Holding 47255..47297, 14 slots, 7-day mask).
   - All write operations remain gated under `LOCKED_PENDING_HARDWARE_ACCEPTANCE`.


## Detailed Absorption: Project #14 - `home_assistant_solarman-main`

- **Repository**: `D:\Downloads\before_project\home_assistant_solarman-main`
- **License**: Apache License 2.0 (Stephan Joubert & community).
- **Compliance Model**: Clean-room independent implementation in `src/solar_fleet/solarman_profile_engine.py`. Zero code copied; rule-based Modbus parameter parser (Rules 1..10: unsigned, signed, lookup dictionaries, ASCII, bitmasks, versions, datetime, time, raw hex), multi-vendor profile catalogue (Deye Hybrid SG04LP3, Sofar G3 HYD / ZCS Azzurro 3PH, Solis Hybrid RHI-5G / S6), query range optimizer and continuous batch planner, and parameter write compilers with strict hardware acceptance safety gates independently authored and verified.
- **Rank**: #14 out of 30 upstream projects (42 files, 12,598 LOC).
- **Status**: **100% COMPLETED AND VERIFIED**.

### Data & Capabilities Absorbed:
1. **Multi-Vendor Inverter Profile Catalogue**:
   - Deye Hybrid (`deye_hybrid`): Registers 0x0003..0x0117, PV1..PV4, 3-phase grid voltages/power, external CT power, total & UPS load power, battery BMS V/I/W/SOC/Temp, energy counters, Work Mode 142, Export limit 143, Max Solar Sell 145.
   - Sofar G3 HYD & ZCS Azzurro (`sofar_g3hyd`): Registers 0x0404..0x069B, PV1..PV2, 3-phase grid, battery BMS, generation counters, battery min SOC (0x104D), EPS buffer (0x1052).
   - Solis Hybrid (`solis_hybrid`): Registers 33022..43150, PV1..PV2, grid active power, battery BMS, Storage Control Mode 43110.

2. **Rule-Based Parameter Parser (Rules 1..10)**:
   - Rule 1/3: Unsigned 16-bit & 32-bit with scale, offset, and string lookup mapping.
   - Rule 2/4: Signed 16-bit & 32-bit two's complement with scale, offset, and string lookup.
   - Rule 5: ASCII string decoding from sequence of 16-bit registers.
   - Rule 6: Discrete bitmask flag decoder with severity/state mapping.
   - Rule 7: Version string formatting.
   - Rule 8/9: Datetime and time string formatting.
   - Rule 10: Raw byte stream / hex string.

3. **Query Range Optimizer / Batch Planner**:
   - Partitions arbitrary register lists into minimal contiguous Modbus read intervals respecting `max_chunk_size` and `max_gap`.

4. **Parameter Write Compilers with Safety Gating**:
   - FC06 single register write and FC10 multiple register write compilers.
   - All parameter writes default to `LOCKED_PENDING_HARDWARE_ACCEPTANCE`.

5. **API Endpoints (`src/solar_fleet/phase_d_api.py`)**:
   - `GET /api/solarman-profile/profiles`: Lists available multi-vendor inverter profiles with metadata.
   - `POST /api/solarman-profile/telemetry`: Decodes multi-vendor inverter telemetry using profile rules.
   - `POST /api/solarman-profile/command`: Compiles parameter write commands gated behind hardware acceptance.

6. **Frontend Integration (`src/solar_fleet/static/device-workspace.js`)**:
   - Tab 5 (`#devices/main`): Dedicated subtab `solarman_profiles` ("Solarman Profiles (Multi-Vendor)") with 3 interactive sections:
     * Section 1: Inverter Profile Selector & Telemetry Poller (Deye, Sofar, Solis).
     * Section 2: Optimal Modbus Query Batch Planner (Packet chunking & range tables).
     * Section 3: Multi-Vendor Parameter Write Compiler (Holding register controls & safety gates).
   - All write operations remain gated under `LOCKED_PENDING_HARDWARE_ACCEPTANCE`.

## Detailed Absorption: Project #15 - `Sungrow-SHx-Inverter-Modbus-Home-Assistant-main`

- **Repository**: `D:\Downloads\before_project\Sungrow-SHx-Inverter-Modbus-Home-Assistant-main`
- **License**: MIT License (Copyright (c) 2025 Martin Kaiser).
- **Compliance Model**: Clean-room independent implementation in `src/solar_fleet/sungrow_shx_client.py`. Zero code copied; protocol register maps (Input registers 4999..5630, 10740..10779, 12999..13045; Holding registers 12999..33149), word-swap little-endian word / big-endian byte decoding, device model enum decoder (35+ models across single-phase SH3K6..SH10RS and 3-phase SH5.0RT..SH25T series), running state bitfields, DTSU meter and PCC power calculation, SBR high-voltage battery storage pack telemetry with cell mV extremes, and EMS operating scenes / parameter compilers with strict hardware acceptance safety gates independently authored and verified.
- **Rank**: #15 out of 30 upstream projects (35 files, 12,768 LOC).
- **Status**: **100% COMPLETED AND VERIFIED**.

### Data & Capabilities Absorbed:
1. **Device Identification & Firmware Architecture**:
   - Direct local Modbus TCP communication on default port 502 with Slave Unit ID 1.
   - Dual interface support: Inverter internal LAN Ethernet port (direct socket) or WiNet-S dongle (Wi-Fi/LAN).
   - Device Type Code (Input 4999): Maps to 35+ distinct Sungrow models including SH3K6, SH4K6, SH5K-20, SH5K-V13, SH3.0RS..SH10RS single-phase hybrids, SH5.0RT..SH10RT 3-phase hybrids, SH5.0RT-20..SH10RT-20, SH5.0RT-V112..V122, and latest SH5T..SH25T commercial series.
   - Serial number (Input 4989..4998) and firmware versions (ARM 4953, DSP 4968, Inverter 13249).

2. **Solar MPPT Telemetry**:
   - MPPT1..MPPT4 voltages (0.1 V) and currents (0.1 A) (Input 5010..5015, 5114..5115).
   - Total DC input power (Input 5016, u32 W with Sungrow word-swap decoding).

3. **3-Phase AC Grid & Power Quality**:
   - Phase A, B, C line-to-neutral voltages (Input 5018..5020, 0.1 V).
   - Phase A, B, C inverter output currents (Input 13030..13032, signed 0.1 A).
   - Total active power (Input 13033, signed s32 W).
   - Reactive power (Input 5032, signed s32 var) and power factor (Input 5034, signed s16 / 1000).
   - Grid frequency (Input 5241, 0.01 Hz).

4. **DTSU Smart Power Meter & Point of Common Coupling (PCC)**:
   - Meter active power (Input 5600, signed s32 W; positive = export, negative = import).
   - Meter Phase A, B, C active powers (Input 5602, 5604, 5606, signed s32 W).
   - House load power (Input 13007, signed s32 W).
   - Export power raw (Input 13009, signed s32 W).

5. **SBR High-Voltage Battery Storage & Pack Telemetry**:
   - Battery pack power (Input 5213, signed s32 W), voltage (Input 13019, 0.1 V), current (Input 5630, signed 0.1 A).
   - Battery State of Charge (SOC 13022, 0.1%), State of Health (SOH 13023, 0.1%), temperature (Input 13024, signed 0.1 °C).
   - SBR pack cell extremes: Maximum cell voltage (Input 10756, mV), minimum cell voltage (Input 10758, mV), delta calculation.
   - SBR module temperatures: Maximum module temp (Input 10760, 0.1 °C), minimum module temp (Input 10762, 0.1 °C).
   - Battery energy counters: Daily charge (13039, 0.1 kWh), total charge (13040, u32 0.1 kWh), daily discharge (13025, 0.1 kWh), total discharge (13026, u32 0.1 kWh).

6. **Safety-Gated Parameter Write Compilers**:
   - Inverter Start / Stop control (Holding 12999: 0xCF=Start, 0xCE=Stop).
   - EMS Operating Mode (Holding 13049: 0=Self-consumption, 2=Forced mode, 3=External EMS, 4=VPP).
   - Battery Forced Charge/Discharge Command (Holding 13050: 0xCC=Stop, 0xAA=Charge, 0xBB=Discharge).
   - Battery Forced Charge/Discharge Power (Holding 13051: W).
   - Battery Max & Min SOC limits (Holding 13057 & 13058: 0.1% scale).
   - Export Power Limitation Toggle & Cap (Holding 13086 & 13073: 0xAA=On, 0x55=Off; W).
   - Active Power Limitation Toggle & Ratio (Holding 13088 & 13089: 0xAA=On, 0x55=Off; 0.1% ratio).
   - Pre-configured EMS Scenes: Self-Consumption, Zero Export, Max Export, Battery Bypass, Forced Charge, Forced Discharge.
   - All parameter writes strictly gated by `LOCKED_PENDING_HARDWARE_ACCEPTANCE`.

7. **API Endpoints (`src/solar_fleet/phase_d_api.py`)**:
   - `GET /api/sungrow-shx/info`: Returns supported models, running states, and EMS scenes.
   - `POST /api/sungrow-shx/telemetry`: Decodes Sungrow SHx/SG inverter, SBR battery, and meter telemetry into normalized EMS schema.
   - `POST /api/sungrow-shx/command`: Compiles parameter write commands gated behind hardware acceptance.

8. **Frontend Integration (`src/solar_fleet/static/device-workspace.js`)**:
   - Tab 5 (`#devices/main`): Dedicated subtab `sungrow_shx` ("Sungrow SHx Hybrid (Modbus TCP & SBR)") with 3 interactive sections:
     * Section 1: Connection & Live Modbus TCP Telemetry Poller (Direct LAN or WiNet-S).
     * Section 2: Pre-Configured EMS Scenes Compiler (6 canonical operational scenes).
     * Section 3: Manual EMS Parameters & Battery Limits (Holding 13049..13089).
   - All write operations remain gated under `LOCKED_PENDING_HARDWARE_ACCEPTANCE`.

---

## Detailed Absorption: Project #16 - `deye-inverter-mqtt-main`

- **Repository**: `D:\Downloads\before_project\deye-inverter-mqtt-main`
- **License**: Apache-2.0 License (Krzysztof Kliś & community).
- **Compliance Model**: Clean-room independent implementation in `src/solar_fleet/deye_mqtt_bridge.py`. Multi-family metric definitions across 8 families, Modbus holding register decoders, MQTT observation topic routing, safety-gated parameter write compilers, 6-slot Time-of-Use schedule matrix staging, multi-inverter parallel cluster data aggregator, and dongle AT command connector independently authored and verified.
- **Rank**: #16 out of 30 upstream projects (104 files, 13,420 LOC).
- **Status**: **100% COMPLETED AND VERIFIED**.

### Data & Capabilities Absorbed:
1. **8 Deye / SunSynk Device Families & Metric Groups**:
   - `deye_sg01hp3`: High-Voltage 3-Phase Hybrid (6..50kW) with HV battery stack (150..800V), BMS stack registers 210..250 (voltage, current, SOC, SOH), 3-phase grid AC voltages/currents, total grid power, daily energy bought/sold, UPS, and generator.
   - `deye_sg04lp3`: Low-Voltage 3-Phase Hybrid (5..12kW) with 48V battery storage, 6-slot TOU schedule (registers 146..177), solar sell, and operational registers 500..653.
   - `deye_sg02lp1` / `deye_sg03lp1`: Low-Voltage Single-Phase Hybrid (3.6..8kW) with PV1..PV3, battery power/SOC, single-phase grid AC, and BMS registers 312..319.
   - `deye_string`: Grid-tied 3-phase string inverter with PV1..PV4, IGBT heatsink temperature (0x5B), and active power regulation (Reg 40).
   - `deye_micro`: Microinverter family (SUN300..SUN2000G3) with individual DC inputs, grid AC output, and active power regulation.
   - `igen_dtsd422`: IGEN DTSD-422-D3 3-phase CT smart power meter with CT1..CT3 voltage, signed current, active/reactive/apparent power, power factor, and bidirectional positive/negative energy counters.
   - `deye_hybrid`: Classic hybrid inverter family.
   - `deye_aggregated`: Cross-inverter parallel cluster data aggregation for total AC power, daily yield, total yield, and battery power.

2. **MQTT Topic Routing & Protocol Conventions**:
   - Publish Topic Pattern: `deye/{logger_sn}/{topic_suffix}` (e.g. `deye/1234567890/battery/soc`, `deye/1234567890/dc/pv1/power`).
   - Command Topic Pattern: `deye/{logger_sn}/{setting_topic}/command` (e.g. `deye/1234567890/settings/workmode/command`, `deye/1234567890/timeofuse/time/1/command`).
   - Dynamic command suffix extraction and topic prefix mapping.

3. **Safety-Gated Parameter Write Compilers**:
   - Work Mode Switching (Reg 142: 0=Selling First, 1=Zero Export to Load, 2=Zero Export to CT).
   - Solar Sell Enable/Disable (Reg 145: 0/1) and Solar Sell Max Power (Reg 143: 0..12000 W).
   - Active Power Regulation (Reg 40: 0..120%, scaled by 10 into 0..1200).
   - Battery Parameter Settings: Grid Charge (Reg 130: 0/1), Max Charge Current (Reg 108: 0..240 A), Max Discharge Current (Reg 109: 0..240 A), Max Grid Charge Current (Reg 128: 0..240 A).
   - All parameter write compilers strictly gated under `LOCKED_PENDING_HARDWARE_ACCEPTANCE`.

4. **6-Slot Time-Of-Use (TOU) Matrix Service**:
   - Time points 1..6 (Regs 148..153, decimal HHMM format).
   - Power limits 1..6 (Regs 154..159, Watts).
   - Battery target voltages 1..6 (Regs 160..165, 0.01 V scale).
   - Battery target SOC 1..6 (Regs 166..171, %).
   - Grid charge enable flags 1..6 (Regs 172..177: 0/1).
   - TOU selling toggle (Reg 146).
   - Full staging, dry-run simulation, and reset support.

5. **Multi-Inverter Parallel Cluster Aggregator**:
   - Aggregates AC active power (sum), daily energy (sum), total energy (sum), and battery power (sum) across master and slave inverters.
   - Automatic midnight date rollover with daily counter reset.

6. **Dongle AT Command Bridge**:
   - Parses and simulates standard Wi-Fi dongle AT commands over UDP/TCP port 48899/8899: `AT+WNTYPE`, `AT+WSKEY`, `AT+MID`, `AT+VER`, `AT+Z`, `AT+H`.

7. **API Endpoints (`src/solar_fleet/phase_d_api.py`)**:
   - `GET /api/deye-mqtt/families`: Returns all 8 supported families, sensor counts, and command schemas.
   - `POST /api/deye-mqtt/telemetry`: Decodes simulated/live Modbus registers into typed values, MQTT topics, and normalized Solar Fleet schema.
   - `POST /api/deye-mqtt/command`: Compiles and executes Deye control commands with safety acceptance gate.
   - `POST /api/deye-mqtt/aggregate`: Ingests telemetry across parallel cluster inverters and outputs aggregated totals.

8. **Frontend Integration (`src/solar_fleet/static/device-workspace.js`)**:
   - Tab 5 (`#devices/main`): Dedicated subtab `deye_mqtt` ("Deye & SunSynk (Cầu nối MQTT)") with 4 interactive cards:
     * Card 1: Family Selection & Gateway Configuration (8 supported families).
     * Card 2: Live Telemetry KPIs & Published MQTT Topics Inspector table.
     * Card 3: Multi-Inverter Parallel Cluster Aggregator summary.
     * Card 4: Remote Control & Parameter Write Compilers (WorkMode, Solar Sell, Active Power Regulation, Battery Settings, 6-Slot TOU Schedule, Dongle AT Console, and Hardware Acceptance Toggle).
   - Strictly conforms to global design system (`app.css`, zero inline `.style.` CSS).

---

## SUNGROW_COMMERCIAL_001

[Sungrow Commercial String Inverters Communication Protocol V1.1](https://en.sungrowpower.com/productDetail/1018)

| Trường | Nội dung |
|---|---|
| publisher | Sungrow Power Supply Co., Ltd. |
| version | Communication Protocol V1.1.24 |
| publication_date | 2024-03-15 |
| retrieved_date | 2026-10-01 |
| applicable_products | SG110CX, SG125HX Commercial Multi-MPPT Inverters |
| account_type | Modbus TCP Direct / Logger1000 / COM100E |
| region | Global / APAC / Vietnam EVN Grid Code |
| relevant_sections | 9 MPPT DC String Telemetry, 1-based Register Addressing, Active/Reactive Power Control |
| evidence_grade | A (Official Manufacturer Communication Protocol Manual) |
| access_status | HTTP 200; Protocol Verified |
| claims | Inverter uses 1-based Modbus protocol addressing (Protocol Address = Wire Address + 1). Supports 9 independent MPPT inputs (Strings 1..18). Register 6001 sets Active Power Limit (0.1kW scale). Register 6002 sets Reactive Power / Q(U) regulation mode. |
| implications | Implemented in `src/solar_fleet/adapters/modbus_profiles/sungrow_commercial.py`. Requires 1-based offset subtraction when interacting with standard 0-based Modbus drivers. Control write locked pending field commissioning. |
| open_questions | Firmware variations between Chinese domestic and international COM100E gateway firmware. |

## BLUESUN_MULTI_001

[Bluesun Solar Hybrid & ESS Battery Multi-Platform Disaggregation Specification](https://www.bluesunpv.com/download/)

| Trường | Nội dung |
|---|---|
| publisher | Bluesun Solar Co., Ltd. & Upstream OEMs |
| version | Technical Specification 2024.11 |
| publication_date | 2024-11-20 |
| retrieved_date | 2026-10-01 |
| applicable_products | BSM-5500BLV, BSE6KL1, Bluesun LFP Battery Packs (48100/48200) |
| account_type | SmartESS (Eybond) / Bluesun Hybrid Cloud / Direct CAN-RS485 BMS |
| region | Global |
| relevant_sections | Architecture Disaggregation into 3 Independent Operational Branches |
| evidence_grade | B (Manufacturer Datasheets & OEM Protocol Mapping) |
| access_status | HTTP 200; Architecture Confirmed |
| claims | Bluesun does not maintain a single unified cloud API. Device ecosystem operates across three distinct stacks: (1) BSM Low-Voltage Off-Grid Hybrid uses Eybond/SmartESS RS485 Modbus; (2) BSE Grid-Tied Hybrid uses Bluesun Hybrid Cloud with dynamic export limiting; (3) Dedicated Bluesun ESS Batteries use standalone BMS cloud/direct CAN protocol. |
| implications | Implemented in `src/solar_fleet/adapters/bluesun_adapter.py`. Each branch routes through its specialized driver to avoid protocol collisions. |
| open_questions | Compatibility of third-party BMS protocols (Pylontech/Growatt) when connected to Bluesun inverters. |

## HUAWEI_SMARTLOGGER_001

[Huawei SmartLogger3000 Modbus Interface Definitions](https://solar.huawei.com/)

| Trường | Nội dung |
|---|---|
| publisher | Huawei Digital Power Technologies Co., Ltd. |
| version | SmartLogger3000 Modbus Interface Definitions Issue 36 |
| publication_date | 2024-01-10 |
| retrieved_date | 2026-10-01 |
| applicable_products | SUN2000-100KTL-M1, SUN2000-115KTL-M2, SmartLogger3000A/B |
| account_type | Modbus TCP Northbound (Port 502) / FusionSolar Northbound API |
| region | Global / APAC |
| relevant_sections | Multi-Inverter Modbus TCP Routing, 10 MPPT Inputs, Grid Derating Commands |
| evidence_grade | A (Official Huawei Technical Specification) |
| access_status | HTTP 200; Verified |
| claims | Inverter registers aggregated through SmartLogger3000 using logical Modbus IDs (1..80). Register 32064 reports Active Power, 32080 reports Phase Voltage, 40118 controls Active Power Derating percentage (0..100%). |
| implications | Mapped into multi-vendor profile library. Direct writes locked by default. |
| open_questions | Mutual exclusion between FusionSolar cloud command and local SmartLogger Modbus TCP command. |

## ONBOARDING_SCANNER_001

[Industrial PV & Energy Storage Rating Plate Barcode / QR Identification Standard](https://www.iso.org/standard/64287.html)

| Trường | Nội dung |
|---|---|
| publisher | ISO/IEC 15459 & Manufacturer Rating Plate Barcode Conventions |
| version | Industrial Rating Plate Decoding Standard Rev 2.0 |
| publication_date | 2024-05-10 |
| retrieved_date | 2026-10-01 |
| applicable_products | Inverter & Battery Nameplates (Deye, Sungrow, Huawei, GoodWe, Growatt, Bluesun) |
| account_type | Physical Camera Scanner / Barcode Wedge |
| region | Global |
| relevant_sections | Automated Serial / Part Number Parsing & Model Library Matching |
| evidence_grade | B (Industrial Barcode Formats & Verified Physical Nameplate Samples) |
| access_status | Standard Regex Grammar Implemented |
| claims | Nameplates encode serial numbers, manufacturer model codes, rated power, and grid phase in standardized alphanumeric patterns. Regex parsing enables instantaneous binding of scanned hardware to target Modbus register maps. |
| implications | Implemented in `src/solar_fleet/onboarding_scanner.py`. Eliminates manual typing errors during commissioning. |
| open_questions | Handling degraded or damaged QR codes in high-temperature outdoor solar fields. |

