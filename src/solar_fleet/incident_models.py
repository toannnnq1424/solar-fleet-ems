"""Incident, SLA and playbook inputs. Workflow state never substitutes equipment state."""

from datetime import UTC, datetime
from typing import Literal

from pydantic import Field, field_validator, model_validator

from .domain import Model

Severity = Literal["critical", "high", "medium", "low"]
Status = Literal["open", "acknowledged", "in_progress", "resolved", "closed"]
RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}
TRANSITIONS = {
    "open": {"open", "acknowledged", "in_progress"},
    "acknowledged": {"acknowledged", "in_progress", "resolved"},
    "in_progress": {"in_progress", "resolved"},
    "resolved": {"resolved", "closed", "open"},
    "closed": {"closed", "open"},
}


class AlarmObservation(Model):
    """Adapter-decoded event. False requires an explicit source recovery indication."""
    namespace: str = Field(pattern=r"^[a-z][a-z0-9_.-]{0,79}$")
    code: str = Field(min_length=1, max_length=120)
    source_event_id: str = Field(min_length=1, max_length=160)
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=4000)
    severity: Severity
    active: bool
    source_timestamp: datetime
    evidence_ids: list[str] = Field(min_length=1, max_length=20)

    @field_validator("source_timestamp")
    @classmethod
    def aware(cls, value):
        if value.tzinfo is None:
            raise ValueError("alarm_timestamp_requires_timezone")
        return value.astimezone(UTC)


class IncidentChange(Model):
    revision: int = Field(ge=1)
    status: Status
    assigned_to: str = Field(default="", max_length=100)
    note: str = Field(min_length=1, max_length=2000)


class IncidentNote(Model):
    revision: int = Field(ge=1)
    text: str = Field(min_length=1, max_length=4000)


class TriageForm(Model):
    revision: int = Field(ge=1)
    severity: Severity
    category: Literal["connectivity", "inverter", "battery", "meter", "grid", "yield", "other"]
    root_cause: str = Field(default="", max_length=2000)
    tags: list[str] = Field(default_factory=list, max_length=12)
    note: str = Field(min_length=1, max_length=2000)

    @field_validator("tags")
    @classmethod
    def tags_valid(cls, values):
        if any(not value.strip() or len(value) > 40 for value in values):
            raise ValueError("invalid_incident_tag")
        return sorted(set(value.strip() for value in values))


class SLATarget(Model):
    response_minutes: int = Field(ge=1, le=43200)
    resolution_minutes: int = Field(ge=1, le=129600)

    @model_validator(mode="after")
    def ordered(self):
        if self.resolution_minutes < self.response_minutes:
            raise ValueError("resolution_before_response_target")
        return self


class SLAPolicy(Model):
    site_id: str
    revision: int = Field(default=0, ge=0)
    name: str = Field(min_length=1, max_length=120)
    targets: dict[Severity, SLATarget]
    escalation_roles: list[Literal["Operator", "Installer", "Senior Engineer", "Administrator"]] = Field(min_length=1, max_length=4)

    @field_validator("targets")
    @classmethod
    def all_severities(cls, value):
        if set(value) != set(RANK):
            raise ValueError("sla_requires_all_severities")
        return value


class PlaybookStep(Model):
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,60}$")
    instruction_vi: str = Field(min_length=1, max_length=1500)
    instruction_en: str = Field(min_length=1, max_length=1500)
    requires_evidence: bool = True


class PlaybookForm(Model):
    site_id: str
    revision: int = Field(default=0, ge=0)
    name: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=2000)
    category: Literal["connectivity", "inverter", "battery", "meter", "grid", "yield", "other"] = "other"
    alarm_codes: list[str] = Field(default_factory=list, max_length=40)
    steps: list[PlaybookStep] = Field(min_length=1, max_length=30)
    enabled: bool = True

    @model_validator(mode="after")
    def distinct(self):
        if len({s.id for s in self.steps}) != len(self.steps):
            raise ValueError("duplicate_playbook_step")
        if any(not code.strip() or len(code) > 120 for code in self.alarm_codes):
            raise ValueError("invalid_playbook_alarm_code")
        return self


class PlaybookAttach(Model):
    revision: int = Field(ge=1)
    playbook_id: str


class PlaybookCheck(Model):
    revision: int = Field(ge=1)
    step_id: str
    outcome: Literal["pass", "fail", "not_applicable", "pending"]
    note: str = Field(default="", max_length=2000)


class IncidentWorkOrder(Model):
    revision: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=200)
    instructions: str = Field(min_length=1, max_length=4000)
    assigned_to: str = Field(default="", max_length=100)
    due_date: str | None = None

    @field_validator("due_date")
    @classmethod
    def valid_date(cls, value):
        if value is not None:
            datetime.strptime(value, "%Y-%m-%d")
        return value
