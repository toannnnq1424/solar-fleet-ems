"""Adversarial command tests against an explicit simulated inverter. No physical writes."""

import asyncio
from datetime import timedelta

import pytest

from solar_fleet.control import CommandEngine
from solar_fleet.domain import Ack, Configuration, OrderResult, Role, SafetyError, VendorCall, utcnow


class Simulator:
    def __init__(self):
        self.value = 10
        self.sent = 0
        self.stale = False
        self.cached = False
        self.online = True
        self.network_timeout = False
        self.pending = False
        self.mismatch = False
        self.fail_order = False
        self.concurrent = 0
        self.max_concurrent = 0

    async def configuration(self, device):
        return Configuration(
            values={"maxChargeCurrent": self.value},
            freshness_verified=not self.cached,
            device_timestamp=utcnow() - timedelta(seconds=60 if self.stale else 0),
        )

    async def send(self, call):
        self.sent += 1
        self.concurrent += 1
        self.max_concurrent = max(self.max_concurrent, self.concurrent)
        await asyncio.sleep(0.005)
        self.concurrent -= 1
        if self.network_timeout:
            raise SafetyError("network_timeout_outcome_unknown")
        if not self.mismatch:
            self.value = call.body["value"]
        return Ack(order_id=f"SIM-ORDER-{self.sent}", online=self.online)

    async def order(self, id):
        return OrderResult(
            state="FAILED" if self.fail_order else "PENDING" if self.pending else "SUCCEEDED",
            vendor_status="SIM",
        )


def setup(store, device, operator, capability):
    sim = Simulator()
    engine = CommandEngine(
        store,
        lambda id: device,
        lambda d: sim,
        lambda d, i: capability,
        lambda id: operator,
        writes_enabled=True,
        poll_seconds=0.001,
        timeout_seconds=0.25,
        compiler=lambda d, i, p: ([VendorCall(path="/simulator", body=p)], {"maxChargeCurrent": p["value"]}),
    )
    return engine, sim


async def settle(engine):
    await asyncio.gather(*list(engine.tasks))


@pytest.mark.asyncio
async def test_dry_run_never_sends_and_confirm_requires_fresh_readback(store, device, operator, capability):
    engine, sim = setup(store, device, operator, capability)
    plan = await engine.preview(operator, device.id, capability.intent, {"value": 20})
    assert sim.sent == 0 and plan.previous == {"maxChargeCurrent": 10}
    await engine.confirm(operator, plan.id, plan.digest, "sim-idempotency-key-001")
    await settle(engine)
    assert store.command(plan.id)["status"] == "VERIFIED"
    assert sim.sent == 1 and store.verify_audit()
    statuses = {row["body"].get("status") for row in store.audit_rows("control")}
    assert {
        "VALIDATING",
        "READY",
        "SENDING",
        "ACCEPTED",
        "WAITING_DEVICE",
        "VERIFYING",
        "VERIFIED",
    } <= statuses


@pytest.mark.asyncio
async def test_concurrent_confirm_is_idempotent_even_after_success(store, device, operator, capability):
    engine, sim = setup(store, device, operator, capability)
    plan = await engine.preview(operator, device.id, capability.intent, {"value": 20})
    results = await asyncio.gather(
        *(engine.confirm(operator, plan.id, plan.digest, "sim-unique-key-001") for _ in range(10))
    )
    await settle(engine)
    assert len({r["id"] for r in results}) == 1 and sim.sent == 1
    await engine.confirm(operator, plan.id, plan.digest, "sim-unique-key-001")
    assert sim.sent == 1
    with pytest.raises(SafetyError, match="idempotency_conflict"):
        await engine.confirm(operator, plan.id, plan.digest, "sim-different-key-001")


@pytest.mark.asyncio
@pytest.mark.parametrize("problem", ["network_timeout", "pending", "mismatch", "fail_order", "offline"])
async def test_uncertain_outcomes_quarantine_device_without_retry(
    store, device, operator, capability, problem
):
    engine, sim = setup(store, device, operator, capability)
    plan = await engine.preview(operator, device.id, capability.intent, {"value": 20})
    if problem == "offline":
        sim.online = False
    else:
        setattr(sim, problem, True)
    await engine.confirm(operator, plan.id, plan.digest, "sim-uncertain-key-001")
    await settle(engine)
    assert store.command(plan.id)["status"] == "TIMEOUT"
    assert sim.sent == 1
    with pytest.raises(SafetyError, match="device_has_unresolved_command"):
        await engine.preview(operator, device.id, capability.intent, {"value": 30})


@pytest.mark.asyncio
async def test_configuration_drift_fails_before_write(store, device, operator, capability):
    engine, sim = setup(store, device, operator, capability)
    plan = await engine.preview(operator, device.id, capability.intent, {"value": 20})
    sim.value = 11
    await engine.confirm(operator, plan.id, plan.digest, "sim-drift-key-001")
    await settle(engine)
    assert sim.sent == 0 and store.command(plan.id)["error"] == "configuration_changed_since_preview"


@pytest.mark.asyncio
async def test_two_plans_are_serialized_and_second_detects_drift(store, device, operator, capability):
    engine, sim = setup(store, device, operator, capability)
    a = await engine.preview(operator, device.id, capability.intent, {"value": 20})
    b = await engine.preview(operator, device.id, capability.intent, {"value": 30})
    await asyncio.gather(
        engine.confirm(operator, a.id, a.digest, "sim-plan-a-key-001"),
        engine.confirm(operator, b.id, b.digest, "sim-plan-b-key-001"),
    )
    await settle(engine)
    assert sim.sent == 1 and sim.max_concurrent == 1
    assert {store.command(p.id)["status"] for p in [a, b]} == {"VERIFIED", "FAILED"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mutate,expected",
    [
        ("read_only", "controller_is_read_only"),
        ("tampered", "plan_digest_mismatch"),
        ("expired", "plan_expired"),
        ("role", "control_role_denied"),
        ("site", "plan_access_denied"),
        ("firmware", "capability_or_parameter_unverified"),
        ("offline", "device_offline_or_stale"),
        ("capability", "capability_or_parameter_unverified"),
    ],
)
async def test_confirmation_revalidates_authority_and_profile(
    store, device, operator, capability, mutate, expected
):
    engine, sim = setup(store, device, operator, capability)
    plan = await engine.preview(operator, device.id, capability.intent, {"value": 20})
    digest = plan.digest
    if mutate == "read_only":
        engine.writes_enabled = False
    if mutate == "tampered":
        digest = "0" * 64
    if mutate == "expired":
        from solar_fleet.control import fingerprint

        plan.expires_at = utcnow() - timedelta(seconds=1)
        plan.digest = fingerprint(plan)
        digest = plan.digest
        store.db.execute("UPDATE plans SET body=? WHERE id=?", (plan.model_dump_json(), plan.id))
    if mutate == "role":
        operator.role = Role.VIEWER
    if mutate == "site":
        operator.site_ids = []
    if mutate == "firmware":
        device.identity = device.identity.model_copy(update={"firmware": "TEST-2"})
    if mutate == "offline":
        device.online = False
    if mutate == "capability":
        capability.state = "UNKNOWN"
    with pytest.raises(SafetyError, match=expected):
        await engine.confirm(operator, plan.id, digest, "sim-authority-key-001")
    assert sim.sent == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("problem", ["stale", "cached"])
async def test_preview_requires_fresh_device_configuration(store, device, operator, capability, problem):
    engine, sim = setup(store, device, operator, capability)
    setattr(sim, problem, True)
    with pytest.raises(SafetyError, match="device_readback"):
        await engine.preview(operator, device.id, capability.intent, {"value": 20})
    assert sim.sent == 0


@pytest.mark.asyncio
async def test_restart_does_not_resend(store, device, operator, capability):
    engine, sim = setup(store, device, operator, capability)
    plan = await engine.preview(operator, device.id, capability.intent, {"value": 20})
    store.claim_command(plan, "sim-recovery-key-001")
    store.recover_commands()
    assert store.command(plan.id)["status"] == "TIMEOUT" and sim.sent == 0
    with pytest.raises(SafetyError, match="device_has_unresolved_command"):
        await engine.preview(operator, device.id, capability.intent, {"value": 30})


@pytest.mark.asyncio
async def test_queued_operator_revocation_is_enforced(store, device, operator, capability):
    engine, sim = setup(store, device, operator, capability)
    plan = await engine.preview(operator, device.id, capability.intent, {"value": 20})
    await engine.locks[device.id].acquire()
    await engine.confirm(operator, plan.id, plan.digest, "sim-revoke-key-001")
    engine.principal = lambda id: None
    engine.locks[device.id].release()
    await settle(engine)
    assert sim.sent == 0 and store.command(plan.id)["error"] == "operator_revoked"


async def test_unrelated_configuration_change_also_invalidates_preview(store, device, operator, capability):
    engine, sim = setup(store, device, operator, capability)
    original = sim.configuration
    sim.solar_sell = "off"

    async def configuration(d):
        result = await original(d)
        result.values["solarSellAction"] = sim.solar_sell
        return result

    sim.configuration = configuration
    plan = await engine.preview(operator, device.id, capability.intent, {"value": 20})
    sim.solar_sell = "on"
    await engine.confirm(operator, plan.id, plan.digest, "sim-context-drift-key")
    await settle(engine)
    assert sim.sent == 0 and store.command(plan.id)["error"] == "configuration_changed_since_preview"


async def test_idempotency_survives_database_reopen(tmp_path, device, operator, capability):
    from solar_fleet.storage import Store

    path = tmp_path / "simulator.db"
    first = Store(path)
    engine, _ = setup(first, device, operator, capability)
    plan = await engine.preview(operator, device.id, capability.intent, {"value": 20})
    first.claim_command(plan, "sim-persistent-key-001")
    first.close()
    second = Store(path)
    second.recover_commands()
    restarted, sim = setup(second, device, operator, capability)
    row = await restarted.confirm(operator, plan.id, plan.digest, "sim-persistent-key-001")
    assert row["status"] == "TIMEOUT" and sim.sent == 0 and not restarted.tasks
    second.close()


@pytest.mark.parametrize("intent", ["SET_ZERO_EXPORT", "SET_RESERVE_SOC"])
def test_nearby_deye_controls_are_never_substituted(device, intent):
    from solar_fleet.adapters.deye_control import compile_deye

    with pytest.raises(SafetyError, match="intent_mapping_unknown"):
        compile_deye(device, intent, {"value": 20})
