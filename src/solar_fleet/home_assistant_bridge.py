"""Explicit Home Assistant sensor bindings feeding the existing agent outbox.

The REST client only reads selected entities; no service call, automation or
state mutation is implemented. HA/SEM/EMHASS remain independent installations.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta
from urllib.parse import urlsplit

import httpx
from pydantic import Field, field_validator, model_validator

from .domain import Model, utcnow
from .local_models import private_ipv4


class EntityBinding(Model):
    entity_id: str = Field(pattern=r"^sensor\.[a-z0-9_]{1,90}$")
    device_id: str = Field(min_length=1, max_length=100)
    expected_unit: str | None = Field(default=None, max_length=40)


class HomeAssistantProfile(Model):
    agent_id: str = Field(min_length=1, max_length=100)
    base_url: str
    bindings: list[EntityBinding] = Field(min_length=1, max_length=100)
    reviewed_by: str = Field(min_length=1, max_length=200)
    evidence_reference: str = Field(min_length=1, max_length=500)
    max_age_seconds: int = Field(default=300, ge=1, le=86400)

    @field_validator("base_url")
    @classmethod
    def local_server(cls, value):
        parsed = urlsplit(value)
        if (
            parsed.scheme not in ("http", "https")
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or parsed.path not in ("", "/")
        ):
            raise ValueError("use an explicit local HA origin without path or credentials")
        private_ipv4(parsed.hostname or "")
        if parsed.port is not None and not 1 <= parsed.port <= 65535:
            raise ValueError("invalid Home Assistant port")
        return value.rstrip("/")

    @model_validator(mode="after")
    def unique_bindings(self):
        keys = [(b.entity_id, b.device_id) for b in self.bindings]
        if len(set(keys)) != len(keys):
            raise ValueError("duplicate Home Assistant binding")
        return self


def collect_home_assistant(profile: HomeAssistantProfile, token: str, client=None, now=None) -> list[dict]:
    if not token or any(c.isspace() for c in token):
        raise ValueError("missing or malformed Home Assistant access token")
    now = now or utcnow()
    own = client is None
    client = client or httpx.Client(timeout=10, trust_env=False, follow_redirects=False)
    points = []
    try:
        for binding in profile.bindings:
            with client.stream(
                "GET",
                profile.base_url + "/api/states/" + binding.entity_id,
                headers={"Authorization": "Bearer " + token},
            ) as response:
                response.raise_for_status()
                body = bytearray()
                for chunk in response.iter_bytes():
                    body.extend(chunk)
                    if len(body) > 128_000:
                        raise ValueError("Home Assistant entity response too large")
                import json

                entity = json.loads(body)
            if entity.get("entity_id") != binding.entity_id:
                raise ValueError("Home Assistant entity mismatch")
            attributes = entity.get("attributes") or {}
            if attributes.get("unit_of_measurement") != binding.expected_unit:
                raise ValueError("Home Assistant unit changed; review the binding")
            # last_reported records a fresh report even when a numeric state did
            # not change. Older HA falls back to last_updated conservatively.
            stamp = datetime.fromisoformat(entity.get("last_reported") or entity["last_updated"])
            if stamp.tzinfo is None or stamp > now + timedelta(seconds=5):
                raise ValueError("invalid Home Assistant acquisition timestamp")
            if now - stamp > timedelta(seconds=profile.max_age_seconds):
                raise ValueError("Home Assistant entity is stale")
            state = entity.get("state")
            if state in ("unknown", "unavailable", None):
                value = None
            elif isinstance(state, bool):
                raise ValueError("non-numeric Home Assistant state")
            else:
                value = float(state)
                if not math.isfinite(value):
                    raise ValueError("non-finite Home Assistant state")
            points.append(
                {
                    "device_id": binding.device_id,
                    "key": "ha." + binding.entity_id,
                    "value": value,
                    "unit": binding.expected_unit,
                    "timestamp": stamp.isoformat(),
                }
            )
        return points
    finally:
        if own:
            client.close()
