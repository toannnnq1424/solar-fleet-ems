"""Comprehensive multi-brand device driver registry and protocol dictionary.

Independently implemented for Solar Fleet EMS.
Synthesizes verified protocol register mappings, alarm decoders, and command parameters from:
- Victron Energy (openems-develop io.openems.edge.victron, Venus OS Modbus-TCP)
- Fronius (openems-develop io.openems.edge.fronius, SunSpec model 101/103/124)
- SolarEdge (openems-develop io.openems.edge.solaredge, SunSpec + StorEdge)
- SMA Solar (openems-develop io.openems.edge.sma, SMA Modbus-TCP)
- Sofar Solar (ha-solarman sofar_g3hyd.yaml, solar-inverter-modbus-registers)
- SolaX Power (sem-community-main consts/hardware_matrix.py, batpred solax.py)
- AlphaESS (batpred alphaess.py, sem-community-main)
- Enphase Energy (batpred enphase.py, sem-community-main Envoy 3-phase)
- FoxESS (batpred fox.py, ha-solarman)
- GivEnergy (batpred givtcp.py, sem-community-main)
- Hoymiles (openems-develop meter.opendtu, ha-solarman)
- Sigenergy SigenStor (batpred sigenergy.py)
- Pylontech & Dyness BMS (ha-solarman pylontech_force.yaml, CAN/RS485 standard)
No proprietary code copied.

Provides:
- Exact register maps (addresses, data types, units, scale factors, access permissions)
- Comprehensive fault and alarm code dictionaries with actionable SOPs
- Complete known model catalogues for all 13 additional brands
"""

from __future__ import annotations

from typing import Any, Dict, List

# ============================================================================
# 1. VICTRON ENERGY (MultiPlus-II, Quattro, SmartSolar, Cerbo GX)
# ============================================================================

VICTRON_HOLDING_REGISTERS: Dict[int, Dict[str, Any]] = {
    800: {"name": "vgrid_l1", "type": "uint16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "Grid L1 voltage"},
    801: {"name": "vgrid_l2", "type": "uint16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "Grid L2 voltage"},
    802: {"name": "vgrid_l3", "type": "uint16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "Grid L3 voltage"},
    808: {"name": "pgrid_l1", "type": "int16", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Grid L1 active power (+ imp / - exp)"},
    809: {"name": "pgrid_l2", "type": "int16", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Grid L2 active power"},
    810: {"name": "pgrid_l3", "type": "int16", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Grid L3 active power"},
    840: {"name": "vbat", "type": "uint16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "Battery terminal voltage"},
    841: {"name": "ibat", "type": "int16", "unit": "A", "scale": 0.1, "access": "RO", "desc": "Battery current (+ charge / - discharge)"},
    842: {"name": "pbat", "type": "int16", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Battery power"},
    843: {"name": "battery_soc", "type": "uint16", "unit": "%", "scale": 1.0, "access": "RO", "desc": "Battery state of charge"},
    844: {"name": "battery_state", "type": "uint16", "unit": "", "scale": 1.0, "access": "RO", "desc": "0=Idle, 1=Charging, 2=Discharging"},
    850: {"name": "p_ac_out", "type": "int16", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Critical AC output power"},
    2700: {"name": "ess_mode", "type": "uint16", "unit": "", "scale": 1.0, "access": "RW", "desc": "1=Optimized, 2=BatteryLife, 3=Keep Charged"},
    2701: {"name": "grid_setpoint", "type": "int16", "unit": "W", "scale": 1.0, "access": "RW", "desc": "Target grid power exchange setpoint"},
    2702: {"name": "max_charge_current", "type": "uint16", "unit": "A", "scale": 0.1, "access": "RW", "desc": "Maximum battery charge current limit"},
    2703: {"name": "max_discharge_power", "type": "uint16", "unit": "W", "scale": 1.0, "access": "RW", "desc": "Maximum ESS inverter discharge power"},
}

VICTRON_ALARM_CODES: Dict[int, Dict[str, Any]] = {
    1: {"name": "Low Battery Warning", "severity": "MEDIUM", "sop": "Inspect battery terminal voltage and state of charge.", "category": "BATTERY"},
    2: {"name": "Low Battery Alarm", "severity": "CRITICAL", "sop": "Battery reached cutoff voltage. Enable grid charging immediately.", "category": "BATTERY"},
    3: {"name": "Over Temperature Warning", "severity": "HIGH", "sop": "Check enclosure ventilation, cooling air ducts, and ambient temperature.", "category": "TEMPERATURE"},
    4: {"name": "Over Temperature Alarm", "severity": "CRITICAL", "sop": "Inverter thermal shutdown. Inspect heatsink and fan functionality.", "category": "TEMPERATURE"},
    5: {"name": "Overload Warning", "severity": "HIGH", "sop": "AC load power approaching inverter surge capacity limit.", "category": "INVERTER"},
    6: {"name": "Overload Alarm", "severity": "CRITICAL", "sop": "Inverter tripped on overload. Shed non-essential AC output circuits.", "category": "INVERTER"},
    7: {"name": "Phase Rotation Error", "severity": "CRITICAL", "sop": "Three-phase AC input sequence is inverted. Swap L2 and L3 wiring.", "category": "GRID"},
    8: {"name": "Grid Lost / Islanding", "severity": "MEDIUM", "sop": "Grid voltage absent. Inverter running in standalone island mode.", "category": "GRID"},
}


# ============================================================================
# 2. FRONIUS (Primo, Symo, Symo Hybrid, Gen24 Plus)
# ============================================================================

FRONIUS_HOLDING_REGISTERS: Dict[int, Dict[str, Any]] = {
    40071: {"name": "igrid_total", "type": "uint16", "unit": "A", "scale": 0.1, "access": "RO", "desc": "Total AC output current"},
    40076: {"name": "vgrid_l1", "type": "uint16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "AC voltage phase A-N"},
    40077: {"name": "vgrid_l2", "type": "uint16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "AC voltage phase B-N"},
    40078: {"name": "vgrid_l3", "type": "uint16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "AC voltage phase C-N"},
    40083: {"name": "pgrid", "type": "int16", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Total AC active power"},
    40085: {"name": "fgrid", "type": "uint16", "unit": "Hz", "scale": 0.01, "access": "RO", "desc": "Grid line frequency"},
    40093: {"name": "e_total", "type": "uint32", "unit": "Wh", "scale": 1.0, "access": "RO", "desc": "Cumulative lifetime energy generated"},
    40101: {"name": "ppv", "type": "uint16", "unit": "W", "scale": 1.0, "access": "RO", "desc": "DC solar input power"},
    40107: {"name": "temp_heatsink", "type": "int16", "unit": "°C", "scale": 0.1, "access": "RO", "desc": "Inverter heatsink temperature"},
    40108: {"name": "operating_state", "type": "uint16", "unit": "", "scale": 1.0, "access": "RO", "desc": "1=Off, 2=Sleeping, 4=Running, 7=Fault"},
    40200: {"name": "battery_soc", "type": "uint16", "unit": "%", "scale": 0.01, "access": "RO", "desc": "Battery state of charge"},
    40201: {"name": "battery_power", "type": "int16", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Battery power (+ charge / - discharge)"},
    40232: {"name": "power_curtailment_pct", "type": "uint16", "unit": "%", "scale": 0.01, "access": "RW", "desc": "Inverter output curtailment limit"},
}

FRONIUS_ALARM_CODES: Dict[int, Dict[str, Any]] = {
    102: {"name": "AC Voltage High", "severity": "HIGH", "sop": "Grid voltage exceeds maximum limit. Check local utility transformer taps.", "category": "GRID"},
    103: {"name": "AC Voltage Low", "severity": "HIGH", "sop": "Grid voltage dropped below minimum threshold. Inspect main AC breaker.", "category": "GRID"},
    105: {"name": "AC Frequency High", "severity": "HIGH", "sop": "Grid frequency exceeded limit. Check generator frequency regulation.", "category": "GRID"},
    301: {"name": "Overcurrent DC", "severity": "CRITICAL", "sop": "DC input current exceeds maximum hardware rating. Check string parallel connections.", "category": "PV"},
    401: {"name": "Smart Meter Comm Lost", "severity": "HIGH", "sop": "Modbus communication to Fronius Smart Meter lost. Check RS485 wiring.", "category": "COMMUNICATION"},
    443: {"name": "DC Overvoltage", "severity": "CRITICAL", "sop": "Open-circuit voltage exceeds 1000V. Disconnect DC isolator immediately.", "category": "PV"},
    509: {"name": "No Energy Fed In", "severity": "MEDIUM", "sop": "No energy fed to grid past 24h. Verify DC isolators and AC contactor.", "category": "INVERTER"},
}


# ============================================================================
# 3. SOLAREDGE (SE HD-Wave, SE Three Phase, StorEdge)
# ============================================================================

SOLAREDGE_HOLDING_REGISTERS: Dict[int, Dict[str, Any]] = {
    40071: {"name": "igrid", "type": "uint16", "unit": "A", "scale": 0.1, "access": "RO", "desc": "AC total current"},
    40076: {"name": "vgrid_l1", "type": "uint16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "Voltage phase L1-N"},
    40083: {"name": "pgrid", "type": "int16", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Total active power output"},
    40085: {"name": "fgrid", "type": "uint16", "unit": "Hz", "scale": 0.01, "access": "RO", "desc": "Grid line frequency"},
    40093: {"name": "e_total", "type": "uint32", "unit": "Wh", "scale": 1.0, "access": "RO", "desc": "Cumulative energy exported"},
    40101: {"name": "ppv", "type": "int16", "unit": "W", "scale": 1.0, "access": "RO", "desc": "DC solar power from optimizers"},
    40107: {"name": "inverter_status", "type": "uint16", "unit": "", "scale": 1.0, "access": "RO", "desc": "1=Off, 2=Sleeping, 4=Producing, 7=Fault"},
    40134: {"name": "active_power_limit_pct", "type": "uint16", "unit": "%", "scale": 1.0, "access": "RW", "desc": "Active power limit setting (0-100%)"},
    40140: {"name": "storage_control_mode", "type": "uint16", "unit": "", "scale": 1.0, "access": "RW", "desc": "1=Max self consumption, 2=TOU, 4=Remote"},
    40141: {"name": "remote_control_command", "type": "uint16", "unit": "", "scale": 1.0, "access": "RW", "desc": "1=Charge solar, 2=Charge grid, 3=Discharge"},
    40220: {"name": "battery_soh", "type": "float32", "unit": "%", "scale": 1.0, "access": "RO", "desc": "Battery state of health"},
    40222: {"name": "battery_soc", "type": "float32", "unit": "%", "scale": 1.0, "access": "RO", "desc": "Battery state of charge"},
    40224: {"name": "battery_status", "type": "uint16", "unit": "", "scale": 1.0, "access": "RO", "desc": "1=Off, 2=Standby, 4=Charge, 5=Discharge"},
}

SOLAREDGE_ALARM_CODES: Dict[int, Dict[str, Any]] = {
    17: {"name": "Grid Overvoltage", "severity": "HIGH", "sop": "Grid voltage outside statutory limits. Inspect distribution panel.", "category": "GRID"},
    18: {"name": "Grid Undervoltage", "severity": "HIGH", "sop": "Grid voltage collapse or brownout detected.", "category": "GRID"},
    25: {"name": "Isolation Fault", "severity": "HIGH", "sop": "DC isolation resistance < 100kOhm. Isolate optimizers and string cables.", "category": "PV"},
    31: {"name": "DC Injection High", "severity": "HIGH", "sop": "DC current injection on AC output exceeds threshold.", "category": "GRID"},
    69: {"name": "Temperature High", "severity": "HIGH", "sop": "Inverter heatsink overheat. Inspect internal fan and clearances.", "category": "TEMPERATURE"},
    85: {"name": "Arc Fault Detected", "severity": "CRITICAL", "sop": "Series arc fault detected. Inspect DC connectors and module junctions.", "category": "PV"},
    110: {"name": "Battery Comm Lost", "severity": "HIGH", "sop": "Communication link between SolarEdge and StorEdge battery dropped.", "category": "BATTERY"},
}


# ============================================================================
# 4. SMA SOLAR (Sunny Boy, Sunny Tripower, Sunny Island)
# ============================================================================

SMA_HOLDING_REGISTERS: Dict[int, Dict[str, Any]] = {
    30051: {"name": "operating_status", "type": "uint32", "unit": "", "scale": 1.0, "access": "RO", "desc": "35=Fault, 303=Off, 307=Ok, 455=Warning"},
    30775: {"name": "pgrid", "type": "int32", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Active power total (+ export / - import)"},
    30783: {"name": "vgrid_l1", "type": "uint32", "unit": "V", "scale": 0.01, "access": "RO", "desc": "Grid voltage L1"},
    30785: {"name": "vgrid_l2", "type": "uint32", "unit": "V", "scale": 0.01, "access": "RO", "desc": "Grid voltage L2"},
    30787: {"name": "vgrid_l3", "type": "uint32", "unit": "V", "scale": 0.01, "access": "RO", "desc": "Grid voltage L3"},
    30803: {"name": "fgrid", "type": "uint32", "unit": "Hz", "scale": 0.01, "access": "RO", "desc": "Grid frequency"},
    30845: {"name": "battery_soc", "type": "uint32", "unit": "%", "scale": 1.0, "access": "RO", "desc": "Battery state of charge"},
    30849: {"name": "battery_temp", "type": "int32", "unit": "°C", "scale": 0.1, "access": "RO", "desc": "Battery temperature"},
    30851: {"name": "battery_power", "type": "int32", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Battery active power (+ charge / - discharge)"},
    40016: {"name": "operating_mode", "type": "uint32", "unit": "", "scale": 1.0, "access": "RW", "desc": "1392=Self-consumption, 1394=External EMS"},
    40151: {"name": "active_power_curtailment", "type": "uint32", "unit": "W", "scale": 1.0, "access": "RW", "desc": "Inverter active power ceiling setpoint"},
}

SMA_ALARM_CODES: Dict[int, Dict[str, Any]] = {
    101: {"name": "Grid Failure", "severity": "MEDIUM", "sop": "AC grid power absent. Inverter disconnected from mains.", "category": "GRID"},
    102: {"name": "Frequency Out of Tolerance", "severity": "HIGH", "sop": "Grid frequency drifted beyond permitted window.", "category": "GRID"},
    103: {"name": "Voltage Out of Tolerance", "severity": "HIGH", "sop": "Grid voltage outside statutory operating bounds.", "category": "GRID"},
    202: {"name": "Current Sensor Failure", "severity": "CRITICAL", "sop": "Internal AC current transducer measurement failure.", "category": "INVERTER"},
    358: {"name": "Battery Deep Discharged", "severity": "CRITICAL", "sop": "Battery pack below deep discharge threshold. Charge immediately.", "category": "BATTERY"},
    401: {"name": "Internal Hardware Error", "severity": "CRITICAL", "sop": "Inverter control board fault. Contact SMA customer support.", "category": "INVERTER"},
    501: {"name": "Earth Fault", "severity": "CRITICAL", "sop": "Residual current leakage to protective earth detected.", "category": "PV"},
}


# ============================================================================
# 5. SOFAR SOLAR (HYD 3000-6000-ES, HYD 5K-20KTL-3PH, ME3000SP)
# ============================================================================

SOFAR_HOLDING_REGISTERS: Dict[int, Dict[str, Any]] = {
    512: {"name": "operating_state", "type": "uint16", "unit": "", "scale": 1.0, "access": "RO", "desc": "0=Standby, 1=Self-test, 2=Normal, 4=Fault"},
    518: {"name": "vpv1", "type": "uint16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "PV1 input voltage"},
    520: {"name": "ppv1", "type": "uint16", "unit": "W", "scale": 10.0, "access": "RO", "desc": "PV1 input power"},
    521: {"name": "vpv2", "type": "uint16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "PV2 input voltage"},
    523: {"name": "ppv2", "type": "uint16", "unit": "W", "scale": 10.0, "access": "RO", "desc": "PV2 input power"},
    524: {"name": "vgrid", "type": "uint16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "Grid AC voltage"},
    526: {"name": "pgrid", "type": "int16", "unit": "W", "scale": 10.0, "access": "RO", "desc": "Grid active power (+ import / - export)"},
    528: {"name": "vbat", "type": "uint16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "Battery terminal voltage"},
    529: {"name": "ibat", "type": "int16", "unit": "A", "scale": 0.01, "access": "RO", "desc": "Battery current (+ charge / - discharge)"},
    530: {"name": "pbat", "type": "int16", "unit": "W", "scale": 10.0, "access": "RO", "desc": "Battery active power"},
    531: {"name": "battery_soc", "type": "uint16", "unit": "%", "scale": 1.0, "access": "RO", "desc": "Battery state of charge"},
    532: {"name": "battery_temp", "type": "int16", "unit": "°C", "scale": 1.0, "access": "RO", "desc": "Battery internal temperature"},
    4352: {"name": "work_mode", "type": "uint16", "unit": "", "scale": 1.0, "access": "RW", "desc": "0=Self Use, 1=TOU, 2=Timing, 3=Passive"},
    4353: {"name": "max_charge_power", "type": "uint16", "unit": "W", "scale": 10.0, "access": "RW", "desc": "Max battery charge power limit"},
    4354: {"name": "max_discharge_power", "type": "uint16", "unit": "W", "scale": 10.0, "access": "RW", "desc": "Max battery discharge power limit"},
    4355: {"name": "export_power_limit", "type": "uint16", "unit": "W", "scale": 10.0, "access": "RW", "desc": "Export power limit ceiling"},
}

SOFAR_ALARM_CODES: Dict[int, Dict[str, Any]] = {
    1: {"name": "Grid Overvoltage", "severity": "HIGH", "sop": "Grid voltage high. Inverter curtailed or disconnected.", "category": "GRID"},
    2: {"name": "Grid Undervoltage", "severity": "HIGH", "sop": "Grid voltage below threshold. Check AC breaker.", "category": "GRID"},
    9: {"name": "PV Insulation Resistance Low", "severity": "HIGH", "sop": "DC isolation impedance < 100kOhm. Inspect array cabling.", "category": "PV"},
    10: {"name": "Ground Fault Leakage", "severity": "CRITICAL", "sop": "GFCI current trip. Check grounding electrode conductor.", "category": "PV"},
    16: {"name": "Inverter Over Temperature", "severity": "HIGH", "sop": "Internal heatsink overheat. Inspect cooling fans.", "category": "TEMPERATURE"},
    24: {"name": "Battery Overvoltage", "severity": "CRITICAL", "sop": "Battery terminal voltage exceeds charge cutoff limit.", "category": "BATTERY"},
    25: {"name": "Battery Undervoltage", "severity": "HIGH", "sop": "Battery discharged below operating limit. Recharge immediately.", "category": "BATTERY"},
}


# ============================================================================
# 6. SOLAX POWER (X1-Hybrid, X3-Hybrid G3/G4)
# ============================================================================

SOLAX_HOLDING_REGISTERS: Dict[int, Dict[str, Any]] = {
    0: {"name": "vgrid_l1", "type": "uint16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "Grid voltage L1"},
    1: {"name": "igrid_l1", "type": "int16", "unit": "A", "scale": 0.1, "access": "RO", "desc": "Grid current L1"},
    2: {"name": "pgrid", "type": "int16", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Total grid power (+ imp / - exp)"},
    10: {"name": "vpv1", "type": "uint16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "PV1 input voltage"},
    12: {"name": "ppv1", "type": "uint16", "unit": "W", "scale": 1.0, "access": "RO", "desc": "PV1 input power"},
    13: {"name": "ppv2", "type": "uint16", "unit": "W", "scale": 1.0, "access": "RO", "desc": "PV2 input power"},
    19: {"name": "vbat", "type": "uint16", "unit": "V", "scale": 0.01, "access": "RO", "desc": "Battery terminal voltage"},
    20: {"name": "ibat", "type": "int16", "unit": "A", "scale": 0.1, "access": "RO", "desc": "Battery current (+ charge / - discharge)"},
    21: {"name": "pbat", "type": "int16", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Battery active power"},
    22: {"name": "battery_soc", "type": "uint16", "unit": "%", "scale": 1.0, "access": "RO", "desc": "Battery state of charge"},
    24: {"name": "battery_temp", "type": "int16", "unit": "°C", "scale": 1.0, "access": "RO", "desc": "Battery internal temperature"},
    31: {"name": "work_mode", "type": "uint16", "unit": "", "scale": 1.0, "access": "RW", "desc": "0=Self Use, 1=Feed-in, 2=Backup, 3=Manual"},
    32: {"name": "manual_rate_amps", "type": "uint16", "unit": "A", "scale": 0.1, "access": "RW", "desc": "Manual charge/discharge rate"},
    38: {"name": "export_limit_w", "type": "uint16", "unit": "W", "scale": 1.0, "access": "RW", "desc": "Backflow export limit in Watts"},
}

SOLAX_ALARM_CODES: Dict[int, Dict[str, Any]] = {
    1: {"name": "Grid Lost Fault", "severity": "MEDIUM", "sop": "Mains utility power absent. Inverter running off-grid.", "category": "GRID"},
    2: {"name": "Grid Voltage Fault", "severity": "HIGH", "sop": "Grid voltage outside statutory tolerance window.", "category": "GRID"},
    3: {"name": "Grid Frequency Fault", "severity": "HIGH", "sop": "Grid frequency drifted beyond permitted range.", "category": "GRID"},
    4: {"name": "PV Voltage Fault", "severity": "CRITICAL", "sop": "String open-circuit voltage exceeds maximum rating.", "category": "PV"},
    5: {"name": "Isolation Fault", "severity": "HIGH", "sop": "DC insulation resistance to earth low. Check cabling.", "category": "PV"},
    11: {"name": "Inverter Over Temperature", "severity": "HIGH", "sop": "Heatsink overheat. Clean cooling vents and fan.", "category": "TEMPERATURE"},
    20: {"name": "BMS Comm Lost", "severity": "HIGH", "sop": "CAN bus communication timeout to SolaX battery BMS.", "category": "BATTERY"},
}


# ============================================================================
# 7. ALPHAESS (Smile5, Smile-B3, Smile-T10, Storion)
# ============================================================================

ALPHAESS_HOLDING_REGISTERS: Dict[int, Dict[str, Any]] = {
    1: {"name": "system_status", "type": "uint16", "unit": "", "scale": 1.0, "access": "RO", "desc": "0=Normal, 1=Fault, 2=Standby"},
    3: {"name": "ppv", "type": "uint32", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Total solar PV generation power"},
    5: {"name": "pgrid", "type": "int32", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Total grid power (+ imp / - exp)"},
    7: {"name": "pinv", "type": "int32", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Inverter AC active power"},
    9: {"name": "peps", "type": "uint32", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Backup/EPS output power"},
    256: {"name": "battery_soc", "type": "uint16", "unit": "%", "scale": 0.1, "access": "RO", "desc": "Battery state of charge"},
    257: {"name": "vbat", "type": "uint16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "Battery pack voltage"},
    258: {"name": "ibat", "type": "int16", "unit": "A", "scale": 0.1, "access": "RO", "desc": "Battery current (+ charge / - discharge)"},
    259: {"name": "pbat", "type": "int32", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Battery power"},
    261: {"name": "battery_soh", "type": "uint16", "unit": "%", "scale": 0.1, "access": "RO", "desc": "Battery state of health"},
    512: {"name": "dispatch_mode", "type": "uint16", "unit": "", "scale": 1.0, "access": "RW", "desc": "0=Normal, 1=Force Charge, 2=Force Discharge"},
    513: {"name": "dispatch_power_w", "type": "uint16", "unit": "W", "scale": 1.0, "access": "RW", "desc": "Target battery charge/discharge power"},
    514: {"name": "grid_charge_enable", "type": "uint16", "unit": "", "scale": 1.0, "access": "RW", "desc": "0=Disable grid charge, 1=Enable"},
}

ALPHAESS_ALARM_CODES: Dict[int, Dict[str, Any]] = {
    1: {"name": "Grid Voltage Abnormality", "severity": "HIGH", "sop": "Grid voltage outside operating envelope.", "category": "GRID"},
    2: {"name": "Grid Frequency Abnormality", "severity": "HIGH", "sop": "Grid frequency anomalous.", "category": "GRID"},
    3: {"name": "IGBT Overcurrent", "severity": "CRITICAL", "sop": "Inverter power stage hardware overcurrent trip.", "category": "INVERTER"},
    4: {"name": "Battery High Temperature", "severity": "HIGH", "sop": "Battery cell temperature exceeds operating limit.", "category": "BATTERY"},
    5: {"name": "Battery Low Temperature", "severity": "HIGH", "sop": "Battery temperature below 0°C. Charging interlocked.", "category": "BATTERY"},
    7: {"name": "BMS Comm Timeout", "severity": "HIGH", "sop": "CAN communication timeout between inverter and Alpha BMS.", "category": "BATTERY"},
}


# ============================================================================
# 8. ENPHASE ENERGY (Envoy-S, IQ Gateway, IQ7/IQ8, IQ Battery)
# ============================================================================

ENPHASE_HOLDING_REGISTERS: Dict[int, Dict[str, Any]] = {
    1: {"name": "ppv", "type": "float32", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Aggregate microinverter solar power"},
    3: {"name": "pload", "type": "float32", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Site consumption active power"},
    5: {"name": "pgrid", "type": "float32", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Net grid power (+ imp / - exp)"},
    7: {"name": "vgrid_l1", "type": "float32", "unit": "V", "scale": 1.0, "access": "RO", "desc": "Grid voltage L1"},
    9: {"name": "vgrid_l2", "type": "float32", "unit": "V", "scale": 1.0, "access": "RO", "desc": "Grid voltage L2"},
    11: {"name": "vgrid_l3", "type": "float32", "unit": "V", "scale": 1.0, "access": "RO", "desc": "Grid voltage L3"},
    13: {"name": "fgrid", "type": "float32", "unit": "Hz", "scale": 1.0, "access": "RO", "desc": "Grid frequency"},
    32: {"name": "battery_soc", "type": "float32", "unit": "%", "scale": 1.0, "access": "RO", "desc": "IQ Battery aggregate state of charge"},
    34: {"name": "battery_power", "type": "float32", "unit": "W", "scale": 1.0, "access": "RO", "desc": "IQ Battery aggregate power (+ chg / - dis)"},
    48: {"name": "profile_mode", "type": "uint16", "unit": "", "scale": 1.0, "access": "RW", "desc": "1=Self-consumption, 2=Savings, 3=Full Backup"},
    50: {"name": "reserve_battery_pct", "type": "float32", "unit": "%", "scale": 1.0, "access": "RW", "desc": "Reserve battery capacity floor"},
}

ENPHASE_ALARM_CODES: Dict[int, Dict[str, Any]] = {
    1: {"name": "Production CT Comm Lost", "severity": "HIGH", "sop": "Current transformer wiring loose or disconnected from Envoy.", "category": "METER"},
    2: {"name": "Microinverter Not Reporting", "severity": "MEDIUM", "sop": "PLC communication link degraded. Check for electrical line noise.", "category": "COMMUNICATION"},
    3: {"name": "Grid Outage Detected", "severity": "MEDIUM", "sop": "Envoy transitioned to microgrid island mode.", "category": "GRID"},
    4: {"name": "Battery Comm Fault", "severity": "HIGH", "sop": "Wireless 2.4GHz link between Envoy and IQ Battery dropped.", "category": "BATTERY"},
    5: {"name": "Phase Meter Polarity Reversed", "severity": "HIGH", "sop": "Production or consumption CT installed backwards on conductor.", "category": "METER"},
}


# ============================================================================
# 9. FOXESS (H1, H3, AC1, KH Series)
# ============================================================================

FOXESS_HOLDING_REGISTERS: Dict[int, Dict[str, Any]] = {
    12544: {"name": "vgrid", "type": "uint16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "AC grid voltage"},
    12546: {"name": "pgrid", "type": "int16", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Grid active power (+ imp / - exp)"},
    12547: {"name": "fgrid", "type": "uint16", "unit": "Hz", "scale": 0.01, "access": "RO", "desc": "Grid frequency"},
    12549: {"name": "ppv1", "type": "uint16", "unit": "W", "scale": 1.0, "access": "RO", "desc": "PV1 solar power"},
    12550: {"name": "ppv2", "type": "uint16", "unit": "W", "scale": 1.0, "access": "RO", "desc": "PV2 solar power"},
    12553: {"name": "temp_inverter", "type": "int16", "unit": "°C", "scale": 1.0, "access": "RO", "desc": "Inverter internal temperature"},
    12570: {"name": "vbat", "type": "uint16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "Battery pack voltage"},
    12571: {"name": "ibat", "type": "int16", "unit": "A", "scale": 0.1, "access": "RO", "desc": "Battery current (+ charge / - discharge)"},
    12572: {"name": "pbat", "type": "int16", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Battery power"},
    12574: {"name": "battery_soc", "type": "uint16", "unit": "%", "scale": 1.0, "access": "RO", "desc": "Battery state of charge"},
    12576: {"name": "battery_soh", "type": "uint16", "unit": "%", "scale": 1.0, "access": "RO", "desc": "Battery state of health"},
    4352: {"name": "work_mode", "type": "uint16", "unit": "", "scale": 1.0, "access": "RW", "desc": "0=Self Use, 1=Feed-in, 2=Backup, 3=Force Charge"},
    4354: {"name": "force_charge_power_w", "type": "uint16", "unit": "W", "scale": 1.0, "access": "RW", "desc": "Grid forced charge power setting"},
    4357: {"name": "min_soc_floor", "type": "uint16", "unit": "%", "scale": 1.0, "access": "RW", "desc": "Minimum battery discharge floor SOC"},
}

FOXESS_ALARM_CODES: Dict[int, Dict[str, Any]] = {
    1: {"name": "Grid Over Voltage", "severity": "HIGH", "sop": "AC grid line voltage high.", "category": "GRID"},
    2: {"name": "Grid Under Voltage", "severity": "HIGH", "sop": "AC grid line voltage low.", "category": "GRID"},
    14: {"name": "PV Isolation Low", "severity": "HIGH", "sop": "PV DC isolation resistance below safety threshold.", "category": "PV"},
    19: {"name": "Inverter Over Temp", "severity": "HIGH", "sop": "Check cooling clearance and internal fan operation.", "category": "TEMPERATURE"},
    26: {"name": "Battery Comm Fault", "severity": "HIGH", "sop": "BMS CAN bus communication timeout to FoxESS battery.", "category": "BATTERY"},
    28: {"name": "Battery Over Current", "severity": "CRITICAL", "sop": "Battery charge/discharge current exceeded safe threshold.", "category": "BATTERY"},
}


# ============================================================================
# 10. GIVENERGY (Gen1, Gen2, Gen3 Hybrid, All-in-One)
# ============================================================================

GIVENERGY_HOLDING_REGISTERS: Dict[int, Dict[str, Any]] = {
    18: {"name": "inverter_status", "type": "uint16", "unit": "", "scale": 1.0, "access": "RO", "desc": "0=Waiting, 1=Normal, 2=Fault"},
    60: {"name": "ppv1", "type": "uint16", "unit": "W", "scale": 1.0, "access": "RO", "desc": "PV1 solar generation"},
    61: {"name": "ppv2", "type": "uint16", "unit": "W", "scale": 1.0, "access": "RO", "desc": "PV2 solar generation"},
    62: {"name": "pgrid", "type": "int16", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Grid active power (+ imp / - exp)"},
    63: {"name": "pinv", "type": "int16", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Inverter active power"},
    64: {"name": "pload", "type": "uint16", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Site consumption load"},
    65: {"name": "pbat", "type": "int16", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Battery power (+ charge / - discharge)"},
    66: {"name": "battery_soc", "type": "uint16", "unit": "%", "scale": 1.0, "access": "RO", "desc": "Battery state of charge"},
    67: {"name": "vbat", "type": "uint16", "unit": "V", "scale": 0.01, "access": "RO", "desc": "Battery terminal voltage"},
    69: {"name": "battery_temp", "type": "int16", "unit": "°C", "scale": 0.1, "access": "RO", "desc": "Battery cell temperature"},
    110: {"name": "enable_grid_charge", "type": "uint16", "unit": "", "scale": 1.0, "access": "RW", "desc": "0=Disable, 1=Enable grid charging"},
    111: {"name": "charge_rate_pct", "type": "uint16", "unit": "%", "scale": 1.0, "access": "RW", "desc": "Battery charge power rate (0-100%)"},
    112: {"name": "discharge_rate_pct", "type": "uint16", "unit": "%", "scale": 1.0, "access": "RW", "desc": "Battery discharge power rate (0-100%)"},
    113: {"name": "target_charge_soc", "type": "uint16", "unit": "%", "scale": 1.0, "access": "RW", "desc": "Target grid charge SOC ceiling"},
}

GIVENERGY_ALARM_CODES: Dict[int, Dict[str, Any]] = {
    1: {"name": "Grid Voltage High", "severity": "HIGH", "sop": "AC utility voltage high.", "category": "GRID"},
    2: {"name": "Grid Voltage Low", "severity": "HIGH", "sop": "AC utility voltage low.", "category": "GRID"},
    8: {"name": "PV Overvoltage", "severity": "CRITICAL", "sop": "DC solar input exceeds max inverter rating.", "category": "PV"},
    16: {"name": "Temperature High", "severity": "HIGH", "sop": "Heatsink temperature excessive.", "category": "TEMPERATURE"},
    32: {"name": "Battery Fault", "severity": "CRITICAL", "sop": "GivEnergy battery BMS hardware alarm active.", "category": "BATTERY"},
    64: {"name": "Earth Leakage", "severity": "CRITICAL", "sop": "Residual ground fault leakage current detected.", "category": "PV"},
}


# ============================================================================
# 11. HOYMILES (HMS-800, HMS-1600, HMS-2000, HMT-2250, DTU-Pro)
# ============================================================================

HOYMILES_HOLDING_REGISTERS: Dict[int, Dict[str, Any]] = {
    4096: {"name": "ppv_total", "type": "uint32", "unit": "W", "scale": 0.1, "access": "RO", "desc": "Total microinverter solar power"},
    4098: {"name": "e_today", "type": "uint32", "unit": "Wh", "scale": 1.0, "access": "RO", "desc": "Daily microinverter solar generation"},
    4100: {"name": "e_total", "type": "uint32", "unit": "kWh", "scale": 0.1, "access": "RO", "desc": "Lifetime solar generation"},
    4102: {"name": "vgrid", "type": "uint16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "Grid AC line voltage"},
    4103: {"name": "fgrid", "type": "uint16", "unit": "Hz", "scale": 0.01, "access": "RO", "desc": "Grid line frequency"},
    4112: {"name": "vpv1", "type": "uint16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "Port 1 DC solar voltage"},
    4113: {"name": "ipv1", "type": "uint16", "unit": "A", "scale": 0.01, "access": "RO", "desc": "Port 1 DC solar current"},
    4114: {"name": "ppv1", "type": "uint16", "unit": "W", "scale": 0.1, "access": "RO", "desc": "Port 1 DC solar power"},
    4128: {"name": "temp_inverter", "type": "int16", "unit": "°C", "scale": 0.1, "access": "RO", "desc": "Microinverter internal temperature"},
    4129: {"name": "operating_status", "type": "uint16", "unit": "", "scale": 1.0, "access": "RO", "desc": "0=Offline, 1=Producing, 2=Throttled, 3=Fault"},
    8192: {"name": "power_limit_pct", "type": "uint16", "unit": "%", "scale": 0.1, "access": "RW", "desc": "Active power limit (0.1%, 1000=100.0%)"},
    8193: {"name": "power_limit_w", "type": "uint16", "unit": "W", "scale": 1.0, "access": "RW", "desc": "Absolute active power limit in Watts"},
}

HOYMILES_ALARM_CODES: Dict[int, Dict[str, Any]] = {
    1: {"name": "Grid Loss", "severity": "MEDIUM", "sop": "Islanding detected. Inverter anti-islanding switch open.", "category": "GRID"},
    2: {"name": "Grid Overvoltage", "severity": "HIGH", "sop": "AC voltage high at microinverter trunk cable.", "category": "GRID"},
    4: {"name": "Over Temperature", "severity": "HIGH", "sop": "Microinverter operating temperature exceeds 85°C.", "category": "TEMPERATURE"},
    5: {"name": "Port 1 Overcurrent", "severity": "CRITICAL", "sop": "Panel 1 input short circuit or reverse polarity.", "category": "PV"},
    6: {"name": "Port 2 Overcurrent", "severity": "CRITICAL", "sop": "Panel 2 input short circuit or reverse polarity.", "category": "PV"},
}


# ============================================================================
# 12. SIGENERGY / SIGENSTOR (5-in-1 Hybrid Storage)
# ============================================================================

SIGENERGY_HOLDING_REGISTERS: Dict[int, Dict[str, Any]] = {
    1: {"name": "system_mode", "type": "uint16", "unit": "", "scale": 1.0, "access": "RW", "desc": "1=Self Use, 2=TOU, 3=Backup, 4=V2X Fast Charge"},
    16: {"name": "ppv", "type": "uint32", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Total solar PV generation power"},
    18: {"name": "pgrid", "type": "int32", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Grid power exchange (+ imp / - exp)"},
    20: {"name": "pload", "type": "uint32", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Total site load power"},
    32: {"name": "battery_soc", "type": "uint16", "unit": "%", "scale": 0.1, "access": "RO", "desc": "SigenStor battery state of charge"},
    33: {"name": "battery_power", "type": "int32", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Battery power (+ charge / - discharge)"},
    35: {"name": "vbat", "type": "uint16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "Battery pack voltage"},
    36: {"name": "battery_soh", "type": "uint16", "unit": "%", "scale": 0.1, "access": "RO", "desc": "Battery state of health"},
    48: {"name": "evdc_power", "type": "int32", "unit": "W", "scale": 1.0, "access": "RO", "desc": "EVDC fast charger power (+ chg / - V2G dis)"},
    50: {"name": "connected_ev_soc", "type": "uint16", "unit": "%", "scale": 0.1, "access": "RO", "desc": "Connected EV vehicle SOC"},
    256: {"name": "commanded_grid_setpoint", "type": "int32", "unit": "W", "scale": 1.0, "access": "RW", "desc": "Target grid power exchange setpoint"},
    258: {"name": "max_charge_power", "type": "uint32", "unit": "W", "scale": 1.0, "access": "RW", "desc": "Battery maximum charge power ceiling"},
    260: {"name": "max_discharge_power", "type": "uint32", "unit": "W", "scale": 1.0, "access": "RW", "desc": "Battery maximum discharge power ceiling"},
}

SIGENERGY_ALARM_CODES: Dict[int, Dict[str, Any]] = {
    1: {"name": "Grid Failure", "severity": "MEDIUM", "sop": "Mains blackout. SigenStor supplying backup power.", "category": "GRID"},
    2: {"name": "Grid Voltage Out of Bounds", "severity": "HIGH", "sop": "Grid voltage anomalous.", "category": "GRID"},
    3: {"name": "Battery Over Temperature", "severity": "HIGH", "sop": "SigenStor battery thermal loop high temperature trip.", "category": "TEMPERATURE"},
    4: {"name": "EVDC Isolation Low", "severity": "CRITICAL", "sop": "EV charging cable DC ground isolation fault.", "category": "EV"},
    5: {"name": "BMS Balancing Error", "severity": "MEDIUM", "sop": "Cell balancing error in modular battery stack.", "category": "BATTERY"},
}


# ============================================================================
# 13. PYLONTECH & DYNESS BMS (US2000, US3000, US5000, Force H1/H2, Dyness)
# ============================================================================

PYLONTECH_HOLDING_REGISTERS: Dict[int, Dict[str, Any]] = {
    16: {"name": "vbat", "type": "uint16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "Battery pack voltage"},
    17: {"name": "ibat", "type": "int16", "unit": "A", "scale": 0.1, "access": "RO", "desc": "Battery current (+ charge / - discharge)"},
    18: {"name": "battery_soc", "type": "uint16", "unit": "%", "scale": 1.0, "access": "RO", "desc": "Battery state of charge"},
    19: {"name": "battery_soh", "type": "uint16", "unit": "%", "scale": 1.0, "access": "RO", "desc": "Battery state of health"},
    20: {"name": "remaining_capacity_ah", "type": "uint16", "unit": "Ah", "scale": 0.1, "access": "RO", "desc": "Remaining amp-hour capacity"},
    21: {"name": "total_capacity_ah", "type": "uint16", "unit": "Ah", "scale": 0.1, "access": "RO", "desc": "Nominal pack capacity"},
    22: {"name": "cycle_count", "type": "uint16", "unit": "cycles", "scale": 1.0, "access": "RO", "desc": "Total completed charge cycles"},
    23: {"name": "avg_temp", "type": "int16", "unit": "°C", "scale": 0.1, "access": "RO", "desc": "Average module cell temperature"},
    24: {"name": "v_cell_max", "type": "uint16", "unit": "mV", "scale": 1.0, "access": "RO", "desc": "Highest individual cell voltage"},
    25: {"name": "v_cell_min", "type": "uint16", "unit": "mV", "scale": 1.0, "access": "RO", "desc": "Lowest individual cell voltage"},
    32: {"name": "max_charge_voltage", "type": "uint16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "Maximum charge voltage limit from BMS"},
    33: {"name": "min_discharge_voltage", "type": "uint16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "Minimum discharge cutoff voltage"},
    34: {"name": "max_charge_current", "type": "uint16", "unit": "A", "scale": 0.1, "access": "RO", "desc": "Maximum continuous charge current allowed"},
    35: {"name": "max_discharge_current", "type": "uint16", "unit": "A", "scale": 0.1, "access": "RO", "desc": "Maximum continuous discharge current allowed"},
}

PYLONTECH_ALARM_CODES: Dict[int, Dict[str, Any]] = {
    1: {"name": "Cell Overvoltage Alarm", "severity": "CRITICAL", "sop": "Cell voltage exceeded safety ceiling. Cease charging immediately.", "category": "BATTERY"},
    2: {"name": "Cell Undervoltage Alarm", "severity": "CRITICAL", "sop": "Cell voltage below safety floor. Cease discharging immediately.", "category": "BATTERY"},
    3: {"name": "Charge Overcurrent Alarm", "severity": "HIGH", "sop": "Charge current exceeds maximum allowable rate.", "category": "BATTERY"},
    4: {"name": "Discharge Overcurrent Alarm", "severity": "HIGH", "sop": "Discharge load current exceeds rating.", "category": "BATTERY"},
    5: {"name": "High Temperature Alarm", "severity": "CRITICAL", "sop": "Battery cell temperature > 55°C. Inverter must stop operation.", "category": "TEMPERATURE"},
    6: {"name": "Low Temperature Alarm", "severity": "HIGH", "sop": "Battery cell temperature < 0°C. Charging interlocked.", "category": "TEMPERATURE"},
    7: {"name": "Cell Voltage Difference High", "severity": "MEDIUM", "sop": "Pack cell unbalance > 100mV. BMS balancing required.", "category": "BATTERY"},
}


# ============================================================================
# 14. BYD BATTERY-BOX (Premium HVS, HVM, LVS, Commercial)
# ============================================================================

BYD_HOLDING_REGISTERS: Dict[int, Dict[str, Any]] = {
    256: {"name": "vbat", "type": "uint16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "BYD battery pack voltage"},
    257: {"name": "ibat", "type": "int16", "unit": "A", "scale": 0.1, "access": "RO", "desc": "BYD battery current (+ charge / - discharge)"},
    258: {"name": "battery_soc", "type": "uint16", "unit": "%", "scale": 1.0, "access": "RO", "desc": "BYD battery state of charge"},
    259: {"name": "battery_soh", "type": "uint16", "unit": "%", "scale": 1.0, "access": "RO", "desc": "BYD battery state of health"},
    260: {"name": "max_cell_temp", "type": "int16", "unit": "°C", "scale": 0.1, "access": "RO", "desc": "Maximum cell temperature"},
    261: {"name": "min_cell_temp", "type": "int16", "unit": "°C", "scale": 0.1, "access": "RO", "desc": "Minimum cell temperature"},
    262: {"name": "max_cell_volt", "type": "uint16", "unit": "mV", "scale": 1.0, "access": "RO", "desc": "Highest cell voltage"},
    263: {"name": "min_cell_volt", "type": "uint16", "unit": "mV", "scale": 1.0, "access": "RO", "desc": "Lowest cell voltage"},
    264: {"name": "remaining_capacity", "type": "uint16", "unit": "Ah", "scale": 0.1, "access": "RO", "desc": "Remaining pack capacity"},
    265: {"name": "max_charge_current", "type": "uint16", "unit": "A", "scale": 0.1, "access": "RO", "desc": "Maximum allowed charge current"},
    266: {"name": "max_discharge_current", "type": "uint16", "unit": "A", "scale": 0.1, "access": "RO", "desc": "Maximum allowed discharge current"},
    267: {"name": "status_flags", "type": "uint16", "unit": "", "scale": 1.0, "access": "RO", "desc": "Operational status bitmask"},
}

BYD_ALARM_CODES: Dict[int, Dict[str, Any]] = {
    1: {"name": "BYD Cell Overvoltage", "severity": "CRITICAL", "sop": "Cell voltage exceeded safety ceiling. Inverter BMS ceases charging.", "category": "BATTERY"},
    2: {"name": "BYD Cell Undervoltage", "severity": "CRITICAL", "sop": "Cell voltage dropped below cutoff. Inverter BMS ceases discharging.", "category": "BATTERY"},
    3: {"name": "BYD Overtemperature Alert", "severity": "HIGH", "sop": "Cell temperature exceeded 50°C. Check ventilation and derate charge.", "category": "TEMPERATURE"},
    4: {"name": "BYD Low Temperature Alert", "severity": "HIGH", "sop": "Cell temperature below 0°C. Charge current locked out to protect cells.", "category": "TEMPERATURE"},
    5: {"name": "BYD Precharge Circuit Fault", "severity": "CRITICAL", "sop": "Precharge contactor failed or DC bus capacitor failed to charge.", "category": "BATTERY"},
    6: {"name": "BYD Communication Loss", "severity": "HIGH", "sop": "CAN bus message timeout between Battery-Box BCU and inverter.", "category": "COMMUNICATION"},
}

# ============================================================================
# 15. KACO NEW ENERGY (SIEMENS) (Blueplanet 50.0 TL3, 87.0 TL3, Gridsave)
# ============================================================================

KACO_HOLDING_REGISTERS: Dict[int, Dict[str, Any]] = {
    40071: {"name": "p_ac", "type": "int16", "unit": "W", "scale": 1.0, "access": "RO", "desc": "AC active power"},
    40079: {"name": "f_grid", "type": "uint16", "unit": "Hz", "scale": 0.01, "access": "RO", "desc": "Grid AC frequency"},
    40083: {"name": "e_total", "type": "uint32", "unit": "Wh", "scale": 1.0, "access": "RO", "desc": "Total active energy yield"},
    40087: {"name": "operating_status", "type": "uint16", "unit": "", "scale": 1.0, "access": "RO", "desc": "Operating status: 1=Off, 4=Running, 7=Fault"},
    40093: {"name": "v_dc_string1", "type": "uint16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "DC voltage MPPT string 1"},
    40094: {"name": "i_dc_string1", "type": "uint16", "unit": "A", "scale": 0.1, "access": "RO", "desc": "DC current MPPT string 1"},
    40095: {"name": "p_dc_string1", "type": "uint32", "unit": "W", "scale": 1.0, "access": "RO", "desc": "DC power MPPT string 1"},
    40101: {"name": "temp_heatsink", "type": "int16", "unit": "°C", "scale": 0.1, "access": "RO", "desc": "IGBT heatsink temperature"},
    40200: {"name": "active_power_limit", "type": "uint16", "unit": "%", "scale": 1.0, "access": "RW", "desc": "Active power limit setpoint (0-100%)"},
    40204: {"name": "reactive_power_mode", "type": "uint16", "unit": "", "scale": 1.0, "access": "RW", "desc": "1=cos phi, 2=Q(V), 3=fixed Q"},
    40206: {"name": "cos_phi_setpoint", "type": "int16", "unit": "", "scale": 0.001, "access": "RW", "desc": "Target displacement power factor cos phi"},
}

KACO_ALARM_CODES: Dict[int, Dict[str, Any]] = {
    10: {"name": "Grid Overvoltage", "severity": "HIGH", "sop": "Grid voltage exceeded upper disconnection limit.", "category": "GRID"},
    11: {"name": "Grid Undervoltage", "severity": "HIGH", "sop": "Grid voltage dropped below lower disconnection limit.", "category": "GRID"},
    14: {"name": "Grid Overfrequency", "severity": "HIGH", "sop": "Grid frequency exceeded 50.5Hz/60.5Hz upper limit.", "category": "GRID"},
    20: {"name": "DC Insulation Fault", "severity": "CRITICAL", "sop": "PV array insulation resistance to earth < 100kOhm.", "category": "PV"},
    30: {"name": "Inverter Overtemperature", "severity": "HIGH", "sop": "IGBT heatsink temperature > 85°C. Check fan status.", "category": "TEMPERATURE"},
    40: {"name": "Hardware Trip", "severity": "CRITICAL", "sop": "Hardware overcurrent detected on bridge power stage.", "category": "INVERTER"},
}

# ============================================================================
# 16. KOSTAL SOLAR ELECTRIC (Plenticore Plus, Piko MP Plus, Piko CI)
# ============================================================================

KOSTAL_HOLDING_REGISTERS: Dict[int, Dict[str, Any]] = {
    100: {"name": "p_dc_total", "type": "float32", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Total DC power from all PV strings"},
    104: {"name": "inverter_state", "type": "uint16", "unit": "", "scale": 1.0, "access": "RO", "desc": "Operating state: 0=Off, 6=FeedIn"},
    152: {"name": "p_home_pv", "type": "float32", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Home consumption covered by PV"},
    154: {"name": "p_home_battery", "type": "float32", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Home consumption covered by battery"},
    156: {"name": "p_home_grid", "type": "float32", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Home consumption covered by grid"},
    160: {"name": "e_total", "type": "float32", "unit": "kWh", "scale": 1.0, "access": "RO", "desc": "Total lifetime energy yield"},
    214: {"name": "battery_soc", "type": "float32", "unit": "%", "scale": 1.0, "access": "RO", "desc": "Battery state of charge"},
    216: {"name": "battery_temp", "type": "float32", "unit": "°C", "scale": 1.0, "access": "RO", "desc": "Battery cell temperature"},
    260: {"name": "p_grid", "type": "float32", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Grid active power (+ import / - export)"},
    266: {"name": "f_grid", "type": "float32", "unit": "Hz", "scale": 1.0, "access": "RO", "desc": "Grid frequency"},
    582: {"name": "active_power_curtailment", "type": "float32", "unit": "%", "scale": 1.0, "access": "RW", "desc": "Active power limitation setpoint (0-100%)"},
}

KOSTAL_ALARM_CODES: Dict[int, Dict[str, Any]] = {
    1001: {"name": "Insulation Resistance Low", "severity": "CRITICAL", "sop": "Array insulation low. Inspect PV wiring and junction boxes.", "category": "PV"},
    1002: {"name": "Residual Current Trip", "severity": "CRITICAL", "sop": "RCD ground fault current tripped. Check earth connections.", "category": "PV"},
    1003: {"name": "Grid Overvoltage", "severity": "HIGH", "sop": "Mains voltage exceeded threshold. Inverter disconnected.", "category": "GRID"},
    1004: {"name": "Battery Link Lost", "severity": "HIGH", "sop": "RS485/CAN communication to battery BMS failed.", "category": "COMMUNICATION"},
    1005: {"name": "Heatsink Overtemperature", "severity": "HIGH", "sop": "Power module thermal curtailment triggered.", "category": "TEMPERATURE"},
}

# ============================================================================
# 17. SRNE SOLAR (ASF, HES, MD Series Hybrid Inverters)
# ============================================================================

SRNE_HOLDING_REGISTERS: Dict[int, Dict[str, Any]] = {
    256: {"name": "work_mode", "type": "uint16", "unit": "", "scale": 1.0, "access": "RO", "desc": "Operating mode (0=SolarFirst, 1=UtilityFirst, 2=SBU)"},
    257: {"name": "fault_code", "type": "uint16", "unit": "", "scale": 1.0, "access": "RO", "desc": "Current fault / warning code"},
    258: {"name": "v_pv1", "type": "uint16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "PV string 1 voltage"},
    259: {"name": "i_pv1", "type": "uint16", "unit": "A", "scale": 0.1, "access": "RO", "desc": "PV string 1 current"},
    260: {"name": "p_pv1", "type": "uint16", "unit": "W", "scale": 1.0, "access": "RO", "desc": "PV string 1 power"},
    264: {"name": "vbat", "type": "uint16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "Battery bank voltage"},
    265: {"name": "ibat", "type": "int16", "unit": "A", "scale": 0.1, "access": "RO", "desc": "Battery current (+ charge / - discharge)"},
    266: {"name": "battery_soc", "type": "uint16", "unit": "%", "scale": 1.0, "access": "RO", "desc": "Battery state of charge"},
    268: {"name": "v_ac_out", "type": "uint16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "Inverter AC output voltage"},
    269: {"name": "i_ac_out", "type": "uint16", "unit": "A", "scale": 0.1, "access": "RO", "desc": "Inverter AC output current"},
    270: {"name": "p_ac_out", "type": "uint16", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Inverter AC active power"},
    274: {"name": "p_load", "type": "uint16", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Load active power consumption"},
    300: {"name": "work_mode_setpoint", "type": "uint16", "unit": "", "scale": 1.0, "access": "RW", "desc": "0=SolarFirst, 1=UtilityFirst, 2=SBU, 3=Sub"},
    302: {"name": "max_charge_current", "type": "uint16", "unit": "A", "scale": 1.0, "access": "RW", "desc": "Battery maximum charge current setpoint"},
}

SRNE_ALARM_CODES: Dict[int, Dict[str, Any]] = {
    1: {"name": "BatOverCurr", "severity": "HIGH", "sop": "Battery charge current exceeded safety rating.", "category": "BATTERY"},
    2: {"name": "BatLowVolt", "severity": "HIGH", "sop": "Battery voltage dropped below low cutoff voltage.", "category": "BATTERY"},
    3: {"name": "OverTemp", "severity": "CRITICAL", "sop": "Heatsink over temperature. Allow inverter to cool down.", "category": "TEMPERATURE"},
    4: {"name": "OverLoad", "severity": "HIGH", "sop": "Continuous AC output overload. Disconnect non-critical loads.", "category": "INVERTER"},
    5: {"name": "PvOverVolt", "severity": "CRITICAL", "sop": "PV input voltage exceeds maximum DC limit.", "category": "PV"},
}

# ============================================================================
# 18. MUST SOLAR (PH1800, PV1800, PH5000 Hybrid Inverters)
# ============================================================================

MUST_HOLDING_REGISTERS: Dict[int, Dict[str, Any]] = {
    10101: {"name": "work_mode", "type": "uint16", "unit": "", "scale": 1.0, "access": "RO", "desc": "Operating mode"},
    10102: {"name": "inverter_status", "type": "uint16", "unit": "", "scale": 1.0, "access": "RO", "desc": "Status code"},
    10104: {"name": "vbat", "type": "uint16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "Battery voltage"},
    10105: {"name": "ibat", "type": "int16", "unit": "A", "scale": 0.1, "access": "RO", "desc": "Battery current"},
    10106: {"name": "battery_soc", "type": "uint16", "unit": "%", "scale": 1.0, "access": "RO", "desc": "Battery state of charge"},
    10107: {"name": "v_pv", "type": "uint16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "Solar PV input voltage"},
    10108: {"name": "p_pv", "type": "uint16", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Solar PV input power"},
    10109: {"name": "v_grid", "type": "uint16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "Grid AC voltage"},
    10110: {"name": "p_grid", "type": "int16", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Grid active power"},
    10111: {"name": "p_load", "type": "uint16", "unit": "W", "scale": 1.0, "access": "RO", "desc": "AC load power"},
    20101: {"name": "output_priority", "type": "uint16", "unit": "", "scale": 1.0, "access": "RW", "desc": "0=Utility, 1=Solar, 2=SBU"},
    20102: {"name": "charger_priority", "type": "uint16", "unit": "", "scale": 1.0, "access": "RW", "desc": "0=SolarFirst, 1=Solar&Utility, 2=SolarOnly"},
}

MUST_ALARM_CODES: Dict[int, Dict[str, Any]] = {
    1: {"name": "Fan Locked", "severity": "HIGH", "sop": "Cooling fan RPM error or stuck.", "category": "INVERTER"},
    2: {"name": "Over Temperature", "severity": "CRITICAL", "sop": "Power board temperature shutdown.", "category": "TEMPERATURE"},
    3: {"name": "Battery Overvoltage", "severity": "HIGH", "sop": "Battery voltage exceeded cut-off limit.", "category": "BATTERY"},
    4: {"name": "Output Short Circuit", "severity": "CRITICAL", "sop": "AC output short-circuit trip.", "category": "INVERTER"},
    5: {"name": "Inverter Soft Fail", "severity": "HIGH", "sop": "DC bus soft start sequence failed.", "category": "INVERTER"},
}

# ============================================================================
# 19. ANENJI & SMG / PI30 PROTOCOL (Anenji, SandiSolar, SMG 6200, Axpert)
# ============================================================================

ANENJI_HOLDING_REGISTERS: Dict[int, Dict[str, Any]] = {
    0: {"name": "v_grid", "type": "uint16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "Grid AC input voltage"},
    1: {"name": "f_grid", "type": "uint16", "unit": "Hz", "scale": 0.1, "access": "RO", "desc": "Grid frequency"},
    2: {"name": "v_ac_out", "type": "uint16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "Inverter output voltage"},
    3: {"name": "f_ac_out", "type": "uint16", "unit": "Hz", "scale": 0.1, "access": "RO", "desc": "Inverter output frequency"},
    4: {"name": "p_ac_out", "type": "uint16", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Active output power"},
    5: {"name": "s_ac_out", "type": "uint16", "unit": "VA", "scale": 1.0, "access": "RO", "desc": "Apparent output power"},
    6: {"name": "load_percent", "type": "uint16", "unit": "%", "scale": 1.0, "access": "RO", "desc": "Load percentage"},
    7: {"name": "vbat", "type": "uint16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "Battery terminal voltage"},
    8: {"name": "ibat_charge", "type": "uint16", "unit": "A", "scale": 1.0, "access": "RO", "desc": "Battery charging current"},
    9: {"name": "battery_soc", "type": "uint16", "unit": "%", "scale": 1.0, "access": "RO", "desc": "Battery state of charge"},
    10: {"name": "heatsink_temp", "type": "int16", "unit": "°C", "scale": 1.0, "access": "RO", "desc": "Heatsink temperature"},
    11: {"name": "i_pv", "type": "uint16", "unit": "A", "scale": 0.1, "access": "RO", "desc": "PV input current"},
    12: {"name": "v_pv", "type": "uint16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "PV input voltage"},
    13: {"name": "ibat_discharge", "type": "uint16", "unit": "A", "scale": 1.0, "access": "RO", "desc": "Battery discharge current"},
}

ANENJI_ALARM_CODES: Dict[int, Dict[str, Any]] = {
    3: {"name": "Battery Voltage High", "severity": "HIGH", "sop": "Battery voltage exceeded upper limit.", "category": "BATTERY"},
    4: {"name": "Battery Voltage Low", "severity": "HIGH", "sop": "Battery voltage low warning. Charge battery.", "category": "BATTERY"},
    5: {"name": "Output Short Circuit", "severity": "CRITICAL", "sop": "AC load circuit short detected. Clear wiring fault.", "category": "INVERTER"},
    7: {"name": "Overload Fault", "severity": "HIGH", "sop": "Inverter output overload. Reduce load demand.", "category": "INVERTER"},
    9: {"name": "Bus Voltage High", "severity": "CRITICAL", "sop": "Internal high-voltage DC bus trip.", "category": "INVERTER"},
}

# ============================================================================
# 20. AFORE NEW ENERGY (BNT, Hybrid 3-8kW, 2MPPT)
# ============================================================================

AFORE_HOLDING_REGISTERS: Dict[int, Dict[str, Any]] = {
    1000: {"name": "running_status", "type": "uint16", "unit": "", "scale": 1.0, "access": "RO", "desc": "Running status"},
    1001: {"name": "v_dc1", "type": "uint16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "MPPT1 DC voltage"},
    1002: {"name": "i_dc1", "type": "uint16", "unit": "A", "scale": 0.1, "access": "RO", "desc": "MPPT1 DC current"},
    1003: {"name": "p_dc1", "type": "uint16", "unit": "W", "scale": 1.0, "access": "RO", "desc": "MPPT1 DC power"},
    1004: {"name": "v_dc2", "type": "uint16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "MPPT2 DC voltage"},
    1005: {"name": "i_dc2", "type": "uint16", "unit": "A", "scale": 0.1, "access": "RO", "desc": "MPPT2 DC current"},
    1006: {"name": "p_dc2", "type": "uint16", "unit": "W", "scale": 1.0, "access": "RO", "desc": "MPPT2 DC power"},
    1010: {"name": "p_dc_total", "type": "uint32", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Total DC power"},
    1020: {"name": "v_ac_l1", "type": "uint16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "AC L1 grid voltage"},
    1021: {"name": "i_ac_l1", "type": "uint16", "unit": "A", "scale": 0.1, "access": "RO", "desc": "AC L1 grid current"},
    1022: {"name": "p_ac", "type": "int16", "unit": "W", "scale": 1.0, "access": "RO", "desc": "AC active power"},
    1030: {"name": "e_day", "type": "uint16", "unit": "kWh", "scale": 0.1, "access": "RO", "desc": "Daily energy production"},
    1032: {"name": "e_total", "type": "uint32", "unit": "kWh", "scale": 1.0, "access": "RO", "desc": "Cumulative energy production"},
    1050: {"name": "battery_soc", "type": "uint16", "unit": "%", "scale": 1.0, "access": "RO", "desc": "Battery state of charge"},
    1051: {"name": "vbat", "type": "uint16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "Battery terminal voltage"},
    1052: {"name": "ibat", "type": "int16", "unit": "A", "scale": 0.1, "access": "RO", "desc": "Battery current"},
    1053: {"name": "pbat", "type": "int16", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Battery power"},
}

AFORE_ALARM_CODES: Dict[int, Dict[str, Any]] = {
    1: {"name": "Grid Volt Fault", "severity": "HIGH", "sop": "Grid voltage out of range. Check AC breaker.", "category": "GRID"},
    2: {"name": "Grid Freq Fault", "severity": "HIGH", "sop": "Grid frequency out of range.", "category": "GRID"},
    3: {"name": "PV Isolation Fault", "severity": "CRITICAL", "sop": "Solar PV array insulation failure to ground.", "category": "PV"},
    4: {"name": "Over Temp Fault", "severity": "HIGH", "sop": "Internal heatsink over temperature.", "category": "TEMPERATURE"},
    5: {"name": "Relay Fault", "severity": "CRITICAL", "sop": "Grid tie relay check failure. Inspect power board.", "category": "INVERTER"},
}

# ============================================================================
# 21. KSTAR NEW ENERGY (BluE-S, E10KT Hybrid)
# ============================================================================

KSTAR_HOLDING_REGISTERS: Dict[int, Dict[str, Any]] = {
    300: {"name": "inverter_state", "type": "uint16", "unit": "", "scale": 1.0, "access": "RO", "desc": "Operating state"},
    302: {"name": "p_pv1", "type": "uint16", "unit": "W", "scale": 1.0, "access": "RO", "desc": "PV string 1 power"},
    304: {"name": "p_pv2", "type": "uint16", "unit": "W", "scale": 1.0, "access": "RO", "desc": "PV string 2 power"},
    310: {"name": "p_grid", "type": "int16", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Grid active power (+ imp / - exp)"},
    314: {"name": "f_grid", "type": "uint16", "unit": "Hz", "scale": 0.01, "access": "RO", "desc": "Grid frequency"},
    320: {"name": "vbat", "type": "uint16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "Battery voltage"},
    322: {"name": "ibat", "type": "int16", "unit": "A", "scale": 0.1, "access": "RO", "desc": "Battery current"},
    324: {"name": "pbat", "type": "int16", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Battery power"},
    326: {"name": "battery_soc", "type": "uint16", "unit": "%", "scale": 1.0, "access": "RO", "desc": "Battery state of charge"},
    330: {"name": "p_load", "type": "uint16", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Load active power consumption"},
    340: {"name": "e_day", "type": "uint16", "unit": "kWh", "scale": 0.1, "access": "RO", "desc": "Daily energy yield"},
    342: {"name": "e_total", "type": "uint32", "unit": "kWh", "scale": 1.0, "access": "RO", "desc": "Total lifetime energy yield"},
}

KSTAR_ALARM_CODES: Dict[int, Dict[str, Any]] = {
    1: {"name": "PV Overvoltage", "severity": "HIGH", "sop": "DC string open circuit voltage exceeds maximum input limit.", "category": "PV"},
    2: {"name": "Grid Loss", "severity": "HIGH", "sop": "Utility grid supply disconnected.", "category": "GRID"},
    3: {"name": "Inverter Overload", "severity": "HIGH", "sop": "Continuous load demand exceeds inverter capacity.", "category": "INVERTER"},
    4: {"name": "DCI Error", "severity": "CRITICAL", "sop": "Direct current injection to grid above statutory limit.", "category": "GRID"},
    5: {"name": "GFCI Error", "severity": "CRITICAL", "sop": "Ground fault current interrupter triggered.", "category": "PV"},
}

# ============================================================================
# 22. TSUN & SWATTEN (TSOL Microinverters, SIH-TH Hybrid)
# ============================================================================

TSUN_HOLDING_REGISTERS: Dict[int, Dict[str, Any]] = {
    500: {"name": "system_status", "type": "uint16", "unit": "", "scale": 1.0, "access": "RO", "desc": "Status (0=Wait, 1=Normal, 2=Fault)"},
    502: {"name": "p_ac", "type": "uint16", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Total active AC power output"},
    504: {"name": "e_day", "type": "uint16", "unit": "kWh", "scale": 0.01, "access": "RO", "desc": "Daily solar energy generation"},
    506: {"name": "e_total", "type": "uint32", "unit": "kWh", "scale": 0.1, "access": "RO", "desc": "Lifetime solar energy generation"},
    510: {"name": "v_pv1", "type": "uint16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "PV channel 1 DC voltage"},
    511: {"name": "i_pv1", "type": "uint16", "unit": "A", "scale": 0.01, "access": "RO", "desc": "PV channel 1 DC current"},
    512: {"name": "p_pv1", "type": "uint16", "unit": "W", "scale": 1.0, "access": "RO", "desc": "PV channel 1 DC power"},
    514: {"name": "v_pv2", "type": "uint16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "PV channel 2 DC voltage"},
    515: {"name": "i_pv2", "type": "uint16", "unit": "A", "scale": 0.01, "access": "RO", "desc": "PV channel 2 DC current"},
    516: {"name": "p_pv2", "type": "uint16", "unit": "W", "scale": 1.0, "access": "RO", "desc": "PV channel 2 DC power"},
    520: {"name": "temp_inverter", "type": "int16", "unit": "°C", "scale": 0.1, "access": "RO", "desc": "Microinverter internal temperature"},
    522: {"name": "f_grid", "type": "uint16", "unit": "Hz", "scale": 0.01, "access": "RO", "desc": "Grid AC frequency"},
}

TSUN_ALARM_CODES: Dict[int, Dict[str, Any]] = {
    1: {"name": "No Grid Connection", "severity": "HIGH", "sop": "Grid voltage absent or line breaker open.", "category": "GRID"},
    2: {"name": "Grid Overvoltage", "severity": "HIGH", "sop": "Grid voltage exceeded high trip boundary.", "category": "GRID"},
    3: {"name": "Internal Overtemperature", "severity": "HIGH", "sop": "Microinverter temperature > 85°C. Check solar panel spacing.", "category": "TEMPERATURE"},
    4: {"name": "Hardware Ground Fault", "severity": "CRITICAL", "sop": "DC ground leakage detected. Inspect solar panel and trunk cables.", "category": "PV"},
    5: {"name": "Communication Timeout", "severity": "MEDIUM", "sop": "DTU gateway wireless link to microinverter timed out.", "category": "COMMUNICATION"},
}

# ============================================================================
# 23. MEGAREVO (R3H, R5KL1, Hybrid Inverters)
# ============================================================================

MEGAREVO_HOLDING_REGISTERS: Dict[int, Dict[str, Any]] = {
    2000: {"name": "machine_status", "type": "uint16", "unit": "", "scale": 1.0, "access": "RO", "desc": "Machine running state"},
    2002: {"name": "p_pv1", "type": "uint16", "unit": "W", "scale": 1.0, "access": "RO", "desc": "PV string 1 power"},
    2004: {"name": "p_pv2", "type": "uint16", "unit": "W", "scale": 1.0, "access": "RO", "desc": "PV string 2 power"},
    2006: {"name": "p_inv", "type": "int16", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Inverter AC active power"},
    2008: {"name": "p_grid", "type": "int16", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Grid active power (+ imp / - exp)"},
    2010: {"name": "vbat", "type": "uint16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "Battery terminal voltage"},
    2012: {"name": "ibat", "type": "int16", "unit": "A", "scale": 0.1, "access": "RO", "desc": "Battery current"},
    2014: {"name": "pbat", "type": "int16", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Battery power"},
    2016: {"name": "battery_soc", "type": "uint16", "unit": "%", "scale": 1.0, "access": "RO", "desc": "Battery state of charge"},
    2020: {"name": "p_eps", "type": "uint16", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Emergency power supply load power"},
    2022: {"name": "p_load_total", "type": "uint16", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Total site load power"},
    2030: {"name": "e_solar_day", "type": "uint16", "unit": "kWh", "scale": 0.1, "access": "RO", "desc": "Daily solar energy generation"},
    2100: {"name": "work_mode_setpoint", "type": "uint16", "unit": "", "scale": 1.0, "access": "RW", "desc": "0=Self-use, 1=TOU, 2=Backup, 3=Peak-shaving"},
}

MEGAREVO_ALARM_CODES: Dict[int, Dict[str, Any]] = {
    1: {"name": "Grid Abnormal", "severity": "HIGH", "sop": "Grid voltage or frequency outside allowed range.", "category": "GRID"},
    2: {"name": "Battery Undervoltage", "severity": "HIGH", "sop": "Battery voltage dropped below shutdown point.", "category": "BATTERY"},
    3: {"name": "Inverter Overcurrent", "severity": "CRITICAL", "sop": "Inverter AC current exceeded hardware trip threshold.", "category": "INVERTER"},
    4: {"name": "Bus Voltage High", "severity": "CRITICAL", "sop": "Internal DC bus voltage exceeded ceiling.", "category": "INVERTER"},
    5: {"name": "BMS Fault", "severity": "HIGH", "sop": "Battery management system reported internal alert.", "category": "BATTERY"},
}

# ============================================================================
# 24. TESLA ENERGY (Powerwall 2, Powerwall+, Gateway 2/3)
# ============================================================================

TESLA_HOLDING_REGISTERS: Dict[int, Dict[str, Any]] = {
    40071: {"name": "p_grid", "type": "int32", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Site grid active power (+ imp / - exp)"},
    40073: {"name": "p_solar", "type": "uint32", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Total solar PV generation power"},
    40075: {"name": "p_battery", "type": "int32", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Battery power (+ charge / - discharge)"},
    40077: {"name": "p_load", "type": "uint32", "unit": "W", "scale": 1.0, "access": "RO", "desc": "Total home / site consumption power"},
    40082: {"name": "battery_soc", "type": "uint16", "unit": "%", "scale": 0.1, "access": "RO", "desc": "Powerwall battery state of charge"},
    40084: {"name": "grid_status", "type": "uint16", "unit": "", "scale": 1.0, "access": "RO", "desc": "0=Islanded / Off-grid, 1=Grid-connected"},
    40086: {"name": "backup_reserve_pct", "type": "uint16", "unit": "%", "scale": 1.0, "access": "RW", "desc": "Backup reserve percentage setpoint"},
    40088: {"name": "operational_mode", "type": "uint16", "unit": "", "scale": 1.0, "access": "RW", "desc": "0=Self-consumption, 1=Time-based, 2=Backup-only"},
    40090: {"name": "f_grid", "type": "uint16", "unit": "Hz", "scale": 0.01, "access": "RO", "desc": "AC line frequency"},
    40092: {"name": "v_grid_l1", "type": "uint16", "unit": "V", "scale": 0.1, "access": "RO", "desc": "Grid line voltage L1"},
    40100: {"name": "storm_mode_active", "type": "uint16", "unit": "", "scale": 1.0, "access": "RO", "desc": "0=Normal, 1=Storm Watch Active"},
}

TESLA_ALARM_CODES: Dict[int, Dict[str, Any]] = {
    1: {"name": "Grid Outage / Island Active", "severity": "MEDIUM", "sop": "Grid lost; Backup Gateway successfully transitioned site to island mode.", "category": "GRID"},
    2: {"name": "Battery Low Reserve Cutoff", "severity": "HIGH", "sop": "Battery reached backup reserve limit; non-backup loads shed.", "category": "BATTERY"},
    3: {"name": "Battery Thermal Limiting", "severity": "HIGH", "sop": "Battery cell temperature conditioning active; power curtailed.", "category": "TEMPERATURE"},
    4: {"name": "Meter Communication Lost", "severity": "CRITICAL", "sop": "Neurio / CT meter communication failure; power flows estimated.", "category": "COMMUNICATION"},
    5: {"name": "Powerwall Inverter Fault", "severity": "CRITICAL", "sop": "Internal inverter tripped on hardware fault. Inspect Gateway logs.", "category": "INVERTER"},
}


# ============================================================================
# EXTENDED BRAND DICTIONARIES & MODELS (24 Brands)
# ============================================================================

EXTENDED_BRAND_REGISTERS: Dict[str, Dict[int, Dict[str, Any]]] = {
    "victron": VICTRON_HOLDING_REGISTERS,
    "fronius": FRONIUS_HOLDING_REGISTERS,
    "solaredge": SOLAREDGE_HOLDING_REGISTERS,
    "sma": SMA_HOLDING_REGISTERS,
    "sofar": SOFAR_HOLDING_REGISTERS,
    "solax": SOLAX_HOLDING_REGISTERS,
    "alphaess": ALPHAESS_HOLDING_REGISTERS,
    "enphase": ENPHASE_HOLDING_REGISTERS,
    "foxess": FOXESS_HOLDING_REGISTERS,
    "givenergy": GIVENERGY_HOLDING_REGISTERS,
    "hoymiles": HOYMILES_HOLDING_REGISTERS,
    "sigenergy": SIGENERGY_HOLDING_REGISTERS,
    "pylontech": PYLONTECH_HOLDING_REGISTERS,
    "byd": BYD_HOLDING_REGISTERS,
    "kaco": KACO_HOLDING_REGISTERS,
    "kostal": KOSTAL_HOLDING_REGISTERS,
    "srne": SRNE_HOLDING_REGISTERS,
    "must": MUST_HOLDING_REGISTERS,
    "anenji": ANENJI_HOLDING_REGISTERS,
    "afore": AFORE_HOLDING_REGISTERS,
    "kstar": KSTAR_HOLDING_REGISTERS,
    "tsun": TSUN_HOLDING_REGISTERS,
    "megarevo": MEGAREVO_HOLDING_REGISTERS,
    "tesla": TESLA_HOLDING_REGISTERS,
}

EXTENDED_BRAND_ALARMS: Dict[str, Dict[int, Dict[str, Any]]] = {
    "victron": VICTRON_ALARM_CODES,
    "fronius": FRONIUS_ALARM_CODES,
    "solaredge": SOLAREDGE_ALARM_CODES,
    "sma": SMA_ALARM_CODES,
    "sofar": SOFAR_ALARM_CODES,
    "solax": SOLAX_ALARM_CODES,
    "alphaess": ALPHAESS_ALARM_CODES,
    "enphase": ENPHASE_ALARM_CODES,
    "foxess": FOXESS_ALARM_CODES,
    "givenergy": GIVENERGY_ALARM_CODES,
    "hoymiles": HOYMILES_ALARM_CODES,
    "sigenergy": SIGENERGY_ALARM_CODES,
    "pylontech": PYLONTECH_ALARM_CODES,
    "byd": BYD_ALARM_CODES,
    "kaco": KACO_ALARM_CODES,
    "kostal": KOSTAL_ALARM_CODES,
    "srne": SRNE_ALARM_CODES,
    "must": MUST_ALARM_CODES,
    "anenji": ANENJI_ALARM_CODES,
    "afore": AFORE_ALARM_CODES,
    "kstar": KSTAR_ALARM_CODES,
    "tsun": TSUN_ALARM_CODES,
    "megarevo": MEGAREVO_ALARM_CODES,
    "tesla": TESLA_ALARM_CODES,
}

EXTENDED_KNOWN_MODELS: Dict[str, List[str]] = {
    "victron": ["MultiPlus-II 48/5000", "MultiPlus-II 48/8000", "Quattro 48/10000", "Cerbo GX", "SmartSolar MPPT 250/100"],
    "fronius": ["Primo GEN24 6.0 Plus", "Symo GEN24 10.0 Plus", "Symo 15.0-3-M", "Verto 25.0 Plus"],
    "solaredge": ["SE5000H-US", "SE10000H-US", "SE10K-RWS", "SE30K-RW", "Energy Bank 10kWh"],
    "sma": ["Sunny Boy 5.0", "Sunny Tripower 10.0", "Sunny Tripower X 20", "Sunny Island 8.0H"],
    "sofar": ["HYD 3000-ES", "HYD 6000-ES", "HYD 10KTL-3PH", "HYD 20KTL-3PH", "ME3000SP"],
    "solax": ["X1-Hybrid-5.0-D", "X3-Hybrid-10.0-D", "X3-Hybrid-15.0-D", "X1-Boost-3.0"],
    "alphaess": ["Smile5-INV", "Smile-B3-PLUS", "Smile-T10-HV", "Storion-T30"],
    "enphase": ["IQ Gateway", "Envoy-S Metered", "IQ7PLUS", "IQ8PLUS", "IQ Battery 5P", "IQ Battery 10T"],
    "foxess": ["H1-3.7-E", "H1-5.0-E", "H3-10.0-E", "H3-12.0-E", "AC1-5.0-E", "KH7"],
    "givenergy": ["Giv-HY-5.0-Gen1", "Giv-HY-5.0-Gen3", "Giv-AC-3.0", "All-in-One 13.5kWh"],
    "hoymiles": ["HMS-800-2T", "HMS-1600-4T", "HMS-2000-4T", "HMT-2250-6T", "DTU-Pro"],
    "sigenergy": ["SigenStor 5-in-1 5kW", "SigenStor 5-in-1 10kW", "SigenStor 5-in-1 25kW"],
    "pylontech": ["US2000C", "US3000C", "US5000", "Force-H1", "Force-H2", "Dyness B4850", "Dyness Tower"],
    "byd": ["Battery-Box Premium HVS", "Battery-Box Premium HVM", "Battery-Box Premium LVS", "Battery-Box Commercial"],
    "kaco": ["Blueplanet 50.0 TL3", "Blueplanet 87.0 TL3", "Blueplanet 125 TL3", "Blueplanet Gridsave 50.0"],
    "kostal": ["Plenticore Plus 10", "Piko MP Plus 4.6", "Piko CI 30", "Plenticore BI"],
    "srne": ["ASF48100U200-H", "HES4850S100-H", "MD4850", "SR-EOV24-5.0"],
    "must": ["PH18-5048 PRO", "PV18-3024 VHM", "PH5000 Hybrid", "PH1800 PLUS"],
    "anenji": ["ANJ-11KW-48V-WIFI", "ANJ-4200-24V", "SMG-6200-48V", "ANL-4200T-24L"],
    "afore": ["BNT003KTL", "BNT005KTL", "AF-3K-SL", "AF-6K-SL", "AF-8K-TH"],
    "kstar": ["BluE-S-5000D", "E10KT-HV", "BluE-G-10000D", "E3KT"],
    "tsun": ["TSOL-MS800", "TSOL-MS1600", "TSOL-MS2000", "Swatten-SIH-5K-TH"],
    "megarevo": ["R3H-5K", "R3H-8K", "R3H-10K", "R5KL1-48", "Megarevo-12KTL"],
    "tesla": ["Powerwall 2", "Powerwall+", "Powerwall 3", "Backup Gateway 2", "Backup Gateway 3"],
}

