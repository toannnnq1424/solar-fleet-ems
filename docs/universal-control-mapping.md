# Universal control mapping

Mọi endpoint dưới đây thuộc Deye OpenAPI v1.0. Catalog giữ spelling/enum gốc; `requires_manual_configuration` là bị khóa, chưa sẵn sàng gửi. Evidence: [DEYE_API_001](https://developer.deyecloud.com/openmcp/docs/deye-open-mcp-tools.html), [DEYE_REGISTRY_001](https://developer.deyecloud.com/openmcp/mcp), [DEYE_MODEL_001](https://hqcdn.hqsmartcloud.com/deyeinverter/2026/01/04/InstallationManual-SUN-5-12K-SG04LP3-AU.pdf).

| Intent | Deye candidate | Semantic match hiện tại | Khác biệt / điều kiện |
|---|---|---|---|
| SET_WORK_MODE | order/sys/workMode/update; workMode | requires_manual_configuration | Mode enum phải thuộc product family; không trộn limitControlFunctionType. |
| SET_SELF_CONSUMPTION | UNKNOWN | requires_manual_configuration | Cần định nghĩa mục tiêu PV/battery/grid ưu tiên; không đồng nghĩa LOAD_FIRST. |
| SET_EXPORT_LIMIT | order/sys/power/update; MAX_SELL_POWER | requires_manual_configuration | Soft limit phụ thuộc work mode; không bảo đảm hard cap. |
| SET_ZERO_EXPORT | workMode + solarSell + CT/meter | requires_manual_configuration | Phải xác minh solar sell, CT/polarity, scope và hard/soft semantics; không chỉ đổi một enum. |
| SET_GRID_IMPORT_LIMIT | UNKNOWN | unsupported | Chưa có mapping typed chính thức đủ để triển khai; cần model/protocol evidence. |
| SET_RESERVE_SOC | UNKNOWN | unsupported | Không map sang BATT_LOW hoặc TOU SOC. |
| SET_MIN_SOC | UNKNOWN | requires_manual_configuration | BATT_LOW chỉ là ứng viên, không chứng minh minimum SOC ở mọi mode. |
| SET_SHUTDOWN_SOC | Read: battShutDownCapacity; write UNKNOWN | unsupported | Đọc được không chứng minh có typed write. |
| SET_RESTART_SOC | UNKNOWN | unsupported | Chưa có mapping typed chính thức đủ để triển khai; cần model/protocol evidence. |
| SET_MAX_CHARGE_CURRENT | order/battery/parameter/update; MAX_CHARGE_CURRENT | requires_manual_configuration | A; readback maxChargeCurrent; range/BMS constraints theo device. |
| SET_MAX_DISCHARGE_CURRENT | order/battery/parameter/update; MAX_DISCHARGE_CURRENT | requires_manual_configuration | A; readback maxDischargeCurrent; range/BMS constraints theo device. |
| SET_MAX_CHARGE_POWER | UNKNOWN | unsupported | Chưa có mapping typed chính thức đủ để triển khai; cần model/protocol evidence. |
| SET_MAX_DISCHARGE_POWER | UNKNOWN | unsupported | Chưa có mapping typed chính thức đủ để triển khai; cần model/protocol evidence. |
| ENABLE_GRID_CHARGE | order/battery/modeControl; GRID_CHARGE/on | requires_manual_configuration | Phân biệt enable chung và enableGridCharge từng TOU slot. |
| DISABLE_GRID_CHARGE | order/battery/modeControl; GRID_CHARGE/off | requires_manual_configuration | Cần đọc lại action; không suy ra off từ batteryPower = 0. |
| SET_TOU | order/sys/tou/update; timeUseSettingItems | requires_manual_configuration | Sáu mốc theo thứ tự; giờ local/timezone; power/SOC/voltage theo profile; preserve toàn bộ slot. |
| ENABLE_TOU | order/sys/tou/switch; action=on + days | requires_manual_configuration | Ghi schedule location stored_on_inverter; ngày phải rõ. |
| DISABLE_TOU | order/sys/tou/switch; action=off | requires_manual_configuration | Readback touAction; không xóa slot tự động. |
| FORCE_CHARGE | UNKNOWN | unsupported | Chưa có mapping typed chính thức đủ để triển khai; cần model/protocol evidence. |
| FORCE_DISCHARGE | UNKNOWN | unsupported | Chưa có mapping typed chính thức đủ để triển khai; cần model/protocol evidence. |
| STOP_FORCE_OPERATION | UNKNOWN | unsupported | Chưa có mapping typed chính thức đủ để triển khai; cần model/protocol evidence. |
| SET_PEAK_SHAVING | order/gridPeakShaving/control | requires_manual_configuration | Schema power required nhưng mô tả nói optional; ưu tiên required, cần readback và range. |
| SET_ACTIVE_POWER_LIMIT | UNKNOWN | unsupported | Chưa có mapping typed chính thức đủ để triển khai; cần model/protocol evidence. |
| SET_REACTIVE_POWER | UNKNOWN | unsupported | Chưa có mapping typed chính thức đủ để triển khai; cần model/protocol evidence. |
| SET_POWER_FACTOR | UNKNOWN | unsupported | Chưa có mapping typed chính thức đủ để triển khai; cần model/protocol evidence. |
| SET_BACKUP_EPS | UNKNOWN | unsupported | Chưa có mapping typed chính thức đủ để triển khai; cần model/protocol evidence. |
| SET_SMART_LOAD | order/smartload/update | requires_manual_configuration | Giữ Vendor Native; ngưỡng và readback freshness chưa xác minh. |
| SET_GENERATOR_POLICY | GEN_CHARGE là một phần | requires_manual_configuration | Không suy ra start/stop/capacity/meter policy từ enable charge. |
| SET_GENERATOR_METER | UNKNOWN | unsupported | Chưa có mapping typed chính thức đủ để triển khai; cần model/protocol evidence. |
| SET_METER | UNKNOWN | unsupported | Chưa có mapping typed chính thức đủ để triển khai; cần model/protocol evidence. |
| SET_CT_RATIO | UNKNOWN | unsupported | Chưa có mapping typed chính thức đủ để triển khai; cần model/protocol evidence. |
| POWER_ON_INVERTER | UNKNOWN | unsupported | Chưa có mapping typed chính thức đủ để triển khai; cần model/protocol evidence. |
| POWER_OFF_INVERTER | UNKNOWN | unsupported | Chưa có mapping typed chính thức đủ để triển khai; cần model/protocol evidence. |
| RESTART_INVERTER | UNKNOWN | unsupported | Chưa có mapping typed chính thức đủ để triển khai; cần model/protocol evidence. |

## Ma trận các hãng còn lại

Bảng sau liệt kê mọi intent và trạng thái từng hãng. `UNKNOWN` nghĩa chưa có command-level schema + model/firmware/readback, không có nghĩa hãng chắc chắn không hỗ trợ. SOLARMAN là transport cần OEM mapping. Dẫn chứng phạm vi nằm trong compatibility/source audit.

| Intent | Solis | GoodWe | Sungrow | Huawei | Growatt | SOLARMAN | Eybond | Bluesun |
|---|---|---|---|---|---|---|---|---|
| SET_WORK_MODE | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| SET_SELF_CONSUMPTION | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| SET_EXPORT_LIMIT | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| SET_ZERO_EXPORT | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| SET_GRID_IMPORT_LIMIT | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| SET_RESERVE_SOC | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| SET_MIN_SOC | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| SET_SHUTDOWN_SOC | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| SET_RESTART_SOC | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| SET_MAX_CHARGE_CURRENT | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| SET_MAX_DISCHARGE_CURRENT | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| SET_MAX_CHARGE_POWER | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| SET_MAX_DISCHARGE_POWER | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| ENABLE_GRID_CHARGE | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| DISABLE_GRID_CHARGE | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| SET_TOU | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| ENABLE_TOU | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| DISABLE_TOU | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| FORCE_CHARGE | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| FORCE_DISCHARGE | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| STOP_FORCE_OPERATION | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| SET_PEAK_SHAVING | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| SET_ACTIVE_POWER_LIMIT | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| SET_REACTIVE_POWER | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| SET_POWER_FACTOR | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| SET_BACKUP_EPS | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| SET_SMART_LOAD | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| SET_GENERATOR_POLICY | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| SET_GENERATOR_METER | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| SET_METER | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| SET_CT_RATIO | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| POWER_ON_INVERTER | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| POWER_OFF_INVERTER | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| RESTART_INVERTER | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |

Không dùng bảng UI chức năng để thay thế contract. Solis: SOLIS_MODBUS_001. GoodWe: GOODWE_API_001. Sungrow: SUNGROW_OM_001/SUNGROW_LOGGER_001. Huawei: HUAWEI_SCHED_001. Growatt: GROWATT_SETTING_001. SOLARMAN: SOLARMAN_CONTROL_001. Eybond: EYBOND_ESS_001. Bluesun: hai profile tách biệt BLUESUN_BSM_001/BLUESUN_BSE_001.

## Dispatch

`battery_power_target_w`, `grid_power_target_w`, `active_power_target_w`, `reactive_power_target_var`, `pv_power_limit_w` thuộc contract dispatch riêng với deadline/TTL/ramp/priority. Chưa có binding production cho các intent này. Dynamic configuration không được coi là bộ điều khiển mỗi giây.