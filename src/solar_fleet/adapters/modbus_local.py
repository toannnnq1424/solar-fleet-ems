"""Modbus TCP poller for inverters with known register profiles.

Supports: Growatt SPH/MIN/MIX, Sungrow SHx, Huawei SUN2000, Eybond/SMG.
Uses the register profiles in modbus_profiles/ to select the correct
register map for each vendor + model_series combination.

Transport: raw Modbus TCP (port 502 default, 8000 for Eybond).
One TCP connection per poll; no persistent connection (avoids firewall timeouts).
"""

from __future__ import annotations

import asyncio
import logging
import socket
import struct
import time
from typing import Any

from .interfaces import TelemetrySnapshot
from .modbus_profiles import decode_registers, get_function_code, get_register_map

logger = logging.getLogger(__name__)


class ModbusTcpPoller:
    """Polls an inverter via raw Modbus TCP and normalises the result.

    Supports both FC03 (Read Holding Registers) and FC04 (Read Input Registers).

    Args:
        device_id: Fleet EMS device identifier
        address: IPv4 address of the inverter or Modbus gateway
        port: Modbus TCP port (default 502; Eybond uses 8000)
        unit_id: Modbus slave/unit ID (default 1)
        vendor: Vendor name for profile selection ("growatt", "sungrow", "huawei")
        model_series: Model series for profile selection ("SPH", "SHx", "SUN2000")
        timeout: Per-request socket timeout in seconds
        request_delay: Pause between consecutive register block reads
        function_code: Explicit Modbus function code (0x03 or 0x04; auto-detected if None)
    """

    transport = "modbus_tcp"

    def __init__(
        self,
        device_id: str,
        address: str,
        port: int = 502,
        unit_id: int = 1,
        vendor: str = "growatt",
        model_series: str = "SPH",
        timeout: float = 5.0,
        request_delay: float = 0.1,
        function_code: int | None = None,
    ):
        self.device_id = device_id
        self.address = address
        self.port = port
        self.unit_id = unit_id
        self.vendor = vendor
        self.model_series = model_series
        self.timeout = timeout
        self.request_delay = request_delay
        self.function_code = (
            function_code if function_code is not None else get_function_code(vendor, model_series)
        )

    def _build_read_request(self, address: int, count: int) -> bytes:
        """Build Modbus TCP frame using configured function code (FC03 or FC04)."""
        pdu = struct.pack(">BBHH", self.unit_id, self.function_code, address, count)
        header = struct.pack(">HHH", 1, 0, len(pdu))
        return header + pdu

    def _parse_response(self, response: bytes, expected_count: int) -> list[int] | None:
        """Parse Modbus TCP response to list of uint16 values."""
        if len(response) < 9:
            return None
        func_code = response[7]
        if func_code & 0x80:
            logger.warning("Modbus exception from %s: fc=%02x", self.address, response[8])
            return None
        if func_code != self.function_code:
            return None
        byte_count = response[8]
        if len(response) < 9 + byte_count:
            return None
        values = []
        for i in range(0, byte_count, 2):
            values.append(struct.unpack(">H", response[9 + i: 11 + i])[0])
        return values if len(values) >= expected_count else None

    def _blocking_request(self, address: int, count: int) -> list[int] | None:
        """Synchronous Modbus TCP request (runs in executor)."""
        frame = self._build_read_request(address, count)
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
                        if len(data) >= 6:
                            length = struct.unpack(">H", data[4:6])[0]
                            if len(data) >= 6 + length:
                                break
                    except socket.timeout:
                        break
                return self._parse_response(data, count)
        except (OSError, ConnectionRefusedError) as exc:
            logger.warning("Modbus TCP %s:%d @ %04x: %s", self.address, self.port, address, exc)
            return None

    async def _read_register_block(self, address: int, count: int) -> list[int] | None:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._blocking_request, address, count)

    async def read_telemetry(self) -> TelemetrySnapshot:
        """Read all configured register blocks and return normalised snapshot."""
        register_map = get_register_map(self.vendor, self.model_series)
        raw: dict[str, int] = {}

        for block_start, block_count in _plan_read_blocks(register_map):
            await asyncio.sleep(self.request_delay)
            values = await self._read_register_block(block_start, block_count)
            if values:
                for i, val in enumerate(values):
                    raw[str(block_start + i)] = val

        points = decode_registers(raw, self.vendor, self.model_series)
        online = bool(raw)
        return TelemetrySnapshot(
            device_sn=self.device_id,
            points=points,
            freshness_state="LOCAL_REALTIME",
            raw={"register_count": len(raw)},
            online=online,
        )

    async def close(self) -> None:
        """No persistent connection; nothing to close."""
        pass


def _plan_read_blocks(register_map: list[Any]) -> list[tuple[int, int]]:
    """Group scattered register addresses into efficient contiguous read blocks.

    Groups registers within 8 addresses of each other into one read block.
    Returns list of (start_address, count) tuples.
    Max block size = 125 registers (Modbus standard limit).
    """
    if not register_map:
        return []

    addresses = sorted(set(r.address for r in register_map))
    blocks: list[tuple[int, int]] = []
    block_start = addresses[0]
    block_end = addresses[0]

    for addr in addresses[1:]:
        if addr - block_end <= 8 and addr - block_start < 125:
            block_end = addr
        else:
            count = block_end - block_start + 2  # +2 for u32 last register
            blocks.append((block_start, min(count, 125)))
            block_start = addr
            block_end = addr

    count = block_end - block_start + 2
    blocks.append((block_start, min(count, 125)))
    return blocks
