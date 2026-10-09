"""SRE incident extension contracts (Phase 0 foundation subset).

Source of truth: docs/design/contracts.md "Incident and exploration
extension" and SRE event handling. These are typed foundation contracts for
the incident demo; runtime behavior is implemented in the owning phases.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from app.core.ids import parse_scoped_id
from pydantic import field_validator


class IncidentState(str, Enum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    MITIGATED = "MITIGATED"
    MONITORING = "MONITORING"
    RESOLVED = "RESOLVED"


class InvestigationCheckStatus(str, Enum):
    KNOWN = "KNOWN"
    MISSING = "MISSING"
    STALE = "STALE"
    RESTRICTED = "RESTRICTED"
    UNAVAILABLE = "UNAVAILABLE"
    NOT_CHECKED = "NOT_CHECKED"


class InvestigationCheck(BaseModel):
    check_id: str
    required: bool
    status: InvestigationCheckStatus = InvestigationCheckStatus.NOT_CHECKED
    attempted_at: Optional[datetime] = None
    evidence_ids: List[str] = Field(default_factory=list)
    coverage: str = "UNKNOWN"
    failure: Optional[str] = None

    @field_validator("coverage")
    @classmethod
    def validate_coverage(cls, v: str) -> str:
        if v not in {"COMPLETE", "PARTIAL", "UNKNOWN"}:
            raise ValueError("coverage must be COMPLETE, PARTIAL or UNKNOWN")
        return v


class AlertSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class AlertInput(BaseModel):
    provider_id: str
    event_id: str
    deduplication_key: str
    occurred_at: datetime
    received_at: datetime
    severity: AlertSeverity
    raw_state: str
    service_id: Optional[str] = None
    service_instance_id: Optional[str] = None
    environment: Optional[str] = None
    region: Optional[str] = None
    release_id: Optional[str] = None
    payload_reference: Optional[str] = None

    @field_validator("service_id", "service_instance_id")
    @classmethod
    def validate_scoped(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return parse_scoped_id(v, field="alert scope")
        return v


class AlertReceipt(BaseModel):
    alert_id: str
    episode_id: str
    job_id: str
    duplicate: bool
    accepted_at: datetime


class PossibleExplanationState(str, Enum):
    POSSIBLE = "POSSIBLE"
    SUPPORTED = "SUPPORTED"
    REJECTED = "REJECTED"
    CONFIRMED_BY_RESPONDER = "CONFIRMED_BY_RESPONDER"


class PossibleExplanation(BaseModel):
    explanation_id: str
    statement: str
    related_change_ids: List[str] = Field(default_factory=list)
    related_service_ids: List[str] = Field(default_factory=list)
    supporting_evidence_ids: List[str] = Field(default_factory=list)
    conflicting_evidence_ids: List[str] = Field(default_factory=list)
    next_check: Optional[str] = None
    state: PossibleExplanationState = PossibleExplanationState.POSSIBLE


class ImpactState(str, Enum):
    OBSERVED = "OBSERVED"
    POSSIBLE = "POSSIBLE"
    NO_FAILURE_OBSERVED = "NO_FAILURE_OBSERVED"
    UNKNOWN = "UNKNOWN"


class ImpactAssessment(BaseModel):
    subject_id: str
    region: Optional[str] = None
    environment: Optional[str] = None
    measurement_window_start: Optional[datetime] = None
    measurement_window_end: Optional[datetime] = None
    state: ImpactState
    evidence_ids: List[str] = Field(default_factory=list)
    affected_operation: Optional[str] = None
    count_scope: Optional[str] = None
