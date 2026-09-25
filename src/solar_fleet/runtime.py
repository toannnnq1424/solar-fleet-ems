"""Persistent operational scheduling and reviewed, per-target command rollouts."""

from __future__ import annotations

import asyncio
import hashlib
import json
import uuid
from datetime import datetime, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import Depends, HTTPException
from pydantic import Field

from .domain import Model, Role, SafetyError, Sample, utcnow
from .rules import RuleAction, RuleForm, evaluate
from .schedule_planning import require_schedule_source
from .security import principal
from .storage import encoded


class MonitorForm(Model):
    enabled: bool
    hold_seconds: int = Field(default=60, ge=0, le=86400)
    cooldown_seconds: int = Field(default=900, ge=60, le=604800)


class RolloutForm(Model):
    name: str = Field(min_length=1, max_length=160)
    actions: list[RuleAction] = Field(min_length=1, max_length=20)
    note: str = Field(default="", max_length=2000)

    # A device gets a single action in a wave; dependent writes need separate fresh previews.


class RolloutConfirmation(Model):
    digest: str = Field(min_length=64, max_length=64)
    stage: Literal["canary", "remaining"] = "canary"


class Runtime:
    def __init__(self, controller):
        self.controller = controller
        self.store = controller.store
        self.task = None
        self.lock = asyncio.Lock()

    async def start(self):
        self.task = asyncio.create_task(self.loop())

    async def close(self):
        if self.task:
            self.task.cancel()
            await asyncio.gather(self.task, return_exceptions=True)

    async def loop(self):
        while True:
            try:
                await self.tick()
            except asyncio.CancelledError:
                raise
            except Exception:
                self.store.audit("system", {"event": "operations_tick_failed"})
            await asyncio.sleep(15)

    def notify(self, site_id, key, title, reference, *, severity="medium"):
        id = hashlib.sha256((site_id + ":" + key).encode()).hexdigest()[:32]
        if not self.store.get("notification", id):
            self.store.put(
                "notification",
                id,
                {
                    "id": id,
                    "site_id": site_id,
                    "title": title,
                    "reference": reference,
                    "severity": severity,
                    "created_at": utcnow().isoformat(),
                    "channel": "in_app",
                    "read_by": [],
                },
            )

    async def tick(self, now=None):
        now = now or utcnow()
        async with self.lock:
            self.maintenance(now)
            self.escalations(now)
            self.controller.incidents.escalate(now)
            self.monitors(now)
            self.rollouts()

    def maintenance(self, now):
        for plan in self.store.list("maintenance_plan"):
            if not plan["enabled"] or plan.get("archived"):
                continue
            user = principal(self.store, plan["updated_by"])
            if not user or user.role == Role.VIEWER or not user.can_access(plan["site_id"]):
                continue
            site = {
                **(self.store.get("site", plan["site_id"]) or {}),
                **(self.store.get("site_profile", plan["site_id"]) or {}),
            }
            try:
                today = now.astimezone(ZoneInfo(site.get("timezone") or "")).date()
            except (KeyError, ValueError):
                continue
            due = datetime.strptime(plan["next_due"], "%Y-%m-%d").date()
            if due > today:
                continue
            key = plan["id"] + ":" + str(due)
            id = hashlib.sha256(key.encode()).hexdigest()[:32]
            with self.store.transaction():
                if not self.store.get("work_order", id):
                    job = {
                        "id": id,
                        "site_id": plan["site_id"],
                        "title": plan["name"],
                        "description": plan["instructions"],
                        "device_id": plan["device_id"],
                        "severity": plan["severity"],
                        "status": "open",
                        "revision": 1,
                        "assigned_to": "",
                        "due_date": str(due),
                        "incident_id": None,
                        "created_at": now.isoformat(),
                        "updated_at": now.isoformat(),
                        "source": "MAINTENANCE_PLAN",
                        "timeline": [
                            {
                                "at": now.isoformat(),
                                "actor": "scheduler",
                                "status": "open",
                                "note": plan["instructions"],
                            }
                        ],
                    }
                    self.store.put("work_order", id, job)
                    self.store.audit("operations", {"event": "maintenance_due", "id": id}, plan["site_id"])
                    self.notify(
                        plan["site_id"],
                        key,
                        plan["name"],
                        {"kind": "work_order", "id": id},
                        severity=plan["severity"],
                    )
                # Coalesce missed periods into one overdue job, keeping the recurrence anchor.
                periods = (today - due).days // plan["interval_days"] + 1
                plan["next_due"] = str(due + timedelta(days=periods * plan["interval_days"]))
                plan["revision"] += 1
                self.store.put("maintenance_plan", plan["id"], plan)

    def escalations(self, now):
        ranks = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        for policy in self.store.list("notification_policy"):
            if policy.get("archived") or not policy["enabled"] or policy["channel"] != "in_app":
                continue
            owner = principal(self.store, policy["updated_by"])
            if not owner or owner.role == Role.VIEWER or not owner.can_access(policy["site_id"]):
                continue
            for incident in self.store.list("incident"):
                if incident["site_id"] != policy["site_id"] or incident["status"] in {"resolved", "closed"}:
                    continue
                if ranks[incident["severity"]] > ranks[policy["minimum_severity"]]:
                    continue
                age = (now - datetime.fromisoformat(incident["created_at"])).total_seconds()
                if age >= policy["escalation_minutes"] * 60:
                    self.notify(
                        incident["site_id"],
                        "escalation:" + incident["id"],
                        incident["title"],
                        {"kind": "incident", "id": incident["id"]},
                        severity=incident["severity"],
                    )

    def monitors(self, now):
        for monitor in self.store.list("rule_monitor"):
            if not monitor["enabled"]:
                continue
            owner = principal(self.store, monitor["owner_id"])
            row = self.store.get("rule", monitor["id"])
            if not owner or owner.role == Role.VIEWER or not owner.can_access(monitor["site_id"]) or not row:
                monitor.update(enabled=False, reason="OWNER_REVOKED", since=None)
                self.store.put("rule_monitor", monitor["id"], monitor)
                continue
            rule = RuleForm.model_validate({k: row[k] for k in RuleForm.model_fields})
            try:
                devices = [
                    self.controller.device(id)
                    for id in {i.device_id for i in [*rule.conditions, *rule.actions]}
                ]
                if any(d.site_id != rule.site_id for d in devices):
                    raise SafetyError("device_site_mismatch")
                samples = [
                    Sample.model_validate(s) for d in devices for s in self.controller.latest(d)["samples"]
                ]
                result = evaluate(rule, samples, now)
                state = result["condition_state"]
            except (SafetyError, ValueError):
                result, state = {"reason": "RULE_INPUT_INVALID"}, "UNKNOWN"
            last_checked = monitor.get("last_checked")
            if (
                not last_checked
                or not 0 <= (now - datetime.fromisoformat(last_checked)).total_seconds() <= 45
            ):
                # An observation gap is not proof of a continuously true condition.
                monitor["since"] = None
            monitor.update(last_checked=now.isoformat(), condition_state=state)
            if state != "TRUE":
                monitor["since"] = None
            else:
                monitor["since"] = monitor.get("since") or now.isoformat()
                held = (now - datetime.fromisoformat(monitor["since"])).total_seconds()
                cooled = (
                    not monitor.get("last_triggered")
                    or (now - datetime.fromisoformat(monitor["last_triggered"])).total_seconds()
                    >= monitor["cooldown_seconds"]
                )
                if held >= monitor["hold_seconds"] and cooled:
                    run_id = uuid.uuid4().hex
                    result = json.loads(json.dumps(result, default=str))
                    result.update(
                        id=run_id,
                        rule_id=rule.site_id,
                        site_id=rule.site_id,
                        created_by=owner.id,
                        mode="MONITOR",
                        rule_id_reference=monitor["id"],
                        dispatch_enabled=False,
                    )
                    result["rule_id"] = monitor["id"]
                    with self.store.transaction():
                        self.store.put("rule_run", run_id, result)
                        self.notify(
                            rule.site_id, "rule:" + run_id, rule.name, {"kind": "rule_run", "id": run_id}
                        )
                        self.store.audit(
                            "operations", {"event": "rule_monitor_matched", "id": run_id}, rule.site_id
                        )
                        monitor["last_triggered"] = now.isoformat()
            self.store.put("rule_monitor", monitor["id"], monitor)

    def rollouts(self):
        for row in self.store.list("rollout"):
            if row["state"] not in {"RUNNING", "CANARY_RUNNING"}:
                continue
            active = [t for t in row["targets"] if t.get("command_id")]
            for target in active:
                command = self.store.command(target["command_id"])
                target["status"] = command["status"] if command else "TIMEOUT"
            statuses = {t["status"] for t in active}
            if statuses & {"FAILED", "TIMEOUT", "UNSUPPORTED", "CANCELLED"}:
                row["state"] = "NEEDS_REVIEW"
            elif active and statuses == {"VERIFIED"}:
                row["state"] = "VERIFIED" if len(active) == len(row["targets"]) else "CANARY_VERIFIED"
            self.store.put("rollout", row["id"], row)


def install_runtime(app, controller, user):
    runtime = Runtime(controller)
    store = controller.store

    def operator(who=Depends(user)):
        if who.role == Role.VIEWER:
            raise HTTPException(403, "operator_required")
        return who

    def scoped(row, who):
        if not row:
            raise HTTPException(404)
        if not all(who.can_access(id) for id in (row.get("site_ids") or [row.get("site_id")])):
            raise HTTPException(403, "site_access_denied")

    @app.post("/api/rules/{id}/monitor")
    async def monitor(id: str, body: MonitorForm, who=Depends(operator)):
        rule = store.get("rule", id)
        scoped(rule, who)
        row = {
            "id": id,
            "site_id": rule["site_id"],
            **body.model_dump(),
            "owner_id": who.id,
            "since": None,
            "last_triggered": None,
            "mode": "NOTIFY_ONLY",
            "dispatch_enabled": False,
        }
        with store.transaction():
            store.put("rule_monitor", id, row)
            store.audit(
                "operations",
                {"event": "rule_monitor_changed", "id": id, "enabled": body.enabled, "operator": who.id},
                rule["site_id"],
            )
        return row

    @app.get("/api/schedules/{id}/timeline")
    async def timeline(id: str, day: str | None = None, who=Depends(user)):
        row = store.get("schedule", id)
        scoped(row, who)
        try:
            day_str = day or utcnow().strftime("%Y-%m-%d")
            local_day = datetime.strptime(day_str, "%Y-%m-%d").date()
            tz = ZoneInfo(row.get("timezone", "Asia/Ho_Chi_Minh"))
        except (ValueError, KeyError):
            raise SafetyError("invalid_schedule_date_or_timezone") from None
        output = []
        for slot in row["slots"]:
            if slot["day"] != local_day.weekday():
                continue
            points = []
            for value in (slot["start"], slot["end"]):
                base = datetime.combine(local_day, datetime.min.time())
                hours, minutes = map(int, value.split(":"))
                wall = base + timedelta(hours=hours, minutes=minutes)
                a, b = wall.replace(tzinfo=tz, fold=0), wall.replace(tzinfo=tz, fold=1)
                if a.utcoffset() != b.utcoffset():
                    raise SafetyError("dst_transition_requires_explicit_schedule_policy")
                points.append(a.isoformat())
            output.append({**slot, "start_at": points[0], "end_at": points[1]})
        return {"slots": output, "state": row["state"], "dispatch_enabled": False}

    @app.post("/api/rollouts", status_code=201)
    async def rollout(body: RolloutForm, who=Depends(operator)):
        if len({a.device_id for a in body.actions}) != len(body.actions):
            raise SafetyError("one_action_per_device_per_wave")
        targets = []
        site_ids = set()
        for action in body.actions:
            device = controller.device(action.device_id)
            if not who.can_access(device.site_id):
                raise HTTPException(403, "site_access_denied")
            site_ids.add(device.site_id)
            cap = controller.capability(device, action.intent)
            reason = None
            try:
                controller.engine.validate(who, device, cap, action.parameters)
            except SafetyError as exc:
                reason = str(exc)
            targets.append(
                {
                    **action.model_dump(),
                    "site_id": device.site_id,
                    "state": cap.state,
                    "status": "BLOCKED" if reason else "NOT_PREVIEWED",
                    "reason": reason,
                }
            )
        row = {
            "id": uuid.uuid4().hex,
            "site_id": sorted(site_ids)[0],
            "site_ids": sorted(site_ids),
            "name": body.name,
            "note": body.note,
            "targets": targets,
            "owner_id": who.id,
            "created_at": utcnow().isoformat(),
            "state": "DRAFT",
            "digest": None,
        }
        with store.transaction():
            store.put("rollout", row["id"], row)
            for id in site_ids:
                store.audit(
                    "operations", {"event": "rollout_created", "id": row["id"], "operator": who.id}, id
                )
        return row

    @app.post("/api/rollouts/{id}/preview")
    async def preview(id: str, who=Depends(operator)):
        async with runtime.lock:
            row = store.get("rollout", id)
            scoped(row, who)
            require_schedule_source(store, row)
            if row["owner_id"] != who.id or row["state"] not in {"DRAFT", "PREVIEWED", "CANARY_VERIFIED"}:
                raise SafetyError("rollout_state_or_owner_invalid")
            targets = []
            for target in row["targets"]:
                if target.get("command_id"):
                    targets.append(target)
                    continue
                target = {k: v for k, v in target.items() if k not in {"plan", "reason"}}
                try:
                    plan = await controller.engine.preview(
                        who, target["device_id"], target["intent"], target["parameters"]
                    )
                    target.update(plan=plan.model_dump(mode="json"), status="READY", reason=None)
                except SafetyError as exc:
                    target.update(status="BLOCKED", reason=str(exc))
                targets.append(target)
            row["targets"] = targets
            row["digest"] = hashlib.sha256(encoded(targets).encode()).hexdigest()
            row["state"] = "CANARY_VERIFIED" if any(t.get("command_id") for t in targets) else "PREVIEWED"
            store.put("rollout", id, row)
            return row

    @app.post("/api/rollouts/{id}/confirm")
    async def confirm(id: str, body: RolloutConfirmation, who=Depends(operator)):
        async with runtime.lock:
            row = store.get("rollout", id)
            scoped(row, who)
            require_schedule_source(store, row)
            if row["owner_id"] != who.id or row["digest"] != body.digest:
                raise SafetyError("rollout_digest_or_owner_mismatch")
            required = "PREVIEWED" if body.stage == "canary" else "CANARY_VERIFIED"
            if row["state"] != required:
                raise SafetyError("rollout_stage_invalid")
            # Re-check the canary from the authoritative journal, not its cached UI state.
            if body.stage == "remaining" and any(
                store.command(t["command_id"])["status"] != "VERIFIED"
                for t in row["targets"]
                if t.get("command_id")
            ):
                raise SafetyError("canary_not_verified")
            pending = [t for t in row["targets"] if not t.get("command_id")]
            if not pending or any(
                t["status"] != "READY" or datetime.fromisoformat(t["plan"]["expires_at"]) <= utcnow()
                for t in pending
            ):
                raise SafetyError("rollout_preview_required_for_all_targets")
            selected = pending[:1] if body.stage == "canary" else pending
            for target in selected:
                plan = target["plan"]
                try:
                    command = await controller.engine.confirm(
                        who, plan["id"], plan["digest"], "rollout_" + plan["id"]
                    )
                    target.update(command_id=command["id"], status=command["status"])
                except SafetyError as exc:
                    target.update(status="BLOCKED", reason=str(exc))
                    row["state"] = "NEEDS_REVIEW"
                    store.put("rollout", id, row)
                    return row
                row["state"] = "CANARY_RUNNING" if body.stage == "canary" else "RUNNING"
                store.put("rollout", id, row)
            return row

    @app.post("/api/rollouts/{id}/cancel")
    async def cancel(id: str, who=Depends(operator)):
        async with runtime.lock:
            row = store.get("rollout", id)
            scoped(row, who)
            if row["owner_id"] != who.id:
                raise HTTPException(403, "rollout_owner_required")
            if row["state"] == "VERIFIED":
                raise SafetyError("rollout_already_complete")
            row["state"] = "CANCELLED_UNSENT_ONLY"
            for target in row["targets"]:
                if not target.get("command_id"):
                    target["status"] = "CANCELLED"
            with store.transaction():
                store.put("rollout", id, row)
                store.audit(
                    "operations",
                    {"event": "rollout_unsent_cancelled", "id": id, "operator": who.id},
                    row["site_id"],
                )
            return row

    @app.post("/api/schedules/{id}/detect-conflicts")
    async def detect_conflicts(id: str, who=Depends(user)):
        sched = store.get("schedule", id)
        if sched is None:
            raise HTTPException(404, "schedule_not_found")
        scoped(sched, who)
        rules = [r for r in store.list("rule") if r.get("site_id") == sched["site_id"]]
        conflicts = detect_schedule_rule_conflicts(sched.get("slots", []), rules)
        return {"schedule_id": id, "conflicts": conflicts, "total_conflicts": len(conflicts)}

    return runtime


def detect_schedule_rule_conflicts(slots: list[dict], rules: list[dict]) -> list[dict]:
    conflicts = []
    for s_idx, slot in enumerate(slots):
        slot_mode = slot.get("mode")
        slot_day = slot.get("day")
        slot_start = slot.get("start", "")
        slot_end = slot.get("end", "")
        target_soc = slot.get("target_soc")

        for rule in rules:
            rule_id = rule.get("id") or rule.get("name", "rule")
            for action in rule.get("actions", []):
                intent = (
                    action.get("intent", "") if isinstance(action, dict) else getattr(action, "intent", "")
                )
                if (
                    slot_mode == "discharge"
                    and "charge" in intent.lower()
                    and "discharge" not in intent.lower()
                ):
                    conflicts.append(
                        {
                            "slot_index": s_idx,
                            "slot_day": slot_day,
                            "time_window": f"{slot_start}-{slot_end}",
                            "rule_id": rule_id,
                            "conflict_type": "MODE_CONTRADICTION",
                            "severity": "WARNING",
                            "description_vi": f"Xung đột chế độ: Khung giờ ({slot_start}-{slot_end}) yêu cầu xả pin, nhưng quy tắc '{rule.get('name', rule_id)}' lại kích hoạt nạp ({intent}).",
                            "description_en": f"Mode contradiction: Slot mandates discharge ({slot_start}-{slot_end}), but rule '{rule.get('name', rule_id)}' triggers charge ({intent}).",
                        }
                    )
                elif slot_mode == "charge" and target_soc is not None and target_soc < 30:
                    conflicts.append(
                        {
                            "slot_index": s_idx,
                            "slot_day": slot_day,
                            "time_window": f"{slot_start}-{slot_end}",
                            "rule_id": rule_id,
                            "conflict_type": "LOW_TARGET_SOC_WARNING",
                            "severity": "INFO",
                            "description_vi": f"Cảnh báo SOC: Khung sạc pin đặt mức đích thấp ({target_soc}%), có thể không tích đủ năng lượng cho giờ cao điểm.",
                            "description_en": f"SOC advisory: Charge slot has low target ({target_soc}%), which may deplete backup reserve.",
                        }
                    )
    return conflicts
