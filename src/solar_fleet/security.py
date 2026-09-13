from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
from datetime import timedelta
from pathlib import Path
from typing import Any

import keyring
from cryptography.fernet import Fernet, InvalidToken

from .domain import Capability, Principal, Role, SafetyError, utcnow

SECRET_KEYS = {
    "password",
    "appsecret",
    "accesstoken",
    "refreshtoken",
    "authorization",
    "token",
    "secret",
    "systemcode",
}


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            k: "[REDACTED]" if any(s in k.lower().replace("_", "") for s in SECRET_KEYS) else redact(v)
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [redact(v) for v in value]
    return value


def password_hash(password: str) -> str:
    if len(password) < 12 or len(password) > 256:
        raise ValueError("password must contain 12–256 characters")
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**15, r=8, p=1, maxmem=64 * 1024 * 1024)
    return base64.b64encode(salt + digest).decode()


def verify_password(password: str, stored: str) -> bool:
    if len(password) > 256:
        return False
    try:
        data = base64.b64decode(stored, validate=True)
        salt, expected = data[:16], data[16:]
        actual = hashlib.scrypt(password.encode(), salt=salt, n=2**15, r=8, p=1, maxmem=64 * 1024 * 1024)
        return hmac.compare_digest(expected, actual)
    except (ValueError, TypeError):
        return False


class Vault:
    def __init__(self, store, master_key: str | bytes):
        self.store = store
        self.fernet = Fernet(master_key)

    def put(self, id: str, value: dict):
        ciphertext = self.fernet.encrypt(json.dumps(value).encode())
        self.store.db.execute(
            "INSERT INTO secrets VALUES(?,?) ON CONFLICT(id) DO UPDATE SET ciphertext=excluded.ciphertext",
            (id, ciphertext),
        )

    def get(self, id: str) -> dict:
        row = self.store.db.execute("SELECT ciphertext FROM secrets WHERE id=?", (id,)).fetchone()
        if not row:
            raise SafetyError("credentials_missing")
        try:
            return json.loads(self.fernet.decrypt(row[0]))
        except (InvalidToken, ValueError):
            raise SafetyError("credentials_unavailable") from None


def master_key(data_dir: Path, *, create: bool = False) -> str:
    value = os.getenv("SOLAR_MASTER_KEY")
    if value:
        Fernet(value)
        return value
    identity = hashlib.sha256(str(data_dir.resolve()).encode()).hexdigest()
    try:
        value = keyring.get_password("solar-fleet-ems", identity)
        if value is None and create:
            value = Fernet.generate_key().decode()
            keyring.set_password("solar-fleet-ems", identity, value)
    except keyring.errors.KeyringError:
        raise SafetyError("OS keyring unavailable; supply SOLAR_MASTER_KEY externally") from None
    if value is None:
        raise SafetyError("run solar-fleet init first")
    return value


def create_user(
    store, id: str, password: str, role: Role, sites: list[str], permissions: list[str] | None = None
):
    if not id or len(id) > 100:
        raise ValueError("invalid user name")
    store.db.execute(
        "INSERT INTO users(id,password_hash,role,sites,permissions) VALUES(?,?,?,?,?)",
        (id, password_hash(password), role, json.dumps(sites), json.dumps(permissions or [])),
    )
    store.audit("security", {"event": "user_created", "operator": id, "role": role})


def principal(store, id: str) -> Principal | None:
    row = store.db.execute("SELECT * FROM users WHERE id=? AND active=1", (id,)).fetchone()
    return (
        Principal(
            id=row["id"],
            role=row["role"],
            site_ids=json.loads(row["sites"]),
            permissions=json.loads(row["permissions"]),
        )
        if row
        else None
    )


def new_session(store, id: str) -> tuple[str, str]:
    token = secrets.token_urlsafe(32)
    csrf = secrets.token_urlsafe(32)
    store.db.execute("DELETE FROM sessions WHERE expires < ?", (utcnow().isoformat(),))
    store.db.execute(
        "INSERT INTO sessions VALUES(?,?,?,?)",
        (hashlib.sha256(token.encode()).hexdigest(), id, csrf, (utcnow() + timedelta(hours=8)).isoformat()),
    )
    return token, csrf


def session_user(store, token: str | None) -> tuple[Principal, str] | None:
    if not token:
        return None
    row = store.db.execute(
        "SELECT * FROM sessions WHERE token_hash=? AND expires>?",
        (hashlib.sha256(token.encode()).hexdigest(), utcnow().isoformat()),
    ).fetchone()
    user = principal(store, row["user_id"]) if row else None
    return (user, row["csrf"]) if user else None


def authorize_control(user: Principal, site_id: str, capability: Capability):
    if not user.can_access(site_id):
        raise SafetyError("site_access_denied")
    rank = {Role.VIEWER: 0, Role.OPERATOR: 1, Role.INSTALLER: 2, Role.ENGINEER: 3, Role.ADMIN: 0}
    if user.role in (Role.VIEWER, Role.ADMIN) or capability.required_role not in (
        Role.OPERATOR,
        Role.INSTALLER,
        Role.ENGINEER,
    ):
        raise SafetyError("control_role_denied")
    if rank[user.role] < rank[capability.required_role]:
        raise SafetyError("control_role_denied")
    if capability.required_permission and capability.required_permission not in user.permissions:
        raise SafetyError("additional_permission_required")
