"""Synthetic HTTP only: stop internal reads, not merely final disclosure."""

import asyncio

import pytest
from test_deye import auth, make, ok

from solar_fleet.domain import SafetyError, VendorCall
from solar_fleet.transport_guard import check_transport_guard, guarded_read


@pytest.mark.parametrize("operation", ["configuration", "order"])
@pytest.mark.parametrize("boundary", ["auth_lock", "auth_budget", "read_budget", "response", "unchanged"])
async def test_deye_internal_read_guard(device, operation, boundary):
    allowed = True
    seen = []

    def guard():
        if not allowed:
            raise SafetyError("synthetic_authority_revoked")

    def handler(request):
        nonlocal allowed
        seen.append(request.url.path)
        if result := auth(request):
            return result
        if boundary == "response":
            allowed = False
        return ok(status=666)

    adapter = make(handler)
    original = adapter.budgets.acquire
    acquired = 0

    async def acquire(*args):
        nonlocal acquired, allowed
        await original(*args)
        acquired += 1
        if (boundary == "auth_budget" and acquired == 1) or (
            boundary == "read_budget" and acquired == 2
        ):
            allowed = False

    adapter.budgets.acquire = acquire
    call = adapter.configuration if operation == "configuration" else adapter.order
    arg = device if operation == "configuration" else "SIM-ORDER"
    task = None
    try:
        if boundary == "auth_lock":
            await adapter.auth_lock.acquire()
            task = asyncio.create_task(guarded_read(guard, call, arg))
            await asyncio.sleep(0)
            allowed = False
            adapter.auth_lock.release()
        if boundary == "unchanged":
            await guarded_read(guard, call, arg)
        else:
            with pytest.raises(SafetyError, match="synthetic_authority_revoked"):
                if task is not None:
                    await task
                else:
                    await guarded_read(guard, call, arg)
        expected = {"auth_lock": 0, "auth_budget": 0, "read_budget": 1,
                    "response": 2, "unchanged": 4 if operation == "configuration" else 2}
        assert len(seen) == expected[boundary], seen
        check_transport_guard()  # Guard must not leak into the caller.
    finally:
        await adapter.close()


async def test_guard_task_isolation_and_cancellation():
    entered, release = asyncio.Event(), asyncio.Event()
    allowed = True

    def guard():
        if not allowed:
            raise SafetyError("revoked")

    async def wait():
        entered.set()
        await release.wait()

    task = asyncio.create_task(guarded_read(guard, wait))
    await entered.wait()
    allowed = False
    check_transport_guard()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    check_transport_guard()


async def test_nested_read_keeps_outer_guard_and_restores_context():
    allowed = True

    def outer():
        if not allowed:
            raise SafetyError("outer_revoked")

    async def inner():
        nonlocal allowed
        allowed = False
        check_transport_guard()

    async def nested():
        await guarded_read(lambda: None, inner)

    with pytest.raises(SafetyError, match="outer_revoked"):
        await guarded_read(outer, nested)
    check_transport_guard()


async def test_send_retains_ack_after_authority_changes_in_response():
    allowed = True

    def guard():
        if not allowed:
            raise SafetyError("revoked")

    def handler(request):
        nonlocal allowed
        if result := auth(request):
            return result
        allowed = False
        return ok(orderId="SIM-ORDER", connectionStatus=1)

    adapter = make(handler)
    try:
        ack = await adapter.send(VendorCall(
            path="/v1.0/order/sys/workMode/update",
            body={"deviceSn": "SIM", "workMode": "SELLING_FIRST"},
        ), before_send=guard)
        assert ack.order_id == "SIM-ORDER"
        with pytest.raises(SafetyError, match="revoked"):
            guard()
    finally:
        await adapter.close()