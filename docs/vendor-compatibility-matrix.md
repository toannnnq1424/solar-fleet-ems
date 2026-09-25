# Vendor compatibility matrix

> **Research baseline, not current implementation or hardware acceptance.** Current code has eight cloud read paths plus Bluesun profiles; see [multi-vendor contracts](multivendor-contracts.md), [implementation status](implementation-status.md) and [Eybond's later integration](eybond-read-integration.md). The [source registry](evidence/source-registry.json) has 57 unique records, including withdrawn claims. The per-vendor rows below retain the original research applicability and UNKNOWN device facts; adding a transport does not establish exact model support. [Documentation index](README.md).

Mỗi block là một row đầy đủ, trình bày dọc để đọc được trên màn hình. Không có `yes` không nguồn. “DOCUMENTED” chỉ xác nhận đường giao tiếp, không chứng nhận thiết bị. Các nhóm còn lại có mapping chi tiết riêng.

## deye

| Thuộc tính | Giá trị |
|---|---|
| vendor | deye |
| ecosystem | Deye Cloud |
| inverter_model | UNKNOWN |
| logger_model | UNKNOWN |
| battery | UNKNOWN |
| firmware | UNKNOWN |
| app | UNKNOWN |
| web | UNKNOWN |
| owner_account | UNKNOWN |
| installer_account | UNKNOWN |
| organization_account | UNKNOWN |
| official_api | UNKNOWN |
| api_authentication | UNKNOWN |
| telemetry | API_DOCUMENTED |
| history | UNKNOWN |
| alarms | UNKNOWN |
| remote_config | UNKNOWN |
| remote_control | API_DOCUMENTED |
| dispatch | UNKNOWN |
| modbus_tcp | UNKNOWN |
| modbus_rtu | UNKNOWN |
| iec104 | UNKNOWN |
| cloud_local_simultaneous | UNKNOWN |
| tou | UNKNOWN |
| zero_export | UNKNOWN |
| export_limit | UNKNOWN |
| battery_reserve_soc | UNKNOWN |
| grid_charge | UNKNOWN |
| force_charge | UNKNOWN |
| force_discharge | UNKNOWN |
| peak_shaving | UNKNOWN |
| active_power | UNKNOWN |
| reactive_power | UNKNOWN |
| generator | UNKNOWN |
| meter_ct | UNKNOWN |
| grid_protection | UNKNOWN |
| readback_support | UNKNOWN |
| source_links | [DEYE_API_001](https://developer.deyecloud.com/openmcp/docs/deye-open-mcp-tools.html); [DEYE_MODEL_001](https://hqcdn.hqsmartcloud.com/deyeinverter/2026/01/04/InstallationManual-SUN-5-12K-SG04LP3-AU.pdf) |
| evidence_grade | See individual source IDs |
| known_limitations | No customer model/firmware/account validation. Not production Supported. Unspecified cells deliberately UNKNOWN. |

## solis

| Thuộc tính | Giá trị |
|---|---|
| vendor | solis |
| ecosystem | SolisCloud |
| inverter_model | Hybrid; exact model UNKNOWN |
| logger_model | S2-WL-ST (local row only) |
| battery | UNKNOWN |
| firmware | UNKNOWN |
| app | UNKNOWN |
| web | UNKNOWN |
| owner_account | UNKNOWN |
| installer_account | UNKNOWN |
| organization_account | UNKNOWN |
| official_api | UNKNOWN |
| api_authentication | UNKNOWN |
| telemetry | MONITORING_PATH |
| history | UNKNOWN |
| alarms | UNKNOWN |
| remote_config | UNKNOWN |
| remote_control | UI_ONLY; MODBUS_CONDITIONAL |
| dispatch | UNKNOWN |
| modbus_tcp | MODBUS_TCP_DOCUMENTED |
| modbus_rtu | UNKNOWN |
| iec104 | UNKNOWN |
| cloud_local_simultaneous | NO_ON_S2_WL_ST_TCP_MODE |
| tou | UNKNOWN |
| zero_export | UNKNOWN |
| export_limit | UNKNOWN |
| battery_reserve_soc | UNKNOWN |
| grid_charge | UNKNOWN |
| force_charge | UNKNOWN |
| force_discharge | UNKNOWN |
| peak_shaving | UNKNOWN |
| active_power | UNKNOWN |
| reactive_power | UNKNOWN |
| generator | UNKNOWN |
| meter_ct | UNKNOWN |
| grid_protection | UNKNOWN |
| readback_support | UNKNOWN |
| source_links | [SOLIS_API_001](https://solis-service.solisinverters.com/en/support/solutions/articles/44002212561-request-api-access-soliscloud); [SOLIS_MODBUS_001](https://solis-service.solisinverters.com/en/support/solutions/articles/44002663852-non-nda-modus-table); [SOLIS_LOCAL_001](https://solis-service.solisinverters.com/en/support/solutions/articles/44002530087-solis-s2-wl-st-modbus-tcp-communication) |
| evidence_grade | See individual source IDs |
| known_limitations | No customer model/firmware/account validation. Not production Supported. Unspecified cells deliberately UNKNOWN. |

## goodwe

| Thuộc tính | Giá trị |
|---|---|
| vendor | goodwe |
| ecosystem | SEMS |
| inverter_model | UNKNOWN |
| logger_model | EzLogger3000C (local row only) |
| battery | UNKNOWN |
| firmware | UNKNOWN |
| app | UNKNOWN |
| web | UNKNOWN |
| owner_account | UNKNOWN |
| installer_account | UNKNOWN |
| organization_account | UNKNOWN |
| official_api | UNKNOWN |
| api_authentication | UNKNOWN |
| telemetry | LICENSED_API |
| history | UNKNOWN |
| alarms | UNKNOWN |
| remote_config | UNKNOWN |
| remote_control | LICENSED_API |
| dispatch | UNKNOWN |
| modbus_tcp | DOCUMENTED_FORWARDING |
| modbus_rtu | UNKNOWN |
| iec104 | DOCUMENTED_FORWARDING |
| cloud_local_simultaneous | MONITORING_SIMULTANEOUS_EZLOGGER3000C |
| tou | UNKNOWN |
| zero_export | UNKNOWN |
| export_limit | UNKNOWN |
| battery_reserve_soc | UNKNOWN |
| grid_charge | UNKNOWN |
| force_charge | UNKNOWN |
| force_discharge | UNKNOWN |
| peak_shaving | UNKNOWN |
| active_power | UNKNOWN |
| reactive_power | UNKNOWN |
| generator | UNKNOWN |
| meter_ct | UNKNOWN |
| grid_protection | UNKNOWN |
| readback_support | UNKNOWN |
| source_links | [GOODWE_API_001](https://community.goodwe.com/static/images/2024-08-20597794.pdf); [GOODWE_LOGGER_001](https://en.goodwe.com/ezlogger3000c); [GOODWE_LOGGER_MANUAL_001](https://en.goodwe.com/Skippower/downloadFileF?id=1944&mid=60) |
| evidence_grade | See individual source IDs |
| known_limitations | No customer model/firmware/account validation. Not production Supported. Unspecified cells deliberately UNKNOWN. |

## sungrow

| Thuộc tính | Giá trị |
|---|---|
| vendor | sungrow |
| ecosystem | iSolarCloud |
| inverter_model | UNKNOWN |
| logger_model | Logger1000A/B |
| battery | UNKNOWN |
| firmware | UNKNOWN |
| app | UNKNOWN |
| web | UNKNOWN |
| owner_account | UNKNOWN |
| installer_account | UNKNOWN |
| organization_account | UNKNOWN |
| official_api | UNKNOWN |
| api_authentication | UNKNOWN |
| telemetry | CLOUD_UI; LOCAL_DOCUMENTED |
| history | UNKNOWN |
| alarms | UNKNOWN |
| remote_config | UNKNOWN |
| remote_control | PARTNER_VPP; LOCAL_CONDITIONAL |
| dispatch | UNKNOWN |
| modbus_tcp | DOCUMENTED_FORWARDING |
| modbus_rtu | UNKNOWN |
| iec104 | DOCUMENTED_FORWARDING |
| cloud_local_simultaneous | UNKNOWN |
| tou | UNKNOWN |
| zero_export | UNKNOWN |
| export_limit | UNKNOWN |
| battery_reserve_soc | UNKNOWN |
| grid_charge | UNKNOWN |
| force_charge | UNKNOWN |
| force_discharge | UNKNOWN |
| peak_shaving | UNKNOWN |
| active_power | UNKNOWN |
| reactive_power | UNKNOWN |
| generator | UNKNOWN |
| meter_ct | UNKNOWN |
| grid_protection | UNKNOWN |
| readback_support | UNKNOWN |
| source_links | [SUNGROW_OM_001](https://info-support.sungrowpower.com/product-materials/8cc7a6f7-36ff-4489-b9af-15546dc42ca2.pdf); [SUNGROW_LOGGER_001](https://info-support.sungrowpower.com/application/pdf/2023/03/10/Logger1000A_B-UEN-Ver110-202301.pdf) |
| evidence_grade | See individual source IDs |
| known_limitations | No customer model/firmware/account validation. Not production Supported. Unspecified cells deliberately UNKNOWN. |

## huawei

| Thuộc tính | Giá trị |
|---|---|
| vendor | huawei |
| ecosystem | FusionSolar SmartPVMS |
| inverter_model | UNKNOWN |
| logger_model | SmartLogger exact model UNKNOWN |
| battery | UNKNOWN |
| firmware | UNKNOWN |
| app | UNKNOWN |
| web | UNKNOWN |
| owner_account | UNKNOWN |
| installer_account | UNKNOWN |
| organization_account | UNKNOWN |
| official_api | UNKNOWN |
| api_authentication | UNKNOWN |
| telemetry | NORTHBOUND_DOCUMENTED |
| history | UNKNOWN |
| alarms | UNKNOWN |
| remote_config | UNKNOWN |
| remote_control | SMARTLOGGER_CONDITIONAL |
| dispatch | UNKNOWN |
| modbus_tcp | SCHEDULING_DOCUMENTED |
| modbus_rtu | UNKNOWN |
| iec104 | SCHEDULING_DOCUMENTED |
| cloud_local_simultaneous | UNKNOWN |
| tou | UNKNOWN |
| zero_export | UNKNOWN |
| export_limit | UNKNOWN |
| battery_reserve_soc | UNKNOWN |
| grid_charge | UNKNOWN |
| force_charge | UNKNOWN |
| force_discharge | UNKNOWN |
| peak_shaving | UNKNOWN |
| active_power | UNKNOWN |
| reactive_power | UNKNOWN |
| generator | UNKNOWN |
| meter_ct | UNKNOWN |
| grid_protection | UNKNOWN |
| readback_support | UNKNOWN |
| source_links | [HUAWEI_AUTH_001](https://info.support.huawei.com/enterprise/en/doc/EDOC1100307213/9e1a18d2/login-interface); [HUAWEI_SCHED_001](https://info.support.huawei.com/DpinfoAppDoc/pro_erp_slice001/doc/fusion_solar/public/commercial_energy/en/en-us_topic_0000002205688713.html); [HUAWEI_FAQ_001](https://info.support.huawei.com/DpinfoAppDoc/pro_erp_slice001/doc/fusion_solar/faq/installer/en/en-us_topic_0000001867081537.html?styleType=white) |
| evidence_grade | See individual source IDs |
| known_limitations | No customer model/firmware/account validation. Not production Supported. Unspecified cells deliberately UNKNOWN. |

## growatt

| Thuộc tính | Giá trị |
|---|---|
| vendor | growatt |
| ecosystem | Shine/OSS |
| inverter_model | UNKNOWN |
| logger_model | UNKNOWN |
| battery | UNKNOWN |
| firmware | UNKNOWN |
| app | UNKNOWN |
| web | UNKNOWN |
| owner_account | UNKNOWN |
| installer_account | UNKNOWN |
| organization_account | UNKNOWN |
| official_api | UNKNOWN |
| api_authentication | UNKNOWN |
| telemetry | APP_DOCUMENTED |
| history | UNKNOWN |
| alarms | UNKNOWN |
| remote_config | UNKNOWN |
| remote_control | UI_ONLY; API_CONTRACT_UNKNOWN |
| dispatch | UNKNOWN |
| modbus_tcp | UNKNOWN |
| modbus_rtu | UNKNOWN |
| iec104 | UNKNOWN |
| cloud_local_simultaneous | UNKNOWN |
| tou | UNKNOWN |
| zero_export | UNKNOWN |
| export_limit | UNKNOWN |
| battery_reserve_soc | UNKNOWN |
| grid_charge | UNKNOWN |
| force_charge | UNKNOWN |
| force_discharge | UNKNOWN |
| peak_shaving | UNKNOWN |
| active_power | UNKNOWN |
| reactive_power | UNKNOWN |
| generator | UNKNOWN |
| meter_ct | UNKNOWN |
| grid_protection | UNKNOWN |
| readback_support | UNKNOWN |
| source_links | [GROWATT_OSS_001](https://vn.growatt.com/support/faq/monitoring); [GROWATT_SETTING_001](https://openapi.growatt.com/commonDeviceSetC/setTlx?type=server) |
| evidence_grade | See individual source IDs |
| known_limitations | No customer model/firmware/account validation. Not production Supported. Unspecified cells deliberately UNKNOWN. |

## solarman

| Thuộc tính | Giá trị |
|---|---|
| vendor | solarman |
| ecosystem | SOLARMAN platform |
| inverter_model | OEM/model UNKNOWN |
| logger_model | OpenData-enabled model UNKNOWN |
| battery | UNKNOWN |
| firmware | UNKNOWN |
| app | UNKNOWN |
| web | UNKNOWN |
| owner_account | UNKNOWN |
| installer_account | UNKNOWN |
| organization_account | UNKNOWN |
| official_api | UNKNOWN |
| api_authentication | UNKNOWN |
| telemetry | LICENSED_CLOUD; CONDITIONAL_LOCAL |
| history | UNKNOWN |
| alarms | UNKNOWN |
| remote_config | UNKNOWN |
| remote_control | OEM_PROTOCOL_AND_PERMISSION_REQUIRED |
| dispatch | UNKNOWN |
| modbus_tcp | UNKNOWN |
| modbus_rtu | UNKNOWN |
| iec104 | UNKNOWN |
| cloud_local_simultaneous | UNKNOWN |
| tou | UNKNOWN |
| zero_export | UNKNOWN |
| export_limit | UNKNOWN |
| battery_reserve_soc | UNKNOWN |
| grid_charge | UNKNOWN |
| force_charge | UNKNOWN |
| force_discharge | UNKNOWN |
| peak_shaving | UNKNOWN |
| active_power | UNKNOWN |
| reactive_power | UNKNOWN |
| generator | UNKNOWN |
| meter_ct | UNKNOWN |
| grid_protection | UNKNOWN |
| readback_support | UNKNOWN |
| source_links | [SOLARMAN_CONTROL_001](https://helpcenter.solarmanpv.com/portal/en/kb/articles/how-to-control-inverter-via-api); [SOLARMAN_LOCAL_001](https://docs.solarman.ai/docs/api/opendata/); [SOLARMAN_LICENSE_001](https://helpcenter.solarmanpv.com/portal/en/kb/articles/i-want-to-open-api-how-can-i-open-api) |
| evidence_grade | See individual source IDs |
| known_limitations | No customer model/firmware/account validation. Not production Supported. Unspecified cells deliberately UNKNOWN. |

## eybond

| Thuộc tính | Giá trị |
|---|---|
| vendor | eybond |
| ecosystem | SmartESS |
| inverter_model | OEM/model UNKNOWN |
| logger_model | PN/model UNKNOWN |
| battery | UNKNOWN |
| firmware | UNKNOWN |
| app | UNKNOWN |
| web | UNKNOWN |
| owner_account | UNKNOWN |
| installer_account | UNKNOWN |
| organization_account | UNKNOWN |
| official_api | UNKNOWN |
| api_authentication | UNKNOWN |
| telemetry | APP_DOCUMENTED |
| history | UNKNOWN |
| alarms | UNKNOWN |
| remote_config | UNKNOWN |
| remote_control | PUBLIC_PROGRAMMABLE_API_NOT_VERIFIED |
| dispatch | UNKNOWN |
| modbus_tcp | UNKNOWN |
| modbus_rtu | UNKNOWN |
| iec104 | UNKNOWN |
| cloud_local_simultaneous | UNKNOWN |
| tou | UNKNOWN |
| zero_export | UNKNOWN |
| export_limit | UNKNOWN |
| battery_reserve_soc | UNKNOWN |
| grid_charge | UNKNOWN |
| force_charge | UNKNOWN |
| force_discharge | UNKNOWN |
| peak_shaving | UNKNOWN |
| active_power | UNKNOWN |
| reactive_power | UNKNOWN |
| generator | UNKNOWN |
| meter_ct | UNKNOWN |
| grid_protection | UNKNOWN |
| readback_support | UNKNOWN |
| source_links | [EYBOND_GUIDE_001](https://fms.eybond.com/fms/api/auth/web/doc/html/previewOnline/72/2); [EYBOND_ESS_001](https://www.eybond.com/Household.html) |
| evidence_grade | See individual source IDs |
| known_limitations | No customer model/firmware/account validation. Not production Supported. Unspecified cells deliberately UNKNOWN. |

## bluesun-bsm

| Thuộc tính | Giá trị |
|---|---|
| vendor | bluesun-bsm |
| ecosystem | SmartESS named in model manual |
| inverter_model | BSM-5500BLV-48DA |
| logger_model | UNKNOWN |
| battery | UNKNOWN |
| firmware | UNKNOWN |
| app | UNKNOWN |
| web | UNKNOWN |
| owner_account | UNKNOWN |
| installer_account | UNKNOWN |
| organization_account | UNKNOWN |
| official_api | UNKNOWN |
| api_authentication | UNKNOWN |
| telemetry | APP_DOCUMENTED |
| history | UNKNOWN |
| alarms | UNKNOWN |
| remote_config | UNKNOWN |
| remote_control | UNKNOWN |
| dispatch | UNKNOWN |
| modbus_tcp | UNKNOWN |
| modbus_rtu | UNKNOWN |
| iec104 | UNKNOWN |
| cloud_local_simultaneous | UNKNOWN |
| tou | UNKNOWN |
| zero_export | UNKNOWN |
| export_limit | UNKNOWN |
| battery_reserve_soc | UNKNOWN |
| grid_charge | UNKNOWN |
| force_charge | UNKNOWN |
| force_discharge | UNKNOWN |
| peak_shaving | UNKNOWN |
| active_power | UNKNOWN |
| reactive_power | UNKNOWN |
| generator | UNKNOWN |
| meter_ct | UNKNOWN |
| grid_protection | UNKNOWN |
| readback_support | UNKNOWN |
| source_links | [BLUESUN_BSM_001](https://www.bluesunpv.com/wp-content/uploads/2024/11/BSM-5500BLV-48DA-User-Manual-V2.0.pdf) |
| evidence_grade | See individual source IDs |
| known_limitations | No customer model/firmware/account validation. Not production Supported. Unspecified cells deliberately UNKNOWN. |

## bluesun-bse

| Thuộc tính | Giá trị |
|---|---|
| vendor | bluesun-bse |
| ecosystem | Cloud Platform unspecified |
| inverter_model | BSE6KL1 |
| logger_model | UNKNOWN |
| battery | UNKNOWN |
| firmware | UNKNOWN |
| app | UNKNOWN |
| web | UNKNOWN |
| owner_account | UNKNOWN |
| installer_account | UNKNOWN |
| organization_account | UNKNOWN |
| official_api | UNKNOWN |
| api_authentication | UNKNOWN |
| telemetry | TOPOLOGY_ONLY |
| history | UNKNOWN |
| alarms | UNKNOWN |
| remote_config | UNKNOWN |
| remote_control | UNKNOWN |
| dispatch | UNKNOWN |
| modbus_tcp | UNKNOWN |
| modbus_rtu | UNKNOWN |
| iec104 | UNKNOWN |
| cloud_local_simultaneous | UNKNOWN |
| tou | UNKNOWN |
| zero_export | UNKNOWN |
| export_limit | UNKNOWN |
| battery_reserve_soc | UNKNOWN |
| grid_charge | UNKNOWN |
| force_charge | UNKNOWN |
| force_discharge | UNKNOWN |
| peak_shaving | UNKNOWN |
| active_power | UNKNOWN |
| reactive_power | UNKNOWN |
| generator | UNKNOWN |
| meter_ct | UNKNOWN |
| grid_protection | UNKNOWN |
| readback_support | UNKNOWN |
| source_links | [BLUESUN_BSE_001](https://www.bluesunpv.com/wp-content/uploads/2024/11/ESS_BSE6KL1_EN_v2406_Rev-01.pdf) |
| evidence_grade | See individual source IDs |
| known_limitations | No customer model/firmware/account validation. Not production Supported. Unspecified cells deliberately UNKNOWN. |
