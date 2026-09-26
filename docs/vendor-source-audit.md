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
