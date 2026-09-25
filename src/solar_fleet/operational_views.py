"""Read models shared by site, map, device and report screens.

Only reviewed canonical channels enter KPIs. An absent or ambiguous measurement
is null, never an estimate based on nameplate capacity or a fabricated zero.
"""

from collections import defaultdict
from datetime import timedelta
from zoneinfo import ZoneInfo

from .analytics import counter_delta
from .domain import SafetyError, Sample, utcnow
from .telemetry import select_source

POWER_FIELDS = {
    "pv_w": "pv_w",
    "load_w": "load_w",
    "generator_w": "generator_w",
    "eps_w": "eps_w",
    "battery_soc": "soc_pct",
}


def period_bounds(site, period, now=None):
    now = now or utcnow()
    local = now.astimezone(ZoneInfo(site.get("timezone") or "UTC"))
    start = local.replace(hour=0, minute=0, second=0, microsecond=0)
    if period in {"today", "day"}:
        pass
    elif period == "week":
        start -= timedelta(days=6)
    elif period == "month":
        start = start.replace(day=1)
    elif period == "year":
        start = start.replace(month=1, day=1)
    else:
        raise SafetyError("invalid_period")
    return start, now


def device_values(controller, device):
    groups = defaultdict(list)
    for raw in controller.latest(device)["samples"]:
        sample = Sample.model_validate(raw)
        groups[sample.metric].append(sample)
    result = {}
    for metric, samples in groups.items():
        policy = next(
            (
                p
                for p in controller.store.list("source_policy")
                if p["site_id"] == device.site_id and not p.get("archived")
            ),
            {},
        )
        selected = select_source(
            samples, policy.get("max_age_seconds", 300), priority_order=policy.get("priority")
        )
        if selected:
            result[metric] = selected.model_dump(mode="json")
    return result


def value(channels, metric, unit):
    row = channels.get(metric)
    return row["value"] if row and row["unit"] == unit else None


def difference(left, right):
    return left - right if left is not None and right is not None else None


class OperationalViews:
    def __init__(self, controller):
        self.controller, self.store = controller, controller.store

    def site(self, id):
        return {
            "capacity_kwp": None,
            "latitude": None,
            "longitude": None,
            **(self.store.get("site", id) or {}),
            **(self.store.get("site_profile", id) or {}),
        }

    def devices(self, site_id):
        return [d for d in self.controller.devices() if d.site_id == site_id]

    def flow(self, site_id, device_id=None):
        # Without an accepted aggregation topology, multiple measurement devices
        # may represent the same PCC. Do not sum them and double-count energy.
        channels = [
            device_values(self.controller, d)
            for d in self.devices(site_id)
            if device_id is None or d.id == device_id
        ]

        def single(metric, unit):
            values = [value(c, metric, unit) for c in channels]
            present = [v for v in values if v is not None]
            return present[0] if len(present) == 1 else None

        result = {k: single(m, "%" if k == "battery_soc" else "W") for k, m in POWER_FIELDS.items()}
        result["grid_w"] = difference(single("grid_import_w", "W"), single("grid_export_w", "W"))
        result["battery_w"] = difference(single("battery_charge_w", "W"), single("battery_discharge_w", "W"))
        result["has_readings"] = any(v is not None for v in result.values())
        result["quality"] = "PARTIAL" if result["has_readings"] else "MISSING"
        return result

    def energy(self, site_id, start, end):
        result = {}
        for metric in ("pv", "load", "grid_import", "grid_export", "battery_charge", "battery_discharge"):
            rows = []
            for device in self.devices(site_id):
                rows.extend(self.store.report_samples(device.id, start, end, metric + "_total_wh", 10001))
            result[metric] = (
                counter_delta(rows, start, end)
                if len(rows) <= 10000
                else {"wh": None, "reason": "EXPORT_LIMIT"}
            )
        return result

    def equipment(self, device):
        channels = device_values(self.controller, device)
        recent = [s for s in self.controller.latest(device)["samples"] if not s["stale"]]
        caps = self.controller.capabilities(device)
        return {
            **device.model_dump(mode="json"),
            "vendor": device.identity.vendor,
            "brand": device.metadata.get("declared_equipment_brand")
            or device.metadata.get("equipment_brand")
            or device.identity.vendor,
            "model": device.identity.model,
            "serial": device.vendor_id,
            "serial_number": device.vendor_id,
            "firmware_version": device.identity.firmware,
            "online": bool(device.online and recent),
            "status": "ONLINE" if device.online and recent else "UNKNOWN",
            "power_kw": self.kw(value(channels, "pv_w", "W")),
            "soc_pct": value(channels, "soc_pct", "%"),
            "temp_c": value(channels, "inverter_temperature_c", "°C"),
            "today_kwh": None,
            "health_score": None,
            "commissioned": any(c.state == "VERIFIED" for c in caps),
        }

    @staticmethod
    def kw(val):
        return val / 1000 if val is not None else None

    def series(self, site_id, metric, period):
        metric = {"pv_power": "pv_w", "load_power": "load_w"}.get(metric, metric)
        start, end = period_bounds(self.site(site_id), period)
        rows = [
            s
            for d in self.devices(site_id)
            for s in self.store.report_samples(d.id, start, end, metric, 10001)
        ]
        rows = [
            r for r in rows if r["quality"] == "GOOD" and r["value"] is not None and r["source_timestamp"]
        ]
        # Curves must refer to a single meter/binding until topology is accepted.
        ambiguous = len({(r["device_id"], r["binding_id"], r["unit"]) for r in rows}) > 1
        truncated = len(rows) > 10000
        if ambiguous or truncated:
            rows = []
        rows.sort(key=lambda r: r["source_timestamp"])
        return {
            "site_id": site_id,
            "metric": metric,
            "period": period,
            "total_points": len(rows),
            "downsampled_points": len(rows),
            "samples": rows,
            "reason": "AMBIGUOUS_SOURCE"
            if ambiguous
            else "EXPORT_LIMIT"
            if truncated
            else "STORED_TELEMETRY",
        }

    def overview(self, site_id):
        site, flow = self.site(site_id), self.flow(site_id)
        periods, status = (
            {},
            {"status": "ONLINE" if flow["has_readings"] else "UNKNOWN", "total_yield_kwh": None},
        )
        for period in ("today", "month", "year"):
            energy = self.energy(site_id, *period_bounds(site, period))
            gen, load = self.kw(energy["pv"]["wh"]), self.kw(energy["load"]["wh"])
            status[period + "_yield_kwh"], status[period + "_consumption_kwh"] = gen, load
            periods[period] = {"yield_kwh": gen, "consumption_kwh": load, "self_use_kwh": None}
        devices = self.devices(site_id)
        integration_ids = {d.integration_id for d in devices}
        connections = [self.store.get("integration_state", id) for id in integration_ids]
        agents = [
            {k: a.get(k) for k in ("id", "name", "site_id", "enabled", "last_seen")}
            for a in self.store.list("agent")
            if a.get("site_id") == site_id
        ]
        incidents = sorted(
            (r for r in self.store.list("incident") if r.get("site_id") == site_id),
            key=lambda r: r.get("updated_at", ""),
            reverse=True,
        )
        commands = [r for r in self.store.commands() if r.get("site_id") == site_id]
        presets = [
            {
                "id": "self_consumption",
                "label": "Tự dùng tối đa",
                "can_actuate": False,
                "status": "LOCKED_UNKNOWN",
                "reason": "Yêu cầu nghiệm thu phần cứng và giao thức thiết bị.",
            },
            {
                "id": "zero_export",
                "label": "Chống phát ngược",
                "can_actuate": False,
                "status": "LOCKED_UNKNOWN",
                "reason": "Yêu cầu nghiệm thu phần cứng và giao thức thiết bị.",
            },
            {
                "id": "battery_first",
                "label": "Ưu tiên pin",
                "can_actuate": False,
                "status": "LOCKED_UNKNOWN",
                "reason": "Yêu cầu nghiệm thu phần cứng và giao thức thiết bị.",
            },
            {
                "id": "backup_eps",
                "label": "Dự phòng mất điện",
                "can_actuate": False,
                "status": "LOCKED_UNKNOWN",
                "reason": "Yêu cầu nghiệm thu phần cứng và giao thức thiết bị.",
            },
        ]
        return {
            "site": site,
            "energy_flow": flow,
            "plant_status": status,
            "quick_presets": presets,
            "generation_chart_24h": [],
            "comparison_yield_load": periods,
            "self_consumption": {"self_consumption_pct": None, "self_sufficiency_pct": None},
            "weather": {
                "temperature_c": None,
                "irradiance_wm2": None,
                "condition": "UNKNOWN",
                "hourly_forecast": [],
                "forecast_24h": [],
            },
            "equipment": {"total": len(devices), "items": [self.equipment(d) for d in devices]},
            "connectivity": {
                "local_agent": {
                    "status": "ENROLLED" if agents else "NOT_ENROLLED",
                    "label": "Local Agent",
                    "agents": agents,
                },
                "cloud_api": {"status": "UNKNOWN", "label": "Cloud", "states": connections},
                "direct_modbus": {"status": "UNKNOWN", "label": "Modbus"},
            },
            "recent_alerts": incidents[:5],
            "recent_commands": commands[:5],
            "location_info": {
                k: site.get(k)
                for k in ("address", "latitude", "longitude", "customer", "capacity_kwp", "timezone")
            },
        }

    def map_data(self, sites):
        from .gis_engine import cluster_plants

        rows = []
        for site in sites:
            site = self.site(site["id"])
            flow = self.flow(site["id"])
            alarms = [
                r
                for r in self.store.list("incident")
                if r.get("site_id") == site["id"] and r.get("status") not in {"closed", "resolved"}
            ]
            rows.append(
                {
                    **site,
                    "current_power_kw": self.kw(flow["pv_w"]),
                    "today_yield_kwh": None,
                    "performance_ratio_pct": None,
                    "status": "WARNING" if alarms else "NORMAL" if flow["has_readings"] else "UNKNOWN",
                    "region": "UNKNOWN",
                    "weather": {"condition": "UNKNOWN", "irradiance_w_per_m2": None, "temperature_c": None},
                    "alert_count": len(alarms),
                }
            )
        known = sum(r.get("latitude") is not None and r.get("longitude") is not None for r in rows)
        power = [r["current_power_kw"] for r in rows]
        return {
            "plants": rows,
            "clusters": cluster_plants(rows),
            "summary": {
                "total_plants": len(rows),
                "geocoded_plants": known,
                "missing_gps_plants": len(rows) - known,
                "total_mwp": sum(r.get("capacity_kwp") or 0 for r in rows) / 1000,
                "current_mw": sum(power) / 1000 if power and all(v is not None for v in power) else None,
                "active_warnings": sum(r["alert_count"] for r in rows),
            },
        }

    def control_state(self, device, who):
        channels = device_values(self.controller, device)
        site = self.site(device.site_id)
        telemetry = {}
        for field, metric in {
            "p_ac_kw": "inverter_ac_w",
            "p_pv_kw": "pv_w",
            "p_charge_kw": "battery_charge_w",
            "p_discharge_kw": "battery_discharge_w",
            "p_grid_kw": "grid_import_w",
        }.items():
            telemetry[field] = self.kw(value(channels, metric, "W"))
        telemetry.update(
            soc_pct=value(channels, "soc_pct", "%"),
            v_grid_v=value(channels, "grid_voltage_v", "V"),
            f_grid_hz=value(channels, "grid_frequency_hz", "Hz"),
            temp_c=value(channels, "inverter_temperature_c", "°C"),
            status="UNKNOWN",
            work_mode=None,
        )
        caps = self.controller.capabilities(device)
        accepted = [c for c in caps if c.state == "VERIFIED"]
        return {
            "device": {
                **self.equipment(device),
                "site_name": site.get("name"),
                "location": site.get("address"),
                "connection_type": device.identity.protocol_version,
                "cloud_connected": None,
                "latency_sec": None,
            },
            "telemetry": telemetry,
            "parameters": {},
            "capabilities": {
                key: {"status": "UNKNOWN", "code": "UNKNOWN"}
                for key in ("read_params", "write_params", "custom_cmd", "grid_setting", "firmware_ota")
            },
            "intent_capabilities": [c.model_dump(mode="json") for c in caps],
            "safety": {
                "hardware_accepted": bool(accepted),
                "can_write": False,
                "lock_reason": "PREVIEW_AND_CONFIRM_REQUIRED",
                "role_tier": who.role,
                "readback_timeout_sec": self.controller.engine.timeout_seconds,
            },
        }

    def topology(self, site_id):
        devices = self.devices(site_id)
        records = [
            r for r in self.store.list("topology") if r["site_id"] == site_id and not r.get("archived")
        ]
        return {
            "site": self.site(site_id),
            "records": records,
            "nodes": [self.equipment(d) for d in devices],
            "edges": [e for r in records for e in r.get("edges", [])],
            "electrical": {
                "pv_strings": [],
                "pv_total_power_kw": self.kw(self.flow(site_id)["pv_w"]),
                **{k: {} for k in ("bess", "inverter", "ac_panel", "meter", "eps_backup", "grid")},
            },
            "validation": {
                k: {"status": "UNKNOWN", "reason": "MEASUREMENTS_REQUIRED"}
                for k in ("dc_ac_ratio", "rs485_bus", "phase_balance")
            },
            "hierarchy": {
                "name": self.site(site_id).get("name"),
                "type": "SITE",
                "children": [{"id": d.id, "name": d.name or d.vendor_id, "type": d.type} for d in devices],
            },
        }
