"""Snapshot, evidence and read-set contracts.

Source of truth: docs/design/contracts.md "Snapshot and evidence".
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field

from app.core.ids import SHA_RE, parse_scoped_id
from pydantic import field_validator


class ProjectionID(str, Enum):
    STRUCTURAL = "STRUCTURAL"
    INCIDENT = "INCIDENT"


class SnapshotMode(str, Enum):
    FIXTURE = "FIXTURE"
    IMPORT = "IMPORT"
    LIVE = "LIVE"


class SnapshotRef(BaseModel):
    model_config = ConfigDict(frozen=True)

    projection_id: ProjectionID
    snapshot_id: str
    generation: int = Field(ge=0)
    mode: SnapshotMode
    observed_at: datetime
    ingested_at: datetime
    scope: Dict[str, Any]
    complete: bool
    source_version: Optional[str] = None


class EvidenceKind(str, Enum):
    TASK_FIELDS = "TASK_FIELDS"
    CONFIRMED_RELATIONSHIP = "CONFIRMED_RELATIONSHIP"
    DOCUMENT_SECTION = "DOCUMENT_SECTION"
    PR_STATE = "PR_STATE"
    REVIEW_STATE = "REVIEW_STATE"
    BRANCH_HEAD = "BRANCH_HEAD"
    REVISION_EFFECT = "REVISION_EFFECT"
    GIT_COVERAGE = "GIT_COVERAGE"
    CONVERSATION_MESSAGE = "CONVERSATION_MESSAGE"
    DESIGN_DECISION_REVIEW = "DESIGN_DECISION_REVIEW"
    OTHER = "OTHER"


class EvidenceItem(BaseModel):
    evidence_id: str
    kind: EvidenceKind
    entity_ids: List[str]
    source_url: Optional[str] = None
    source_record_ref: str
    source_version: Optional[str] = None
    observed_at: datetime
    verified_at: Optional[datetime] = None
    projection_tokens: List[Tuple[ProjectionID, int, str]] = Field(default_factory=list)
    content_hash: str
    excerpt: Optional[str] = None
    value: Optional[Any] = None
    document_tab_id: Optional[str] = None
    section_anchor: Optional[str] = None

    @field_validator("entity_ids")
    @classmethod
    def validate_entities(cls, v: List[str]) -> List[str]:
        for entity_id in v:
            parse_scoped_id(entity_id, field="entity_ids member")
        return v

    @field_validator("content_hash")
    @classmethod
    def validate_hash(cls, v: str) -> str:
        if not v or len(v) != 64 or not all(c in "0123456789abcdef" for c in v):
            raise ValueError("content_hash must be a lowercase hex sha256 digest")
        return v


class TraversalStep(BaseModel):
    step_id: str
    template_id: str
    parameters: Dict[str, Any]
    node_ids: List[str]
    edge_ids: List[str]
    evidence_ids: List[str]
    selection_method: str
    duration_ms: float
    stop_reason: Optional[str] = None


class GitCoverage(BaseModel):
    """Bounded history/import coverage for commit ancestry reads."""

    repository_id: str
    history_complete: bool
    imported_limit: Optional[int] = None

    @field_validator("repository_id")
    @classmethod
    def validate_repo(cls, v: str) -> str:
        return parse_scoped_id(v, field="repository_id")


def is_full_sha(value: str) -> bool:
    return bool(SHA_RE.match(value))
