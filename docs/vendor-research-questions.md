# Vendor research questions

Các câu chưa đủ evidence được giữ UNKNOWN và có hành động tiếp theo; không bỏ qua câu hỏi. Mỗi vendor dùng cùng checklist để tránh suy diễn giữa các hãng.

## deye

Nguồn: DEYE_API_001, DEYE_MODEL_001. Xem [matrix](vendor-compatibility-matrix.md) cho chi tiết có nguồn.

| Câu hỏi | Câu trả lời / bước tiếp |
|---|---|
| Cloud architecture | Deye Cloud; xem nguồn theo scope. |
| Logger/gateway | UNKNOWN |
| Roles/organization | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Official API/read/write | API_DOCUMENTED / API_DOCUMENTED |
| Public/partner control | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Local Modbus/read/write | UNKNOWN; command register map chưa được cấp. |
| Cloud/local coexistence | UNKNOWN |
| Realtime interval | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| History resolution | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Rate limits | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Authentication/token expiration | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Discovery/alarms | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| TOU/export/zero export | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Battery/generator/grid | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Bulk/dispatch | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| ACK/readback | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Firmware/region | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Licensing/NDA | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Unsupported features | Không feature UNKNOWN nào được phép ghi production; xem universal-control-mapping. |

## solis

Nguồn: SOLIS_API_001, SOLIS_MODBUS_001, SOLIS_LOCAL_001. Xem [matrix](vendor-compatibility-matrix.md) cho chi tiết có nguồn.

| Câu hỏi | Câu trả lời / bước tiếp |
|---|---|
| Cloud architecture | SolisCloud; xem nguồn theo scope. |
| Logger/gateway | S2-WL-ST (local row only) |
| Roles/organization | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Official API/read/write | MONITORING_PATH / UI_ONLY; MODBUS_CONDITIONAL |
| Public/partner control | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Local Modbus/read/write | MODBUS_TCP_DOCUMENTED; command register map chưa được cấp. |
| Cloud/local coexistence | NO_ON_S2_WL_ST_TCP_MODE |
| Realtime interval | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| History resolution | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Rate limits | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Authentication/token expiration | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Discovery/alarms | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| TOU/export/zero export | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Battery/generator/grid | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Bulk/dispatch | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| ACK/readback | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Firmware/region | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Licensing/NDA | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Unsupported features | Không feature UNKNOWN nào được phép ghi production; xem universal-control-mapping. |

## goodwe

Nguồn: GOODWE_API_001, GOODWE_LOGGER_001, GOODWE_LOGGER_MANUAL_001. Xem [matrix](vendor-compatibility-matrix.md) cho chi tiết có nguồn.

| Câu hỏi | Câu trả lời / bước tiếp |
|---|---|
| Cloud architecture | SEMS; xem nguồn theo scope. |
| Logger/gateway | EzLogger3000C (local row only) |
| Roles/organization | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Official API/read/write | LICENSED_API / LICENSED_API |
| Public/partner control | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Local Modbus/read/write | DOCUMENTED_FORWARDING; command register map chưa được cấp. |
| Cloud/local coexistence | MONITORING_SIMULTANEOUS_EZLOGGER3000C |
| Realtime interval | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| History resolution | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Rate limits | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Authentication/token expiration | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Discovery/alarms | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| TOU/export/zero export | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Battery/generator/grid | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Bulk/dispatch | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| ACK/readback | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Firmware/region | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Licensing/NDA | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Unsupported features | Không feature UNKNOWN nào được phép ghi production; xem universal-control-mapping. |

## sungrow

Nguồn: SUNGROW_OM_001, SUNGROW_LOGGER_001. Xem [matrix](vendor-compatibility-matrix.md) cho chi tiết có nguồn.

| Câu hỏi | Câu trả lời / bước tiếp |
|---|---|
| Cloud architecture | iSolarCloud; xem nguồn theo scope. |
| Logger/gateway | Logger1000A/B |
| Roles/organization | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Official API/read/write | CLOUD_UI; LOCAL_DOCUMENTED / PARTNER_VPP; LOCAL_CONDITIONAL |
| Public/partner control | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Local Modbus/read/write | DOCUMENTED_FORWARDING; command register map chưa được cấp. |
| Cloud/local coexistence | UNKNOWN |
| Realtime interval | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| History resolution | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Rate limits | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Authentication/token expiration | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Discovery/alarms | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| TOU/export/zero export | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Battery/generator/grid | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Bulk/dispatch | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| ACK/readback | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Firmware/region | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Licensing/NDA | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Unsupported features | Không feature UNKNOWN nào được phép ghi production; xem universal-control-mapping. |

## huawei

Nguồn: HUAWEI_AUTH_001, HUAWEI_SCHED_001, HUAWEI_FAQ_001. Xem [matrix](vendor-compatibility-matrix.md) cho chi tiết có nguồn.

| Câu hỏi | Câu trả lời / bước tiếp |
|---|---|
| Cloud architecture | FusionSolar SmartPVMS; xem nguồn theo scope. |
| Logger/gateway | SmartLogger exact model UNKNOWN |
| Roles/organization | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Official API/read/write | NORTHBOUND_DOCUMENTED / SMARTLOGGER_CONDITIONAL |
| Public/partner control | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Local Modbus/read/write | SCHEDULING_DOCUMENTED; command register map chưa được cấp. |
| Cloud/local coexistence | UNKNOWN |
| Realtime interval | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| History resolution | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Rate limits | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Authentication/token expiration | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Discovery/alarms | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| TOU/export/zero export | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Battery/generator/grid | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Bulk/dispatch | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| ACK/readback | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Firmware/region | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Licensing/NDA | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Unsupported features | Không feature UNKNOWN nào được phép ghi production; xem universal-control-mapping. |

## growatt

Nguồn: GROWATT_OSS_001, GROWATT_SETTING_001. Xem [matrix](vendor-compatibility-matrix.md) cho chi tiết có nguồn.

| Câu hỏi | Câu trả lời / bước tiếp |
|---|---|
| Cloud architecture | Shine/OSS; xem nguồn theo scope. |
| Logger/gateway | UNKNOWN |
| Roles/organization | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Official API/read/write | APP_DOCUMENTED / UI_ONLY; API_CONTRACT_UNKNOWN |
| Public/partner control | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Local Modbus/read/write | UNKNOWN; command register map chưa được cấp. |
| Cloud/local coexistence | UNKNOWN |
| Realtime interval | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| History resolution | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Rate limits | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Authentication/token expiration | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Discovery/alarms | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| TOU/export/zero export | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Battery/generator/grid | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Bulk/dispatch | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| ACK/readback | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Firmware/region | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Licensing/NDA | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Unsupported features | Không feature UNKNOWN nào được phép ghi production; xem universal-control-mapping. |

## solarman

Nguồn: SOLARMAN_CONTROL_001, SOLARMAN_LOCAL_001, SOLARMAN_LICENSE_001. Xem [matrix](vendor-compatibility-matrix.md) cho chi tiết có nguồn.

| Câu hỏi | Câu trả lời / bước tiếp |
|---|---|
| Cloud architecture | SOLARMAN platform; xem nguồn theo scope. |
| Logger/gateway | OpenData-enabled model UNKNOWN |
| Roles/organization | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Official API/read/write | LICENSED_CLOUD; CONDITIONAL_LOCAL / OEM_PROTOCOL_AND_PERMISSION_REQUIRED |
| Public/partner control | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Local Modbus/read/write | UNKNOWN; command register map chưa được cấp. |
| Cloud/local coexistence | UNKNOWN |
| Realtime interval | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| History resolution | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Rate limits | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Authentication/token expiration | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Discovery/alarms | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| TOU/export/zero export | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Battery/generator/grid | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Bulk/dispatch | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| ACK/readback | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Firmware/region | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Licensing/NDA | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Unsupported features | Không feature UNKNOWN nào được phép ghi production; xem universal-control-mapping. |

## eybond

Nguồn: EYBOND_GUIDE_001, EYBOND_ESS_001. Xem [matrix](vendor-compatibility-matrix.md) cho chi tiết có nguồn.

| Câu hỏi | Câu trả lời / bước tiếp |
|---|---|
| Cloud architecture | SmartESS; xem nguồn theo scope. |
| Logger/gateway | PN/model UNKNOWN |
| Roles/organization | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Official API/read/write | APP_DOCUMENTED / PUBLIC_PROGRAMMABLE_API_NOT_VERIFIED |
| Public/partner control | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Local Modbus/read/write | UNKNOWN; command register map chưa được cấp. |
| Cloud/local coexistence | UNKNOWN |
| Realtime interval | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| History resolution | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Rate limits | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Authentication/token expiration | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Discovery/alarms | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| TOU/export/zero export | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Battery/generator/grid | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Bulk/dispatch | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| ACK/readback | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Firmware/region | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Licensing/NDA | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Unsupported features | Không feature UNKNOWN nào được phép ghi production; xem universal-control-mapping. |

## bluesun-bsm

Nguồn: BLUESUN_BSM_001. Xem [matrix](vendor-compatibility-matrix.md) cho chi tiết có nguồn.

| Câu hỏi | Câu trả lời / bước tiếp |
|---|---|
| Cloud architecture | SmartESS named in model manual; xem nguồn theo scope. |
| Logger/gateway | UNKNOWN |
| Roles/organization | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Official API/read/write | APP_DOCUMENTED / UNKNOWN |
| Public/partner control | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Local Modbus/read/write | UNKNOWN; command register map chưa được cấp. |
| Cloud/local coexistence | UNKNOWN |
| Realtime interval | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| History resolution | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Rate limits | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Authentication/token expiration | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Discovery/alarms | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| TOU/export/zero export | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Battery/generator/grid | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Bulk/dispatch | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| ACK/readback | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Firmware/region | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Licensing/NDA | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Unsupported features | Không feature UNKNOWN nào được phép ghi production; xem universal-control-mapping. |

## bluesun-bse

Nguồn: BLUESUN_BSE_001. Xem [matrix](vendor-compatibility-matrix.md) cho chi tiết có nguồn.

| Câu hỏi | Câu trả lời / bước tiếp |
|---|---|
| Cloud architecture | Cloud Platform unspecified; xem nguồn theo scope. |
| Logger/gateway | UNKNOWN |
| Roles/organization | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Official API/read/write | TOPOLOGY_ONLY / UNKNOWN |
| Public/partner control | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Local Modbus/read/write | UNKNOWN; command register map chưa được cấp. |
| Cloud/local coexistence | UNKNOWN |
| Realtime interval | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| History resolution | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Rate limits | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Authentication/token expiration | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Discovery/alarms | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| TOU/export/zero export | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Battery/generator/grid | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Bulk/dispatch | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| ACK/readback | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Firmware/region | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Licensing/NDA | UNKNOWN cho cấu hình dự án; cần xác nhận hãng và model/logger/firmware/account trước activation. |
| Unsupported features | Không feature UNKNOWN nào được phép ghi production; xem universal-control-mapping. |
