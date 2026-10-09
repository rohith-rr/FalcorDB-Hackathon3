"""Import state, batching and source-access contracts.

Source of truth: docs/design/contracts.md "Snapshot and evidence",
"Source access registry" and graph_publication.md.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ProjectionID(str, Enum):
    STRUCTURAL = "STRUCTURAL"
    INCIDENT = "INCIDENT"


class ImportStateCode(str, Enum):
    UNINITIALIZED = "UNINITIALIZED"
    DIRTY = "DIRTY"
    READY = "READY"


class ImportState(BaseModel):
    """Per-projection durable control metadata (outside domain traversal)."""

    graph_name: str
    projection_id: ProjectionID
    state: ImportStateCode = ImportStateCode.UNINITIALIZED
    generation: int = Field(default=0, ge=0)
    active_snapshot_id: Optional[str] = None
    pending_bundle_id: Optional[str] = None
    pending_bundle_hash: Optional[str] = None
    published_log_position: Optional[int] = None  # INCIDENT only
    last_published_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_failure: Optional[str] = None

    @model_validator(mode="after")
    def validate_shape(self) -> "ImportState":
        if self.state is ImportStateCode.READY:
            if self.active_snapshot_id is None:
                raise ValueError("READY import state requires active_snapshot_id")
        if self.published_log_position is not None and self.projection_id is not ProjectionID.INCIDENT:
            raise ValueError("published_log_position is INCIDENT-only")
        return self


class ImportOutcome(str, Enum):
    PREPARATION_FAILED = "PREPARATION_FAILED"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"
    PUBLISHED = "PUBLISHED"


class ImportReport(BaseModel):
    projection_id: ProjectionID
    bundle_id: str
    bundle_hash: str
    previous_snapshot_id: Optional[str] = None
    published_snapshot_id: Optional[str] = None
    generation: int
    outcome: ImportOutcome
    source_scopes: List[Dict[str, str]] = Field(default_factory=list)
    validation_conflicts: List[str] = Field(default_factory=list)
    started_at: datetime
    finished_at: Optional[datetime] = None
    failure: Optional[str] = None


class EventBatchPolicy(BaseModel):
    """Fixed 30-second incident batching policy (graph_publication.md)."""

    window_seconds: int = Field(default=30, ge=15, le=30)
    min_read_interval_seconds: int = Field(default=15, gt=0)
    max_batch_events: int = Field(default=100, gt=0)
    max_pending_events: int = Field(default=1000, gt=0)


class EventBatchRecord(BaseModel):
    batch_id: str
    tenant_id: str
    source_scopes: List[str]
    accepted_log_position: int
    consumed_log_position: int
    oldest_accepted_at: datetime
    deadline: datetime
    delta_hash: Optional[str] = None
    bundle_hash: Optional[str] = None
    outcome: str  # PUBLISHED | NOOP | FAILED
    previous_token: Optional[Dict[str, int]] = None
    published_token: Optional[Dict[str, int]] = None
    published_at: Optional[datetime] = None


class AccessStatus(str, Enum):
    ALLOWED = "ALLOWED"
    DENIED = "DENIED"
    UNAVAILABLE = "UNAVAILABLE"
    UNKNOWN = "UNKNOWN"


class SourceAccessRecord(BaseModel):
    """Retained source-access registry record (outside graph rebuild deletion)."""

    tenant_id: str
    principal_id: str
    provider: str
    credential_scope: str
    resource_id: Optional[str] = None  # None = provider/instance-level scope
    access_status: AccessStatus
    checked_at: datetime
    access_version: int = Field(ge=1)
    reason: Optional[str] = None
