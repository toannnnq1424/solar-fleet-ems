"""Durable, scoped UI invalidations. This does not accelerate the equipment sample rate."""

from __future__ import annotations

import asyncio
from collections import Counter

from fastapi import WebSocket, WebSocketDisconnect

from .security import session_user

MAX_EVENTS = 20_000


def initialize_events(db):
    db.executescript("""
        CREATE TABLE IF NOT EXISTS ui_events(
            seq INTEGER PRIMARY KEY AUTOINCREMENT, site_id TEXT NOT NULL,
            topic TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS ui_events_scope ON ui_events(site_id, seq);
    """)


def invalidation(store, kind, id, body):
    # An event contains no native values, credentials, record notes or user identities.
    topics = {
        "device": "devices",
        "latest": "telemetry",
        "agent_latest": "telemetry",
        "site": "plants",
        "site_profile": "plants",
        "incident": "incidents",
        "work_order": "maintenance",
        "schedule": "schedules",
        "rule": "rules",
        "mapping_draft": "mappings",
        "collection_policy": "collection",
        "agent": "connections",
        "handover": "commissioning",
        "native_alarm": "alarms",
        "alarm_source": "alarms",
        "incident_playbook": "incidents",
        "incident_sla_policy": "incidents",
        "work_execution": "maintenance",
        "work_time": "maintenance",
        "schedule_compilation": "schedules",
    }
    topic = topics.get(kind)
    if not topic:
        return
    site_id = body.get("site_id") or (id if kind in ("site", "site_profile") else None)
    if kind == "latest" and not site_id:
        device = store.get("device", id)
        site_id = device["site_id"] if device else None
    if not site_id:
        return
    from .domain import utcnow

    store.db.execute(
        "INSERT INTO ui_events(site_id,topic,created_at) VALUES(?,?,?)",
        (site_id, topic, utcnow().isoformat()),
    )
    watermark = store.db.execute("SELECT MAX(seq) FROM ui_events").fetchone()[0]
    store.db.execute("DELETE FROM ui_events WHERE seq<=?", (watermark - MAX_EVENTS,))


def events_since(store, who, cursor):
    oldest, newest = store.db.execute("SELECT MIN(seq),MAX(seq) FROM ui_events").fetchone()
    newest = newest or 0
    if cursor < 0 or cursor > newest:
        return {"type": "reset", "cursor": newest, "reason": "cursor_outside_retention"}
    if oldest and cursor < oldest - 1:
        return {"type": "reset", "cursor": newest, "reason": "cursor_outside_retention"}
    sites = [s["id"] for s in store.list("site") if who.can_access(s["id"])]
    rows = []
    # Query by scope; never materialize another site's event payload for a scoped user.
    for offset in range(0, len(sites), 400):
        chunk = sites[offset : offset + 400]
        placeholders = ",".join("?" for _ in chunk)
        rows.extend(
            store.db.execute(
                f"SELECT seq,site_id,topic FROM ui_events WHERE seq>? AND seq<=? "
                f"AND site_id IN ({placeholders}) ORDER BY seq LIMIT 501",
                (cursor, newest, *chunk),
            ).fetchall()
        )
    if len(rows) > 500:
        return {"type": "reset", "cursor": newest, "reason": "client_catchup_required"}
    changes = sorted({(r["site_id"], r["topic"]) for r in rows})
    return {
        "type": "changes" if changes else "heartbeat",
        "cursor": newest,
        "changes": [{"site_id": site, "topic": topic} for site, topic in changes],
    }


def install_stream(app, controller, origins, hosts):
    connections = Counter()

    @app.websocket("/api/stream")
    async def stream(socket: WebSocket):
        if socket.headers.get("host") not in hosts or socket.headers.get("origin") not in origins:
            await socket.close(code=1008)
            return
        session = session_user(controller.store, socket.cookies.get("solar_session"))
        if session is None:
            await socket.close(code=1008)
            return
        who = session[0]
        if connections[who.id] >= 4 or sum(connections.values()) >= 64:
            await socket.close(code=1013)
            return
        try:
            cursor = int(socket.query_params.get("cursor", "0"))
            if cursor < 0:
                raise ValueError()
        except ValueError:
            await socket.close(code=1008)
            return
        connections[who.id] += 1
        try:
            await socket.accept()
            scope = tuple(sorted(who.site_ids))
            await asyncio.wait_for(socket.send_json({"type": "ready", "cadence_seconds": 2}), 5)
            while True:
                session = session_user(controller.store, socket.cookies.get("solar_session"))
                if session is None or tuple(sorted(session[0].site_ids)) != scope:
                    await socket.close(code=1008)
                    break
                packet = events_since(controller.store, session[0], cursor)
                await asyncio.wait_for(socket.send_json(packet), 5)
                cursor = packet["cursor"]
                try:
                    message = await asyncio.wait_for(socket.receive_text(), 2)
                    # Read-only subscription. No device commands, filters or arbitrary messages accepted.
                    if message != "ping":
                        await socket.close(code=1008)
                        break
                    await asyncio.sleep(0.1)
                except TimeoutError:
                    pass
        except (WebSocketDisconnect, TimeoutError, RuntimeError):
            pass
        finally:
            connections[who.id] -= 1
            if not connections[who.id]:
                del connections[who.id]
