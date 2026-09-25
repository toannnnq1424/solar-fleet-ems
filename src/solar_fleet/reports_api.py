"""Immutable reports from scoped, quality-checked counter observations."""

from __future__ import annotations

import base64
import csv
import html
import io
import uuid
from datetime import datetime, timedelta
from typing import Literal

from fastapi import Depends, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field

from .analytics import workbook
from .domain import utcnow
from .operational_views import OperationalViews, period_bounds
from .telemetry import energy_ratios


class ReportGenerateForm(BaseModel):
    model_config = ConfigDict(extra="forbid")
    site_id: str | None = None
    title: str | None = Field(None, max_length=300)
    report_type: Literal["daily", "monthly", "energy"] = "monthly"
    format: str = "html"
    period: str = "month"
    start: datetime | None = None
    end: datetime | None = None
    email_recipient: str | None = None


def install_reports(app, controller, operator, viewer):
    store, views = controller.store, OperationalViews(controller)

    def sites_for(who, site_id=None):
        if site_id and not who.can_access(site_id):
            raise HTTPException(403, "site_access_denied")
        rows = [
            views.site(s["id"])
            for s in store.list("site")
            if who.can_access(s["id"]) and (not site_id or s["id"] == site_id)
        ]
        if site_id and not rows:
            raise HTTPException(404, "site_not_found")
        return rows

    def bounds(sites, period, start, end):
        if start is None and end is None:
            # Fleet periods need a common explicit timezone. UTC is the fleet boundary.
            start, end = period_bounds(sites[0] if len(sites) == 1 else {}, period)
        if (
            start is None
            or end is None
            or start.tzinfo is None
            or end.tzinfo is None
            or start >= end
            or end - start > timedelta(days=366)
        ):
            raise HTTPException(422, "invalid_time_range")
        return start, end

    def summary(sites, start, end, period):
        evidence = {s["id"]: views.energy(s["id"], start, end) for s in sites}
        totals = {}
        for key in ("pv", "load", "grid_import", "grid_export", "battery_discharge"):
            vals = [row[key]["wh"] for row in evidence.values()]
            totals[key] = sum(vals) / 1000 if vals and all(v is not None for v in vals) else None
        storage_absent = bool(sites) and all(
            (store.get("site_acceptance", s["id"]) or {}).get("battery_absent_verified") is True
            for s in sites
        )
        ratios = energy_ratios(
            totals["pv"],
            totals["load"],
            totals["grid_export"],
            totals["grid_import"],
            battery_present=not storage_absent,
        )
        rate = ratios["self_consumption_ratio"]
        self_kwh = totals["pv"] * rate if rate is not None else None
        ids = set(evidence)
        incidents = []
        for incident in store.list("incident"):
            if incident.get("site_id") not in ids:
                continue
            try:
                at = datetime.fromisoformat(incident.get("created_at", "").replace("Z", "+00:00"))
                if at.tzinfo is not None and start <= at < end:
                    incidents.append(incident)
            except (TypeError, ValueError):
                continue
        kpis = {
            "generation_kwh": totals["pv"],
            "consumption_kwh": totals["load"],
            "grid_import_kwh": totals["grid_import"],
            "grid_export_kwh": totals["grid_export"],
            "self_consumption_kwh": self_kwh,
            "self_consumption_rate_pct": rate * 100 if rate is not None else None,
            "cost_savings_vnd": None,
            "avoided_co2_kg": None,
            "trees_equivalent": None,
            "uptime_pct": None,
            "battery_cycles": None,
            "incident_count": len(incidents),
        }
        for key in (
            "generation",
            "consumption",
            "grid_import",
            "grid_export",
            "cost_savings",
            "avoided_co2",
            "uptime",
            "battery_cycles",
            "incident",
        ):
            kpis[key + "_trend_pct"] = None
        return {
            "period": period,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "scope": {
                "site_ids": sorted(ids),
                "site_id": sites[0]["id"] if len(sites) == 1 else None,
                "site_name": sites[0]["name"] if len(sites) == 1 else "Fleet",
                "sites_count": len(sites),
                "devices_count": sum(len(views.devices(s["id"])) for s in sites),
            },
            **kpis,
            "pv_generation_kwh": totals["pv"],
            "load_consumption_kwh": totals["load"],
            "evn_savings_vnd": None,
            "co2_avoided_ton": None,
            "trees_planted_equiv": None,
            "kpis": kpis,
            "evidence": evidence,
            "highlights": [],
            "executive_summary": "Các ô trống chưa đủ dữ liệu đo. / Empty values lack verified measurements.",
            "limitations": [
                "Storage energy attribution requires provenance.",
                "Tariff and carbon assumptions are not configured.",
                "Availability requires a continuous event history; online inventory is not uptime.",
            ],
        }

    @app.get("/api/reports/analytics/summary")
    async def report_summary(
        site_id: str | None = None,
        period: str = "month",
        start: datetime | None = None,
        end: datetime | None = None,
        who=Depends(viewer),
    ):
        sites = sites_for(who, site_id)
        return summary(sites, *bounds(sites, period, start, end), period)

    @app.get("/api/reports/analytics/timeseries")
    async def report_timeseries(
        site_id: str | None = None,
        period: str = "month",
        step: str = "day",
        start: datetime | None = None,
        end: datetime | None = None,
        who=Depends(viewer),
    ):
        sites = sites_for(who, site_id)
        start, end = bounds(sites, period, start, end)
        if step != "day":
            raise HTTPException(422, "daily_buckets_only")
        main, grid, battery, incidents = [], [], [], []
        cursor = start
        while cursor < end:
            next_time = min(cursor + timedelta(days=1), end)
            data = summary(sites, cursor, next_time, period)
            day = cursor.date().isoformat()
            main.append(
                {
                    "date": day,
                    "time": day,
                    "pv_kwh": data["pv_generation_kwh"],
                    "load_kwh": data["load_consumption_kwh"],
                    "consumption_kwh": data["load_consumption_kwh"],
                    "self_consumption_kwh": data["self_consumption_kwh"],
                    "grid_export_kwh": data["grid_export_kwh"],
                }
            )
            grid.append(
                {"date": day, "import_kwh": data["grid_import_kwh"], "export_kwh": data["grid_export_kwh"]}
            )
            battery.append({"date": day, "cycles": None})
            incidents.append({"date": day, "count": data["incident_count"]})
            cursor = next_time
        total = summary(sites, start, end, period)
        donut = {
            "self_consumption_kwh": total["self_consumption_kwh"],
            "grid_export_kwh": total["grid_export_kwh"],
            "rate_pct": total["self_consumption_rate_pct"],
        }
        mini = {
            "self_consumption_donut": donut,
            "grid_bars": grid,
            "battery_bars": battery,
            "incident_bars": incidents,
        }
        return {
            "period": period,
            "step": step,
            "timestamps": [r["date"] for r in main],
            "main_chart": main,
            "pv_generation_kwh": [r["pv_kwh"] for r in main],
            "load_consumption_kwh": [r["load_kwh"] for r in main],
            **mini,
            "mini_charts": mini,
        }

    def visible(record, who):
        ids = record.get("site_ids")
        # Legacy fleet reports did not persist their scope and cannot be safely shared.
        return bool(ids) and all(who.can_access(id) for id in ids)

    def public(record):
        return {k: v for k, v in record.items() if k != "artifact_base64"}

    @app.post("/api/reports/generate", status_code=201)
    async def generate_report(body: ReportGenerateForm, who=Depends(operator)):
        if body.email_recipient:
            raise HTTPException(422, "email_delivery_not_configured")
        fmt = body.format.lower()
        if fmt not in {"csv", "excel", "html"}:
            raise HTTPException(422, "supported_formats_csv_excel_html")
        sites = sites_for(who, body.site_id)
        if not sites:
            raise HTTPException(422, "empty_report_scope")
        data = summary(sites, *bounds(sites, body.period, body.start, body.end), body.period)
        title = body.title or "SolarOne energy report"
        rows = [
            {"Metric": name, "Value": data[key], "Unit": "kWh"}
            for name, key in (
                ("PV Generation", "pv_generation_kwh"),
                ("Consumption", "load_consumption_kwh"),
                ("Grid Import", "grid_import_kwh"),
                ("Grid Export", "grid_export_kwh"),
                ("Self Consumption", "self_consumption_kwh"),
            )
        ]
        if fmt == "csv":
            stream = io.StringIO(newline="")
            writer = csv.DictWriter(stream, fieldnames=["Metric", "Value", "Unit"])
            writer.writeheader()
            writer.writerows(rows)
            artifact, mime, extension = stream.getvalue().encode("utf-8-sig"), "text/csv", "csv"
        elif fmt == "excel":
            artifact = workbook(rows, ["Metric", "Value", "Unit"])
            mime, extension = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "xlsx"
        else:
            cells = "".join(
                "<tr>"
                + "".join(
                    "<td>" + html.escape(str(v) if v is not None else "—") + "</td>" for v in row.values()
                )
                + "</tr>"
                for row in rows
            )
            artifact = (
                '<!DOCTYPE html><html lang="vi"><meta charset="utf-8">'
                '<link rel="stylesheet" href="/static/app.css"><title>'
                + html.escape(title)
                + '</title><main class="panel"><h1>'
                + html.escape(title)
                + "</h1><p>"
                + html.escape(data["start"] + " → " + data["end"])
                + "</p><table>"
                + cells
                + "</table><p>"
                + html.escape(data["executive_summary"])
                + "</p></main></html>"
            ).encode()
            mime, extension = "text/html", "html"
        id = uuid.uuid4().hex
        record = {
            "id": id,
            "title": title,
            "site_id": body.site_id or "fleet",
            "site_ids": data["scope"]["site_ids"],
            "site_name": data["scope"]["site_name"],
            "report_type": body.report_type,
            "format": fmt.upper(),
            "status": "READY",
            "size_bytes": len(artifact),
            "created_at": utcnow().isoformat(),
            "created_by": who.id,
            "download_url": f"/api/reports/download/{id}",
            "snapshot": data,
            "mime": mime,
            "extension": extension,
            "artifact_base64": base64.b64encode(artifact).decode(),
        }
        with store.transaction():
            store.put("report_archive", id, record)
            store.audit(
                "report",
                {"event": "generated", "report_id": id, "site_ids": record["site_ids"], "actor": who.id},
                body.site_id,
            )
        return public(record)

    @app.get("/api/reports/recent")
    async def recent(site_id: str | None = None, limit: int = Query(10, ge=1, le=100), who=Depends(viewer)):
        sites_for(who, site_id)
        rows = [
            r
            for r in store.list("report_archive")
            if visible(r, who) and (not site_id or site_id in r["site_ids"])
        ]
        return [public(r) for r in sorted(rows, key=lambda r: r["created_at"], reverse=True)[:limit]]

    @app.get("/api/reports/download/{id}")
    async def download(id: str, who=Depends(viewer)):
        record = store.get("report_archive", id)
        if not record:
            raise HTTPException(404, "report_not_found")
        if not visible(record, who):
            raise HTTPException(403, "site_access_denied")
        if not record.get("artifact_base64"):
            raise HTTPException(409, "report_artifact_missing")
        return Response(
            base64.b64decode(record["artifact_base64"]),
            media_type=record["mime"],
            headers={"Content-Disposition": f'attachment; filename="report-{id}.{record["extension"]}"'},
        )
