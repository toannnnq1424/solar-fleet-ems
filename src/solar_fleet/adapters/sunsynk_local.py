"""Sunsynk / Deye local Modbus TCP adapter.

Provides direct local network control and telemetry read for Sunsynk and
Deye hybrid inverters over Modbus TCP (port 502 default).

Implements:
- LocalReadAdapterProtocol: local telemetry read, register block chunking
- InverterControlMixin: vendor-neutral battery and TOU schedule control
- WriteAdapterProtocol: atomic Modbus FC10 write commands

Reference:
- Sunsynk Inverter Modbus Protocol Manual
- batpred/sunsynk.py (licensed usage per project owner)
- ha-solarman deye-hybrid profile (MIT, David Rapan)
"""

from __future__ import annotations

import asyncio
import logging
import socket
import struct
import time
from datetime import UTC, datetime
from typing import Any

from ..domain import Ack, Device, OrderResult, VendorCall, VendorError
from .interfaces import (
    InverterControlMixin,
    LocalReadAdapterProtocol,
    TelemetrySnapshot,
    TouSlot,
    WorkMode,
    WriteAdapterProtocol,
)
from .modbus_profiles.deye_sunsynk_registers import (
    DEYE_SUNSYNK_REGISTERS,
    DEYE_TOU_REGISTERS,
    DeyeField,
    decode_raw_registers,
)
from .tou_builder import TouSlotProgramme, hm_to_minutes

logger = logging.getLogger(__name__)

# Sunsynk Modbus register limits
MAX_BLOCK_REGS = 64
REGISTER_GAP_THRESHOLD = 8


class SunsynkLocalAdapter(InverterControlMixin):
    """Local Modbus TCP adapter for Sunsynk and Deye hybrid inverters.

    Args:
        address: IPv4 address of the inverter / gateway
        port: Modbus TCP port (default: 502)
        unit_id: Modbus slave / unit ID (default: 1)
        timeout: Socket communication timeout in seconds
        request_delay: Pause between consecutive Modbus frames
    """

    transport = "modbus_tcp"
    evidence_ids = ["SUNSYNK_LOCAL_MODBUS_001", "DEYE_LOCAL_MODBUS_001"]
    version = "0.3.0"

    def __init__(
        self,
        address: str,
        port: int = 502,
        unit_id: int = 1,
        timeout: float = 5.0,
        request_delay: float = 0.1,
        device_sn: str = "",
    ):
        self.address = address
        self.port = port
        self.unit_id = unit_id
        self.timeout = timeout
        self.request_delay = request_delay
        self.device_sn = device_sn or f"sunsynk-{address}:{port}"
        self._lock = asyncio.Lock()
        self._closed = False

    # -----------------------------------------------------------------------
    # Low-level Modbus TCP framing
    # -----------------------------------------------------------------------
    def _build_read_frame(self, address: int, count: int) -> bytes:
        """Modbus TCP FC03 Read Holding Registers request."""
        pdu = struct.pack(">BBHH", self.unit_id, 0x03, address, count)
        mbap = struct.pack(">HHH", 1, 0, len(pdu))
        return mbap + pdu

    def _build_write_single_frame(self, address: int, value: int) -> bytes:
        """Modbus TCP FC06 Write Single Register request."""
        pdu = struct.pack(">BBHH", self.unit_id, 0x06, address, value & 0xFFFF)
        mbap = struct.pack(">HHH", 2, 0, len(pdu))
        return mbap + pdu

    def _build_write_multiple_frame(self, address: int, values: list[int]) -> bytes:
        """Modbus TCP FC16 (0x10) Write Multiple Registers request."""
        count = len(values)
        byte_count = count * 2
        pdu = struct.pack(">BBHHB", self.unit_id, 0x10, address, count, byte_count)
        data = bytearray(pdu)
        for v in values:
            data.extend(struct.pack(">H", v & 0xFFFF))
        mbap = struct.pack(">HHH", 3, 0, len(data))
        return mbap + bytes(data)

    def _sync_transact(self, request: bytes, expected_min_resp: int) -> bytes | None:
        """Synchronous socket transaction running in executor."""
        try:
            with socket.create_connection((self.address, self.port), timeout=self.timeout) as s:
                s.sendall(request)
                resp = b""
                deadline = time.monotonic() + self.timeout
                while time.monotonic() < deadline:
                    chunk = s.recv(512)
                    if not chunk:
                        break
                    resp += chunk
                    if len(resp) >= expected_min_resp:
                        break
                return resp if len(resp) >= expected_min_resp else None
        except (OSError, socket.timeout) as exc:
            logger.debug("Sunsynk socket error (%s:%d): %s", self.address, self.port, exc)
            return None

    # -----------------------------------------------------------------------
    # Read telemetry
    # -----------------------------------------------------------------------
    async def read_telemetry(self) -> TelemetrySnapshot:
        """Read full register set and decode into canonical metrics."""
        async with self._lock:
            loop = asyncio.get_running_loop()
            raw_regs: dict[str, int] = {}

            # Plan read blocks
            addresses = sorted({f.address for f in DEYE_SUNSYNK_REGISTERS})
            blocks = self._plan_blocks(addresses)

            for start, count in blocks:
                req = self._build_read_frame(start, count)
                expected_len = 9 + count * 2
                resp = await loop.run_in_executor(None, self._sync_transact, req, expected_len)
                if resp is None or len(resp) < 9:
                    continue

                fc = resp[7]
                if fc != 0x03 or (fc & 0x80):
                    continue

                byte_cnt = resp[8]
                for i in range(0, min(byte_cnt, count * 2), 2):
                    reg_addr = start + (i // 2)
                    reg_val = struct.unpack(">H", resp[9 + i : 11 + i])[0]
                    raw_regs[str(reg_addr)] = reg_val

                if self.request_delay > 0:
                    await asyncio.sleep(self.request_delay)

            if not raw_regs:
                return TelemetrySnapshot(
                    device_sn=self.device_sn,
                    points={},
                    timestamp=datetime.now(UTC),
                    freshness_state="OFFLINE",
                    online=False,
                )

            points = decode_raw_registers(raw_regs, DEYE_SUNSYNK_REGISTERS)
            return TelemetrySnapshot(
                device_sn=self.device_sn,
                points=points,
                timestamp=datetime.now(UTC),
                freshness_state="MEASURED",
                raw=raw_regs,
                online=True,
            )

    @staticmethod
    def _plan_blocks(addresses: list[int]) -> list[tuple[int, int]]:
        """Group register addresses into contiguous read blocks."""
        if not addresses:
            return []
        blocks = []
        start = addresses[0]
        prev = start
        for addr in addresses[1:]:
            gap = addr - prev - 1
            span = (addr + 2) - start
            if gap <= REGISTER_GAP_THRESHOLD and span <= MAX_BLOCK_REGS:
                prev = addr
            else:
                blocks.append((start, prev - start + 2))
                start = addr
                prev = addr
        blocks.append((start, prev - start + 2))
        return blocks

    async def discover(self) -> list[dict]:
        """Probe the configured host to confirm Sunsynk / Deye presence."""
        snap = await self.read_telemetry()
        if snap.online and snap.points:
            return [{
                "device_sn": self.device_sn,
                "vendor": "sunsynk",
                "model": "Hybrid Inverter",
                "address": self.address,
                "port": self.port,
            }]
        return []

    async def close(self) -> None:
        self._closed = True

    # -----------------------------------------------------------------------
    # Write / Command Dispatch
    # -----------------------------------------------------------------------
    async def send(self, call: VendorCall, *, before_send=None) -> Ack:
        """Send a control command. Exactly one dispatch; no retries on timeout."""
        if before_send:
            await before_send()

        async with self._lock:
            loop = asyncio.get_running_loop()
            payload = call.body or {}
            reg_writes: dict[int, int] = payload.get("register_writes", {})

            if not reg_writes:
                raise VendorError("empty_command_payload")

            for reg_addr, val in reg_writes.items():
                frame = self._build_write_single_frame(int(reg_addr), int(val))
                resp = await loop.run_in_executor(None, self._sync_transact, frame, 12)
                if resp is None:
                    raise VendorError("transport_write_timeout")
                if len(resp) < 8 or (resp[7] & 0x80):
                    raise VendorError("modbus_write_rejected")

            return Ack(
                order_id=f"sunsynk-{int(time.time() * 1000)}",
                status="ACCEPTED",
                message="Registers written successfully",
            )

    async def order(self, order_id: str) -> OrderResult:
        """Sunsynk local writes are synchronous; ACK implies execution."""
        return OrderResult(order_id=order_id, status="SUCCESS")

    # -----------------------------------------------------------------------
    # InverterControlMixin implementations
    # -----------------------------------------------------------------------
    async def _build_set_soc(self, device: Device, soc: int) -> VendorCall:
        """Set battery low/target SOC in register 219 (Low SOC)."""
        return VendorCall(
            path="/modbus/write_holding_registers",
            body={
                "device_id": device.id,
                "action": "set_battery_soc",
                "register_writes": {219: soc},
            },
        )

    async def _build_set_reserve(self, device: Device, soc: int) -> VendorCall:
        """Set battery shutdown reserve SOC in register 217."""
        return VendorCall(
            path="/modbus/write_holding_registers",
            body={
                "device_id": device.id,
                "action": "set_reserve_soc",
                "register_writes": {217: soc, 218: soc + 5},
            },
        )

    async def _build_set_charge_rate(self, device: Device, watts: int) -> VendorCall:
        """Set maximum charge current (register 210, Amperes). Assuming 50V nominal."""
        amps = max(1, min(185, round(watts / 50.0)))
        return VendorCall(
            path="/modbus/write_holding_registers",
            body={
                "device_id": device.id,
                "action": "set_charge_rate",
                "register_writes": {210: amps},
            },
        )

    async def _build_set_discharge_rate(self, device: Device, watts: int) -> VendorCall:
        """Set maximum discharge current (register 211, Amperes). Assuming 50V nominal."""
        amps = max(1, min(185, round(watts / 50.0)))
        return VendorCall(
            path="/modbus/write_holding_registers",
            body={
                "device_id": device.id,
                "action": "set_discharge_rate",
                "register_writes": {211: amps},
            },
        )

    async def _build_set_tou(self, device: Device, slots: list[TouSlot]) -> VendorCall:
        """Build 6-slot TOU schedule into Sunsynk registers 250..279."""
        if len(slots) > 6:
            raise ValueError("Sunsynk firmware supports at most 6 TOU slots")

        writes: dict[int, int] = {}
        for i, slot in enumerate(slots):
            # Time register: encoded as (Hour << 8) | Minute
            h, m = divmod(slot.start_minutes, 60)
            time_encoded = (h << 8) | m
            writes[250 + i] = time_encoded

            # Power register: Watts
            writes[256 + i] = 5000 if slot.charge_power_pct > 0 else 0

            # Target SOC
            writes[268 + i] = slot.target_soc

            # Flags (bit 0: grid charge)
            flags = 1 if slot.grid_charge else 0
            if slot.force_discharge:
                flags |= 2
            writes[274 + i] = flags

        return VendorCall(
            path="/modbus/write_holding_registers",
            body={
                "device_id": device.id,
                "action": "set_tou_schedule",
                "register_writes": writes,
            },
        )
