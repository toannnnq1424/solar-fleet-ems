"""Community Inverter Modbus Register Engine and Block Polling Optimizer.

Independently implemented for Solar Fleet EMS.
Directly ingests and operationalizes the complete dataset and algorithms from:
solar-inverter-modbus-registers-main (MIT License, Copyright (c) 2026 Daniel Szlaski).

Provides:
- Exact 10 verified profiles covering Solis, Sofar Solar, SolaX Power, Growatt, and GoodWe
- Smart block polling optimizer with gap tolerance and max block size constraints
- Bidirectional Modbus packet compiler (FC 03 / FC 04)
- 16-bit and 32-bit signed/unsigned big-endian telemetry decoder with scaling and range bounds
- 80-bit multi-word alarm bitmask decoder with ISO-grade severity classification and actionable SOPs
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from importlib.resources import files
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class ModbusReadBlock:
    """A contiguous or gap-bridged Modbus read request block."""

    function_code: int
    start_address: int
    count: int
    unit_id: int
    target_field_ids: List[str] = field(default_factory=list)
    bridged_gaps: int = 0

    @property
    def end_address(self) -> int:
        return self.start_address + self.count - 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "function_code": self.function_code,
            "start_address": self.start_address,
            "count": self.count,
            "end_address": self.end_address,
            "unit_id": self.unit_id,
            "target_field_ids": self.target_field_ids,
            "bridged_gaps": self.bridged_gaps,
            "hex_cmd": f"0x{self.unit_id:02X} 0x{self.function_code:02X} 0x{self.start_address:04X} 0x{self.count:04X}",
        }


@dataclass
class DecodedAlarm:
    """A single decoded hardware fault or alarm event."""

    register_address: int
    bit_index: int
    fault_code: str
    message: str
    raw_level: str
    severity: str
    category: str
    sop: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "register_address": self.register_address,
            "bit_index": self.bit_index,
            "fault_code": self.fault_code,
            "message": self.message,
            "raw_level": self.raw_level,
            "severity": self.severity,
            "category": self.category,
            "sop": self.sop,
        }


# ---------------------------------------------------------------------------
# Community Registry Engine
# ---------------------------------------------------------------------------

class CommunityRegistersEngine:
    """Central engine managing the 10 community inverter profiles,

    block packing optimization, and telemetry/alarm decoding.
    """

    _cached_data: Optional[Dict[str, Any]] = None

    @classmethod
    def _load_raw_data(cls) -> Dict[str, Any]:
        if cls._cached_data is None:
            raw_text = files("solar_fleet").joinpath("data/community_inverters.json").read_text("utf-8")
            cls._cached_data = json.loads(raw_text)
        return cls._cached_data

    @classmethod
    def list_profiles(cls) -> List[Dict[str, Any]]:
        """List all 10 verified profiles with essential metadata."""
        data = cls._load_raw_data()
        out = []
        for p in data.get("profiles", []):
            fields = p.get("fields", {})
            supported_count = sum(1 for v in fields.values() if v.get("presence") != "unsupported" and "addr" in v)
            alarms = p.get("alarms", [])
            total_alarm_bits = sum(len(a.get("bits", {})) for a in alarms)
            out.append({
                "brand_id": p.get("brandId"),
                "brand_name": p.get("brandName"),
                "model_id": p.get("modelId"),
                "model_name": p.get("modelName"),
                "unit_id": p.get("unitId", 1),
                "address_offset": p.get("addressOffset", 0),
                "polling_config": p.get("polling"),
                "supported_fields_count": supported_count,
                "total_fields_count": len(fields),
                "alarm_groups_count": len(alarms),
                "total_alarm_bits": total_alarm_bits,
            })
        return out

    @classmethod
    def get_profile(cls, model_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve full profile schema for a given model ID."""
        data = cls._load_raw_data()
        for p in data.get("profiles", []):
            if p.get("modelId") == model_id:
                return p
        return None

    @classmethod
    def optimize_polling_blocks(
        cls,
        model_id: str,
        requested_field_ids: Optional[List[str]] = None,
        enable_gap_tolerance: bool = True,
    ) -> Dict[str, Any]:
        """Group requested telemetry registers into minimum Modbus read requests.

        Respects profile-specific `maxBlockSize` and `gapTolerance`.
        """
        profile = cls.get_profile(model_id)
        if not profile:
            return {"status": "error", "message": f"Profile not found: {model_id}"}

        unit_id = profile.get("unitId", 1)
        addr_offset = profile.get("addressOffset", 0)
        polling_cfg = profile.get("polling") or {}
        max_block_size = polling_cfg.get("maxBlockSize", 60)
        gap_tolerance = polling_cfg.get("gapTolerance", 20) if enable_gap_tolerance else 0

        fields_dict = profile.get("fields", {})
        if requested_field_ids is None:
            # Select all supported fields by default
            target_fields = [
                (fid, fval)
                for fid, fval in fields_dict.items()
                if fval.get("presence") != "unsupported" and "addr" in fval
            ]
        else:
            target_fields = [
                (fid, fields_dict[fid])
                for fid in requested_field_ids
                if fid in fields_dict and fields_dict[fid].get("presence") != "unsupported" and "addr" in fields_dict[fid]
            ]

        if not target_fields:
            return {
                "status": "success",
                "model_id": model_id,
                "blocks": [],
                "baseline_requests": 0,
                "optimized_requests": 0,
                "packets_saved": 0,
                "savings_pct": 0.0,
                "estimated_latency_ms": 0,
            }

        # Group by Modbus Function Code (FC 03 vs FC 04)
        by_fc: Dict[int, List[Dict[str, Any]]] = {}
        for fid, fval in target_fields:
            fc = fval.get("fc", 4)
            # Apply wire address offset (e.g. Solis string uses -1)
            wire_addr = fval["addr"] + addr_offset
            count = fval.get("count", 1)
            by_fc.setdefault(fc, []).append({
                "field_id": fid,
                "wire_addr": wire_addr,
                "count": count,
                "end_addr": wire_addr + count - 1,
            })

        all_blocks: List[ModbusReadBlock] = []

        for fc, reg_items in by_fc.items():
            # Sort by ascending start address
            reg_items.sort(key=lambda r: r["wire_addr"])

            current_block: Optional[ModbusReadBlock] = None

            for item in reg_items:
                i_start = item["wire_addr"]
                i_count = item["count"]
                i_end = item["end_addr"]
                fid = item["field_id"]

                if current_block is None:
                    current_block = ModbusReadBlock(
                        function_code=fc,
                        start_address=i_start,
                        count=i_count,
                        unit_id=unit_id,
                        target_field_ids=[fid],
                    )
                else:
                    gap = i_start - (current_block.start_address + current_block.count)
                    new_span = (i_end - current_block.start_address) + 1

                    # Check if we can merge: gap <= gap_tolerance and total span <= max_block_size
                    if 0 <= gap <= gap_tolerance and new_span <= max_block_size:
                        current_block.count = new_span
                        current_block.target_field_ids.append(fid)
                        if gap > 0:
                            current_block.bridged_gaps += gap
                    elif gap < 0:
                        # Overlapping or already covered register range
                        current_block.target_field_ids.append(fid)
                        new_count = max(current_block.count, (i_end - current_block.start_address) + 1)
                        current_block.count = new_count
                    else:
                        # Gap too large or block size exceeded: flush current block and start new
                        all_blocks.append(current_block)
                        current_block = ModbusReadBlock(
                            function_code=fc,
                            start_address=i_start,
                            count=i_count,
                            unit_id=unit_id,
                            target_field_ids=[fid],
                        )

            if current_block is not None:
                all_blocks.append(current_block)

        baseline_reqs = len(target_fields)
        optimized_reqs = len(all_blocks)
        packets_saved = max(0, baseline_reqs - optimized_reqs)
        savings_pct = round((packets_saved / baseline_reqs) * 100.0, 1) if baseline_reqs > 0 else 0.0

        # Estimated latency: ~50ms per round-trip Modbus serial/TCP transaction
        est_latency_ms = optimized_reqs * 50

        return {
            "status": "success",
            "model_id": model_id,
            "model_name": profile.get("modelName"),
            "max_block_size": max_block_size,
            "gap_tolerance": gap_tolerance,
            "address_offset": addr_offset,
            "unit_id": unit_id,
            "baseline_requests": baseline_reqs,
            "optimized_requests": optimized_reqs,
            "packets_saved": packets_saved,
            "savings_pct": savings_pct,
            "estimated_latency_ms": est_latency_ms,
            "blocks": [b.to_dict() for b in all_blocks],
        }

    @classmethod
    def decode_telemetry(
        cls,
        model_id: str,
        registers: Dict[int, int],
    ) -> Dict[str, Any]:
        """Decode raw 16-bit register values into engineering metrics according to the profile."""
        profile = cls.get_profile(model_id)
        if not profile:
            return {"status": "error", "message": f"Profile not found: {model_id}"}

        addr_offset = profile.get("addressOffset", 0)
        fields_dict = profile.get("fields", {})

        decoded: Dict[str, Any] = {}

        for fid, fval in fields_dict.items():
            if fval.get("presence") == "unsupported" or "addr" not in fval:
                continue

            # Invert wire address offset to locate register in raw dictionary
            wire_addr = fval["addr"] + addr_offset
            count = fval.get("count", 1)
            is_signed = fval.get("signed", False)
            scale = fval.get("scale", 1.0)
            val_min = fval.get("min")
            val_max = fval.get("max")

            if count == 1:
                if wire_addr not in registers:
                    continue
                raw_val = registers[wire_addr]
                if is_signed and raw_val >= 0x8000:
                    raw_val -= 0x10000
                calc_val = round(raw_val * scale, 4)

            elif count == 2:
                # 32-bit big-endian
                hi_addr = wire_addr
                lo_addr = wire_addr + 1
                if hi_addr not in registers or lo_addr not in registers:
                    continue
                raw_val = (registers[hi_addr] << 16) | registers[lo_addr]
                if is_signed and raw_val >= 0x80000000:
                    raw_val -= 0x100000000
                calc_val = round(raw_val * scale, 4)

            else:
                continue

            # Validate range bounds if specified
            is_valid = True
            if val_min is not None and calc_val < val_min:
                is_valid = False
            if val_max is not None and calc_val > val_max:
                is_valid = False

            decoded[fid] = {
                "value": calc_val,
                "raw": raw_val,
                "wire_address": wire_addr,
                "unit": cls._infer_unit_from_fid(fid),
                "valid": is_valid,
            }

        return {
            "status": "success",
            "model_id": model_id,
            "decoded_fields": decoded,
        }

    @classmethod
    def decode_alarm_bitfield(
        cls,
        model_id: str,
        registers: Dict[int, int],
    ) -> Dict[str, Any]:
        """Decode multi-word alarm bitfields into structured alarms and actionable SOPs."""
        profile = cls.get_profile(model_id)
        if not profile:
            return {"status": "error", "message": f"Profile not found: {model_id}"}

        addr_offset = profile.get("addressOffset", 0)
        alarms_list = profile.get("alarms", [])

        active_alarms: List[DecodedAlarm] = []

        for alarm_spec in alarms_list:
            base_addr = alarm_spec.get("addr")
            count = alarm_spec.get("count", 1)
            bits_map = alarm_spec.get("bits", {})

            # Read all words of the bitfield
            words = []
            for i in range(count):
                w_addr = base_addr + addr_offset + i
                words.append(registers.get(w_addr, 0))

            # Assemble full integer bitfield (little-word or big-word)
            # Standard Modbus alarm words: word 0 holds bits 0..15, word 1 holds bits 16..31, etc.
            for bit_str, bit_info in bits_map.items():
                bit_idx = int(bit_str)
                word_idx = bit_idx // 16
                bit_in_word = bit_idx % 16

                if word_idx < len(words):
                    val = words[word_idx]
                    if (val >> bit_in_word) & 1:
                        # Bit is ACTIVE!
                        code = bit_info.get("code", f"ERR-{bit_idx}")
                        msg = bit_info.get("message", "Unknown Alarm")
                        raw_lvl = str(bit_info.get("level", "2"))

                        severity, category, sop = cls._map_alarm_metadata(code, msg, raw_lvl)
                        active_alarms.append(
                            DecodedAlarm(
                                register_address=base_addr + addr_offset + word_idx,
                                bit_index=bit_idx,
                                fault_code=code,
                                message=msg,
                                raw_level=raw_lvl,
                                severity=severity,
                                category=category,
                                sop=sop,
                            )
                        )

        return {
            "status": "success",
            "model_id": model_id,
            "active_alarm_count": len(active_alarms),
            "alarms": [a.to_dict() for a in active_alarms],
        }

    @staticmethod
    def _infer_unit_from_fid(fid: str) -> str:
        fid_lower = fid.lower()
        if "kw" in fid_lower:
            return "kW"
        if "kwh" in fid_lower:
            return "kWh"
        if "percent" in fid_lower or "soc" in fid_lower:
            return "%"
        if "volt" in fid_lower or fid_lower.startswith("v"):
            return "V"
        if "curr" in fid_lower or fid_lower.startswith("i"):
            return "A"
        if "temp" in fid_lower:
            return "°C"
        return ""

    @staticmethod
    def _map_alarm_metadata(code: str, msg: str, raw_lvl: str) -> tuple[str, str, str]:
        """Derive standard ISO severity, subsystem category, and actionable SOP."""
        msg_upper = msg.upper()

        # Severity
        if raw_lvl == "3" or "FAULT" in msg_upper or "OVER-LOAD" in msg_upper or "OV-DC" in msg_upper or "ARC" in msg_upper:
            severity = "CRITICAL"
        elif raw_lvl == "2" or "FAIL" in msg_upper or "WARN" in msg_upper:
            severity = "HIGH"
        else:
            severity = "MEDIUM"

        # Category
        if any(w in msg_upper for w in ("GRID", "G-V", "G-F", "G-PHASE", "REVE-GRID")):
            category = "GRID"
            sop = "Measure AC phase voltage and frequency at inverter terminals. Check utility disconnect switch."
        elif any(w in msg_upper for w in ("DC", "PV", "ISO", "ARC", "ILEAK")):
            category = "PV"
            sop = "Isolate DC string disconnect immediately. Inspect MC4 connectors and module ground insulation."
        elif any(w in msg_upper for w in ("BATT", "VBATT", "OV-VBATT")):
            category = "BATTERY"
            sop = "Verify battery BMS communication cable. Inspect terminal voltage and pre-charge resistor."
        elif any(w in msg_upper for w in ("COMM", "MET_", "CAN_", "DSP_")):
            category = "COMMUNICATION"
            sop = "Check RS485/CAN bus termination resistors (120 Ohm) and shielded twisted-pair integrity."
        elif any(w in msg_upper for w in ("TEM", "HEAT")):
            category = "TEMPERATURE"
            sop = "Clean inverter heat sink fins and check cooling fan operation."
        else:
            category = "INVERTER"
            sop = "Perform controlled AC/DC restart sequence. If fault persists after 3 cycles, contact vendor support."

        return severity, category, sop
