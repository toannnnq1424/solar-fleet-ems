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

    async def send(self, call, *, before_send):
        before_send()
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


@pytest.mark.parametrize("pause", ["auth", "budget"])
@pytest.mark.parametrize("change", ["revoke", "disable", "replace", "unchanged"])
async def test_deye_transport_wait_revalidates_before_http(
    store, device, operator, capability, pause, change,
):
    from test_deye import auth, make, ok

    entered, release = asyncio.Event(), asyncio.Event()
    writes = []

    async def handler(request):
        if result := auth(request):
            if pause == "auth":
                entered.set()
                await release.wait()
            return result
        if request.method == "POST":
            writes.append(request)
            return ok(orderId="SIM-ORDER", connectionStatus=1)
        return ok(status=666)

    engine, sim = setup(store, device, operator, capability)
    engine.timeout_seconds = 5
    transport = make(handler)
    transport.configuration = sim.configuration
    original_acquire = transport.budgets.acquire

    async def acquire(account, devices):
        if pause == "budget" and devices:
            entered.set()
            await release.wait()
        await original_acquire(account, devices)

    transport.budgets.acquire = acquire
    engine.adapter = lambda d: transport
    engine.compiler = lambda d, i, p: ([VendorCall(
        path="/v1.0/order/battery/parameter/update",
        body={"deviceSn": d.vendor_id, "paramterType": "MAX_CHARGE_CURRENT", "value": p["value"]},
    )], {"maxChargeCurrent": p["value"]})
    plan = await engine.preview(operator, device.id, capability.intent, {"value": 20})
    await engine.confirm(operator, plan.id, plan.digest, "sim-transport-barrier-key")
    try:
        await asyncio.wait_for(entered.wait(), 2)
        if change == "revoke":
            engine.principal = lambda id: None
        elif change == "disable":
            def disabled(d):
                raise SafetyError("integration_not_available")
            engine.adapter = disabled
        elif change == "replace":
            engine.adapter = lambda d: sim
        else:
            sim.value = 20
    finally:
        release.set()
        await settle(engine)
        await transport.close()
    assert len(writes) == (1 if change == "unchanged" else 0)
    row = store.command(plan.id)
    assert row["status"] == ("VERIFIED" if change == "unchanged" else "TIMEOUT")
    assert store.verify_audit()


@pytest.mark.parametrize("field", ["integration_id", "vendor_id", "logger_id", "metadata"])
async def test_preview_binding_cannot_be_replaced_before_execution(
    store, device, operator, capability, field,
):
    engine, sim = setup(store, device, operator, capability)
    plan = await engine.preview(operator, device.id, capability.intent, {"value": 20})
    setattr(device, field, {"route": "replacement"} if field == "metadata" else "sim-replacement")
    await engine.confirm(operator, plan.id, plan.digest, "sim-preview-binding-key")
    await settle(engine)
    assert sim.sent == 0
    assert store.command(plan.id)["error"] == "device_binding_changed"


async def test_preview_rejects_binding_drift_during_configuration(store, device, operator, capability):
    engine, sim = setup(store, device, operator, capability)
    original = sim.configuration

    async def changed(d):
        result = await original(d)
        device.integration_id = "sim-replacement"
        return result

    sim.configuration = changed
    with pytest.raises(SafetyError, match="device_binding_changed"):
        await engine.preview(operator, device.id, capability.intent, {"value": 20})
    assert sim.sent == 0


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


@pytest.mark.parametrize("change,error", [
    ("revoke", "operator_revoked"),
    ("role", "control_role_denied"),
    ("scope", "site_access_denied"),
    ("disable", "write_disabled_or_plan_expired"),
    ("binding", "device_binding_changed"),
])
async def test_configuration_await_rechecks_authority_before_send(
    store, device, operator, capability, change, error,
):
    engine, sim = setup(store, device, operator, capability)
    plan = await engine.preview(operator, device.id, capability.intent, {"value": 20})
    entered, release = asyncio.Event(), asyncio.Event()
    original = sim.configuration

    async def blocked_configuration(d):
        entered.set()
        await release.wait()
        return await original(d)

    sim.configuration = blocked_configuration
    await engine.confirm(operator, plan.id, plan.digest, "sim-await-authority-key")
    try:
        await asyncio.wait_for(entered.wait(), timeout=2)
        if change == "revoke":
            engine.principal = lambda id: None
        elif change == "role":
            operator.role = Role.VIEWER
        elif change == "scope":
            operator.site_ids = []
        elif change == "disable":
            engine.writes_enabled = False
        else:
            device.integration_id = "sim-replacement-account"
    finally:
        release.set()
        await settle(engine)
    row = store.command(plan.id)
    assert sim.sent == 0
    assert row["status"] == "FAILED"
    assert row["error"] == error
    assert store.verify_audit()


async def test_revocation_between_calls_stops_remaining_writes_and_quarantines(
    store, device, operator, capability,
):
    engine, sim = setup(store, device, operator, capability)
    engine.compiler = lambda d, i, p: (
        [VendorCall(path="/simulator", body=p), VendorCall(path="/simulator", body=p)],
        {"maxChargeCurrent": p["value"]},
    )
    plan = await engine.preview(operator, device.id, capability.intent, {"value": 20})
    original = sim.order

    async def revoke_after_order(id):
        result = await original(id)
        engine.principal = lambda id: None
        return result

    sim.order = revoke_after_order
    await engine.confirm(operator, plan.id, plan.digest, "sim-multicall-revoke-key")
    await settle(engine)
    row = store.command(plan.id)
    assert sim.sent == 1
    assert row["status"] == "TIMEOUT"
    assert row["error"] == "operator_revoked"
    with pytest.raises(SafetyError, match="device_has_unresolved_command"):
        engine.assert_clear(device.id)
    assert store.verify_audit()


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


def test_verify_semantic_readback_deye_fields():
    from solar_fleet.control import verify_semantic_readback

    # Deye camelCase maxSellPower (within tolerance 50W / 2%)
    assert verify_semantic_readback(
        readback={"maxSellPower": 5020},
        expected={"maxSellPower": 5000},
        intent="SET_EXPORT_LIMIT",
    )
    # Beyond tolerance
    assert not verify_semantic_readback(
        readback={"maxSellPower": 5200},
        expected={"maxSellPower": 5000},
        intent="SET_EXPORT_LIMIT",
    )

    # Deye maxChargeCurrent (tolerance 1.0A)
    assert verify_semantic_readback(
        readback={"maxChargeCurrent": 30.5},
        expected={"maxChargeCurrent": 30.0},
        intent="SET_CHARGE_CURRENT",
    )
    assert not verify_semantic_readback(
        readback={"maxChargeCurrent": 32.0},
        expected={"maxChargeCurrent": 30.0},
        intent="SET_CHARGE_CURRENT",
    )

    # Boolean gridChargeAction
    assert verify_semantic_readback(
        readback={"gridChargeAction": "1"},
        expected={"gridChargeAction": True},
        intent="SET_GRID_CHARGE",
    )
    assert not verify_semantic_readback(
        readback={"gridChargeAction": "0"},
        expected={"gridChargeAction": True},
        intent="SET_GRID_CHARGE",
    )


def test_verify_semantic_readback_tou_slots():
    from solar_fleet.control import verify_semantic_readback

    slots_expected = [
        {"time": "01:00", "target_soc": 80.0, "power_w": 3000, "grid_charge": True},
        {"time": "05:00", "target_soc": 20.0, "power_w": 5000, "grid_charge": False},
    ]
    # Match within tolerances (soc ±1%, power ±50W, normalized boolean)
    slots_readback_ok = [
        {"time": "01:00", "target_soc": 80.5, "power_w": 3040, "grid_charge": 1},
        {"time": "05:00", "target_soc": 19.5, "power_w": 4980, "grid_charge": "0"},
    ]
    assert verify_semantic_readback(
        readback={"timeUseSettingItems": slots_readback_ok},
        expected={"timeUseSettingItems": slots_expected},
        intent="SET_TOU",
    )

    # SOC mismatch > 1%
    slots_bad_soc = [
        {"time": "01:00", "target_soc": 83.0, "power_w": 3000, "grid_charge": True},
        {"time": "05:00", "target_soc": 20.0, "power_w": 5000, "grid_charge": False},
    ]
    assert not verify_semantic_readback(
        readback={"timeUseSettingItems": slots_bad_soc},
        expected={"timeUseSettingItems": slots_expected},
        intent="SET_TOU",
    )

    # Time mismatch
    slots_bad_time = [
        {"time": "01:30", "target_soc": 80.0, "power_w": 3000, "grid_charge": True},
        {"time": "05:00", "target_soc": 20.0, "power_w": 5000, "grid_charge": False},
    ]
    assert not verify_semantic_readback(
        readback={"timeUseSettingItems": slots_bad_time},
        expected={"timeUseSettingItems": slots_expected},
        intent="SET_TOU",
    )


def test_verify_semantic_readback_intent_mismatch():
    from solar_fleet.control import verify_semantic_readback

    assert not verify_semantic_readback(
        readback={"someOtherField": 10},
        expected={"someOtherField": 10},
        intent="SET_CHARGE_CURRENT",
    )
