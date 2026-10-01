"""Authenticated local agent ingest and durable outbound spool; no guessed hardware driver."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from fastapi import Depends, HTTPException, Request
from pydantic import Field, field_validator

from .adapters.local_daemon import LocalAgentDaemon, LocalDeviceConfig, PollResult
from .domain import Model, Sample, Source, utcnow
from .storage import encoded


class AgentPoint(Model):
    device_id: str = Field(min_length=1, max_length=100)
    key: str = Field(min_length=1, max_length=120, pattern=r"^[A-Za-z0-9_.:-]+$")
    value: float | None = Field(allow_inf_nan=False)
    unit: str | None = Field(default=None, max_length=40)
    timestamp: datetime

    @field_validator("timestamp")
    @classmethod
    def aware(cls, value):
        if value.tzinfo is None:
            raise ValueError("timestamp timezone required")
        return value


class AgentBatch(Model):
    agent_id: str = Field(min_length=1, max_length=100)
    sequence: int = Field(ge=1)
    version: str = Field(min_length=1, max_length=80)
    points: list[AgentPoint] = Field(min_length=1, max_length=1000)


class LocalDeviceCreate(Model):
    device_id: str = Field(min_length=1, max_length=100)
    site_id: str = Field(default="default", max_length=100)
    transport: str = Field(pattern=r"^(modbus_tcp|solarman_v5|goodwe_udp|eybond_local|sunsynk_local)$")
    address: str = Field(min_length=1, max_length=255)
    port: int = Field(default=502, ge=1, le=65535)
    vendor: str = Field(min_length=1, max_length=50)
    model_series: str = Field(default="", max_length=50)
    unit_id: int = Field(default=1, ge=1, le=255)
    logger_serial: int | None = None
    poll_interval_s: float = Field(default=30.0, ge=1.0, le=3600.0)


def _persist_local_snapshot(store, result: PollResult):
    device_id = result.device_id
    snapshot = result.snapshot
    if not snapshot or not snapshot.points:
        return
    now = utcnow()
    agent_id = "local-daemon"
    cfg = store.get("local_device", device_id) or {}
    site_id = cfg.get("site_id", "default")

    # Ensure agent entity exists in store
    agent = store.get("agent", agent_id)
    if not agent:
        store.put("agent", agent_id, {
            "id": agent_id,
            "site_id": site_id,
            "enabled": True,
            "device_ids": [device_id],
            "last_sequence": 0,
            "token_hash": "",
        })
    elif device_id not in agent.get("device_ids", []):
        agent["device_ids"].append(device_id)
        store.put("agent", agent_id, agent)

    samples = []
    for metric, (val, unit) in snapshot.points.items():
        if val is None or not isinstance(val, (int, float)):
            continue
        try:
            sample = Sample(
                device_id=device_id,
                metric=metric,
                value=float(val),
                unit=unit,
                source=Source.AGENT,
                source_timestamp=snapshot.timestamp or now,
                received_at=now,
                quality="GOOD" if snapshot.online else "UNVERIFIED",
                binding_id=agent_id,
                evidence_ids=[],
            )
            samples.append(sample)
        except Exception:
            continue

    if not samples:
        return

    try:
        store.add_samples(samples)
        latest_key = f"{agent_id}:{device_id}"
        latest = store.get("agent_latest", latest_key) or {"samples": []}
        by_metric = {s["metric"]: s for s in latest.get("samples", [])}
        for s in samples:
            by_metric[s.metric] = s.model_dump(mode="json")
        store.put(
            "agent_latest",
            latest_key,
            {
                "device_id": device_id,
                "agent_id": agent_id,
                "site_id": site_id,
                "samples": list(by_metric.values()),
                "received_at": now.isoformat(),
            },
        )
        device = store.get("device", device_id)
        if device:
            device["last_seen"] = now.isoformat()
            device["online"] = snapshot.online
            store.put("device", device_id, device)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("Failed to persist local snapshot for %s: %s", device_id, exc)


def install_agent(app, controller, user=None, admin=None):
    store = controller.store

    @app.post("/api/agent/inbox")
    async def inbox(body: AgentBatch, request: Request):
        # Isolated machine endpoint: never accepts a browser session as authentication.
        authorization = request.headers.get("authorization", "")
        token = authorization[7:] if authorization.startswith("Bearer ") else ""
        row = store.get("agent", body.agent_id)
        if (
            not row
            or not row["enabled"]
            or not token
            or not hmac.compare_digest(hashlib.sha256(token.encode()).hexdigest(), row["token_hash"])
        ):
            raise HTTPException(401, "agent_authentication_failed")
        digest = hashlib.sha256(encoded(body.model_dump(mode="json")).encode()).hexdigest()
        now = utcnow()
        samples = []
        dropped = 0
        for point in body.points:
            device = store.get("device", point.device_id)
            if point.device_id not in row["device_ids"] or not device or device["site_id"] != row["site_id"]:
                raise HTTPException(403, "agent_device_scope_denied")
            if point.timestamp > now + timedelta(seconds=5):
                raise HTTPException(422, "agent_timestamp_outside_retention")
            if point.timestamp < now - timedelta(days=7):
                dropped += 1
                continue
            samples.append(
                Sample(
                    device_id=point.device_id,
                    metric="agent.native." + point.key,
                    value=point.value,
                    unit=point.unit,
                    source=Source.AGENT,
                    source_timestamp=point.timestamp,
                    received_at=now,
                    quality="UNVERIFIED",
                    binding_id=body.agent_id,
                    evidence_ids=[],
                )
            )
        with store.transaction():
            row = store.get("agent", body.agent_id)
            if body.sequence == row["last_sequence"] and row.get("last_digest") == digest:
                return {"accepted": True, "duplicate": True, "sequence": body.sequence}
            if body.sequence != row["last_sequence"] + 1:
                raise HTTPException(409, "agent_sequence_conflict")
            store.add_samples(samples)
            for device_id in {s.device_id for s in samples}:
                latest = store.get("agent_latest", body.agent_id + ":" + device_id) or {"samples": []}
                by_metric = {s["metric"]: s for s in latest["samples"]}
                for sample in samples:
                    if sample.device_id != device_id:
                        continue
                    previous = by_metric.get(sample.metric)
                    if not previous or sample.source_timestamp >= datetime.fromisoformat(
                        previous["source_timestamp"]
                    ):
                        by_metric[sample.metric] = sample.model_dump(mode="json")
                # Bound active channel count; history retains old channels within the store cap.
                if len(by_metric) > 500:
                    raise HTTPException(422, "agent_metric_limit")
                store.put(
                    "agent_latest",
                    body.agent_id + ":" + device_id,
                    {
                        "device_id": device_id,
                        "agent_id": body.agent_id,
                        "site_id": row["site_id"],
                        "samples": list(by_metric.values()),
                        "received_at": now.isoformat(),
                    },
                )
                device = store.get("device", device_id)
                if device["integration_id"] == "MANUAL":
                    stamp = max(s.source_timestamp for s in samples if s.device_id == device_id)
                    previous_seen = (
                        datetime.fromisoformat(device["last_seen"]) if device.get("last_seen") else None
                    )
                    if previous_seen is None or stamp >= previous_seen:
                        device.update(
                            last_seen=stamp.isoformat(), online=(now - stamp).total_seconds() <= 300
                        )
                        store.put("device", device_id, device)
            row.update(
                last_sequence=body.sequence,
                last_digest=digest,
                last_seen=now.isoformat(),
                version=body.version,
                last_dropped_expired=dropped,
            )
            if dropped:
                store.audit(
                    "operations",
                    {
                        "event": "agent_expired_points_discarded",
                        "agent_id": body.agent_id,
                        "count": dropped,
                        "sequence": body.sequence,
                    },
                    row["site_id"],
                )
            store.put("agent", body.agent_id, row)
        return {
            "accepted": True,
            "duplicate": False,
            "sequence": body.sequence,
            "samples": len(samples),
            "dropped_expired": dropped,
        }

    daemon = LocalAgentDaemon(
        on_snapshot=lambda res: _persist_local_snapshot(store, res)
    )
    app.state.local_daemon = daemon

    for row in store.list("local_device"):
        if row.get("enabled", True):
            try:
                daemon.add_device(LocalDeviceConfig(
                    device_id=row["device_id"],
                    transport=row["transport"],
                    address=row["address"],
                    port=row["port"],
                    vendor=row["vendor"],
                    model_series=row.get("model_series", ""),
                    unit_id=row.get("unit_id", 1),
                    logger_serial=row.get("logger_serial"),
                    poll_interval_s=row.get("poll_interval_s", 30.0),
                ))
            except Exception:
                pass

    @app.get("/api/agent/devices")
    async def list_local_devices(who=Depends(user) if user else None):
        statuses = {s["device_id"]: s for s in daemon.status()}
        stored = store.list("local_device")
        result = []
        for dev in stored:
            if who and hasattr(who, "can_access") and not who.can_access(dev.get("site_id", "default")):
                continue
            item = dict(dev)
            item["status"] = statuses.get(dev["device_id"], {})
            result.append(item)
        return result

    @app.post("/api/agent/devices")
    async def create_or_update_local_device(body: LocalDeviceCreate, who=Depends(user) if user else None):
        if admin and who:
            await admin(who)
        config = LocalDeviceConfig(
            device_id=body.device_id,
            transport=body.transport,
            address=body.address,
            port=body.port,
            vendor=body.vendor,
            model_series=body.model_series,
            unit_id=body.unit_id,
            logger_serial=body.logger_serial,
            poll_interval_s=body.poll_interval_s,
        )
        stored_dict = body.model_dump(mode="json")
        stored_dict["enabled"] = True
        store.put("local_device", body.device_id, stored_dict)

        existing_dev = store.get("device", body.device_id)
        if not existing_dev:
            from .domain import Device, DeviceIdentity
            d = Device(
                id=body.device_id,
                site_id=body.site_id,
                integration_id="LOCAL",
                vendor_id=body.vendor,
                type="inverter",
                identity=DeviceIdentity(vendor=body.vendor, model=body.model_series or "Local Inverter"),
                name=f"{body.vendor.capitalize()} {body.model_series}".strip(),
            )
            store.put("device", body.device_id, d.model_dump(mode="json"))

        if body.device_id not in daemon._pollers:
            daemon.add_device(config)

        return {"status": "ok", "device_id": body.device_id}

    @app.post("/api/agent/devices/{device_id}/poll")
    async def poll_local_device(device_id: str, who=Depends(user) if user else None):
        if who and hasattr(who, "can_access"):
            dev_entry = store.get("local_device", device_id)
            if dev_entry and not who.can_access(dev_entry.get("site_id", "default")):
                raise HTTPException(403, "site_scope_denied")
        poller = daemon._pollers.get(device_id)
        if not poller:
            raise HTTPException(404, "local_device_not_active")
        res = await poller.poll_once()
        if not res:
            return {"status": "failed", "device_id": device_id}
        _persist_local_snapshot(store, res)
        return {
            "status": "success",
            "device_id": device_id,
            "points": {k: v[0] for k, v in res.snapshot.points.items()},
            "online": res.snapshot.online,
        }

    @app.delete("/api/agent/devices/{device_id}")
    @app.post("/api/agent/devices/{device_id}/delete")
    async def delete_local_device(device_id: str, who=Depends(user) if user else None):
        if admin and who:
            await admin(who)
        await daemon.remove_device(device_id)
        row = store.get("local_device", device_id)
        if row:
            row["enabled"] = False
            store.put("local_device", device_id, row)
        return {"status": "ok", "device_id": device_id}


class Outbox:
    """One agent spool per database; acknowledge only after the server commits the same sequence."""

    def __init__(self, path):
        self.db = sqlite3.connect(path, isolation_level=None)
        self.db.executescript(
            "PRAGMA journal_mode=WAL; CREATE TABLE IF NOT EXISTS queue(sequence INTEGER PRIMARY KEY AUTOINCREMENT,body TEXT NOT NULL,sent INTEGER NOT NULL DEFAULT 0);"
        )
        self.db.execute("CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL)")

    def enqueue(self, agent_id, points):
        parsed = [AgentPoint.model_validate(p).model_dump(mode="json") for p in points]
        if not 1 <= len(parsed) <= 1000:
            raise ValueError("1..1000 points required")
        if self.db.execute("SELECT COUNT(*) FROM queue WHERE sent=0").fetchone()[0] >= 10000:
            raise ValueError("outbox capacity reached")
        self.db.execute("BEGIN IMMEDIATE")
        try:
            enrolled = self.db.execute("SELECT value FROM metadata WHERE key='agent_id'").fetchone()
            if enrolled and enrolled[0] != agent_id:
                raise ValueError("one agent identity per spool")
            self.db.execute("INSERT OR IGNORE INTO metadata VALUES('agent_id',?)", (agent_id,))
            cursor = self.db.execute("INSERT INTO queue(body) VALUES('{}')")
            body = {"agent_id": agent_id, "sequence": cursor.lastrowid, "version": "0.2.0", "points": parsed}
            self.db.execute("UPDATE queue SET body=? WHERE sequence=?", (encoded(body), cursor.lastrowid))
            self.db.commit()
        except BaseException:
            self.db.rollback()
            raise
        return body["sequence"]

    def flush(self, url, token, client=None):
        parsed = urlsplit(url)
        if (
            parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or parsed.path not in ("", "/")
        ):
            raise ValueError("controller base URL required")
        if parsed.scheme != "https" and not (
            parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost"}
        ):
            raise ValueError("HTTPS or local tunnel required")
        own_client = client is None
        client = client or httpx.Client(timeout=20, trust_env=False, follow_redirects=False)
        sent = 0
        try:
            for sequence, body in self.db.execute(
                "SELECT sequence,body FROM queue WHERE sent=0 ORDER BY sequence LIMIT 100"
            ).fetchall():
                response = client.post(
                    url.rstrip("/") + "/api/agent/inbox",
                    content=body,
                    headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
                )
                response.raise_for_status()
                result = response.json()
                if result.get("accepted") is not True or result.get("sequence") != sequence:
                    raise ValueError("agent acknowledgement mismatch")
                self.db.execute("UPDATE queue SET sent=1 WHERE sequence=?", (sequence,))
                sent += 1
            # AUTOINCREMENT retains the high watermark after pruning.
            self.db.execute(
                "DELETE FROM queue WHERE sent=1 AND sequence < (SELECT COALESCE(MAX(sequence),0)-100 FROM queue)"
            )
            return sent
        finally:
            if own_client:
                client.close()

    def close(self):
        self.db.close()


def main():
    parser = argparse.ArgumentParser(description="Solar Fleet outbound agent spool")
    parser.add_argument("--spool", type=Path, required=True)
    sub = parser.add_subparsers(dest="command", required=True)
    enqueue = sub.add_parser("enqueue", help="Queue timestamped JSON readings from an authorized driver")
    enqueue.add_argument("--agent-id", required=True)
    enqueue.add_argument("--file", type=Path, required=True)
    flush = sub.add_parser("flush", help="Send pending batches; token comes from SOLAR_AGENT_TOKEN")
    flush.add_argument("--controller", required=True)
    local = sub.add_parser(
        "collect-solarman", help="Read explicit reviewed register blocks and queue raw values"
    )
    local.add_argument("--profile", type=Path, required=True)
    model = sub.add_parser("collect-model", help="Read selected fields from a pinned community model profile")
    model.add_argument("--profile", type=Path, required=True)
    ha = sub.add_parser("collect-home-assistant", help="Read selected HA sensors; token from SOLAR_HA_TOKEN")
    ha.add_argument("--profile", type=Path, required=True)
    daemon_cmd = sub.add_parser(
        "daemon", help="Run background daemon polling local devices with auto-reconnect and spool enqueue"
    )
    daemon_cmd.add_argument("--config", type=Path, required=True, help="Path to devices JSON config list")
    daemon_cmd.add_argument("--agent-id", default="local-daemon", help="Agent identifier for queued telemetry")
    daemon_cmd.add_argument("--controller", help="Optional controller URL for automatic flush")
    daemon_cmd.add_argument("--cycles", type=int, default=1, help="Number of poll cycles to run (0 = run indefinitely)")
    args = parser.parse_args()
    args.spool.parent.mkdir(parents=True, exist_ok=True)
    outbox = Outbox(args.spool)
    try:
        if args.command == "enqueue":
            print(
                "Queued sequence",
                outbox.enqueue(args.agent_id, json.loads(args.file.read_text(encoding="utf-8"))),
            )
        elif args.command == "collect-solarman":
            from .local_solarman import CollectionProfile, collect

            profile = CollectionProfile.model_validate_json(args.profile.read_text(encoding="utf-8"))
            points = collect(profile)
            print("Queued sequence", outbox.enqueue(profile.agent_id, points))
        elif args.command == "collect-model":
            from .local_models import ModelCollectionProfile, collect_model

            profile = ModelCollectionProfile.model_validate_json(args.profile.read_text(encoding="utf-8"))
            print("Queued sequence", outbox.enqueue(profile.agent_id, collect_model(profile)))
        elif args.command == "collect-home-assistant":
            from .home_assistant_bridge import HomeAssistantProfile, collect_home_assistant

            profile = HomeAssistantProfile.model_validate_json(args.profile.read_text(encoding="utf-8"))
            points = collect_home_assistant(profile, os.environ.get("SOLAR_HA_TOKEN", ""))
            print("Queued sequence", outbox.enqueue(profile.agent_id, points))
        elif args.command == "daemon":
            import time

            devices_raw = json.loads(args.config.read_text(encoding="utf-8"))
            if isinstance(devices_raw, dict):
                devices_raw = [devices_raw]
            configs = [LocalDeviceConfig(**d) for d in devices_raw]

            points_batch: list[dict] = []

            def on_poll(res: PollResult):
                if res.snapshot and res.snapshot.points:
                    now_iso = (res.snapshot.timestamp or utcnow()).isoformat()
                    for k, (v, u) in res.snapshot.points.items():
                        if v is not None and isinstance(v, (int, float)):
                            points_batch.append({
                                "device_id": res.device_id,
                                "key": k,
                                "value": float(v),
                                "unit": u,
                                "timestamp": now_iso,
                            })

            daemon = LocalAgentDaemon(configs=configs, on_snapshot=on_poll)
            cycles_run = 0
            while True:
                points_batch.clear()
                daemon.poll_all_sync()
                cycles_run += 1
                if points_batch:
                    seq = outbox.enqueue(args.agent_id, points_batch)
                    print(f"Cycle {cycles_run}: Queued sequence {seq} ({len(points_batch)} points)")
                    if args.controller:
                        token = os.environ.get("SOLAR_AGENT_TOKEN", "")
                        if token:
                            try:
                                ack = outbox.flush(args.controller, token)
                                print(f"Cycle {cycles_run}: Flushed {ack} batches to controller")
                            except Exception as flush_err:
                                print(f"Cycle {cycles_run}: Flush warning: {flush_err}")
                else:
                    print(f"Cycle {cycles_run}: No points collected (devices offline or in backoff)")

                if args.cycles > 0 and cycles_run >= args.cycles:
                    break
                time.sleep(min(cfg.poll_interval_s for cfg in configs) if configs else 30)
        else:
            token = os.environ.get("SOLAR_AGENT_TOKEN")
            if not token:
                raise ValueError("missing agent token")
            print("Acknowledged batches", outbox.flush(args.controller, token))
    except Exception:
        parser.exit(
            1,
            "Agent operation failed; queued data was retained. Check configuration and scoped credentials.\n",
        )
    finally:
        outbox.close()


if __name__ == "__main__":
    main()
