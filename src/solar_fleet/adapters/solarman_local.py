"""SOLARMAN V5 logger poller.

Wraps the SolarmanV5Frame transport from solarman_v5.py (already in the codebase)
to provide a read_telemetry() interface compatible with LocalAgentDaemon.

The SOLARMAN V5 logger is a transport; it does NOT determine OEM identity.
The inverter's register profile is still selected by (vendor, model_series),
same as ModbusTcpPoller. The logger just wraps the Modbus RTU request in
a V5 TCP framing layer.

Source for framing: pysolarmanv5 (MIT, confirmed), solarman_v5.py in core.
"""

from __future__ import annotations

import asyncio
import logging
import socket
import struct
import time

from .interfaces import TelemetrySnapshot
from .modbus_local import _plan_read_blocks
from .modbus_profiles import decode_registers, get_exact_profile, get_register_map
from .solarman_v5 import SolarmanV5Frame

logger = logging.getLogger(__name__)

SOLARMAN_V5_PORT = 8899    # Default SOLARMAN V5 logger TCP port


class SolarmanV5Poller:
    """Polls inverters behind a SOLARMAN V5 logger via TCP.

    The logger translates V5 TCP frames into Modbus RTU on the RS-485 bus.
    Register profiles are selected by (vendor, model_series) exactly as in
    ModbusTcpPoller — the transport layer is the only difference.

    Args:
        device_id: Fleet EMS device identifier
        address: IP address of SOLARMAN logger
        port: TCP port (default 8899)
        unit_id: Modbus slave ID of the inverter on the RS-485 bus
        logger_serial: SOLARMAN logger serial number (uint32)
        vendor: Vendor name for profile selection
        model_series: Model series for profile selection
        timeout: Socket timeout per request
        request_delay: Pause between block reads
    """

    transport = "solarman_v5"

    def __init__(
        self,
        device_id: str,
        address: str,
        port: int = SOLARMAN_V5_PORT,
        unit_id: int = 1,
        logger_serial: int = 0,
        vendor: str = "deye",
        model_series: str = "",
        timeout: float = 5.0,
        request_delay: float = 0.1,
        exact_profile: bool = True,
    ):
        self.device_id = device_id
        self.address = address
        self.port = port
        self.unit_id = unit_id
        self.logger_serial = logger_serial
        self.vendor = vendor
        self.model_series = model_series
        self.timeout = timeout
        self.request_delay = request_delay
        self.exact_profile = exact_profile

    def _blocking_request(self, register_address: int, count: int) -> list[int] | None:
        """Send a V5-encapsulated Modbus read and return raw register values."""
        try:
            frame = SolarmanV5Frame.encode_read_holding_registers(
                logger_serial=self.logger_serial,
                slave_id=self.unit_id,
                start_register=register_address,
                quantity=count,
            )
        except Exception as exc:
            logger.warning("SolarmanV5 frame build error @ %04x: %s", register_address, exc)
            return None

        try:
            with socket.create_connection((self.address, self.port), timeout=self.timeout) as sock:
                sock.sendall(frame)
                data = b""
                deadline = time.monotonic() + self.timeout
                while time.monotonic() < deadline:
                    try:
                        chunk = sock.recv(512)
                        if not chunk:
                            break
                        data += chunk
                        # V5 response ends with 0x15
                        if data and data[-1] == 0x15:
                            break
                    except socket.timeout:
                        break
                return self._parse_v5_response(data, count)
        except (OSError, ConnectionRefusedError) as exc:
            logger.warning(
                "SolarmanV5 %s:%d @ %04x: %s", self.address, self.port, register_address, exc
            )
            return None

    def _parse_v5_response(self, data: bytes, expected_count: int) -> list[int] | None:
        """Parse a V5 response frame, extract Modbus RTU payload, return register values."""
        if len(data) < 29:  # V5 minimum response length
            return None
        if data[0] != 0xA5 or data[-1] != 0x15:
            return None

        # V5 frame: START(1) + len(2) + ctrl(2) + seq(2) + serial(4) + ...inner... + checksum(1) + END(1)
        # Inner Modbus RTU response starts after the V5 header (offset 11 typically)
        # Find Modbus RTU header: unit_id + func_code + byte_count + data + CRC
        # V5 inner payload starts at byte 11
        inner = data[11:-2]  # strip V5 checksum + END
        if len(inner) < 5:
            return None

        # Modbus RTU response: [unit_id, func_code, byte_count, data..., CRC_lo, CRC_hi]
        func_code = inner[1] if len(inner) > 1 else 0
        if func_code & 0x80:
            logger.warning("Modbus exception in V5 response: fc=%02x", inner[2] if len(inner) > 2 else 0)
            return None
        if func_code != 0x03:
            return None
        byte_count = inner[2]
        if len(inner) < 3 + byte_count + 2:
            return None
        values = []
        for i in range(0, byte_count, 2):
            values.append(struct.unpack(">H", inner[3 + i: 5 + i])[0])
        return values if len(values) >= expected_count else None

    async def read_telemetry(self) -> TelemetrySnapshot:
        """Read all configured register blocks and return normalised snapshot."""
        if self.exact_profile:
            register_map, decoder = get_exact_profile(self.vendor, self.model_series)
        else:
            register_map = get_register_map(self.vendor, self.model_series, exact=False)
            decoder = None
        raw: dict[str, int] = {}
        loop = asyncio.get_event_loop()

        for block_start, block_count in _plan_read_blocks(register_map):
            await asyncio.sleep(self.request_delay)
            values = await loop.run_in_executor(
                None, self._blocking_request, block_start, block_count
            )
            if values:
                for i, val in enumerate(values):
                    raw[str(block_start + i)] = val

        if self.exact_profile and decoder is not None:
            points = decoder(raw, self.model_series)
        else:
            points = decode_registers(raw, self.vendor, self.model_series, exact=self.exact_profile)
        online = bool(raw)
        return TelemetrySnapshot(
            device_sn=self.device_id,
            points=points,
            freshness_state="LOCAL_REALTIME",
            raw={"logger_serial": self.logger_serial, "register_count": len(raw)},
            online=online,
        )

    async def close(self) -> None:
        """No persistent connection; nothing to close."""
        pass
