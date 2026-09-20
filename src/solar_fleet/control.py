from __future__ import annotations

import asyncio
import hashlib
import hmac
import re
import uuid
from collections import defaultdict
from datetime import timedelta
from typing import Callable

from .adapters.base import ControlAdapter
from .domain import (
    Capability,
    CommandPlan,
    CommandStatus,
    Configuration,
    Device,
    Principal,
    SafetyError,
    utcnow,
)
from .integration import no_mapping
from .security import authorize_control
from .storage import Store, encoded


def fingerprint(plan: CommandPlan) -> str:
    return hashlib.sha256(encoded(plan.model_dump(mode="json", exclude={"digest"})).encode()).hexdigest()


def fresh(config: Configuration, *, after=None):
    timestamp = config.device_timestamp
    if not config.freshness_verified or timestamp is None or timestamp.tzinfo is None:
        raise SafetyError("device_readback_freshness_unverified")
    age = (utcnow() - timestamp).total_seconds()
    if age > 30 or age < -5 or (after is not None and timestamp < after):
        raise SafetyError("device_readback_stale")


class CommandEngine:
    def __init__(
        self,
        store: Store,
        device: Callable[[str], Device],
        adapter: Callable[[Device], ControlAdapter],
        capability: Callable[[Device, str], Capability],
        principal: Callable[[str], Principal | None],
        *,
        writes_enabled=False,
        compiler=no_mapping,
        poll_seconds=2.0,
        timeout_seconds=90.0,
    ):
        self.store, self.device, self.adapter = store, device, adapter
        self.capability, self.principal = capability, principal
        self.writes_enabled = writes_enabled
        self.compiler = compiler
        self.poll_seconds, self.timeout_seconds = poll_seconds, timeout_seconds
        self.locks = defaultdict(asyncio.Lock)
        self.tasks = set()

    def validate(self, user: Principal, device: Device, capability: Capability, parameters: dict):
        authorize_control(user, device.site_id, capability)
        try:
            capability.validate_for(device, parameters)
        except ValueError:
            raise SafetyError("capability_or_parameter_unverified") from None
        if (
            not device.online
            or device.last_seen is None
            or (utcnow() - device.last_seen).total_seconds() > 120
        ):
            raise SafetyError("device_offline_or_stale")
        if (utcnow() - device.last_seen).total_seconds() < -5:
            raise SafetyError("device_clock_invalid")

    def assert_clear(self, device_id: str, excluding: str = ""):
        # TIMEOUT means physical outcome unknown; another write must wait for reconciliation.
        row = self.store.db.execute(
            "SELECT id FROM commands WHERE device_id=? AND id<>? AND status IN "
            "('SENDING','ACCEPTED','WAITING_DEVICE','VERIFYING','TIMEOUT') LIMIT 1",
            (device_id, excluding),
        ).fetchone()
        if row:
            raise SafetyError("device_has_unresolved_command")

    async def preview(self, user: Principal, device_id: str, intent: str, parameters: dict) -> CommandPlan:
        device = self.device(device_id)
        capability = self.capability(device, intent)
        self.validate(user, device, capability, parameters)
        async with self.locks[device.id]:
            self.assert_clear(device.id)
            before = await self.adapter(device).configuration(device)
            fresh(before)
            calls, expected = self.compiler(device, intent, parameters)
            if set(expected) != set(capability.readback_fields) or not set(expected) <= set(before.values):
                raise SafetyError("readback_fields_incomplete")
            # Other settings (work mode, solar sell, meter, TOU) can change an intent's safety context.
            previous = dict(before.values)
            now = utcnow()
            plan = CommandPlan(
                id=uuid.uuid4().hex,
                device_id=device.id,
                site_id=device.site_id,
                operator_id=user.id,
                intent=intent,
                parameters=parameters,
                previous=previous,
                expected=expected,
                calls=calls,
                capability=capability,
                created_at=now,
                expires_at=now + timedelta(seconds=120),
                risks=[
                    "Thay đổi hành vi năng lượng tại thiết bị.",
                    "Không tự rollback; cần đọc lại nếu lệnh hết hạn hoặc kết quả không rõ.",
                ],
            )
            plan.digest = fingerprint(plan)
            self.store.save_plan(plan)
            self.store.audit(
                "control",
                {
                    "event": "dry_run",
                    "plan_id": plan.id,
                    "operator": user.id,
                    "device_id": device.id,
                    "intent": intent,
                    "before": previous,
                    "expected": expected,
                    "plan_digest": plan.digest,
                },
                device.site_id,
            )
            return plan

    async def confirm(self, user: Principal, plan_id: str, digest: str, key: str) -> dict:
        if not self.writes_enabled:
            raise SafetyError("controller_is_read_only")
        plan = self.store.plan(plan_id)
        if plan is None or plan.operator_id != user.id or not user.can_access(plan.site_id):
            raise SafetyError("plan_access_denied")
        if not hmac.compare_digest(plan.digest, digest) or not hmac.compare_digest(
            plan.digest, fingerprint(plan)
        ):
            raise SafetyError("plan_digest_mismatch")
        if not re.fullmatch(r"[A-Za-z0-9_-]{16,128}", key):
            raise SafetyError("idempotency_key_invalid")
        device = self.device(plan.device_id)
        current = self.capability(device, plan.intent)
        self.validate(user, device, current, plan.parameters)
        if current != plan.capability:
            raise SafetyError("capability_profile_changed")
        existing = self.store.command(plan_id)
        if not existing and utcnow() > plan.expires_at:
            raise SafetyError("plan_expired")
        try:
            row, created = self.store.claim_command(plan, key)
        except ValueError:
            raise SafetyError("idempotency_conflict") from None
        if created:
            self.transition(plan, CommandStatus.CREATED)
            task = asyncio.create_task(self._execute(plan))
            self.tasks.add(task)
            task.add_done_callback(self.tasks.discard)
        return row

    def transition(self, plan: CommandPlan, status: CommandStatus, *, orders=None, error=None, readback=None):
        self.store.update_command(plan.id, status, order_ids=orders, error=error, readback=readback)
        self.store.audit(
            "control",
            {
                "event": "command_status",
                "command_id": plan.id,
                "operator": plan.operator_id,
                "device_id": plan.device_id,
                "intent": plan.intent,
                "status": status,
                "order_ids": orders,
                "error": error,
                "readback": readback,
            },
            plan.site_id,
        )

    async def _execute(self, plan: CommandPlan):
        sent = False
        orders = []
        try:
            async with self.locks[plan.device_id]:
                self.transition(plan, CommandStatus.VALIDATING)
                self.assert_clear(plan.device_id, plan.id)
                if not self.writes_enabled or utcnow() > plan.expires_at:
                    raise SafetyError("write_disabled_or_plan_expired")
                user = self.principal(
                    plan.operator_id
                )  # Re-check role/site revocation while waiting in the queue.
                if user is None:
                    raise SafetyError("operator_revoked")
                device = self.device(plan.device_id)
                capability = self.capability(device, plan.intent)
                self.validate(user, device, capability, plan.parameters)
                if capability != plan.capability or device.site_id != plan.site_id:
                    raise SafetyError("device_or_capability_changed")
                adapter = self.adapter(device)
                before = await adapter.configuration(device)
                fresh(before)
                if any(before.values.get(k) != v for k, v in plan.previous.items()):
                    raise SafetyError("configuration_changed_since_preview")
                calls, expected = self.compiler(device, plan.intent, plan.parameters)
                if calls != plan.calls or expected != plan.expected:
                    raise SafetyError("compiled_plan_changed")
                self.transition(plan, CommandStatus.READY)
                sent_at = utcnow()
                async with asyncio.timeout(self.timeout_seconds):
                    for call in calls:
                        self.transition(plan, CommandStatus.SENDING, orders=orders)
                        sent = True
                        ack = await adapter.send(call)
                        orders.append(ack.order_id)
                        self.transition(plan, CommandStatus.ACCEPTED, orders=orders)
                        if not ack.online:
                            raise SafetyError("vendor_accepted_while_device_offline")
                        self.transition(plan, CommandStatus.WAITING_DEVICE, orders=orders)
                        while True:
                            result = await adapter.order(ack.order_id)
                            if result.state in ("FAILED", "CANCELLED"):
                                # A failed order does not prove that an earlier part of a multi-step write did not apply.
                                raise SafetyError("vendor_order_failed_reconcile_required")
                            if result.state == "SUCCEEDED":
                                break
                            await asyncio.sleep(self.poll_seconds)
                    self.transition(plan, CommandStatus.VERIFYING, orders=orders)
                    after = await adapter.configuration(device)
                    fresh(after, after=sent_at)
                    readback = {k: after.values.get(k) for k in plan.expected}
                    if readback != plan.expected:
                        raise SafetyError("readback_mismatch_reconcile_required")
                    self.transition(plan, CommandStatus.VERIFIED, orders=orders, readback=readback)
        except asyncio.CancelledError:
            self.transition(
                plan,
                CommandStatus.TIMEOUT if sent else CommandStatus.CANCELLED,
                orders=orders,
                error="controller_stopped_outcome_unknown" if sent else "controller_stopped",
            )
            raise
        except (TimeoutError, SafetyError) as exc:
            self.transition(
                plan,
                CommandStatus.TIMEOUT if sent else CommandStatus.FAILED,
                orders=orders,
                error="command_timeout_outcome_unknown" if isinstance(exc, TimeoutError) else str(exc),
            )
        except Exception:
            # Do not log arbitrary exception strings: network libraries may include auth or raw bodies.
            self.transition(
                plan,
                CommandStatus.TIMEOUT if sent else CommandStatus.FAILED,
                orders=orders,
                error="internal_control_error",
            )

    async def close(self):
        tasks = list(self.tasks)
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
