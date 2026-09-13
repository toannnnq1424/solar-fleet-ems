"""All identities and measurements in tests are explicit SIMULATOR fixtures; never imported by production."""

import socket

import httpx
import pytest

from solar_fleet.domain import Capability, Constraint, Device, DeviceIdentity, Principal, Role, utcnow
from solar_fleet.storage import Store


@pytest.fixture(autouse=True)
def no_live_network(monkeypatch):
    original_connect = socket.socket.connect

    def denied(*args, **kwargs):
        raise AssertionError("Unit/contract tests must not reach real vendor or hardware")

    def guarded_connect(sock, address):
        # Windows asyncio uses a TCP loopback socketpair internally. External HTTP remains blocked below.
        if isinstance(address, tuple) and address[0] in ("127.0.0.1", "::1"):
            return original_connect(sock, address)
        return denied()

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", denied)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", denied)


@pytest.fixture
def store():
    s = Store(":memory:")
    yield s
    s.close()


@pytest.fixture
def device():
    return Device(
        id="sim-device",
        site_id="sim-site",
        integration_id="sim-account",
        vendor_id="SIMULATOR-ONLY",
        type="INVERTER",
        online=True,
        last_seen=utcnow(),
        identity=DeviceIdentity(
            vendor="SIMULATOR",
            model="TEST",
            logger_model="TEST-LOGGER",
            firmware="TEST-1",
            protocol_version="TEST",
            account_type="TEST",
            privilege="TEST",
            region="TEST",
        ),
    )


@pytest.fixture
def operator():
    return Principal(id="sim-operator", role=Role.INSTALLER, site_ids=["sim-site"])


@pytest.fixture
def capability(device):
    return Capability(
        intent="SET_MAX_CHARGE_CURRENT",
        state="VERIFIED",
        semantic_match="exact",
        identity=device.identity,
        evidence_ids=["SIMULATOR_TEST_ONLY"],
        evidence_grade="E",
        constraints={"value": Constraint(min=0, max=50, step=1, unit="A")},
        hardware_verified=True,
        transport="SIMULATOR",
        reason="Test fixture only",
        readback_fields=["maxChargeCurrent"],
    )
