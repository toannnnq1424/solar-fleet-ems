from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import threading
import uuid
from collections.abc import Iterable
from contextlib import contextmanager
from datetime import timedelta
from pathlib import Path
from typing import Any

from .domain import CommandPlan, CommandStatus, Sample, utcnow
from .streams import initialize_events, invalidation

DEFAULT_RETENTION_DAYS = int(os.environ.get("TELEMETRY_RETENTION_DAYS", "30"))
DEFAULT_MAX_POINTS = int(os.environ.get("MAX_TELEMETRY_POINTS", "1000000"))


def encoded(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


class Store:
    """Single-controller pilot store; explicit schema and bounded telemetry retention."""

    def __init__(self, path: Path | str):
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        # CPython 3.12/3.13 statement-cache reuse can corrupt concurrent read results
        # on a shared connection (python/cpython#118172). This pilot has one controller.
        self.db = sqlite3.connect(
            str(path), check_same_thread=False, isolation_level=None, timeout=10, cached_statements=0
        )
        self.db.row_factory = sqlite3.Row
        self.lock = threading.RLock()
        self.db.executescript("""
            PRAGMA journal_mode=WAL;
            PRAGMA foreign_keys=ON;
            CREATE TABLE IF NOT EXISTS entities(kind TEXT,id TEXT,body TEXT NOT NULL,PRIMARY KEY(kind,id));
            CREATE TABLE IF NOT EXISTS entity_revisions(
                kind TEXT,id TEXT,revision INTEGER NOT NULL,PRIMARY KEY(kind,id));
            CREATE TRIGGER IF NOT EXISTS entity_revision_insert AFTER INSERT ON entities
                BEGIN INSERT INTO entity_revisions VALUES(NEW.kind,NEW.id,1)
                ON CONFLICT(kind,id) DO UPDATE SET revision=revision+1; END;
            DROP TRIGGER IF EXISTS entity_revision_update;
            CREATE TRIGGER entity_revision_update AFTER UPDATE ON entities
                WHEN OLD.body IS NOT NEW.body OR OLD.kind IS NOT NEW.kind OR OLD.id IS NOT NEW.id
                BEGIN
                INSERT INTO entity_revisions VALUES(OLD.kind,OLD.id,1)
                ON CONFLICT(kind,id) DO UPDATE SET revision=revision+1;
                INSERT INTO entity_revisions(kind,id,revision)
                SELECT NEW.kind,NEW.id,1
                WHERE OLD.kind IS NOT NEW.kind OR OLD.id IS NOT NEW.id
                ON CONFLICT(kind,id) DO UPDATE SET revision=revision+1; END;
            CREATE TRIGGER IF NOT EXISTS entity_revision_delete AFTER DELETE ON entities
                BEGIN INSERT INTO entity_revisions VALUES(OLD.kind,OLD.id,1)
                ON CONFLICT(kind,id) DO UPDATE SET revision=revision+1; END;
            CREATE TABLE IF NOT EXISTS secrets(id TEXT PRIMARY KEY,ciphertext BLOB NOT NULL);
            CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,password_hash TEXT NOT NULL,
                role TEXT NOT NULL,sites TEXT NOT NULL,permissions TEXT NOT NULL,active INTEGER NOT NULL DEFAULT 1);
            CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY,user_id TEXT NOT NULL,
                csrf TEXT NOT NULL,expires TEXT NOT NULL,FOREIGN KEY(user_id) REFERENCES users(id));
            CREATE TABLE IF NOT EXISTS security_revisions(
                kind TEXT,id TEXT,revision INTEGER NOT NULL,PRIMARY KEY(kind,id));
            CREATE TRIGGER IF NOT EXISTS user_revision_insert AFTER INSERT ON users
                BEGIN INSERT INTO security_revisions VALUES('user',NEW.id,1)
                ON CONFLICT(kind,id) DO UPDATE SET revision=revision+1; END;
            CREATE TRIGGER IF NOT EXISTS user_revision_update AFTER UPDATE ON users
                WHEN OLD.id IS NOT NEW.id OR OLD.password_hash IS NOT NEW.password_hash
                OR OLD.role IS NOT NEW.role OR OLD.sites IS NOT NEW.sites
                OR OLD.permissions IS NOT NEW.permissions OR OLD.active IS NOT NEW.active
                BEGIN
                INSERT INTO security_revisions VALUES('user',OLD.id,1)
                ON CONFLICT(kind,id) DO UPDATE SET revision=revision+1;
                INSERT INTO security_revisions SELECT 'user',NEW.id,1 WHERE OLD.id IS NOT NEW.id
                ON CONFLICT(kind,id) DO UPDATE SET revision=revision+1; END;
            CREATE TRIGGER IF NOT EXISTS user_revision_delete AFTER DELETE ON users
                BEGIN INSERT INTO security_revisions VALUES('user',OLD.id,1)
                ON CONFLICT(kind,id) DO UPDATE SET revision=revision+1; END;
            CREATE TRIGGER IF NOT EXISTS session_revision_insert AFTER INSERT ON sessions
                BEGIN INSERT INTO security_revisions VALUES('session',NEW.token_hash,1)
                ON CONFLICT(kind,id) DO UPDATE SET revision=revision+1; END;
            CREATE TRIGGER IF NOT EXISTS session_revision_update AFTER UPDATE ON sessions
                WHEN OLD.token_hash IS NOT NEW.token_hash OR OLD.user_id IS NOT NEW.user_id
                OR OLD.csrf IS NOT NEW.csrf OR OLD.expires IS NOT NEW.expires
                BEGIN
                INSERT INTO security_revisions VALUES('session',OLD.token_hash,1)
                ON CONFLICT(kind,id) DO UPDATE SET revision=revision+1;
                INSERT INTO security_revisions SELECT 'session',NEW.token_hash,1
                WHERE OLD.token_hash IS NOT NEW.token_hash
                ON CONFLICT(kind,id) DO UPDATE SET revision=revision+1; END;
            CREATE TRIGGER IF NOT EXISTS session_revision_delete AFTER DELETE ON sessions
                BEGIN INSERT INTO security_revisions VALUES('session',OLD.token_hash,1)
                ON CONFLICT(kind,id) DO UPDATE SET revision=revision+1; END;
            CREATE TABLE IF NOT EXISTS plans(id TEXT PRIMARY KEY,body TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS commands(id TEXT PRIMARY KEY,idempotency_key TEXT NOT NULL UNIQUE,
                plan_id TEXT NOT NULL UNIQUE,device_id TEXT NOT NULL,site_id TEXT NOT NULL,operator_id TEXT NOT NULL,
                status TEXT NOT NULL,order_ids TEXT NOT NULL,updated_at TEXT NOT NULL,error TEXT,
                readback TEXT, FOREIGN KEY(plan_id) REFERENCES plans(id));
            CREATE TABLE IF NOT EXISTS audit(seq INTEGER PRIMARY KEY AUTOINCREMENT,category TEXT NOT NULL,
                site_id TEXT,body TEXT NOT NULL,previous_hash TEXT NOT NULL,hash TEXT NOT NULL);
            CREATE TRIGGER IF NOT EXISTS audit_no_update BEFORE UPDATE ON audit
                BEGIN SELECT RAISE(ABORT,'audit is append only'); END;
            CREATE TRIGGER IF NOT EXISTS audit_no_delete BEFORE DELETE ON audit
                BEGIN SELECT RAISE(ABORT,'audit is append only'); END;
            CREATE TABLE IF NOT EXISTS samples(device_id TEXT,metric TEXT,binding_id TEXT,source_ts TEXT,
                received_at TEXT NOT NULL,body TEXT NOT NULL,
                PRIMARY KEY(device_id,metric,binding_id,source_ts));
            CREATE INDEX IF NOT EXISTS samples_time ON samples(received_at);
            CREATE INDEX IF NOT EXISTS samples_lookup ON samples(device_id,metric,received_at DESC);
            PRAGMA user_version=1;
        """)

        initialize_events(self.db)

    @contextmanager
    def transaction(self):
        """Atomic synchronous work, including audit writes. Never await inside this scope."""
        with self.lock:
            if self.db.in_transaction:
                savepoint = "sf_" + uuid.uuid4().hex
                self.db.execute(f"SAVEPOINT {savepoint}")
                try:
                    yield self.db
                    self.db.execute(f"RELEASE SAVEPOINT {savepoint}")
                except BaseException:
                    self.db.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
                    self.db.execute(f"RELEASE SAVEPOINT {savepoint}")
                    raise
                return
            self.db.execute("BEGIN IMMEDIATE")
            try:
                yield self.db
                self.db.commit()
            except BaseException:
                self.db.rollback()
                raise

    def close(self):
        self.db.close()

    def put(self, kind: str, id: str, body: dict):
        with self.transaction():
            self.db.execute(
                "INSERT INTO entities VALUES(?,?,?) ON CONFLICT(kind,id) DO UPDATE SET body=excluded.body",
                (kind, id, encoded(body)),
            )
            invalidation(self, kind, id, body)

    def get(self, kind: str, id: str) -> dict | None:
        row = self.db.execute("SELECT body FROM entities WHERE kind=? AND id=?", (kind, id)).fetchone()
        return json.loads(row[0]) if row else None

    def revisions(self, *kinds: str) -> dict[str, dict[str, int]]:
        """Durable tombstones catch ABA, including SQL deletes; rollback is atomic.

        Kind-wide fences deliberately invalidate unrelated concurrent changes too.
        This is a safety fence, not a multiprocess command serialization mechanism.
        """
        with self.lock:
            return {kind: dict(self.db.execute(
                "SELECT id,revision FROM entity_revisions WHERE kind=? ORDER BY id", (kind,)
            ).fetchall()) for kind in kinds}

    def object_revisions(self, selection: dict[str, Iterable[str]]) -> dict[str, dict[str, int]]:
        """Capture only selected identities, including absent rows and tombstones.

        Mapping values are iterables of IDs (snapshot dictionaries work too).
        A returned snapshot can itself be passed here to revalidate the same set.
        Full-body revisions intentionally retain heartbeat/write-conflict fencing.
        """
        with self.transaction():
            return {kind: {id: self._entity_revision(kind, id) for id in ids}
                    for kind, ids in selection.items()}

    def _entity_revision(self, kind: str, id: str) -> int:
        row = self.db.execute(
            "SELECT revision FROM entity_revisions WHERE kind=? AND id=?", (kind, id)
        ).fetchone()
        return row[0] if row else 0

    def security_revision(self, kind: str, id: str) -> int:
        row = self.db.execute(
            "SELECT revision FROM security_revisions WHERE kind=? AND id=?", (kind, id)
        ).fetchone()
        return row[0] if row else 0

    def list(self, kind: str) -> list[dict]:
        return [
            json.loads(r[0])
            for r in self.db.execute("SELECT body FROM entities WHERE kind=? ORDER BY id", (kind,))
        ]

    def save_plan(self, plan: CommandPlan):
        self.db.execute("INSERT INTO plans VALUES(?,?)", (plan.id, plan.model_dump_json()))

    def plan(self, id: str) -> CommandPlan | None:
        row = self.db.execute("SELECT body FROM plans WHERE id=?", (id,)).fetchone()
        return CommandPlan.model_validate_json(row[0]) if row else None

    def claim_command(self, plan: CommandPlan, key: str) -> tuple[dict, bool]:
        with self.transaction() as db:
            row = db.execute(
                "SELECT * FROM commands WHERE idempotency_key=? OR plan_id=?", (key, plan.id)
            ).fetchone()
            if row:
                if row["plan_id"] != plan.id or row["idempotency_key"] != key:
                    raise ValueError("idempotency key or plan already used")
                return dict(row), False
            db.execute(
                "INSERT INTO commands VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (
                    plan.id,
                    key,
                    plan.id,
                    plan.device_id,
                    plan.site_id,
                    plan.operator_id,
                    CommandStatus.CREATED,
                    "[]",
                    utcnow().isoformat(),
                    None,
                    None,
                ),
            )
            return dict(db.execute("SELECT * FROM commands WHERE id=?", (plan.id,)).fetchone()), True

    def command(self, id: str) -> dict | None:
        row = self.db.execute("SELECT * FROM commands WHERE id=?", (id,)).fetchone()
        return dict(row) if row else None

    def update_command(
        self,
        id: str,
        status: CommandStatus,
        *,
        order_ids: list[str] | None = None,
        error: str | None = None,
        readback: dict | None = None,
    ):
        with self.transaction() as db:
            current = db.execute("SELECT order_ids FROM commands WHERE id=?", (id,)).fetchone()
            db.execute(
                "UPDATE commands SET status=?,order_ids=?,updated_at=?,error=?,readback=? WHERE id=?",
                (
                    status,
                    encoded(order_ids) if order_ids is not None else current[0],
                    utcnow().isoformat(),
                    error,
                    encoded(readback) if readback is not None else None,
                    id,
                ),
            )

    def commands(self) -> list[dict]:
        return [dict(r) for r in self.db.execute("SELECT * FROM commands ORDER BY updated_at DESC LIMIT 500")]

    def recover_commands(self):
        # Restart does not mean the inverter did not receive an earlier request.
        inflight = {"CREATED", "VALIDATING", "READY", "SENDING", "ACCEPTED", "WAITING_DEVICE", "VERIFYING"}
        for row in self.commands():
            if row["status"] in inflight:
                self.update_command(
                    row["id"], CommandStatus.TIMEOUT, error="controller_restarted_outcome_unknown"
                )
                self.audit("control", {"command_id": row["id"], "event": "recovery_timeout"}, row["site_id"])

    def audit(self, category: str, body: dict, site_id: str | None = None):
        from .security import redact

        payload = encoded(
            {**redact(body), "timestamp": utcnow().isoformat(), "category": category, "site_id": site_id}
        )
        with self.transaction() as db:
            last = db.execute("SELECT hash FROM audit ORDER BY seq DESC LIMIT 1").fetchone()
            previous = last[0] if last else "0" * 64
            digest = hashlib.sha256((previous + payload).encode()).hexdigest()
            db.execute(
                "INSERT INTO audit(category,site_id,body,previous_hash,hash) VALUES(?,?,?,?,?)",
                (category, site_id, payload, previous, digest),
            )

    def audit_rows(self, category: str) -> list[dict]:
        return [
            dict(r) | {"body": json.loads(r["body"])}
            for r in self.db.execute(
                "SELECT * FROM audit WHERE category=? ORDER BY seq DESC LIMIT 500", (category,)
            )
        ]

    def verify_audit(self) -> bool:
        previous = "0" * 64
        for r in self.db.execute("SELECT * FROM audit ORDER BY seq"):
            if (
                r["previous_hash"] != previous
                or hashlib.sha256((previous + r["body"]).encode()).hexdigest() != r["hash"]
            ):
                return False
            previous = r["hash"]
        return True

    def add_samples(
        self,
        samples: list[Sample],
        retention_days: int | None = None,
        max_points: int | None = None,
    ):
        r_days = retention_days if retention_days is not None else DEFAULT_RETENTION_DAYS
        m_points = max_points if max_points is not None else DEFAULT_MAX_POINTS
        with self.transaction() as db:
            for s in samples:
                # Without a source timestamp retain only latest unknown measurement per binding/metric.
                timestamp = s.source_timestamp.isoformat() if s.source_timestamp else "UNKNOWN"
                db.execute(
                    "INSERT INTO samples VALUES(?,?,?,?,?,?) ON CONFLICT(device_id,metric,binding_id,source_ts) "
                    "DO UPDATE SET received_at=excluded.received_at,body=excluded.body",
                    (
                        s.device_id,
                        s.metric,
                        s.binding_id,
                        timestamp,
                        s.received_at.isoformat(),
                        s.model_dump_json(),
                    ),
                )
            cutoff = (utcnow() - timedelta(days=r_days)).isoformat()
            db.execute("DELETE FROM samples WHERE received_at < ?", (cutoff,))
            db.execute(
                "DELETE FROM samples WHERE rowid IN (SELECT rowid FROM samples ORDER BY received_at DESC "
                "LIMIT -1 OFFSET ?)",
                (m_points,),
            )

    def history(self, device_id: str, limit: int = 1000) -> list[dict]:
        return [
            json.loads(r[0])
            for r in self.db.execute(
                "SELECT body FROM samples WHERE device_id=? ORDER BY source_ts DESC LIMIT ?",
                (device_id, min(limit, 5000)),
            )
        ]

    def report_samples(self, device_id, start=None, end=None, metric=None, limit=10001):
        # Filter before limiting; julianday handles timezone offsets rather than lexicographic ISO ordering.
        moment = "julianday(CASE WHEN source_ts='UNKNOWN' THEN received_at ELSE source_ts END)"
        where, parameters = ["device_id=?"], [device_id]
        for bound, op in ((start, ">="), (end, "<")):
            if bound is not None:
                where.append(f"{moment} {op} julianday(?)")
                parameters.append(bound.isoformat())
        if metric is not None:
            where.append("metric=?")
            parameters.append(metric)
        parameters.append(min(limit, 10001))
        return [
            json.loads(r[0])
            for r in self.db.execute(
                f"SELECT body FROM samples WHERE {' AND '.join(where)} ORDER BY {moment} DESC LIMIT ?",
                parameters,
            )
        ]
