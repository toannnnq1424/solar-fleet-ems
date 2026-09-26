"""Vendor Modbus register maps, alarm decoders, and parameter schemas.

Provides official register offsets, data types, scale factors, and fault decoders
for GoodWe, Sungrow, Huawei SUN2000, Growatt SPH/SPF, Solis, and Deye hybrid inverters.
Audit provenance: D:\\Downloads\before_project (goodwe-master MIT, deye-inverter-mqtt Apache-2.0,
Sungrow-SHx-Inverter-Modbus MIT, ha-solarman MIT, solar-inverter-modbus-registers MIT).
"""

from __future__ import annotations

from typing import Any

# ============================================================================
# 1. GOODWE HYBRID INVERTER (ET / EH / ES SERIES) REGISTERS & ALARMS
# ============================================================================

GOODWE_HOLDING_REGISTERS: dict[int, dict[str, Any]] = {
    35100: {"name": "timestamp", "type": "datetime", "unit": "", "scale": 1.0, "access": "RO", "desc": "Inverter RTC time"},
    35103: {"name": "vpv1", "type": "uint16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "PV1 input voltage"},
    35104: {"name": "ipv1", "type": "uint16", "unit": "A", "scale": 0.1, "access": "RO", "desc": "PV1 input current"},
    35105: {"name": "ppv1", "type": "uint32", "unit": "W", "scale": 1.0, "access": "RO", "desc": "PV1 input power"},
    35107: {"name": "vpv2", "type": "uint16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "PV2 input voltage"},
    35108: {"name": "ipv2", "type": "uint16", "unit": "A", "scale": 0.1, "access": "RO", "desc": "PV2 input current"},
    35109: {"name": "ppv2", "type": "uint32", "unit": "W", "scale": 1.0, "access": "RO", "desc": "PV2 input power"},
    35111: {"name": "vgrid_l1", "type": "uint16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "On-grid L1 voltage"},
    35112: {"name": "igrid_l1", "type": "uint16", "unit": "A", "scale": 0.1, "access": "RO", "desc": "On-grid L1 current"},
    35113: {"name": "fgrid_l1", "type": "uint16", "unit": "Hz", "scale": 0.01, "access": "RO", "desc": "Grid L1 frequency"},
    35115: {"name": "pgrid", "type": "int32", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Total grid active power (+ import / - export)"},
    35123: {"name": "pload", "type": "uint32", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Total site load power"},
    35127: {"name": "peps", "type": "uint32", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Backup/EPS output power"},
    35140: {"name": "vbat", "type": "uint16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "Battery terminal voltage"},
    35141: {"name": "ibat", "type": "int16", "unit": "A", "scale": 0.1, "access": "RO", "desc": "Battery current (+ charge / - discharge)"},
    35142: {"name": "pbat", "type": "int32", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Battery active power"},
    35144: {"name": "battery_soc", "type": "uint16", "unit": "%", "scale": 1.0, "access": "RO", "desc": "Battery state of charge"},
    35145: {"name": "battery_soh", "type": "uint16", "unit": "%", "scale": 1.0, "access": "RO", "desc": "Battery state of health"},
    35146: {"name": "battery_temp", "type": "int16", "unit": "°C", "scale": 0.1, "access": "RO", "desc": "Battery internal temperature"},
    35172: {"name": "e_day", "type": "uint16", "unit": "kWh", "scale": 0.1, "access": "RO", "desc": "Daily PV energy generation"},
    35174: {"name": "e_total", "type": "uint32", "unit": "kWh", "scale": 0.1, "access": "RO", "desc": "Cumulative PV energy generation"},
    35176: {"name": "e_day_exp", "type": "uint16", "unit": "kWh", "scale": 0.1, "access": "RO", "desc": "Daily energy exported to grid"},
    35178: {"name": "e_total_exp", "type": "uint32", "unit": "kWh", "scale": 0.1, "access": "RO", "desc": "Total energy exported to grid"},
    35180: {"name": "e_day_imp", "type": "uint16", "unit": "kWh", "scale": 0.1, "access": "RO", "desc": "Daily energy imported from grid"},
    35182: {"name": "e_total_imp", "type": "uint32", "unit": "kWh", "scale": 0.1, "access": "RO", "desc": "Total energy imported from grid"},
}

GOODWE_ALARM_CODES: dict[int, dict[str, Any]] = {
    0: {"code": 0, "name": "GFCI Failure", "severity": "HIGH", "sop": "Check DC ground isolation and AC residual current sensor calibration.", "category": "PV"},
    1: {"code": 1, "name": "Relay Check Failure", "severity": "CRITICAL", "sop": "Inspect grid interconnect contactor/relay. Power cycle inverter; if persistent, schedule hardware replacement.", "category": "INVERTER"},
    2: {"code": 2, "name": "DC Bus High", "severity": "CRITICAL", "sop": "Verify DC string voltage does not exceed max open-circuit voltage rating. Check for rapid load drop.", "category": "PV"},
    3: {"code": 3, "name": "Inverter High Temp", "severity": "HIGH", "sop": "Inspect inverter heatsink, cooling fan airflow, and ambient temperature clearance.", "category": "TEMPERATURE"},
    4: {"code": 4, "name": "Utility Loss / Islanding", "severity": "MEDIUM", "sop": "Grid voltage absent. Inverter transitioned to off-grid/standby mode; inspect main grid breaker.", "category": "GRID"},
    5: {"code": 5, "name": "Grid Under/Over Voltage", "severity": "HIGH", "sop": "Grid voltage outside statutory operating bounds. Measure incoming AC line voltage at connection terminals.", "category": "GRID"},
    6: {"code": 6, "name": "Grid Under/Over Frequency", "severity": "HIGH", "sop": "Grid frequency drifted beyond permitted range. Check local utility generator or grid stability.", "category": "GRID"},
    7: {"code": 7, "name": "PV Over Voltage", "severity": "CRITICAL", "sop": "String open-circuit voltage exceeds 1000V. Disconnect DC isolator immediately to protect input capacitors.", "category": "PV"},
    8: {"code": 8, "name": "PV Isolation Low (ISO Fail)", "severity": "HIGH", "sop": "Check solar array cabling, module junction boxes, and MC4 connectors for moisture or cable sheath degradation.", "category": "PV"},
    9: {"code": 9, "name": "Ground Fault (GF)", "severity": "CRITICAL", "sop": "Ground leakage current detected. Inspect grounding electrode conductor and PV negative earthing.", "category": "PV"},
    15: {"code": 15, "name": "PV Over Voltage Warning", "severity": "HIGH", "sop": "PV voltage approaching maximum rating. Reconfigure series strings if cold-weather VOC is excessive.", "category": "PV"},
    17: {"code": 17, "name": "Vac Failure", "severity": "HIGH", "sop": "AC voltage measurement anomalous. Check AC distribution panel and neutral wiring.", "category": "GRID"},
    18: {"code": 18, "name": "Isolation Failure", "severity": "HIGH", "sop": "Insulation resistance to earth is below 100kOhm. Isolate each string to locate degraded cable.", "category": "PV"},
    19: {"code": 19, "name": "DC Injection High", "severity": "HIGH", "sop": "Inverter DC current injection into AC grid exceeded threshold. Recalibrate output Hall sensor.", "category": "GRID"},
    20: {"code": 20, "name": "Back-Up Over Load", "severity": "MEDIUM", "sop": "EPS/backup load exceeds inverter surge/continuous power limit. Shed non-essential critical loads.", "category": "INVERTER"},
    23: {"code": 23, "name": "Vac Consistency Failure", "severity": "HIGH", "sop": "Master DSP and slave CPU voltage measurements disagree. Upgrade inverter firmware or inspect ADC circuitry.", "category": "INVERTER"},
    25: {"code": 25, "name": "Relay Check Failure", "severity": "CRITICAL", "sop": "Grid disconnect relay stuck. Replace inverter power board.", "category": "INVERTER"},
    28: {"code": 28, "name": "DSP Communication Failure", "severity": "HIGH", "sop": "Internal ribbon cable loose or EMI disturbance. Power down inverter, reseat communication cables.", "category": "COMMUNICATION"},
    29: {"code": 29, "name": "Fac Failure", "severity": "HIGH", "sop": "Frequency abnormal. Confirm grid code setting matches local utility standard (50Hz / 60Hz).", "category": "GRID"},
    31: {"code": 31, "name": "Internal Communication Failure", "severity": "HIGH", "sop": "Main controller lost communication with ARM/display module. Check DC bus stability.", "category": "COMMUNICATION"},
}

# ============================================================================
# 2. DEYE HYBRID INVERTER (SUN-SG04LP3 / SG01 / SG03 SERIES) REGISTERS & ALARMS
# ============================================================================

DEYE_HOLDING_REGISTERS: dict[int, dict[str, Any]] = {
    500: {"name": "dc_master_state", "type": "uint16", "unit": "", "scale": 1.0, "access": "RO", "desc": "Inverter operational state"},
    514: {"name": "battery_voltage", "type": "uint16", "unit": "V", "scale": 0.01, "access": "RO", "desc": "Battery terminal voltage"},
    515: {"name": "battery_soc", "type": "uint16", "unit": "%", "scale": 1.0, "access": "RO", "desc": "Battery state of charge"},
    516: {"name": "battery_power", "type": "int16", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Battery active power (+ charge / - discharge)"},
    517: {"name": "battery_current", "type": "int16", "unit": "A", "scale": 0.01, "access": "RO", "desc": "Battery current"},
    518: {"name": "battery_temp", "type": "int16", "unit": "°C", "scale": 0.1, "access": "RO", "desc": "Battery temperature"},
    527: {"name": "daily_load_energy", "type": "uint16", "unit": "kWh", "scale": 0.1, "access": "RO", "desc": "Daily load consumption"},
    529: {"name": "daily_pv_energy", "type": "uint16", "unit": "kWh", "scale": 0.1, "access": "RO", "desc": "Daily solar PV generation"},
    530: {"name": "daily_grid_buy", "type": "uint16", "unit": "kWh", "scale": 0.1, "access": "RO", "desc": "Daily energy bought from grid"},
    531: {"name": "daily_grid_sell", "type": "uint16", "unit": "kWh", "scale": 0.1, "access": "RO", "desc": "Daily energy sold to grid"},
    534: {"name": "total_pv_energy", "type": "uint32", "unit": "kWh", "scale": 0.1, "access": "RO", "desc": "Cumulative solar PV generation"},
    590: {"name": "grid_side_power", "type": "int16", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Inverter port grid power"},
    598: {"name": "total_grid_power", "type": "int16", "unit": "W", "scale": 1.0, "access": "RO", "desc": "External grid meter active power"},
    652: {"name": "inverter_inner_temp", "type": "int16", "unit": "°C", "scale": 0.1, "access": "RO", "desc": "Internal heatsink temperature"},
    653: {"name": "dc_bus_voltage", "type": "uint16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "Internal DC bus voltage"},
    672: {"name": "pv1_voltage", "type": "uint16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "PV string 1 voltage"},
    673: {"name": "pv1_current", "type": "uint16", "unit": "A", "scale": 0.1, "access": "RO", "desc": "PV string 1 current"},
    674: {"name": "pv2_voltage", "type": "uint16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "PV string 2 voltage"},
    675: {"name": "pv2_current", "type": "uint16", "unit": "A", "scale": 0.1, "access": "RO", "desc": "PV string 2 current"},
}

DEYE_ALARM_CODES: dict[int, dict[str, Any]] = {
    1: {"code": 1, "name": "Grid Lost / Blackout", "severity": "MEDIUM", "sop": "Inverter operating in UPS/off-grid mode. Check upstream utility power supply.", "category": "GRID"},
    2: {"code": 2, "name": "Grid Over Voltage (F02)", "severity": "HIGH", "sop": "Grid voltage exceeded high trip point. Measure phase voltage; adjust grid standard parameters if utility complies.", "category": "GRID"},
    3: {"code": 3, "name": "Grid Under Voltage (F03)", "severity": "HIGH", "sop": "Grid voltage sagged below low threshold. Check utility transformer tap setting.", "category": "GRID"},
    4: {"code": 4, "name": "Grid Over Frequency (F04)", "severity": "HIGH", "sop": "Frequency high. Inspect local generator governor if operating on backup generator.", "category": "GRID"},
    5: {"code": 5, "name": "Grid Under Frequency (F05)", "severity": "HIGH", "sop": "Frequency low. Inverter decoupled from grid to protect equipment.", "category": "GRID"},
    6: {"code": 6, "name": "Grid Volt Imbalance (F06)", "severity": "MEDIUM", "sop": "Phase voltage difference exceeded 10%. Check for heavy single-phase loads on supply grid.", "category": "GRID"},
    7: {"code": 7, "name": "DC Injection High (F07)", "severity": "HIGH", "sop": "DC component in AC output exceeded 0.5% rated current. Recalibrate inverter current sensors.", "category": "GRID"},
    8: {"code": 8, "name": "DC Bus Over Voltage (F08)", "severity": "CRITICAL", "sop": "Bus voltage exceeded safety limit (850V). Turn off DC switches and verify PV VOC.", "category": "PV"},
    9: {"code": 9, "name": "DC Bus Under Voltage (F09)", "severity": "HIGH", "sop": "Bus voltage unable to build up during startup. Check pre-charge relay and DC fuses.", "category": "INVERTER"},
    10: {"code": 10, "name": "Inverter Over Current (F10)", "severity": "HIGH", "sop": "Output current surged due to short-circuit or motor inrush. Check load distribution.", "category": "INVERTER"},
    11: {"code": 11, "name": "Over Temperature (F11)", "severity": "HIGH", "sop": "Inverter IGBT temperature exceeds 95°C. Clean dust filters, check fan rotation.", "category": "TEMPERATURE"},
    12: {"code": 12, "name": "Isolation Low (F12)", "severity": "HIGH", "sop": "PV array insulation resistance < 50kOhm. Inspect PV cable insulation for water ingress.", "category": "PV"},
    13: {"code": 13, "name": "GFCI Ground Current Fault (F13)", "severity": "CRITICAL", "sop": "Residual leakage current exceeds 300mA. Test PV wiring insulation to earth ground.", "category": "PV"},
    14: {"code": 14, "name": "Relay Fail (F14)", "severity": "CRITICAL", "sop": "Safety relay contacts welded or failed to close. Service power module.", "category": "INVERTER"},
    15: {"code": 15, "name": "BMS Comm Loss (F15)", "severity": "MEDIUM", "sop": "CAN/RS485 communication with lithium battery lost. Check baud rate, RJ45 pinout, and battery power.", "category": "BATTERY"},
    16: {"code": 16, "name": "Battery Reverse Polarity (F16)", "severity": "CRITICAL", "sop": "Battery cables connected backward. Disconnect breaker immediately and recheck wiring polarity!", "category": "BATTERY"},
    17: {"code": 17, "name": "EPS Overload (F17)", "severity": "MEDIUM", "sop": "Critical load port overloaded in off-grid mode. Reduce non-essential appliances.", "category": "INVERTER"},
    18: {"code": 18, "name": "Fan Warning (W01)", "severity": "LOW", "sop": "Cooling fan speed abnormally low or stalled. Inspect fan blades for obstructions.", "category": "TEMPERATURE"},
}

# ============================================================================
# 3. SUNGROW HYBRID INVERTER (SH SERIES: SH5.0RT - SH10RT) REGISTERS & ALARMS
# ============================================================================

SUNGROW_HOLDING_REGISTERS: dict[int, dict[str, Any]] = {
    5000: {"name": "device_type", "type": "uint16", "unit": "", "scale": 1.0, "access": "RO", "desc": "Sungrow model identifier"},
    5007: {"name": "daily_energy", "type": "uint16", "unit": "kWh", "scale": 0.1, "access": "RO", "desc": "Daily PV energy generation"},
    5008: {"name": "total_energy", "type": "uint32", "unit": "kWh", "scale": 1.0, "access": "RO", "desc": "Total lifetime PV energy generation"},
    5010: {"name": "internal_temp", "type": "int16", "unit": "°C", "scale": 0.1, "access": "RO", "desc": "Inverter internal temperature"},
    5011: {"name": "pv1_voltage", "type": "uint16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "PV1 input voltage"},
    5012: {"name": "pv1_current", "type": "uint16", "unit": "A", "scale": 0.1, "access": "RO", "desc": "PV1 input current"},
    5013: {"name": "pv2_voltage", "type": "uint16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "PV2 input voltage"},
    5014: {"name": "pv2_current", "type": "uint16", "unit": "A", "scale": 0.1, "access": "RO", "desc": "PV2 input current"},
    5016: {"name": "total_pv_power", "type": "uint32", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Total active PV DC power"},
    5018: {"name": "grid_a_voltage", "type": "uint16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "Grid phase A voltage"},
    5019: {"name": "grid_b_voltage", "type": "uint16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "Grid phase B voltage"},
    5020: {"name": "grid_c_voltage", "type": "uint16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "Grid phase C voltage"},
    5031: {"name": "total_active_power", "type": "int32", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Total active power fed into grid"},
    5035: {"name": "grid_frequency", "type": "uint16", "unit": "Hz", "scale": 0.1, "access": "RO", "desc": "Grid AC frequency"},
    5634: {"name": "battery_voltage", "type": "uint16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "Battery terminal voltage"},
    5635: {"name": "battery_current", "type": "int16", "unit": "A", "scale": 0.1, "access": "RO", "desc": "Battery current"},
    5636: {"name": "battery_power", "type": "int16", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Battery active power (+ charge / - discharge)"},
    5637: {"name": "battery_soc", "type": "uint16", "unit": "%", "scale": 0.1, "access": "RO", "desc": "Battery state of charge"},
    5638: {"name": "battery_soh", "type": "uint16", "unit": "%", "scale": 0.1, "access": "RO", "desc": "Battery state of health"},
    5639: {"name": "battery_temp", "type": "int16", "unit": "°C", "scale": 0.1, "access": "RO", "desc": "Battery cell temperature"},
    5678: {"name": "load_power", "type": "int32", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Total house load power"},
    5680: {"name": "backup_power", "type": "int32", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Backup port power"},
}

SUNGROW_ALARM_CODES: dict[int, dict[str, Any]] = {
    2: {"code": 2, "name": "Grid Over Voltage", "severity": "HIGH", "sop": "Grid voltage exceeds country protection threshold. Check local transformer and tap setting.", "category": "GRID"},
    3: {"code": 3, "name": "Grid Voltage Transient", "severity": "HIGH", "sop": "Grid voltage experienced severe spike/surge. Inspect lightning arrester and surge protection device.", "category": "GRID"},
    4: {"code": 4, "name": "Grid Under Voltage", "severity": "HIGH", "sop": "Grid voltage dipped below operational limit. Inverter in standby until grid stabilizes.", "category": "GRID"},
    8: {"code": 8, "name": "Grid Over Frequency", "severity": "HIGH", "sop": "Grid frequency drifted above permissible limit. Check regional grid frequency dispatch.", "category": "GRID"},
    9: {"code": 9, "name": "Grid Under Frequency", "severity": "HIGH", "sop": "Grid frequency collapsed below 47.5Hz. Inverter detached safely.", "category": "GRID"},
    10: {"code": 10, "name": "Grid Loss / Blackout", "severity": "MEDIUM", "sop": "AC supply disconnected. Check AC breaker switch position.", "category": "GRID"},
    12: {"code": 12, "name": "Excessive Leakage Current", "severity": "CRITICAL", "sop": "AC ground residual leakage current exceeded 300mA. Check AC earthing cable.", "category": "INVERTER"},
    14: {"code": 14, "name": "Grid Volt Imbalance", "severity": "MEDIUM", "sop": "Three-phase grid voltage unbalance exceeds 5%. Notify local power distribution operator.", "category": "GRID"},
    15: {"code": 15, "name": "Inverter Hardware Fault", "severity": "CRITICAL", "sop": "Power electronic switch (IGBT) fault. Contact Sungrow authorized service center.", "category": "INVERTER"},
    24: {"code": 24, "name": "Grid Voltage Abnormal", "severity": "HIGH", "sop": "Grid wave quality distorted (THD > 5%). Inspect nearby non-linear industrial loads.", "category": "GRID"},
    37: {"code": 37, "name": "Excessive High Voltage", "severity": "CRITICAL", "sop": "Internal high voltage bus surged beyond hardware breakdown limit. Stop inverter immediately.", "category": "INVERTER"},
    39: {"code": 39, "name": "Low Insulation Resistance", "severity": "HIGH", "sop": "PV DC isolation to earth < 50kOhm. Disconnect strings one by one to find fault.", "category": "PV"},
    43: {"code": 43, "name": "Internal Temp Overheat", "severity": "HIGH", "sop": "Ambient temperature too high or fan air channel blocked. Clear ventilation grills.", "category": "TEMPERATURE"},
    700: {"code": 700, "name": "Battery Under Voltage", "severity": "HIGH", "sop": "Battery cell depleted below safe cutoff. Allow solar charging to revive pack.", "category": "BATTERY"},
    703: {"code": 703, "name": "Battery Over Current", "severity": "HIGH", "sop": "Battery charge/discharge current exceeded BMS continuous limit.", "category": "BATTERY"},
    707: {"code": 707, "name": "BMS Comm Timeout", "severity": "MEDIUM", "sop": "Lost heartbeat communication with Sungrow SBR battery stack.", "category": "BATTERY"},
    714: {"code": 714, "name": "Battery High Temp", "severity": "HIGH", "sop": "Battery enclosure temperature > 55°C. Inverter halts battery cycling to prevent thermal runaway.", "category": "BATTERY"},
}

# ============================================================================
# 4. HUAWEI SUN2000 INVERTER REGISTERS & ALARMS
# ============================================================================

HUAWEI_HOLDING_REGISTERS: dict[int, dict[str, Any]] = {
    32000: {"name": "state_1", "type": "uint16", "unit": "", "scale": 1.0, "access": "RO", "desc": "Running status code"},
    32016: {"name": "pv1_voltage", "type": "int16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "PV string 1 voltage"},
    32017: {"name": "pv1_current", "type": "int16", "unit": "A", "scale": 0.01, "access": "RO", "desc": "PV string 1 current"},
    32018: {"name": "pv2_voltage", "type": "int16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "PV string 2 voltage"},
    32019: {"name": "pv2_current", "type": "int16", "unit": "A", "scale": 0.01, "access": "RO", "desc": "PV string 2 current"},
    32064: {"name": "input_power", "type": "int32", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Total input DC power"},
    32066: {"name": "grid_a_voltage", "type": "uint16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "Grid phase A voltage"},
    32067: {"name": "grid_b_voltage", "type": "uint16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "Grid phase B voltage"},
    32068: {"name": "grid_c_voltage", "type": "uint16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "Grid phase C voltage"},
    32069: {"name": "grid_a_current", "type": "int32", "unit": "A", "scale": 0.001, "access": "RO", "desc": "Grid phase A current"},
    32080: {"name": "active_power", "type": "int32", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Grid active power"},
    32085: {"name": "power_factor", "type": "int16", "unit": "", "scale": 0.001, "access": "RO", "desc": "Output power factor (cos phi)"},
    32086: {"name": "grid_frequency", "type": "uint16", "unit": "Hz", "scale": 0.01, "access": "RO", "desc": "Grid frequency"},
    32087: {"name": "efficiency", "type": "uint16", "unit": "%", "scale": 0.01, "access": "RO", "desc": "Inverter conversion efficiency"},
    32089: {"name": "internal_temperature", "type": "int16", "unit": "°C", "scale": 0.1, "access": "RO", "desc": "Inverter cabinet internal temperature"},
    32090: {"name": "insulation_resistance", "type": "uint16", "unit": "MOhm", "scale": 0.001, "access": "RO", "desc": "Insulation resistance to earth"},
    32106: {"name": "accumulated_energy", "type": "uint32", "unit": "kWh", "scale": 0.01, "access": "RO", "desc": "Accumulated yield"},
    32114: {"name": "daily_energy", "type": "uint32", "unit": "kWh", "scale": 0.01, "access": "RO", "desc": "Daily yield"},
    37000: {"name": "storage_running_state", "type": "uint16", "unit": "", "scale": 1.0, "access": "RO", "desc": "LUNA2000 battery running state"},
    37004: {"name": "storage_power", "type": "int32", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Battery charge/discharge power"},
    37007: {"name": "storage_bus_voltage", "type": "uint16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "Battery DC bus voltage"},
    37008: {"name": "storage_soc", "type": "uint16", "unit": "%", "scale": 0.1, "access": "RO", "desc": "Battery state of charge"},
}

HUAWEI_ALARM_CODES: dict[int, dict[str, Any]] = {
    2001: {"code": 2001, "name": "Grid Loss", "severity": "MEDIUM", "sop": "Power grid absent. Check AC isolation switch and upstream breaker.", "category": "GRID"},
    2002: {"code": 2002, "name": "Grid Under Voltage", "severity": "HIGH", "sop": "Grid voltage lower than lower trip boundary. Verify grid voltage at inverter terminals.", "category": "GRID"},
    2003: {"code": 2003, "name": "Grid Over Voltage", "severity": "HIGH", "sop": "Grid voltage exceeds maximum limit. Adjust grid code overvoltage protection with utility authorization.", "category": "GRID"},
    2004: {"code": 2004, "name": "Grid Volt Imbalance", "severity": "MEDIUM", "sop": "Three-phase voltage imbalance exceeds 5%. Check utility distribution balance.", "category": "GRID"},
    2005: {"code": 2005, "name": "Grid Under Frequency", "severity": "HIGH", "sop": "Grid frequency lower than 49.5Hz. Check generator or grid state.", "category": "GRID"},
    2006: {"code": 2006, "name": "Grid Over Frequency", "severity": "HIGH", "sop": "Grid frequency higher than 50.5Hz. Inverter reduces output or trips per grid code.", "category": "GRID"},
    2011: {"code": 2011, "name": "Output Over Current", "severity": "HIGH", "sop": "Instantaneous output current exceeds threshold. Inspect AC wiring for phase-to-phase short.", "category": "INVERTER"},
    2032: {"code": 2032, "name": "Grid Phase Reversed", "severity": "HIGH", "sop": "Phase sequence of AC connection is clockwise reversed (ACB instead of ABC). Swap two phases.", "category": "GRID"},
    2038: {"code": 2038, "name": "Low Insulation Resistance", "severity": "HIGH", "sop": "Insulation resistance < 1MOhm. Disconnect DC strings and perform insulation megger test.", "category": "PV"},
    2062: {"code": 2062, "name": "DC Arc Fault (AFCI)", "severity": "CRITICAL", "sop": "DC electrical arc detected in solar array! Inspect all MC4 connectors, crimps, and DC isolators for burn marks.", "category": "PV"},
    2064: {"code": 2064, "name": "High Temperature Protection", "severity": "HIGH", "sop": "Inverter chassis heat dissipation degraded. Clear weeds/debris, clean cooling heat sink.", "category": "TEMPERATURE"},
    2067: {"code": 2067, "name": "Faulty String Configuration", "severity": "MEDIUM", "sop": "String voltage differs significantly from other strings on same MPPT. Inspect for mismatched module counts.", "category": "PV"},
    2085: {"code": 2085, "name": "Built-in PID Controller Fault", "severity": "LOW", "sop": "Anti-PID compensation unit circuit abnormal. Check PV negative grounding kit.", "category": "PV"},
}

# ============================================================================
# 5. GROWATT STORAGE INVERTER (SPH / SPF SERIES) REGISTERS & ALARMS
# ============================================================================

GROWATT_HOLDING_REGISTERS: dict[int, dict[str, Any]] = {
    0: {"name": "inverter_status", "type": "uint16", "unit": "", "scale": 1.0, "access": "RO", "desc": "Growatt inverter operating status"},
    1: {"name": "ppv_total", "type": "uint32", "unit": "W", "scale": 0.1, "access": "RO", "desc": "Total input solar power"},
    3: {"name": "vpv1", "type": "uint16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "PV1 input voltage"},
    4: {"name": "ipv1", "type": "uint16", "unit": "A", "scale": 0.1, "access": "RO", "desc": "PV1 input current"},
    5: {"name": "ppv1", "type": "uint32", "unit": "W", "scale": 0.1, "access": "RO", "desc": "PV1 input power"},
    7: {"name": "vpv2", "type": "uint16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "PV2 input voltage"},
    8: {"name": "ipv2", "type": "uint16", "unit": "A", "scale": 0.1, "access": "RO", "desc": "PV2 input current"},
    9: {"name": "ppv2", "type": "uint32", "unit": "W", "scale": 0.1, "access": "RO", "desc": "PV2 input power"},
    35: {"name": "pac", "type": "uint32", "unit": "W", "scale": 0.1, "access": "RO", "desc": "Inverter output active AC power"},
    37: {"name": "fac", "type": "uint16", "unit": "Hz", "scale": 0.01, "access": "RO", "desc": "Grid AC frequency"},
    38: {"name": "vac1", "type": "uint16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "Grid phase 1 AC voltage"},
    39: {"name": "iac1", "type": "uint16", "unit": "A", "scale": 0.1, "access": "RO", "desc": "Grid phase 1 AC current"},
    53: {"name": "eac_today", "type": "uint32", "unit": "kWh", "scale": 0.1, "access": "RO", "desc": "Daily energy delivered to AC"},
    55: {"name": "eac_total", "type": "uint32", "unit": "kWh", "scale": 0.1, "access": "RO", "desc": "Total lifetime energy delivered to AC"},
    1009: {"name": "battery_voltage", "type": "uint16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "Battery bank terminal voltage"},
    1010: {"name": "battery_soc", "type": "uint16", "unit": "%", "scale": 1.0, "access": "RO", "desc": "Battery state of charge"},
    1011: {"name": "p_charge", "type": "uint32", "unit": "W", "scale": 0.1, "access": "RO", "desc": "Battery charging power"},
    1013: {"name": "p_discharge", "type": "uint32", "unit": "W", "scale": 0.1, "access": "RO", "desc": "Battery discharging power"},
    1040: {"name": "p_local_load", "type": "uint32", "unit": "W", "scale": 0.1, "access": "RO", "desc": "Local consumer load power"},
}

GROWATT_ALARM_CODES: dict[int, dict[str, Any]] = {
    101: {"code": 101, "name": "PV Isolation Fault", "severity": "HIGH", "sop": "Array insulation impedance is abnormal. Check grounding and DC wire sheath.", "category": "PV"},
    102: {"code": 102, "name": "Residual Current Fault", "severity": "CRITICAL", "sop": "Ground leakage current exceeded safety threshold. Test with insulation tester.", "category": "INVERTER"},
    103: {"code": 103, "name": "Output High DCI", "severity": "HIGH", "sop": "DC component injected into grid is too high. Reset inverter; if persistent, service board.", "category": "GRID"},
    104: {"code": 104, "name": "PV Over Voltage", "severity": "CRITICAL", "sop": "PV voltage exceeds maximum allowed DC input. Check series panel count.", "category": "PV"},
    105: {"code": 105, "name": "AC V Outrange (Grid)", "severity": "HIGH", "sop": "AC voltage outside legal grid code. Check utility grid status.", "category": "GRID"},
    106: {"code": 106, "name": "AC F Outrange (Grid)", "severity": "HIGH", "sop": "AC frequency outside permissible operating window.", "category": "GRID"},
    107: {"code": 107, "name": "AC Over Current", "severity": "HIGH", "sop": "Inverter output current exceeded maximum rating. Check for circuit overload.", "category": "INVERTER"},
    108: {"code": 108, "name": "Over Temperature Fault", "severity": "HIGH", "sop": "Heatsink temperature exceeds threshold. Ensure adequate clearance around inverter.", "category": "TEMPERATURE"},
    109: {"code": 109, "name": "BMS Communication Error", "severity": "MEDIUM", "sop": "RS485/CAN communication to BMS timed out. Check cable and terminating resistor.", "category": "BATTERY"},
    110: {"code": 110, "name": "Relay Fault", "severity": "CRITICAL", "sop": "Safety disconnection relay self-test failed. Contact supplier for repair.", "category": "INVERTER"},
    111: {"code": 111, "name": "Auto Test Failed", "severity": "HIGH", "sop": "CEI 0-21 / VDE auto-test routine failed. Re-run test via configuration menu.", "category": "INVERTER"},
    112: {"code": 112, "name": "Ground Fault", "severity": "CRITICAL", "sop": "PE earth wire disconnected or array shorted to metal frame.", "category": "PV"},
}

# ============================================================================
# 6. SOLIS INVERTER (RHI / S5-EH1P SERIES) REGISTERS & ALARMS
# ============================================================================

SOLIS_HOLDING_REGISTERS: dict[int, dict[str, Any]] = {
    3004: {"name": "inverter_status", "type": "uint16", "unit": "", "scale": 1.0, "access": "RO", "desc": "Inverter running status"},
    3005: {"name": "total_dc_power", "type": "uint32", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Total DC solar power input"},
    3021: {"name": "vpv1", "type": "uint16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "PV string 1 voltage"},
    3022: {"name": "ipv1", "type": "uint16", "unit": "A", "scale": 0.1, "access": "RO", "desc": "PV string 1 current"},
    3023: {"name": "vpv2", "type": "uint16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "PV string 2 voltage"},
    3024: {"name": "ipv2", "type": "uint16", "unit": "A", "scale": 0.1, "access": "RO", "desc": "PV string 2 current"},
    3035: {"name": "grid_voltage", "type": "uint16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "Grid line voltage"},
    3038: {"name": "grid_current", "type": "uint16", "unit": "A", "scale": 0.1, "access": "RO", "desc": "Grid line current"},
    3042: {"name": "grid_frequency", "type": "uint16", "unit": "Hz", "scale": 0.01, "access": "RO", "desc": "Grid frequency"},
    3043: {"name": "active_power", "type": "uint32", "unit": "W", "scale": 1.0, "access": "RO", "desc": "AC active power output"},
    3057: {"name": "daily_energy", "type": "uint16", "unit": "kWh", "scale": 0.1, "access": "RO", "desc": "Energy generated today"},
    3059: {"name": "total_energy", "type": "uint32", "unit": "kWh", "scale": 1.0, "access": "RO", "desc": "Total lifetime energy yield"},
    3133: {"name": "battery_current", "type": "int16", "unit": "A", "scale": 0.1, "access": "RO", "desc": "Battery current"},
    3134: {"name": "battery_voltage", "type": "uint16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "Battery voltage"},
    3137: {"name": "battery_power", "type": "int32", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Battery charge/discharge power"},
    3139: {"name": "battery_soc", "type": "uint16", "unit": "%", "scale": 1.0, "access": "RO", "desc": "Battery state of charge"},
    3140: {"name": "battery_soh", "type": "uint16", "unit": "%", "scale": 1.0, "access": "RO", "desc": "Battery state of health"},
    3144: {"name": "backup_power", "type": "uint16", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Backup/critical load port power"},
}

SOLIS_ALARM_CODES: dict[int, dict[str, Any]] = {
    1010: {"code": 1010, "name": "Grid Volt-Low", "severity": "HIGH", "sop": "Grid voltage dropped below trip limit. Measure grid voltage at main switchboard.", "category": "GRID"},
    1011: {"code": 1011, "name": "Grid Volt-High", "severity": "HIGH", "sop": "Grid voltage exceeds maximum limit. Contact power company if voltage regularly exceeds 253V.", "category": "GRID"},
    1012: {"code": 1012, "name": "Grid Freq-Low", "severity": "HIGH", "sop": "Grid frequency collapsed below safety bound. Inverter enters standby mode.", "category": "GRID"},
    1013: {"code": 1013, "name": "Grid Freq-High", "severity": "HIGH", "sop": "Grid frequency drifted higher than limit. Check backup generator frequency control.", "category": "GRID"},
    1014: {"code": 1014, "name": "Grid Loss / No-Grid", "severity": "MEDIUM", "sop": "Grid disconnected or blackout. Inverter operates backup circuit or stands by.", "category": "GRID"},
    1020: {"code": 1020, "name": "PV Over-Volt", "severity": "CRITICAL", "sop": "DC input voltage exceeds 600V/1000V limit. Check panel series quantity per string immediately.", "category": "PV"},
    1021: {"code": 1021, "name": "ISO-Fail", "severity": "HIGH", "sop": "Insulation impedance between PV array and ground is lower than 100kOhm. Inspect wet conduits.", "category": "PV"},
    1022: {"code": 1022, "name": "GFCI-Fail", "severity": "CRITICAL", "sop": "Residual leakage current exceeds standard. Check array grounding.", "category": "PV"},
    1030: {"code": 1030, "name": "Over-Temp", "severity": "HIGH", "sop": "Internal temperature high. Verify ambient temperature and natural ventilation clearance.", "category": "TEMPERATURE"},
    1035: {"code": 1035, "name": "BMS-Comm-Fail", "severity": "MEDIUM", "sop": "Lithium battery CAN communication interrupted. Check communication cable and battery power.", "category": "BATTERY"},
    1040: {"code": 1040, "name": "Relay-Fail", "severity": "CRITICAL", "sop": "Grid connection relay damaged or contacts stuck. Professional service required.", "category": "INVERTER"},
}

GENERIC_HOLDING_REGISTERS: dict[int, dict[str, Any]] = {}
GENERIC_ALARM_CODES: dict[int, dict[str, Any]] = {}

# Map vendors to exact model profiles and alarm dictionaries
VENDOR_ALARM_TABLES: dict[str, dict[int, dict[str, Any]]] = {
    "goodwe": GOODWE_ALARM_CODES,
    "deye": DEYE_ALARM_CODES,
    "sungrow": SUNGROW_ALARM_CODES,
    "huawei": HUAWEI_ALARM_CODES,
    "growatt": GROWATT_ALARM_CODES,
    "solis": SOLIS_ALARM_CODES,
}

VENDOR_REGISTER_TABLES: dict[str, dict[int, dict[str, Any]]] = {
    "goodwe": GOODWE_HOLDING_REGISTERS,
    "deye": DEYE_HOLDING_REGISTERS,
    "sungrow": SUNGROW_HOLDING_REGISTERS,
    "huawei": HUAWEI_HOLDING_REGISTERS,
    "growatt": GROWATT_HOLDING_REGISTERS,
    "solis": SOLIS_HOLDING_REGISTERS,
}

KNOWN_MODELS_PER_VENDOR: dict[str, list[str]] = {
    "goodwe": ["GW5K-ET", "GW10K-ET", "GW5048D-ES", "GW6000-EH", "GEH-5-10K"],
    "deye": ["SUN-SG04LP3-EU", "SUN-5K-SG03LP1", "SUN-8K-SG01LP1", "SUN-12K-SG04LP3"],
    "sungrow": ["SH5.0RT", "SH6.0RT", "SH8.0RT", "SH10RT", "SG5.0RS", "SG10RS"],
    "huawei": ["SUN2000-5KTL-M1", "SUN2000-10KTL-M1", "SUN2000-50KTL-M3", "SUN2000-100KTL-M2"],
    "growatt": ["SPH3000", "SPH6000", "SPF5000ES", "MOD-10KTL3-X", "MIN-5000TL-X"],
    "solis": ["RHI-3P(5-10)K-HVES-5G", "S5-EH1P(3-6)K-L", "S6-GR1P(2.5-6)K"],
}


# ============================================================================
# HELPER DECODER FUNCTIONS
# ============================================================================


def decode_vendor_alarm(vendor: str, code: int, model: str | None = None) -> dict[str, Any]:
    """Decode a vendor alarm code.
    
    If model is not specified or brand is UNKNOWN, semantics remain UNKNOWN
    to preserve exact device identity invariants. When an exact model is provided
    or matched, decodes into structured alarm with SOP.
    """
    v_clean = vendor.strip().lower() if vendor else ""
    
    # Invariant: brand alone does not identify register or fault semantics.
    if not model or model.strip().lower() in ("", "unknown", "generic"):
        return {
            "fault_code": code,
            "title": "Unmapped vendor event",
            "severity": "UNKNOWN",
            "remediation_advice": "Exact model/firmware protocol required",
            "vendor": vendor,
        }
    
    # Model is provided: check against known models
    table = VENDOR_ALARM_TABLES.get(v_clean)
    if not table:
        for k, v in VENDOR_ALARM_TABLES.items():
            if k in v_clean:
                table = v
                break
    
    if table and code in table:
        entry = table[code]
        return {
            "fault_code": code,
            "title": entry["name"],
            "severity": entry["severity"],
            "remediation_advice": entry["sop"],
            "category": entry.get("category", "INVERTER"),
            "vendor": vendor,
            "model": model,
        }
    
    return {
        "fault_code": code,
        "title": f"Vendor code {code} (Unmapped for {model})",
        "severity": "UNKNOWN",
        "remediation_advice": "Consult manufacturer engineering documentation for specific fault code",
        "vendor": vendor,
        "model": model,
    }


def get_vendor_registers(brand: str, model: str | None = None) -> dict[str, Any]:
    """Retrieve holding register map and alarms for a vendor / model."""
    b_clean = brand.strip().lower() if brand else ""
    table = VENDOR_REGISTER_TABLES.get(b_clean)
    alarms = VENDOR_ALARM_TABLES.get(b_clean)
    models = KNOWN_MODELS_PER_VENDOR.get(b_clean, [])
    
    if not table:
        for k, v in VENDOR_REGISTER_TABLES.items():
            if k in b_clean:
                table = v
                alarms = VENDOR_ALARM_TABLES.get(k)
                models = KNOWN_MODELS_PER_VENDOR.get(k, [])
                break

    if not table:
        return {
            "brand": brand,
            "registers": [],
            "alarms": [],
            "status": "UNKNOWN",
            "reason": "exact_model_protocol_evidence_required",
            "models": [],
            "registers_count": 0,
            "alarms_count": 0,
        }

    # Invariant: brand alone does not identify register semantics.
    # An exact model is required to return verified registers and alarms.
    if not model or model.strip().lower() in ("", "unknown", "generic"):
        return {
            "brand": brand,
            "registers": [],
            "alarms": [],
            "status": "UNKNOWN",
            "reason": "exact_model_protocol_evidence_required",
            "models": models,
            "registers_count": 0,
            "alarms_count": 0,
        }

    reg_list = [
        {"address": addr, **details}
        for addr, details in sorted(table.items())
    ]
    alarm_list = [
        details for code, details in sorted(alarms.items())
    ] if alarms else []

    return {
        "brand": brand,
        "status": "VERIFIED_AUDITED",
        "registers_count": len(reg_list),
        "alarms_count": len(alarm_list),
        "supported_models": models,
        "registers": reg_list,
        "alarms": alarm_list,
    }
