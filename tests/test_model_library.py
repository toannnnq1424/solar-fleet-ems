"""Synthetic wire values; source maps are candidates, never hardware acceptance."""

import json
import struct
from datetime import datetime

import pytest
from pydantic import ValidationError
from test_management_runtime import enroll
from test_workspaces import login

from solar_fleet.agent import Outbox
from solar_fleet.local_models import ModbusTcpReader, ModelCollectionProfile, collect_model
from solar_fleet.model_library import (
    DecodeSpec,
    ModelField,
    RegisterReading,
    decode,
    decode_value,
    get_profile,
    native_label,
    plan,
    profiles,
)


def configured(**changes):
    profile = get_profile("glance-solis-rhi-s6-hybrid")
    return ModelCollectionProfile.model_validate(
        {
            "agent_id": "SIM-AGENT",
            "device_id": "sim-device",
            "profile_id": profile.id,
            "profile_digest": profile.profile_digest,
            "field_ids": ["powerkw"],
            "address": "192.168.50.1",
            "port": 502,
            "unit_id": 1,
            "transport": "modbus_tcp",
            "inverter_model": "SIMULATOR",
            "inverter_firmware": "TEST",
            "logger_model": "TEST",
            "logger_firmware": "TEST",
            "reviewed_by": "TEST",
            "evidence_reference": "TEST-ONLY",
            "request_delay_seconds": 0,
            **changes,
        }
    )


def reading(address, value, function=4):
    return RegisterReading(function=function, address=address, value=value)


def test_catalog_is_model_specific_and_not_a_write_registry():
    data = profiles()
    assert len(data) == 41
    assert sum(len(p.fields) for p in data) == 3145
    assert sum(f.decode is not None for p in data for f in p.fields) == 913
    assert all(p.source_revision in p.source_url and p.license == "MIT" for p in data)
    assert get_profile("glance-goodwe-et-eh-hybrid").unit_id_hint == 247
    assert get_profile("glance-growatt-sph-tl-bh").fields[0].decode.scale == 0.0001
    assert get_profile("glance-solis-s5-s6-string").fields[0].decode.registers == [3004, 3005]
    profile = get_profile("ha-solarman-models-deye-hybrid")
    blocked = next(f for f in profile.fields if f.blocked_reason)
    with pytest.raises(ValueError, match=blocked.id):
        plan(profile, [blocked.id])


def test_profile_revision_pin_and_copy_isolation():
    profile = get_profile("glance-solis-rhi-s6-hybrid")
    with pytest.raises(ValueError, match="changed"):
        get_profile(profile.id, "a" * 64)
    profile.fields.clear()
    assert get_profile(profile.id).fields


@pytest.mark.parametrize(
    "options,words,expected",
    [
        ({"encoding": "unsigned", "word_order": "big"}, [1, 2], 65538),
        ({"encoding": "unsigned", "word_order": "little"}, [1, 2], 131073),
        ({"encoding": "signed", "word_order": "big", "scale": 0.001}, [65535, 64536], -1),
        ({"encoding": "signed", "word_order": "little"}, [65534, 65535], -2),
        ({"encoding": "magnitude"}, [32768, 20], -20),
        ({"encoding": "unsigned", "offset": -1000, "scale": 0.1}, [0, 1250], 25),
        ({"encoding": "unsigned", "post_offset": -10, "scale": 0.1}, [0, 250], 15),
        ({"encoding": "unsigned", "mask": 255, "bit": 1}, [0, 258], 1),
        ({"encoding": "unsigned", "floor_divisor": 3}, [0, 10], 3),
        ({"encoding": "ascii"}, [0x4142, 0x4300], "ABC"),
        ({"encoding": "float32"}, [0x3F80, 0], 1),
    ],
)
def test_encoding_transform_contract(options, words, expected):
    spec = DecodeSpec(function=3, registers=[90, 91], **options)
    assert decode_value(spec, {(3, 90): words[0], (3, 91): words[1]}) == expected


def test_descending_word_addresses_preserve_declared_significance():
    spec = DecodeSpec(function=3, registers=[91, 90], word_order="little")
    assert decode_value(spec, {(3, 90): 1, (3, 91): 2}) == 65538


def test_plan_reads_only_selected_addresses_and_splits_at_limits():
    p = get_profile("glance-solis-rhi-s6-hybrid")
    p.max_block_size = 2
    p.fields = [
        ModelField(id="x", name="Synthetic", decode=DecodeSpec(function=3, registers=[0, 1, 2, 4])),
        ModelField(id="y", name="Synthetic", decode=DecodeSpec(function=4, registers=[0])),
    ]
    result = plan(p, ["x", "y"])
    assert [(b.function, b.address, b.count) for b in result.blocks] == [
        (3, 0, 2),
        (3, 2, 1),
        (3, 4, 1),
        (4, 0, 1),
    ]
    assert not result.hardware_verified and not result.write_enabled
    with pytest.raises(ValueError):
        plan(p, ["x", "x"])


@pytest.mark.parametrize("value", [-1, 65536, True, 1.2, "100"])
def test_raw_register_contract_rejects_coercion(value):
    with pytest.raises(ValidationError):
        reading(33057, value)


def test_partial_invalid_and_unrequested_responses_stay_non_good():
    p = get_profile("glance-solis-rhi-s6-hybrid")
    assert decode(p, ["powerkw"], [reading(33057, 0)])[0]["quality"] == "MISSING"
    assert decode(p, ["batterypercent"], [reading(33139, 65535)])[0]["quality"] == "INVALID"
    for readings in ([reading(33057, 0), reading(33057, 1)], [reading(1, 10)]):
        with pytest.raises(ValueError):
            decode(p, ["powerkw"], readings)


@pytest.mark.parametrize(
    "address", ["127.0.0.1", "0.0.0.0", "8.8.8.8", "169.254.1.1", "224.0.0.1", "::1", "localhost"]
)
def test_collector_requires_explicit_private_installation_address(address):
    with pytest.raises(ValidationError):
        configured(address=address)


class FakeSocket:
    def __init__(self, response):
        self.response = bytearray(response)
        self.sent = []
        self.closed = False

    def sendall(self, frame):
        self.sent.append(frame)

    def recv(self, size):
        # Simulate TCP fragmentation down to one byte.
        part = bytes(self.response[: min(size, 1)])
        del self.response[: len(part)]
        return part

    def settimeout(self, value):
        assert value > 0

    def close(self):
        self.closed = True


def tcp_response(tx=1, protocol=0, unit=1, function=4, count=4, data=b"\x00\x00\x03\xe8"):
    return struct.pack(">HHHBBB", tx, protocol, len(data) + 3, unit, function, count) + data


def test_tcp_read_fragmentation_unit_and_transaction():
    sock = FakeSocket(tcp_response())
    reader = ModbusTcpReader(configured(), connector=lambda *a, **k: sock)
    assert reader.read(4, 33057, 2) == [0, 1000]
    assert struct.unpack(">HHHBBHH", sock.sent[0]) == (1, 0, 6, 1, 4, 33057, 2)
    reader.close()
    assert sock.closed


@pytest.mark.parametrize(
    "changes",
    [
        {"tx": 2},
        {"protocol": 1},
        {"unit": 2},
        {"function": 3},
        {"count": 2},
        {"data": b"\x00\x01"},
        {"function": 0x84, "count": 2, "data": b""},
    ],
)
def test_tcp_rejects_mismatched_and_exception_frames(changes):
    sock = FakeSocket(tcp_response(**changes))
    reader = ModbusTcpReader(configured(), connector=lambda *a, **k: sock)
    with pytest.raises(ValueError):
        reader.read(4, 33057, 2)


def test_no_write_opcode_and_no_truncated_frame_accepted():
    reader = ModbusTcpReader(configured(), connector=lambda *a, **k: FakeSocket(b"\x00"))
    with pytest.raises(ValueError, match="invalid read"):
        reader.read(6, 0, 1)
    with pytest.raises(ValueError, match="truncated"):
        reader.read(3, 0, 1)


class FakeReader:
    def __init__(self, config):
        self.closed = False

    def read(self, function, address, count):
        assert (function, address, count) == (4, 33057, 2)
        return [0, 1000]

    def close(self):
        self.closed = True


def test_collection_to_spool_ingestion_and_mapping_context(local, tmp_path):
    client, ctl = local
    agent, headers = enroll(local)
    config = configured(agent_id=agent["id"])
    fake = FakeReader(config)
    points = collect_model(config, factory=lambda _: fake)
    assert fake.closed and points[0]["value"] == 1
    assert "powerkw" in points[0]["key"] and points[0]["unit"] == "kW"
    with_payload = {"agent_id": agent["id"], "sequence": 1, "version": "TEST", "points": points}
    # Existing durable spool serializes the exact same native points.
    outbox = Outbox(tmp_path / "spool.sqlite")
    assert outbox.enqueue(agent["id"], points) == 1
    saved = json.loads(outbox.db.execute("SELECT body FROM queue").fetchone()[0])
    for actual, expected in zip(saved["points"], points, strict=True):
        assert datetime.fromisoformat(actual["timestamp"]) == datetime.fromisoformat(expected["timestamp"])
        assert {k: v for k, v in actual.items() if k != "timestamp"} == {
            k: v for k, v in expected.items() if k != "timestamp"
        }
    outbox.close()
    client.cookies.clear()
    response = client.post(
        "/api/agent/inbox", json=with_payload, headers={"Authorization": "Bearer " + agent["token"]}
    )
    assert response.status_code == 200
    login(local)
    context = client.get("/api/devices/sim-device/mapping-context").json()
    channel = next(c for c in context["channels"] if c["metric"].startswith("agent.native.model."))
    assert channel["quality"] == "UNVERIFIED" and channel["value"] == 1
    assert channel["label"].startswith("powerKW") and native_label(channel["metric"])
    assert not ctl.store.commands()
    assert all(s["quality"] != "GOOD" for s in ctl.store.history("sim-device"))


def test_partial_collection_closes_connection_and_returns_no_batch():
    config = configured()
    reader = FakeReader(config)
    reader.read = lambda *args: [0]
    with pytest.raises(ValueError, match="incomplete"):
        collect_model(config, factory=lambda _: reader)
    assert reader.closed


def test_model_library_api_is_offline_authenticated_and_revision_bound(local):
    client, ctl = local
    assert client.get("/api/model-library").status_code == 401
    headers = login(local, "viewer")
    result = client.get("/api/model-library?q=GoodWe").json()
    assert result["count"] == 2
    profile = get_profile("glance-solis-rhi-s6-hybrid")
    url = f"/api/model-library/{profile.id}"
    body = {"profile_digest": profile.profile_digest, "field_ids": ["powerkw"]}
    assert client.post(url + "/plan", json=body, headers=headers).json()["write_enabled"] is False
    result = client.post(
        url + "/decode",
        json=body
        | {
            "readings": [
                {"function": 4, "address": 33057, "value": 0},
                {"function": 4, "address": 33058, "value": 1000},
            ]
        },
        headers=headers,
    )
    assert result.json()["results"][0]["value"] == 1
    assert (
        client.post(url + "/plan", json=body | {"profile_digest": "0" * 64}, headers=headers).status_code
        == 409
    )
    assert not ctl.store.commands()


def test_configuration_validation_respects_agent_scope_and_revocation(local):
    client, ctl = local
    agent, headers = enroll(local)
    config = configured(agent_id=agent["id"]).model_dump(mode="json")
    url = "/api/local-collection/model/validate"
    assert client.post(url, json=config, headers=headers).json()["connection_tested"] is False
    other = login(local, "other")
    assert client.post(url, json=config, headers=other).status_code == 404
    headers = login(local)
    row = ctl.store.get("agent", agent["id"])
    row["enabled"] = False
    ctl.store.put("agent", row["id"], row)
    assert client.post(url, json=config, headers=headers).status_code == 409
    result = client.post(url, json=config | {"token": "SIM-SECRET-MUST-NOT-ECHO"}, headers=headers)
    assert result.status_code == 422 and "SIM-SECRET" not in result.text
