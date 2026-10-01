from __future__ import annotations

import asyncio
import hashlib
import hmac
import re
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Callable

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
from .transport_guard import guarded_read


@dataclass(frozen=True)
class ReadbackRule:
    abs_tolerance: float = 0.0
    rel_tolerance: float = 0.0
    is_boolean: bool = False
    is_tou: bool = False


DEFAULT_READBACK_RULES: dict[str, ReadbackRule] = {
    # Power and limits: +/- 50W or 2%
    "export_limit": ReadbackRule(abs_tolerance=50.0, rel_tolerance=0.02),
    "active_power_limit": ReadbackRule(abs_tolerance=50.0, rel_tolerance=0.02),
    "power_limit": ReadbackRule(abs_tolerance=50.0, rel_tolerance=0.02),
    "max_charge_power": ReadbackRule(abs_tolerance=50.0, rel_tolerance=0.02),
    "max_discharge_power": ReadbackRule(abs_tolerance=50.0, rel_tolerance=0.02),
    # Currents: +/- 1.0 A
    "max_charge_current": ReadbackRule(abs_tolerance=1.0),
    "max_discharge_current": ReadbackRule(abs_tolerance=1.0),
    "charge_current_limit": ReadbackRule(abs_tolerance=1.0),
    "discharge_current_limit": ReadbackRule(abs_tolerance=1.0),
    # SOC: +/- 1.0 %
    "target_soc": ReadbackRule(abs_tolerance=1.0),
    "min_soc": ReadbackRule(abs_tolerance=1.0),
    "max_soc": ReadbackRule(abs_tolerance=1.0),
    "battery_soc": ReadbackRule(abs_tolerance=1.0),
    # Boolean switches
    "grid_charge_enabled": ReadbackRule(is_boolean=True),
    "zero_export_enabled": ReadbackRule(is_boolean=True),
    "tou_enabled": ReadbackRule(is_boolean=True),
    # TOU schedules
    "tou_schedule": ReadbackRule(is_tou=True),
    "touList": ReadbackRule(is_tou=True),
}


def _normalize_bool(val: Any) -> bool | None:
    if isinstance(val, str):
        v = val.strip().lower()
        if v in ("true", "1", "on", "enable", "enabled"):
            return True
        if v in ("false", "0", "off", "disable", "disabled"):
            return False
    elif isinstance(val, (int, float)):
        if val == 1:
            return True
        if val == 0:
            return False
    elif isinstance(val, bool):
        return val
    return None


def verify_semantic_readback(
    readback: dict[str, Any],
    expected: dict[str, Any],
    intent: str,
) -> bool:
    """Semantic and tolerant readback comparison per intent and field."""
    for field, exp_val in expected.items():
        if field not in readback:
            return False
        rb_val = readback[field]
        if rb_val == exp_val:
            continue

        rule = DEFAULT_READBACK_RULES.get(field, ReadbackRule())
        if rule.is_boolean:
            rb_b = _normalize_bool(rb_val)
            exp_b = _normalize_bool(exp_val)
            if rb_b is not None and exp_b is not None and rb_b == exp_b:
                continue
            return False

        if isinstance(exp_val, (int, float)) and isinstance(rb_val, (int, float)):
            diff = abs(float(rb_val) - float(exp_val))
            allowed = max(rule.abs_tolerance, abs(float(exp_val)) * rule.rel_tolerance)
            if allowed <= 0.0:
                allowed = 1e-4
            if diff <= allowed:
                continue
            return False

        return False
    return True


def fingerprint(plan: CommandPlan) -> str:
    excluded = {"digest"}
    # Preserve the pre-scope digest of persisted kind-wide plans exactly.
    if plan.revision_scope == "kind_wide":
        excluded.add("revision_scope")
    return hashlib.sha256(encoded(plan.model_dump(mode="json", exclude=excluded)).encode()).hexdigest()


def command_selection(device: Device) -> dict[str, list[str]]:
    # Same primary binding identity used by discovery and vendor read contexts.
    binding_id = hashlib.sha256(
        f"{device.integration_id}|binding|{device.vendor_id}".encode()
    ).hexdigest()[:24]
    return {"integration": [device.integration_id], "device": [device.id],
            "site": [device.site_id], "binding": [binding_id]}


def binding_fingerprint(device: Device) -> str:
    binding = device.model_dump(mode="json", exclude={"last_seen", "online", "name"})
    return hashlib.sha256(encoded(binding).encode()).hexdigest()


def fresh(config: Configuration, *, after=None):
    timestamp = config.device_timestamp
    if not config.freshness_verified or timestamp is None or timestamp.tzinfo is None:
        raise SafetyError("device_readback_freshness_unverified")
    age = (utcnow() - timestamp).total_seconds()
    if age > 60 or age < -5 or (after is not None and timestamp < after):
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

    async def preview(
        self, user: Principal, device_id: str, intent: str, parameters: dict,
        *, revalidate: Callable[[], None] | None = None, persist: bool = True,
    ) -> CommandPlan:
        with self.store.transaction():
            device = self.device(device_id)
            capability = self.capability(device, intent).model_copy(deep=True)
            self.validate(user, device, capability, parameters)
            binding_digest = binding_fingerprint(device)
            integration = self.store.get("integration", device.integration_id)
            revisions = self.store.object_revisions(command_selection(device))
        adapter = self.adapter(device)

        def check_context():
            if self.store.object_revisions(revisions) != revisions:
                raise SafetyError("authority_revision_changed")
            if revalidate is not None:
                revalidate()
            current_user = self.principal(user.id)
            if current_user is None:
                raise SafetyError("operator_revoked")
            if current_user._authority_revision != user._authority_revision:
                raise SafetyError("operator_authority_changed")
            current = self.device(device_id)
            current_capability = self.capability(current, intent)
            self.validate(current_user, current, current_capability, parameters)
            if binding_fingerprint(current) != binding_digest:
                raise SafetyError("device_binding_changed")
            if current_capability != capability:
                raise SafetyError("capability_profile_changed")
            if self.store.get("integration", device.integration_id) != integration or (
                integration is not None and not integration.get("enabled")
            ):
                raise SafetyError("integration_context_changed")
            if self.adapter(current) is not adapter:
                raise SafetyError("control_adapter_changed")
            self.assert_clear(device.id)

        async with self.locks[device.id]:
            check_context()
            before = await guarded_read(check_context, adapter.configuration, device)
            check_context()
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
                binding_digest=binding_digest,
                authority_revisions=revisions,
                revision_scope="selected_objects_v1",
                operator_revision=user._authority_revision,
                created_at=now,
                expires_at=now + timedelta(seconds=120),
                risks=[
                    "Thay đổi hành vi năng lượng tại thiết bị.",
                    "Không tự rollback; cần đọc lại nếu lệnh hết hạn hoặc kết quả không rõ.",
                ],
            )
            plan.digest = fingerprint(plan)
            if persist:
                self.persist_preview(plan)
            return plan

    def persist_preview(self, plan: CommandPlan):
        """Persist a freshly revalidated preview; callers must not await before saving."""
        with self.store.transaction():
            self.store.save_plan(plan)
            self.store.audit(
                "control",
                {
                    "event": "dry_run",
                    "plan_id": plan.id,
                    "operator": plan.operator_id,
                    "device_id": plan.device_id,
                    "intent": plan.intent,
                    "before": plan.previous,
                    "expected": plan.expected,
                    "plan_digest": plan.digest,
                },
                plan.site_id,
            )

    async def confirm(
        self, user: Principal, plan_id: str, digest: str, key: str,
        *, execution_guard: Callable[[], None] | None = None,
    ) -> dict:
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
        # An authorized idempotent replay retrieves its existing outcome; it does
        # not authorize another send under a stale revision.
        if not existing:
            self.validate_revisions(plan)
        if not existing and utcnow() > plan.expires_at:
            raise SafetyError("plan_expired")
        try:
            row, created = self.store.claim_command(plan, key)
        except ValueError:
            raise SafetyError("idempotency_conflict") from None
        if created:
            self.transition(plan, CommandStatus.CREATED)
            task = asyncio.create_task(self._execute(plan, execution_guard=execution_guard))
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

    def validate_revisions(self, plan: CommandPlan):
        user = self.principal(plan.operator_id)
        if user is None:
            raise SafetyError("operator_revoked")
        if plan.operator_revision != user._authority_revision:
            raise SafetyError("operator_authority_changed")
        current = (
            self.store.object_revisions(plan.authority_revisions)
            if plan.revision_scope == "selected_objects_v1"
            else self.store.revisions(*plan.authority_revisions)
        )
        if not plan.authority_revisions or current != plan.authority_revisions:
            raise SafetyError("authority_revision_changed")

    def validate_before_send(self, plan: CommandPlan, snapshot: Device):
        # No await between this check and adapter.send: the single-controller
        # event loop must not reuse authority cached before network I/O.
        if not self.writes_enabled or utcnow() > plan.expires_at:
            raise SafetyError("write_disabled_or_plan_expired")
        self.validate_revisions(plan)
        user = self.principal(plan.operator_id)
        if user is None:
            raise SafetyError("operator_revoked")
        device = self.device(plan.device_id)
        capability = self.capability(device, plan.intent)
        self.validate(user, device, capability, plan.parameters)
        if not plan.binding_digest or binding_fingerprint(device) != plan.binding_digest:
            raise SafetyError("device_binding_changed")
        if capability != plan.capability or device.site_id != plan.site_id:
            raise SafetyError("device_or_capability_changed")
        # Heartbeats and display names may change during I/O; routing, identity
        # and metadata must still describe the device used for configuration.
        excluded = {"last_seen", "online", "name"}
        if device.model_dump(exclude=excluded) != snapshot.model_dump(exclude=excluded):
            raise SafetyError("device_binding_changed")
        calls, expected = self.compiler(device, plan.intent, plan.parameters)
        if calls != plan.calls or expected != plan.expected:
            raise SafetyError("compiled_plan_changed")
        self.assert_clear(plan.device_id, plan.id)

    async def _execute(self, plan: CommandPlan, *, execution_guard: Callable[[], None] | None = None):
        sent = False
        orders = []
        try:
            async with self.locks[plan.device_id]:
                if execution_guard is not None:
                    execution_guard()
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
                snapshot = device.model_copy(deep=True)
                adapter = self.adapter(device)

                def before_send():
                    if execution_guard is not None:
                        execution_guard()
                    self.validate_before_send(plan, snapshot)
                    if self.adapter(self.device(plan.device_id)) is not adapter:
                        raise SafetyError("control_adapter_changed")

                before = await guarded_read(before_send, adapter.configuration, device)
                before_send()
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
                        self.validate_before_send(plan, snapshot)
                        self.transition(plan, CommandStatus.SENDING, orders=orders)
                        sent = True
                        ack = await adapter.send(call, before_send=before_send)
                        orders.append(ack.order_id)
                        before_send()
                        self.transition(plan, CommandStatus.ACCEPTED, orders=orders)
                        if not ack.online:
                            raise SafetyError("vendor_accepted_while_device_offline")
                        self.transition(plan, CommandStatus.WAITING_DEVICE, orders=orders)
                        while True:
                            result = await guarded_read(before_send, adapter.order, ack.order_id)
                            before_send()
                            if result.state in ("FAILED", "CANCELLED"):
                                # A failed order does not prove that an earlier part of a multi-step write did not apply.
                                raise SafetyError("vendor_order_failed_reconcile_required")
                            if result.state == "SUCCEEDED":
                                break
                            await asyncio.sleep(self.poll_seconds)
                            before_send()
                    self.transition(plan, CommandStatus.VERIFYING, orders=orders)
                    after = await guarded_read(before_send, adapter.configuration, device)
                    before_send()
                    fresh(after, after=sent_at)
                    readback = {k: after.values.get(k) for k in plan.expected}
                    if not verify_semantic_readback(readback, plan.expected, plan.intent):
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
