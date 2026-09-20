"""Counter-based energy reporting and minimal, formula-free Excel export."""

from __future__ import annotations

import io
import math
import zipfile
from datetime import datetime
from xml.sax.saxutils import escape

from fastapi import Depends, HTTPException, Response

from .domain import SafetyError
from .telemetry import energy_ratios


def workbook(rows, columns):
    def col(index):
        result = ""
        while index:
            index, rem = divmod(index - 1, 26)
            result = chr(65 + rem) + result
        return result

    def cell(value, address):
        if type(value) in (int, float) and math.isfinite(value):
            return f'<c r="{address}"><v>{value}</v></c>'
        value = "" if value is None else str(value)
        # XML 1.0 legal characters; inline strings cannot execute spreadsheet formulas.
        value = "".join(
            ch
            for ch in value[:32767]
            if ch in "\t\r\n"
            or 32 <= ord(ch) <= 0xD7FF
            or 0xE000 <= ord(ch) <= 0xFFFD
            or 0x10000 <= ord(ch) <= 0x10FFFF
        )
        return f'<c r="{address}" t="inlineStr"><is><t xml:space="preserve">{escape(value)}</t></is></c>'

    data = [columns, *[[r.get(c) for c in columns] for r in rows]]
    sheet = '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" state="frozen"/></sheetView></sheetViews><sheetData>'
    sheet += "".join(
        f'<row r="{i}">' + "".join(cell(v, col(j) + str(i)) for j, v in enumerate(row, 1)) + "</row>"
        for i, row in enumerate(data, 1)
    )
    sheet += f'</sheetData><autoFilter ref="A1:{col(len(columns))}{len(data)}"/></worksheet>'
    files = {
        "[Content_Types].xml": '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>',
        "_rels/.rels": '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>',
        "xl/workbook.xml": '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Solar Fleet" sheetId="1" r:id="rId1"/></sheets></workbook>',
        "xl/_rels/workbook.xml.rels": '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>',
        "xl/worksheets/sheet1.xml": sheet,
    }
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' + content)
    return stream.getvalue()


def counter_delta(rows, start, end):
    relevant = [
        r
        for r in rows
        if r["quality"] == "GOOD"
        and r["source_timestamp"]
        and r["value"] is not None
        and r["unit"] == "Wh"
        and start <= datetime.fromisoformat(r["source_timestamp"]) <= end
    ]
    if len({(r["device_id"], r["binding_id"]) for r in relevant}) != 1:
        return {"wh": None, "reason": "SINGLE_VERIFIED_COUNTER_REQUIRED"}
    relevant.sort(key=lambda r: datetime.fromisoformat(r["source_timestamp"]))
    if len(relevant) < 2:
        return {"wh": None, "reason": "COUNTER_SAMPLES_REQUIRED"}
    first, last = relevant[0], relevant[-1]
    if any(b["value"] < a["value"] for a, b in zip(relevant, relevant[1:])):
        return {"wh": None, "reason": "COUNTER_RESET_OR_ROLLOVER"}
    if (datetime.fromisoformat(first["source_timestamp"]) - start).total_seconds() > 300 or (
        end - datetime.fromisoformat(last["source_timestamp"])
    ).total_seconds() > 300:
        return {"wh": None, "reason": "INCOMPLETE_PERIOD_COVERAGE"}
    return {
        "wh": last["value"] - first["value"],
        "reason": "COUNTER_DELTA",
        "from": first["source_timestamp"],
        "to": last["source_timestamp"],
        "device_id": first["device_id"],
        "binding_id": first["binding_id"],
    }


def install_analytics(app, controller, user):
    store = controller.store

    @app.get("/api/sites/{id}/analytics")
    async def analytics(id: str, start: datetime, end: datetime, who=Depends(user)):
        if not who.can_access(id):
            raise HTTPException(403, "site_access_denied")
        if not store.get("site", id):
            raise HTTPException(404)
        if start.tzinfo is None or end.tzinfo is None or start >= end or (end - start).days > 366:
            raise SafetyError("invalid_time_range")
        devices = [d for d in store.list("device") if d["site_id"] == id]
        series = {}
        for metric in (
            "pv_total_wh",
            "load_total_wh",
            "grid_import_total_wh",
            "grid_export_total_wh",
            "battery_charge_total_wh",
            "battery_discharge_total_wh",
        ):
            rows = []
            truncated = False
            for device in devices:
                points = store.report_samples(device["id"], start, end, metric, 10001)
                truncated |= len(points) > 10000
                rows += points
            series[metric] = (
                {"wh": None, "reason": "EXPORT_LIMIT"} if truncated else counter_delta(rows, start, end)
            )

        def values(metric):
            return series[metric + "_total_wh"]["wh"]

        # An incomplete inventory cannot prove that storage is absent.
        storage_absent = (store.get("site_acceptance", id) or {}).get("battery_absent_verified") is True
        ratios = energy_ratios(
            values("pv"),
            values("load"),
            values("grid_export"),
            values("grid_import"),
            battery_present=not storage_absent,
        )
        incidents = [
            r
            for r in store.list("incident")
            if r["site_id"] == id and start <= datetime.fromisoformat(r["created_at"]) < end
        ]
        response_times = []
        for incident in incidents:
            first = next(
                (r for r in incident["timeline"] if r["status"] in {"acknowledged", "in_progress"}), None
            )
            if first:
                response_times.append(
                    (
                        datetime.fromisoformat(first["at"]) - datetime.fromisoformat(incident["created_at"])
                    ).total_seconds()
                )
        return {
            "site_id": id,
            "period": {"start": start, "end": end},
            "energy": series,
            "ratios": ratios,
            "incidents": {
                "count": len(incidents),
                "responded": len(response_times),
                "mean_response_seconds": sum(response_times) / len(response_times)
                if response_times
                else None,
            },
            "financial": {
                "savings": None,
                "co2_kg": None,
                "reason": "ENERGY_PROVENANCE_AND_TARIFF_ALLOCATION_REQUIRED",
            },
            "method": "VERIFIED_CUMULATIVE_COUNTER_DIFFERENCE",
            "retention_days": 7,
        }

    @app.get("/api/reports/telemetry.xlsx")
    async def excel(
        device_id: str,
        start: datetime | None = None,
        end: datetime | None = None,
        metric: str | None = None,
        who=Depends(user),
    ):
        device = controller.device(device_id)
        if not who.can_access(device.site_id):
            raise HTTPException(403, "site_access_denied")
        if any(t is not None and t.tzinfo is None for t in (start, end)) or (start and end and start >= end):
            raise SafetyError("invalid_time_range")
        rows = store.report_samples(device_id, start, end, metric, 10001)
        columns = [
            "device_id",
            "metric",
            "value",
            "unit",
            "source",
            "source_timestamp",
            "received_at",
            "quality",
            "binding_id",
        ]
        return Response(
            workbook(rows[:10000], columns),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": 'attachment; filename="solar-fleet.xlsx"',
                "X-Data-Truncated": str(len(rows) > 10000).lower(),
            },
        )
