"""Query request/response and clarification contracts.

Source of truth: docs/design/contracts.md "Request and resolution" and
"Clarification and continuation".
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.ids import parse_scoped_id


class Intent(str, Enum):
    BRANCH_BASE = "BRANCH_BASE"
    TASK_CONTEXT = "TASK_CONTEXT"
    BLOCKERS = "BLOCKERS"
    EPIC_PROGRESS = "EPIC_PROGRESS"
    CONVERSATION_CONTEXT = "CONVERSATION_CONTEXT"
    INCIDENT_BRIEF = "INCIDENT_BRIEF"
    INCIDENT_HISTORY = "INCIDENT_HISTORY"
    OTHER = "OTHER"


class Resolution(str, Enum):
    RESOLVED = "RESOLVED"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    NOT_FOUND = "NOT_FOUND"
    UNSUPPORTED = "UNSUPPORTED"


class Candidate(BaseModel):
    """Typed clarification candidate."""

    model_config = ConfigDict(frozen=True)

    id: str
    label: str


class ClarificationSelection(BaseModel):
    """Typed answer to a prior NEEDS_CLARIFICATION question.

    Exactly one selection field must be set, and it must match the token's
    kind (TASK -> selected_task_id, REPOSITORY -> selected_repository_id,
    BRANCH -> selected_ref).
    """

    token: str
    selected_task_id: Optional[str] = None
    selected_repository_id: Optional[str] = None
    selected_ref: Optional[str] = None

    @model_validator(mode="after")
    def exactly_one_selection(self) -> "ClarificationSelection":
        selected = [
            field
            for field in (self.selected_task_id, self.selected_repository_id, self.selected_ref)
            if field is not None
        ]
        if len(selected) != 1:
            raise ValueError(
                "clarification_answer requires exactly one selection field"
            )
        for value in selected:
            if not value or not value.strip():
                raise ValueError("selection values must be non-empty")
        return self


class QueryRequest(BaseModel):
    question: str = Field(min_length=1)
    project_id: Optional[str] = None
    repository_id: Optional[str] = None
    task_id: Optional[str] = None
    incident_id: Optional[str] = None
    service_id: Optional[str] = None
    service_instance_id: Optional[str] = None
    conversation_id: Optional[str] = None
    design_decision_id: Optional[str] = None
    requested_intent: Optional[Intent] = None
    clarification_answer: Optional[ClarificationSelection] = None

    @model_validator(mode="after")
    def validate_scope(self) -> "QueryRequest":
        for field in ("project_id", "repository_id", "task_id", "incident_id",
                      "service_id", "service_instance_id", "conversation_id",
                      "design_decision_id"):
            value = getattr(self, field)
            if value is not None:
                parse_scoped_id(value, field=field)
        return self


class Clarification(BaseModel):
    """Token-bearing typed clarification, exposed as QueryResponse.clarification."""

    kind: Literal["TASK", "REPOSITORY", "BRANCH"]
    candidates: List[Candidate]
    token: str
    expires_at: datetime


class QueryResponse(BaseModel):
    request_id: str
    resolution: Resolution
    clarification: Optional[Clarification] = None
    decision: Optional[dict] = None  # tagged BRANCH | INCIDENT in later phases
    branch_associations: List[dict] = Field(default_factory=list)
    answer: Optional[dict] = None
    citations: List[dict] = Field(default_factory=list)
    trace: Optional[dict] = None
    limitations: List[str] = Field(default_factory=list)
    timings: Optional[dict] = None
    conversation_context: Optional[dict] = None
    validated_against: Optional[dict] = None
    validated_at: Optional[datetime] = None

    @model_validator(mode="after")
    def clarification_shape(self) -> "QueryResponse":
        if self.resolution is Resolution.NEEDS_CLARIFICATION:
            if self.clarification is None:
                raise ValueError("NEEDS_CLARIFICATION responses require a clarification object")
            if self.decision is not None:
                raise ValueError("NEEDS_CLARIFICATION responses must not carry a decision")
        elif self.clarification is not None:
            raise ValueError("clarification is only present when resolution is NEEDS_CLARIFICATION")
        return self
