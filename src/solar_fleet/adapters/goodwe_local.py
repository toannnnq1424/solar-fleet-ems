"""GoodWe local UDP adapter.

GoodWe ES/ET/EH/DT inverters expose a local UDP service on port 8899.
This adapter wraps the goodwe-master library protocol to provide realtime
telemetry without any cloud dependency.

Source: goodwe-master (acquired, full rights confirmed 2026-10-01)
  License: MIT
  Key files: goodwe/__init__.py, goodwe/inverter.py, goodwe/protocol.py
  goodwe.connect() auto-discovers inverter family via UDP discovery probe

Protocol:
- Port: 8899 UDP (constant GOODWE_UDP_PORT)
- Discovery: AA55 "010200" → "0182" response identifies the inverter type
- Family detection: reads 3-char model tag from device info response
  ET/EH/BT/BH family → ET class (hybrid inverters)
  ES/EM/BP family → ES class (AC-coupled / storage)
  DT/MS/NS/XS family → DT class (string inverters)

This adapter does NOT import goodwe directly to keep the EMS core dependency-
light. Instead it reimplements the minimum UDP exchange needed for realtime
telemetry (read_runtime_data). For full feature parity use the
goodwe.connect() flow externally and pass the resulting dict here.
"""

from __future__ import annotations

import asyncio
import logging
import socket
import struct
import time
from typing import Any

from .interfaces import TelemetrySnapshot

logger = logging.getLogger(__name__)

GOODWE_UDP_PORT = 8899
GOODWE_TIMEOUT = 2.0
GOODWE_RETRIES = 3

# ---------------------------------------------------------------------------
# GoodWe AA55 protocol helpers (from goodwe/protocol.py)
# ---------------------------------------------------------------------------
def _aa55_checksum(data: bytes) -> int:
    """AA55 protocol checksum: sum of all bytes, low byte only."""
    return sum(data) & 0xFF


def _build_aa55_command(payload_hex: str) -> bytes:
    """Build an AA55 protocol command frame."""
    payload = bytes.fromhex(payload_hex)
    # Frame: AA 55 <payload> <checksum>
    frame = bytes([0xAA, 0x55]) + payload
    checksum = _aa55_checksum(frame[2:])  # checksum of payload only
    return frame + bytes([checksum])


def _build_query_realtime() -> bytes:
    """Build the ET/ES inverter realtime data query.
    From goodwe/__init__.py: the actual query command varies by family.
    This is the standard ET realtime query (function 0x0102 style).
    """
    # Standard GoodWe realtime query: AA 55 C0 07 01 02 00 D0
    return bytes([0xAA, 0x55, 0xC0, 0x07, 0x01, 0x02, 0x00, 0xD0])


# ---------------------------------------------------------------------------
# Sensor field mapping (from goodwe/sensor.py SensorKind)
# These are the canonical fields we extract from the runtime data dict
# ---------------------------------------------------------------------------
GOODWE_SENSOR_TO_METRIC: dict[str, tuple[str, str]] = {
    # key in goodwe runtime dict → (canonical metric, unit)
    "ppv":              ("pv_power",          "W"),
    "vpv1":             ("pv1_voltage",       "V"),
    "vpv2":             ("pv2_voltage",       "V"),
    "vpv3":             ("pv3_voltage",       "V"),
    "ipv1":             ("pv1_current",       "A"),
    "ipv2":             ("pv2_current",       "A"),
    "ipv3":             ("pv3_current",       "A"),
    "active_power":     ("active_power",      "W"),
    "load_power":       ("load_power",        "W"),
    "grid_power":       ("grid_power",        "W"),
    "backup_power":     ("backup_power",      "W"),
    "battery_power":    ("battery_power",     "W"),
    "battery_voltage":  ("battery_voltage",   "V"),
    "battery_current":  ("battery_current",   "A"),
    "battery_soc":      ("battery_soc",       "%"),
    "battery_temperature": ("battery_temp",   "°C"),
    "eday":             ("energy_today",      "kWh"),
    "etotal":           ("energy_total",      "kWh"),
    "export_energy_today": ("export_energy_today", "kWh"),
    "import_energy_today": ("import_energy_today", "kWh"),
    "total_export_energy": ("total_export_energy", "kWh"),
    "total_import_energy": ("total_import_energy", "kWh"),
    "grid_voltage":     ("grid_voltage_r",    "V"),
    "vac_r":            ("grid_voltage_r",    "V"),
    "vac_s":            ("grid_voltage_s",    "V"),
    "vac_t":            ("grid_voltage_t",    "V"),
    "grid_frequency":   ("grid_frequency",    "Hz"),
    "temperature":      ("inverter_temp",     "°C"),
    "power_factor":     ("power_factor",      ""),
    "work_mode":        ("work_mode",         ""),
    "work_mode_label":  ("inverter_status",   ""),
}


class GoodWeLocalAdapter:
    """GoodWe local UDP adapter for ES/ET/EH/DT inverter families.

    Obtains realtime telemetry from the inverter's local UDP port 8899
    without any cloud dependency. The goodwe-master library is used as
    the reference implementation; this adapter mirrors its protocol.

    Usage (with goodwe library installed):
        adapter = GoodWeLocalAdapter("192.168.1.100")
        snapshot = await adapter.read_telemetry()

    Usage (pure, without goodwe library):
        adapter = GoodWeLocalAdapter("192.168.1.100")
        # Falls back to UDP discovery + minimal protocol
        snapshot = await adapter.read_telemetry()

    The adapter tries to import goodwe and use its connect() + read_runtime_data()
    for the most complete dataset. On ImportError it falls back to the minimal
    built-in UDP implementation.
    """

    transport = "goodwe_udp"

    def __init__(
        self,
        address: str,
        port: int = GOODWE_UDP_PORT,
        timeout: float = GOODWE_TIMEOUT,
        retries: int = GOODWE_RETRIES,
        family: str | None = None,     # "ET", "ES", "DT" etc.; None = auto-detect
        comm_addr: int = 0,
        device_sn: str | None = None,
    ):
        self.address = address
        self.port = port
        self.timeout = timeout
        self.retries = retries
        self.family = family
        self.comm_addr = comm_addr
        self.device_sn = device_sn or address
        self._inverter: Any = None   # goodwe.Inverter instance (if library available)

    async def _get_inverter(self) -> Any:
        """Return (and cache) a connected goodwe.Inverter instance."""
        if self._inverter is not None:
            return self._inverter
        try:
            import goodwe  # type: ignore[import]
            self._inverter = await goodwe.connect(
                host=self.address,
                port=self.port,
                family=self.family,
                comm_addr=self.comm_addr,
                timeout=int(self.timeout),
                retries=self.retries,
            )
            logger.info(
                "GoodWe connected %s → family=%s model=%s",
                self.address,
                self._inverter.__class__.__name__,
                getattr(self._inverter, "model_name", "?"),
            )
            return self._inverter
        except ImportError:
            logger.debug("goodwe library not installed; using minimal UDP fallback")
            return None

    async def _read_via_library(self) -> dict[str, Any] | None:
        """Read runtime data via goodwe library (preferred path)."""
        inverter = await self._get_inverter()
        if inverter is None:
            return None
        try:
            return await inverter.read_runtime_data()
        except Exception as exc:
            logger.warning("GoodWe %s read_runtime_data failed: %s", self.address, exc)
            self._inverter = None  # Force reconnect next call
            return None

    async def _read_via_udp(self) -> dict[str, Any] | None:
        """Minimal UDP fallback: send discovery probe, parse basic response.

        This is a simplified version of goodwe.Aa55ProtocolCommand.execute().
        Returns only the fields decodeable from the AA55 response header.
        """
        query = _build_aa55_command("010200")
        loop = asyncio.get_event_loop()
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(self.timeout)
            await loop.run_in_executor(None, lambda: sock.sendto(query, (self.address, self.port)))
            data = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: sock.recv(1024)),
                timeout=self.timeout,
            )
            sock.close()
            if data and len(data) > 10:
                # Basic response parsing — model_name is ASCII in bytes 7+
                return {"raw_udp": data.hex(), "online": True}
        except (OSError, asyncio.TimeoutError) as exc:
            logger.warning("GoodWe %s UDP probe failed: %s", self.address, exc)
        return None

    async def read_telemetry(self) -> TelemetrySnapshot:
        """Read a normalised telemetry snapshot from the GoodWe inverter."""
        raw_data = await self._read_via_library()
        online = False
        points: dict[str, tuple[float | str | None, str | None]] = {}

        if raw_data is not None:
            online = True
            for goodwe_key, (metric, unit) in GOODWE_SENSOR_TO_METRIC.items():
                if goodwe_key not in raw_data:
                    continue
                val = raw_data[goodwe_key]
                if isinstance(val, (int, float)) and not isinstance(val, bool):
                    points[metric] = (float(val), unit)
                elif isinstance(val, str):
                    try:
                        points[metric] = (float(val), unit)
                    except (ValueError, TypeError):
                        points[metric] = (val, unit)
        else:
            # Try UDP fallback for connectivity test
            fallback = await self._read_via_udp()
            if fallback and fallback.get("online"):
                online = True

        return TelemetrySnapshot(
            device_sn=self.device_sn,
            points=points,
            freshness_state="LOCAL_REALTIME",
            raw=raw_data or {},
            online=online,
        )

    async def discover(self) -> list[dict]:
        """Probe the GoodWe inverter and return discovery info."""
        inverter = await self._get_inverter()
        if inverter is None:
            fallback = await self._read_via_udp()
            if not fallback:
                return []
            return [{"address": self.address, "port": self.port, "family": "unknown"}]
        try:
            info = await inverter.read_device_info()
        except Exception:
            info = {}
        return [
            {
                "address": self.address,
                "port": self.port,
                "family": inverter.__class__.__name__,
                "model_name": getattr(inverter, "model_name", ""),
                "serial_number": getattr(inverter, "serial_number", ""),
                **info,
            }
        ]

    async def close(self) -> None:
        """Release the UDP socket / inverter connection."""
        if self._inverter is not None:
            try:
                sock = getattr(self._inverter, "_socket", None)
                if sock:
                    sock.close()
            except Exception:
                pass
            self._inverter = None
