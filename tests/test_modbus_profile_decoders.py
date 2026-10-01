"""Unit tests for Modbus register profile decoders (new profiles).

Tests validate:
- Sungrow SHx register decode (uint16, int16, uint32, int32, scaling)
- Huawei SUN2000 register decode (gain-based, signed values)
- Modbus profile registry (get_register_map, decode_registers, fallback)
- Eybond fingerprint logic (layout_code → protocol family mapping)
- GoodWe sensor metric mapping (known keys → canonical names)

All tests use pre-computed raw values without any network calls.
"""

from __future__ import annotations

import pytest

from solar_fleet.adapters.eybond_local import (
    EYBOND_PROTOCOL_FAMILIES,
    _modbus_crc16,
    _parse_registers,
)
from solar_fleet.adapters.goodwe_local import GOODWE_SENSOR_TO_METRIC
from solar_fleet.adapters.interfaces import TouSlot
from solar_fleet.adapters.modbus_profiles import (
    decode_registers,
    get_register_map,
    list_supported_profiles,
)
from solar_fleet.adapters.modbus_profiles.deye_sunsynk_registers import (
    decode_raw_registers as deye_decode,
)
from solar_fleet.adapters.modbus_profiles.huawei_registers import (
    HUAWEI_SUN2000_REGISTERS,
)
from solar_fleet.adapters.modbus_profiles.huawei_registers import (
    decode_raw_registers as huawei_decode,
)
from solar_fleet.adapters.modbus_profiles.sungrow_registers import (
    SUNGROW_SHX_INPUT_REGISTERS,
)
from solar_fleet.adapters.modbus_profiles.sungrow_registers import (
    decode_raw_registers as sungrow_decode,
)
from solar_fleet.adapters.sunsynk_local import SunsynkLocalAdapter
from solar_fleet.domain import Device


# ---------------------------------------------------------------------------
# Sungrow SHx register decode tests
# ---------------------------------------------------------------------------
class TestSungrowDecode:
    def test_int16_inverter_temp(self):
        """Reg 5007: int16, scale 0.1, unit °C → 280 raw = 28.0°C"""
        field = next(f for f in SUNGROW_SHX_INPUT_REGISTERS
                     if f.metric == "inverter_temp" and f.address == 5007)
        raw = {str(field.address): 280}
        result = sungrow_decode(raw, SUNGROW_SHX_INPUT_REGISTERS)
        assert "inverter_temp" in result
        val, unit = result["inverter_temp"]
        assert abs(val - 28.0) < 0.01
        assert unit == "°C"

    def test_int32_battery_power_negative(self):
        """Reg 5213: int32, scale 1.0 — negative = discharge (-1000W)"""
        field = next(f for f in SUNGROW_SHX_INPUT_REGISTERS if f.metric == "battery_power")
        # -1000 as i32: 0xFFFFFC18
        raw = {
            str(field.address): 0xFFFF,
            str(field.address + 1): 0xFC18,
        }
        result = sungrow_decode(raw, SUNGROW_SHX_INPUT_REGISTERS)
        assert "battery_power" in result
        val, unit = result["battery_power"]
        assert val == -1000.0
        assert unit == "W"

    def test_uint32_energy_total(self):
        """Reg 5003: uint32, scale 0.1 — combined 65536 raw = 6553.6 kWh"""
        field = next(f for f in SUNGROW_SHX_INPUT_REGISTERS
                     if f.address == 5003 and f.metric == "energy_total")
        raw = {
            str(field.address): 1,
            str(field.address + 1): 0,
        }
        result = sungrow_decode(raw, SUNGROW_SHX_INPUT_REGISTERS)
        assert "energy_total" in result
        val, unit = result["energy_total"]
        assert abs(val - 6553.6) < 0.1
        assert unit == "kWh"

    def test_uint16_battery_soc(self):
        """Reg 5217: uint16, scale 1.0 → 85%"""
        field = next(f for f in SUNGROW_SHX_INPUT_REGISTERS if f.metric == "battery_soc")
        raw = {str(field.address): 85}
        result = sungrow_decode(raw, SUNGROW_SHX_INPUT_REGISTERS)
        assert "battery_soc" in result
        val, unit = result["battery_soc"]
        assert val == 85.0
        assert unit == "%"

    def test_empty_raw_returns_empty(self):
        """Missing register address → field not in result (no KeyError)"""
        result = sungrow_decode({}, SUNGROW_SHX_INPUT_REGISTERS)
        assert len(result) == 0

    def test_grid_power_positive_export(self):
        """Reg 5600: int32, scale 1.0 — positive = export"""
        field = next(f for f in SUNGROW_SHX_INPUT_REGISTERS if f.metric == "grid_power")
        raw = {
            str(field.address): 0,
            str(field.address + 1): 3500,
        }
        result = sungrow_decode(raw, SUNGROW_SHX_INPUT_REGISTERS)
        assert "grid_power" in result
        val, _ = result["grid_power"]
        assert val == 3500.0


# ---------------------------------------------------------------------------
# Huawei SUN2000 register decode tests (gain = divisor)
# ---------------------------------------------------------------------------
class TestHuaweiDecode:
    def test_u16_grid_voltage_gain10(self):
        """Reg 32066: u16, gain=10 → 2350 raw = 235.0V"""
        field = next(f for f in HUAWEI_SUN2000_REGISTERS if f.address == 32066)
        raw = {str(field.address): 2350}
        result = huawei_decode(raw, HUAWEI_SUN2000_REGISTERS)
        assert "grid_voltage_r" in result
        val, unit = result["grid_voltage_r"]
        assert abs(val - 235.0) < 0.01
        assert unit == "V"

    def test_i32_active_power_positive(self):
        """Reg 32080: i32, gain=1 → 5000W"""
        field = next(f for f in HUAWEI_SUN2000_REGISTERS if f.address == 32080)
        raw = {
            str(field.address): 0,
            str(field.address + 1): 5000,
        }
        result = huawei_decode(raw, HUAWEI_SUN2000_REGISTERS)
        assert "active_power" in result
        val, unit = result["active_power"]
        assert val == 5000.0
        assert unit == "W"

    def test_i32_battery_power_negative(self):
        """Reg 37765: i32, gain=1 → -2000W (discharge)"""
        field = next(f for f in HUAWEI_SUN2000_REGISTERS if f.address == 37765)
        # -2000 = 0xFFFF_F830
        raw = {
            str(field.address): 0xFFFF,
            str(field.address + 1): 0xF830,
        }
        result = huawei_decode(raw, HUAWEI_SUN2000_REGISTERS)
        assert "battery_power" in result
        val, _ = result["battery_power"]
        assert val == -2000.0

    def test_u16_battery_soc_gain10(self):
        """Reg 37760: u16, gain=10 → 900 raw = 90.0%"""
        field = next(f for f in HUAWEI_SUN2000_REGISTERS if f.address == 37760)
        raw = {str(field.address): 900}
        result = huawei_decode(raw, HUAWEI_SUN2000_REGISTERS)
        assert "battery_soc" in result
        val, _ = result["battery_soc"]
        assert abs(val - 90.0) < 0.01

    def test_u32_daily_yield_gain100(self):
        """Reg 32114: u32, gain=100 → 1200 raw = 12.0 kWh"""
        field = next(f for f in HUAWEI_SUN2000_REGISTERS if f.address == 32114)
        raw = {
            str(field.address): 0,
            str(field.address + 1): 1200,
        }
        result = huawei_decode(raw, HUAWEI_SUN2000_REGISTERS)
        assert "energy_today" in result
        val, unit = result["energy_today"]
        assert abs(val - 12.0) < 0.001
        assert unit == "kWh"

    def test_i16_internal_temp_gain10(self):
        """Reg 32087: i16, gain=10 → 253 raw = 25.3°C"""
        field = next(f for f in HUAWEI_SUN2000_REGISTERS if f.address == 32087)
        raw = {str(field.address): 253}
        result = huawei_decode(raw, HUAWEI_SUN2000_REGISTERS)
        assert "inverter_temp" in result
        val, _ = result["inverter_temp"]
        assert abs(val - 25.3) < 0.01

    def test_empty_raw_returns_empty(self):
        result = huawei_decode({}, HUAWEI_SUN2000_REGISTERS)
        assert len(result) == 0


# ---------------------------------------------------------------------------
# Modbus profile registry tests
# ---------------------------------------------------------------------------
class TestModbusProfileRegistry:
    def test_get_register_map_growatt_sph(self):
        fields = get_register_map("growatt", "SPH")
        assert len(fields) > 0

    def test_get_register_map_case_insensitive(self):
        f1 = get_register_map("Growatt", "SPH")
        f2 = get_register_map("growatt", "sph")
        assert len(f1) == len(f2)

    def test_get_register_map_sungrow(self):
        fields = get_register_map("sungrow", "SHx")
        assert len(fields) > 0

    def test_get_register_map_huawei(self):
        fields = get_register_map("huawei", "SUN2000")
        assert len(fields) > 0

    def test_get_register_map_vendor_fallback(self):
        """Unknown model series falls back to vendor default (empty key)"""
        f = get_register_map("sungrow", "XH99")
        assert len(f) > 0

    def test_get_register_map_unknown_vendor_raises(self):
        with pytest.raises(KeyError):
            get_register_map("fronius", "primo")

    def test_decode_registers_huawei_empty(self):
        result = decode_registers({}, "huawei", "SUN2000")
        assert isinstance(result, dict)
        assert len(result) == 0

    def test_decode_registers_sungrow_empty(self):
        result = decode_registers({}, "sungrow", "SHx")
        assert isinstance(result, dict)

    def test_list_supported_profiles_includes_all_vendors(self):
        profiles = list_supported_profiles()
        vendors = {p["vendor"] for p in profiles}
        assert "growatt" in vendors
        assert "sungrow" in vendors
        assert "huawei" in vendors
        assert "solis" in vendors
        assert "deye" in vendors


# ---------------------------------------------------------------------------
# Eybond fingerprint and CRC tests
# ---------------------------------------------------------------------------
class TestEybondLocal:
    def test_protocol_family_mapping_smg(self):
        assert EYBOND_PROTOCOL_FAMILIES[1] == "modbus_smg"

    def test_protocol_family_mapping_pi17(self):
        assert EYBOND_PROTOCOL_FAMILIES[4] == "modbus_pi17"

    def test_protocol_family_mapping_pi30(self):
        assert EYBOND_PROTOCOL_FAMILIES[8] == "modbus_pi30"

    def test_protocol_family_mapping_smg_v2(self):
        assert EYBOND_PROTOCOL_FAMILIES[11] == "modbus_smg_v2"

    def test_crc16_returns_uint16(self):
        data = bytes([0x01, 0x03, 0x00, 0x00, 0x00, 0x0A])
        crc = _modbus_crc16(data)
        assert isinstance(crc, int)
        assert 0 <= crc <= 0xFFFF

    def test_crc16_empty(self):
        crc = _modbus_crc16(b"")
        assert crc == 0xFFFF  # CRC of empty = 0xFFFF (initial)

    def test_parse_registers_valid_response(self):
        """Valid Modbus TCP FC03 response with 2 registers (100 and 400)"""
        response = bytes([
            0x00, 0x01,  # transaction ID
            0x00, 0x00,  # protocol ID
            0x00, 0x07,  # length
            0x01,        # unit ID
            0x03,        # FC03
            0x04,        # byte count (4 bytes = 2 regs)
            0x00, 0x64,  # reg 1 = 100
            0x01, 0x90,  # reg 2 = 400
        ])
        regs = _parse_registers(response, 2)
        assert regs == [100, 400]

    def test_parse_registers_exception_response_returns_none(self):
        response = bytes([
            0x00, 0x01, 0x00, 0x00, 0x00, 0x03,
            0x01, 0x83,  # FC03 | 0x80 = exception
            0x02,
        ])
        regs = _parse_registers(response, 1)
        assert regs is None

    def test_parse_registers_too_short_returns_none(self):
        regs = _parse_registers(b"\x00\x01", 1)
        assert regs is None

    def test_parse_registers_wrong_function_code_returns_none(self):
        response = bytes([
            0x00, 0x01, 0x00, 0x00, 0x00, 0x05,
            0x01, 0x04,  # FC04 (not FC03)
            0x02,
            0x00, 0x0A,
        ])
        regs = _parse_registers(response, 1)
        assert regs is None


# ---------------------------------------------------------------------------
# GoodWe sensor mapping tests
# ---------------------------------------------------------------------------
class TestGoodWeMapping:
    def test_ppv_maps_to_pv_power(self):
        metric, unit = GOODWE_SENSOR_TO_METRIC["ppv"]
        assert metric == "pv_power"
        assert unit == "W"

    def test_battery_soc_canonical(self):
        metric, unit = GOODWE_SENSOR_TO_METRIC["battery_soc"]
        assert metric == "battery_soc"
        assert unit == "%"

    def test_eday_maps_to_energy_today(self):
        metric, unit = GOODWE_SENSOR_TO_METRIC["eday"]
        assert metric == "energy_today"
        assert unit == "kWh"

    def test_grid_power_canonical(self):
        metric, unit = GOODWE_SENSOR_TO_METRIC["grid_power"]
        assert metric == "grid_power"
        assert unit == "W"

    def test_temperature_canonical(self):
        metric, unit = GOODWE_SENSOR_TO_METRIC["temperature"]
        assert metric == "inverter_temp"

    def test_all_values_are_two_tuples(self):
        for k, v in GOODWE_SENSOR_TO_METRIC.items():
            assert isinstance(v, tuple), f"Key {k!r}: expected tuple, got {type(v)}"
            assert len(v) == 2, f"Key {k!r}: expected 2-tuple, got {len(v)}"

    def test_minimum_sensor_coverage(self):
        """At least 20 sensor mappings for adequate coverage"""
        assert len(GOODWE_SENSOR_TO_METRIC) >= 20


# ---------------------------------------------------------------------------
# Deye / Sunsynk register decode tests
# ---------------------------------------------------------------------------
class TestDeyeSunsynkDecode:
    def test_bms_soc_precedence(self):
        """Lithium BMS SOC (reg 316) takes precedence over lead-acid SOC (reg 184)."""
        raw = {"184": 65, "316": 92}
        result = deye_decode(raw)
        assert result["battery_soc"] == (92.0, "%")
        assert result["bms_soc"] == (92.0, "%")

    def test_signed_battery_power(self):
        """Battery power is signed int16 (negative = charge, positive = discharge)."""
        # Charging at 2500 W -> -2500 in uint16 is 0xF63C = 63036
        raw = {"190": 63036}
        result = deye_decode(raw)
        assert result["battery_power"] == (-2500.0, "W")

    def test_energy_u32_scaling(self):
        """Total energy is 32-bit big-endian with 0.1 scale."""
        # 123456 * 0.1 = 12345.6 kWh
        # 123456 = (1 << 16) | 57920
        raw = {"63": 1, "64": 57920}
        result = deye_decode(raw)
        assert result["energy_total"] == (12345.6, "kWh")

    def test_grid_power_signed(self):
        """Grid power is signed: negative = import from grid."""
        # Import 1500W -> -1500 -> 0xFA24 = 64036
        raw = {"175": 64036}
        result = deye_decode(raw)
        assert result["grid_power"] == (-1500.0, "W")

    def test_registry_lookup_sunsynk(self):
        fields = get_register_map("sunsynk", "hybrid")
        assert len(fields) > 0
        profiles = list_supported_profiles()
        assert any(p["vendor"] == "sunsynk" for p in profiles)


# ---------------------------------------------------------------------------
# SunsynkLocalAdapter tests
# ---------------------------------------------------------------------------
class TestSunsynkLocalAdapter:
    def test_plan_blocks(self):
        addresses = [53, 60, 63, 70, 71, 76, 77, 84, 90, 91, 172, 173, 175, 176, 177, 178, 182, 183, 184, 186, 187, 188, 189, 190, 191, 194, 195, 196, 197, 316, 317, 318, 324]
        blocks = SunsynkLocalAdapter._plan_blocks(addresses)
        assert len(blocks) > 0
        for start, count in blocks:
            assert count <= 64

    def test_build_read_frame(self):
        adapter = SunsynkLocalAdapter("192.168.1.100", 502, unit_id=1)
        frame = adapter._build_read_frame(100, 10)
        assert len(frame) == 12
        # MBAP: trans_id(2), proto_id(2), len(2) = 6 bytes
        # PDU: unit_id=1, fc=0x03, addr=100, count=10
        assert frame[6] == 1      # unit_id
        assert frame[7] == 0x03   # FC03

    def test_build_write_single_frame(self):
        adapter = SunsynkLocalAdapter("192.168.1.100", 502, unit_id=1)
        frame = adapter._build_write_single_frame(219, 20)
        assert len(frame) == 12
        assert frame[7] == 0x06   # FC06
        assert frame[11] == 20    # value

    @pytest.mark.asyncio
    async def test_build_set_soc(self):
        from solar_fleet.domain import DeviceIdentity
        adapter = SunsynkLocalAdapter("192.168.1.100", 502)
        dev = Device(
            id="dev-sunsynk-1",
            site_id="site-1",
            integration_id="int-1",
            vendor_id="sunsynk",
            type="inverter",
            identity=DeviceIdentity(vendor="sunsynk", model="Hybrid 8.8k"),
            name="Sunsynk",
        )
        call = await adapter._build_set_soc(dev, 25)
        assert call.body["register_writes"][219] == 25

    @pytest.mark.asyncio
    async def test_build_set_tou(self):
        from solar_fleet.domain import DeviceIdentity
        adapter = SunsynkLocalAdapter("192.168.1.100", 502)
        dev = Device(
            id="dev-sunsynk-1",
            site_id="site-1",
            integration_id="int-1",
            vendor_id="sunsynk",
            type="inverter",
            identity=DeviceIdentity(vendor="sunsynk", model="Hybrid 8.8k"),
            name="Sunsynk",
        )
        slots = [
            TouSlot("00:00", grid_charge=True, target_soc=90),
            TouSlot("05:00", grid_charge=False, target_soc=20),
        ]
        call = await adapter._build_set_tou(dev, slots)
        writes = call.body["register_writes"]
        # Slot 1: 00:00 -> reg 250 = 0
        assert writes[250] == 0
        assert writes[268] == 90  # target_soc
        assert writes[274] == 1   # grid_charge flag
        # Slot 2: 05:00 -> reg 251 = (5 << 8) | 0 = 1280
        assert writes[251] == (5 << 8)
        assert writes[269] == 20  # target_soc
        assert writes[275] == 0   # grid_charge flag False


# ---------------------------------------------------------------------------
# Unified Inverter Adapter tests
# ---------------------------------------------------------------------------
class TestUnifiedInverterAdapter:
    def test_create_unified_local_adapter(self):
        from solar_fleet.adapters.interfaces import (
            UnifiedLocalAdapter,
            create_unified_adapter,
        )
        poller = SunsynkLocalAdapter("192.168.1.100", 502)
        unified = create_unified_adapter(
            poller,
            device_id="inv-sunsynk-01",
            vendor="sunsynk",
            model="Hybrid 8.8k",
            site_id="site-hn-1",
        )
        assert isinstance(unified, UnifiedLocalAdapter)
        assert unified.vendor == "sunsynk"
        assert unified.model == "Hybrid 8.8k"
        assert unified.transport_type == "local_modbus_tcp"
        assert "unified_adapter" in unified.capabilities()
        assert "local" in unified.capabilities()
        assert "control_interface" in unified.capabilities()

    @pytest.mark.asyncio
    async def test_unified_local_device_info(self):
        from solar_fleet.adapters.interfaces import create_unified_adapter
        poller = SunsynkLocalAdapter("192.168.1.100", 502)
        unified = create_unified_adapter(
            poller,
            device_id="inv-sunsynk-01",
            vendor="sunsynk",
            model="Hybrid 8.8k",
        )
        info = await unified.get_device_info()
        assert info["address"] == "192.168.1.100"
        assert info["port"] == 502
        assert info["vendor"] == "sunsynk"

    @pytest.mark.asyncio
    async def test_create_unified_cloud_adapter(self):
        from solar_fleet.adapters.interfaces import (
            UnifiedCloudAdapter,
            create_unified_adapter,
        )

        class MockCloudClient:
            async def latest(self, serials):
                return [{"points": {"pv_power": (3500.0, "W"), "battery_soc": (80.0, "%")}}]

        mock_cloud = MockCloudClient()
        unified = create_unified_adapter(
            mock_cloud,
            device_id="inv-cloud-01",
            serial="SOLIS12345",
            vendor="solis",
            model="S6-EH1P",
        )
        assert isinstance(unified, UnifiedCloudAdapter)
        assert unified.vendor == "solis"
        assert unified.transport_type == "cloud"
        assert "cloud" in unified.capabilities()

        snap = await unified.get_telemetry()
        assert snap.online is True
        assert snap.get("pv_power") == 3500.0
        assert snap.get("battery_soc") == 80.0


class TestSofarDecode:
    def test_sofar_telemetry_decode(self):
        from solar_fleet.adapters.modbus_profiles.sofar_registers import (
            SOFAR_HYD_REGISTERS,
        )
        from solar_fleet.adapters.modbus_profiles.sofar_registers import (
            decode_raw_registers as sofar_decode,
        )
        raw = {
            "518": 3800,  # 380.0 V
            "520": 250,   # 2500 W
            "521": 3900,  # 390.0 V
            "523": 250,   # 2500 W
            "524": 2300,  # 230.0 V
            "526": 120,   # 1200 W (grid import)
            "528": 520,   # 52.0 V
            "529": 1000,  # 10.00 A
            "530": -50,   # -500 W (discharge as negative int16 if signed)
            "531": 85,    # 85 %
            "532": 28,    # 28 °C
        }
        res = sofar_decode(raw, SOFAR_HYD_REGISTERS)
        assert res["battery_soc"] == (85.0, "%")
        assert res["pv1_power"] == (2500.0, "W")
        assert res["pv2_power"] == (2500.0, "W")
        assert res["pv_power"] == (5000.0, "W")
        assert res["grid_power"] == (1200.0, "W")
        assert res["battery_voltage"] == (52.0, "V")

    def test_sofar_registry_integration(self):
        f = get_register_map("sofar", "hyd")
        assert len(f) > 0
        raw = {"531": 92}
        points = decode_registers(raw, "sofar", "hyd")
        assert points["battery_soc"] == (92.0, "%")


class TestSolaxDecode:
    def test_solax_telemetry_decode(self):
        from solar_fleet.adapters.modbus_profiles.solax_registers import (
            SOLAX_HYBRID_REGISTERS,
        )
        from solar_fleet.adapters.modbus_profiles.solax_registers import (
            decode_raw_registers as solax_decode,
        )
        raw = {
            "0": 2310,   # 231.0 V
            "2": 500,    # 500 W
            "10": 4000,  # 400.0 V
            "12": 1800,  # 1800 W
            "13": 1800,  # 1800 W
            "19": 24000, # 240.0 V (scale 0.01)
            "21": -800,  # -800 W
            "22": 78,    # 78 %
            "24": 30,    # 30 °C
        }
        res = solax_decode(raw, SOLAX_HYBRID_REGISTERS)
        assert res["battery_soc"] == (78.0, "%")
        assert res["pv_power"] == (3600.0, "W")
        assert res["battery_voltage"] == (240.0, "V")
        assert res["grid_power"] == (500.0, "W")

    def test_solax_registry_integration(self):
        f = get_register_map("solax", "x3")
        assert len(f) > 0
        raw = {"22": 65}
        points = decode_registers(raw, "solax", "x3")
        assert points["battery_soc"] == (65.0, "%")


class TestFoxessDecode:
    def test_foxess_telemetry_decode(self):
        from solar_fleet.adapters.modbus_profiles.foxess_registers import (
            FOXESS_H_REGISTERS,
        )
        from solar_fleet.adapters.modbus_profiles.foxess_registers import (
            decode_raw_registers as foxess_decode,
        )
        raw = {
            "12544": 2300,  # 230.0 V
            "12546": -300,  # -300 W (export)
            "12547": 5000,  # 50.00 Hz
            "12549": 2000,  # 2000 W
            "12550": 1500,  # 1500 W
            "12570": 3500,  # 350.0 V
            "12574": 94,    # 94 %
            "12576": 99,    # 99 %
        }
        res = foxess_decode(raw, FOXESS_H_REGISTERS)
        assert res["battery_soc"] == (94.0, "%")
        assert res["battery_soh"] == (99.0, "%")
        assert res["pv_power"] == (3500.0, "W")
        assert res["grid_frequency"] == (50.0, "Hz")

    def test_foxess_registry_integration(self):
        f = get_register_map("foxess", "h")
        assert len(f) > 0
        raw = {"12574": 82}
        points = decode_registers(raw, "foxess", "h")
        assert points["battery_soc"] == (82.0, "%")



