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
from fastapi import HTTPException, Request
from pydantic import Field, field_validator

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


def install_agent(app, controller):
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
