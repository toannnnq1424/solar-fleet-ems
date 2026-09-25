"""Electrical single-line diagram (SLD) and communication bus topology validation."""

from __future__ import annotations

from typing import Any


class TopologyValidator:
    """Validates physical electrical interconnections and RS485 communication buses."""

    @staticmethod
    def validate_dc_ac_oversizing_ratio(dc_power_kwp: float, ac_rated_power_kw: float) -> dict[str, Any]:
        """Validate DC/AC sizing ratio (typically 1.1x to 1.5x for modern PV+Storage)."""
        if ac_rated_power_kw <= 0:
            return {"valid": False, "ratio": 0.0, "reason": "AC rated power must be positive"}

        ratio = dc_power_kwp / ac_rated_power_kw
        if ratio < 0.8:
            status = "UNDERSIZED"
            advisory = (
                "Mảng pin mặt trời nhỏ hơn công suất định mức biến tần (hiệu suất thấp vào sáng/chiều)."
            )
        elif 0.8 <= ratio <= 1.5:
            status = "OPTIMAL"
            advisory = "Tỉ lệ DC/AC tối ưu theo tiêu chuẩn kỹ thuật thiết kế điện mặt trời."
        else:
            status = "HIGH_CLIPPING"
            advisory = (
                "Tỉ lệ DC/AC cao (>150%), biến tần sẽ bị cắt giảm công suất đỉnh (clipping) vào buổi trưa."
            )

        return {
            "valid": True,
            "ratio": round(ratio, 2),
            "status": status,
            "advisory": advisory,
        }

    @staticmethod
    def validate_rs485_bus(devices_on_bus: list[dict[str, Any]]) -> dict[str, Any]:
        """Validate daisy-chained RS485 communication bus configuration.

        Checks for slave ID collisions and baud rate uniformity.
        """
        seen_ids = set()
        baud_rates = set()
        collisions = []

        for d in devices_on_bus:
            slave_id = d.get("slave_id")
            baud = d.get("baud_rate", 9600)
            baud_rates.add(baud)

            if slave_id is not None:
                if slave_id in seen_ids:
                    collisions.append(slave_id)
                seen_ids.add(slave_id)

        issues = []
        if collisions:
            issues.append(f"Xung đột địa chỉ Modbus Slave ID trên cùng một bus: {list(set(collisions))}")
        if len(baud_rates) > 1:
            issues.append(f"Không đồng nhất tốc độ baud rate trên bus RS485: {list(baud_rates)}")

        return {
            "valid": len(issues) == 0,
            "device_count": len(devices_on_bus),
            "slave_ids": sorted(list(seen_ids)),
            "issues": issues,
        }

    @staticmethod
    def check_three_phase_balance(power_r_w: float, power_s_w: float, power_t_w: float) -> dict[str, Any]:
        """Check phase power balance and calculate phase imbalance percentage."""
        avg_power = (power_r_w + power_s_w + power_t_w) / 3.0
        if avg_power <= 0:
            return {"imbalance_pct": 0.0, "status": "BALANCED"}

        max_dev = max(
            abs(power_r_w - avg_power),
            abs(power_s_w - avg_power),
            abs(power_t_w - avg_power),
        )
        imbalance_pct = (max_dev / avg_power) * 100.0

        return {
            "imbalance_pct": round(imbalance_pct, 1),
            "status": "BALANCED" if imbalance_pct <= 10.0 else "UNBALANCED",
            "advisory": "Lệch pha trong giới hạn cho phép"
            if imbalance_pct <= 10.0
            else "Cảnh báo lệch pha phụ tải >10%",
        }
