"""Tests for LocalAgentDaemon and local device management API."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from starlette.testclient import TestClient

from solar_fleet.adapters.interfaces import TelemetrySnapshot
from solar_fleet.adapters.local_daemon import (
    LocalAgentDaemon,
    LocalDeviceConfig,
    PollResult,
)
from solar_fleet.agent import _persist_local_snapshot
from solar_fleet.app import create_app
from solar_fleet.controller import Controller
from solar_fleet.domain import Source
from solar_fleet.storage import Store


@pytest.fixture
def test_storage(tmp_path):
    db_path = tmp_path / "test.db"
    return Store(db_path)


@pytest.fixture
def test_controller(test_storage):
    return Controller(test_storage)


class TestLocalSnapshotPersistence:
    def test_persist_local_snapshot_creates_agent_latest(self, test_storage):
        snapshot = TelemetrySnapshot(
            device_sn="SN-TEST-01",
            points={
                "pv_power": (4200.0, "W"),
                "battery_soc": (88.0, "%"),
                "grid_power": (-1200.0, "W"),
            },
            timestamp=datetime.now(UTC),
            freshness_state="MEASURED",
            online=True,
        )
        res = PollResult(
            device_id="inv-local-01",
            snapshot=snapshot,
            polled_at=datetime.now(UTC),
        )

        _persist_local_snapshot(test_storage, res)

        latest = test_storage.get("agent_latest", "local-daemon:inv-local-01")
        assert latest is not None
        assert latest["device_id"] == "inv-local-01"
        assert latest["site_id"] == "default"

        metrics = {s["metric"]: s["value"] for s in latest["samples"]}
        assert metrics["pv_power"] == 4200.0
        assert metrics["battery_soc"] == 88.0
        assert metrics["grid_power"] == -1200.0


class TestLocalAgentDaemonQuarantine:
    @pytest.mark.asyncio
    async def test_daemon_quarantines_after_consecutive_failures(self):
        daemon = LocalAgentDaemon()
        config = LocalDeviceConfig(
            device_id="failing-dev",
            transport="modbus_tcp",
            address="192.0.2.1",
            port=502,
            vendor="growatt",
            model_series="SPH",
            poll_interval_s=1.0,
            timeout_s=0.1,
        )
        daemon.add_device(config)
        poller = daemon._pollers.get("failing-dev")
        if not poller:
            poller = daemon._pollers.setdefault("failing-dev", daemon._build_poller(config) if hasattr(daemon, "_build_poller") else None)

        # Trigger consecutive failures manually on poller
        from solar_fleet.adapters.local_daemon import LocalDevicePoller
        poller = LocalDevicePoller(config, on_snapshot=daemon._on_snapshot, on_failure=daemon._on_failure)
        for i in range(5):
            poller._handle_failure(f"connection_error_{i}")

        assert poller._consecutive_failures == 5
        assert poller._quarantined_until > 0

        # Next poll_once should return None immediately due to quarantine
        res = await poller.poll_once()
        assert res is None


ORIGIN = "http://127.0.0.1:8765"
PASSWORD = "SIMULATOR-workspace-password-only"


def _auth_headers(client, username="admin"):
    res = client.post(
        "/api/login",
        json={"username": username, "password": PASSWORD},
        headers={"Origin": ORIGIN},
    )
    assert res.status_code == 200
    csrf = res.json()["csrf"]
    return {"Origin": ORIGIN, "X-CSRF-Token": csrf, "Content-Type": "application/json"}


class TestLocalDeviceAPI:
    def test_list_and_register_local_device(self, local):
        client, ctl = local
        headers = _auth_headers(client, "admin")

        # Get initial list (empty or restored)
        resp = client.get("/api/agent/devices", headers={"Origin": ORIGIN})
        assert resp.status_code == 200

        # Register a new local device
        payload = {
            "device_id": "inv-sunsynk-01",
            "site_id": "sim-site",
            "transport": "sunsynk_local",
            "address": "192.168.1.55",
            "port": 502,
            "vendor": "sunsynk",
            "model_series": "Hybrid 8.8k",
            "unit_id": 1,
            "poll_interval_s": 15.0,
        }
        create_resp = client.post("/api/agent/devices", json=payload, headers=headers)
        assert create_resp.status_code == 200
        assert create_resp.json()["status"] == "ok"

        # List again - should contain the registered device
        list_resp = client.get("/api/agent/devices", headers={"Origin": ORIGIN})
        assert list_resp.status_code == 200
        devices = list_resp.json()
        matching = [d for d in devices if d["device_id"] == "inv-sunsynk-01"]
        assert len(matching) == 1
        assert matching[0]["address"] == "192.168.1.55"
        assert matching[0]["vendor"] == "sunsynk"

        # Delete device
        del_resp = client.delete("/api/agent/devices/inv-sunsynk-01", headers=headers)
        assert del_resp.status_code == 200
        assert del_resp.json()["status"] == "ok"

    def test_agent_cli_daemon_execution(self, tmp_path, monkeypatch):
        import json
        from solar_fleet.agent import main

        cfg_file = tmp_path / "devices.json"
        cfg_file.write_text(
            json.dumps([
                {
                    "device_id": "test-cli-dev",
                    "transport": "goodwe_udp",
                    "address": "127.0.0.1",
                    "port": 8899,
                    "vendor": "goodwe",
                    "poll_interval_s": 0.1,
                }
            ])
        )
        spool_db = tmp_path / "spool" / "outbox.db"
        test_args = [
            "solar_fleet.agent",
            "--spool",
            str(spool_db),
            "daemon",
            "--config",
            str(cfg_file),
            "--cycles",
            "1",
        ]
        monkeypatch.setattr("sys.argv", test_args)
        main()
        assert spool_db.exists()

