"""Branch decision contracts.

Source of truth: docs/design/contracts.md "Branch decision" and
graph_schema.md "Delivery mappings"/"Revision effects and candidate history".
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.ids import SHA_RE, parse_scoped_id
from pydantic import field_validator


class BranchDecisionStatus(str, Enum):
    RECOMMENDED = "RECOMMENDED"
    INTEGRATION_REQUIRED = "INTEGRATION_REQUIRED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    STALE_EVIDENCE = "STALE_EVIDENCE"
    POLICY_BLOCKED = "POLICY_BLOCKED"
    DEPENDENCY_CYCLE = "DEPENDENCY_CYCLE"


class ReviewReadiness(str, Enum):
    APPROVED = "APPROVED"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"
    PENDING = "PENDING"
    UNKNOWN = "UNKNOWN"


class DeploymentReadiness(str, Enum):
    NOT_EVALUATED = "NOT_EVALUATED"
    READY = "READY"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"


class DeliveryRole(str, Enum):
    IMPLEMENTATION = "IMPLEMENTATION"
    INTEGRATION = "INTEGRATION"


class CoverageState(str, Enum):
    INCLUDED = "INCLUDED"
    ABSENT = "ABSENT"
    UNKNOWN = "UNKNOWN"
    REVERTED = "REVERTED"


class DeliveryCoverage(BaseModel):
    delivery_id: str
    role: DeliveryRole
    implementation_revision: str  # full SHA or symbolic label pending resolution
    pr_id: Optional[str] = None
    equivalent_to_delivery_id: Optional[str] = None
    coverage: str  # COMPLETE | PARTIAL | UNKNOWN

    @field_validator("implementation_revision")
    @classmethod
    def validate_revision(cls, v: str) -> str:
        if not SHA_RE.match(v):
            raise ValueError("implementation_revision must be a full 40-char SHA")
        return v


class RevisionEffectKind(str, Enum):
    REVERT = "REVERT"
    REAPPLICATION = "REAPPLICATION"


class RevisionEffect(BaseModel):
    """Canonical revision-effect record (graph node + contract use the same
    record; provider-native shapes stay internal)."""

    id: str
    repository_id: str
    delivery_id: str
    effect_kind: RevisionEffectKind
    effect_commit_sha: str
    affected_revision_shas: List[str]
    coverage: str  # COMPLETE | PARTIAL | UNKNOWN
    authority: str = "CONFIRMED"
    mapping_version: str
    resolves_revert_ids: List[str] = Field(default_factory=list)
    tenant_id: str = "demo"
    observed_at: Optional[datetime] = None

    @field_validator("repository_id")
    @classmethod
    def validate_repo(cls, v: str) -> str:
        return parse_scoped_id(v, field="repository_id")

    @field_validator("effect_commit_sha")
    @classmethod
    def validate_sha(cls, v: str) -> str:
        if not SHA_RE.match(v):
            raise ValueError("effect_commit_sha must be a full 40-char SHA")
        return v

    @field_validator("affected_revision_shas")
    @classmethod
    def validate_affected(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("affected_revision_shas must be nonempty")
        for sha in v:
            if not SHA_RE.match(sha):
                raise ValueError(f"affected revision {sha!r} is not a full 40-char SHA")
        return v

    @field_validator("coverage")
    @classmethod
    def validate_coverage(cls, v: str) -> str:
        if v not in {"COMPLETE", "PARTIAL", "UNKNOWN"}:
            raise ValueError("coverage must be COMPLETE, PARTIAL or UNKNOWN")
        return v

    @model_validator(mode="after")
    def resolve_rules(self) -> "RevisionEffect":
        if self.effect_kind is RevisionEffectKind.REVERT and self.resolves_revert_ids:
            raise ValueError("revert records have no resolved IDs")
        if self.effect_kind is RevisionEffectKind.REAPPLICATION and not self.resolves_revert_ids:
            raise ValueError("reapplications must identify the reverts they address")
        return self


class EffectInclusion(str, Enum):
    INCLUDED = "INCLUDED"
    ABSENT = "ABSENT"
    UNKNOWN = "UNKNOWN"


class EffectCheck(BaseModel):
    effect_id: str
    effect_kind: RevisionEffectKind
    effect_commit_sha: str
    candidate_head_sha: str
    inclusion: EffectInclusion
    resolution_result: Optional[str] = None
    evidence_ids: List[str] = Field(default_factory=list)


class CandidateResult(BaseModel):
    repository_id: str
    ref: str
    head_sha: str
    exists: bool
    policy_eligible: bool
    per_delivery_coverage: Dict[str, CoverageState]
    verification_method: Optional[str] = None
    verification_source: Optional[str] = None
    verified_at: Optional[datetime] = None
    graph_generation: Optional[int] = None
    mapping_version: Optional[str] = None
    applicable_effect_ids: List[str] = Field(default_factory=list)
    resolved_revert_ids: List[str] = Field(default_factory=list)
    effect_checks: List[EffectCheck] = Field(default_factory=list)

    @field_validator("repository_id")
    @classmethod
    def validate_repo(cls, v: str) -> str:
        return parse_scoped_id(v, field="repository_id")

    @field_validator("head_sha")
    @classmethod
    def validate_head(cls, v: str) -> str:
        if not SHA_RE.match(v):
            raise ValueError("head_sha must be a full 40-char SHA")
        return v


class ProposedCommand(BaseModel):
    """Engine-generated argument array; never an LLM string."""

    argv: List[str]

    @field_validator("argv")
    @classmethod
    def validate_argv(cls, v: List[str]) -> List[str]:
        if not v or not v[0]:
            raise ValueError("proposed commands need a program")
        for arg in v[1:]:
            if arg.startswith("-"):
                raise ValueError(f"option-like argument rejected: {arg!r}")
        return v


class BranchDecision(BaseModel):
    status: BranchDecisionStatus
    task_id: str
    repository_id: str
    stable_ref: str
    required_task_ids: List[str] = Field(default_factory=list)
    required_delivery_ids: List[str] = Field(default_factory=list)
    candidate_results: List[CandidateResult] = Field(default_factory=list)
    selected_ref: Optional[str] = None
    selected_head_sha: Optional[str] = None
    development_use_allowed: bool = False
    review_readiness: ReviewReadiness = ReviewReadiness.UNKNOWN
    deployment_readiness: DeploymentReadiness = DeploymentReadiness.NOT_EVALUATED
    warnings: List[str] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)
    verified_at: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    proposed_commands: List[ProposedCommand] = Field(default_factory=list)

    @field_validator("task_id", "repository_id")
    @classmethod
    def validate_ids(cls, v: str) -> str:
        return parse_scoped_id(v, field="id")

    @model_validator(mode="after")
    def command_gate(self) -> "BranchDecision":
        if self.proposed_commands:
            if self.status is not BranchDecisionStatus.RECOMMENDED:
                raise ValueError("commands are only proposed for RECOMMENDED decisions")
            if not self.selected_ref or not self.selected_head_sha:
                raise ValueError("RECOMMENDED decisions with commands need selected_ref and SHA")
            if not self.development_use_allowed:
                raise ValueError("commands require development_use_allowed")
        if self.status is BranchDecisionStatus.RECOMMENDED:
            if self.selected_ref is None or self.selected_head_sha is None:
                raise ValueError("RECOMMENDED decisions must select ref and head SHA")
        return self
