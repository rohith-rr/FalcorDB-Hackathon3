"""Codex conversation extension contracts.

Source of truth: docs/design/contracts.md "Codex conversation extension"
and docs/design/codex_conversations.md.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.ids import parse_scoped_id


class CaptureCoverage(str, Enum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class ConversationRole(str, Enum):
    USER = "USER"
    ASSISTANT = "ASSISTANT"


class ConversationOrigin(str, Enum):
    HUMAN_INPUT = "HUMAN_INPUT"
    ASSISTANT_VISIBLE = "ASSISTANT_VISIBLE"
    INJECTED_CONTEXT = "INJECTED_CONTEXT"
    UNKNOWN = "UNKNOWN"


class ConversationRecord(BaseModel):
    id: str
    tenant_id: str
    source_instance: str
    native_session_id: Optional[str] = None
    source_key: str
    source_epoch: int = 1
    project_ids: List[str] = Field(default_factory=list)
    repository_ids: List[str] = Field(default_factory=list)
    title: Optional[str] = None
    source_started_at: Optional[datetime] = None
    source_updated_at: Optional[datetime] = None
    active_capture_id: Optional[str] = None
    mode: Literal["FIXTURE", "IMPORT"] = "FIXTURE"
    dialect: Optional[str] = None
    producer_version: Optional[str] = None
    parser_version: str
    redaction_version: str
    coverage: Dict[str, str] = Field(default_factory=dict)

    @field_validator("project_ids", "repository_ids")
    @classmethod
    def validate_bindings(cls, v: List[str]) -> List[str]:
        for value in v:
            parse_scoped_id(value, field="conversation binding")
        return v


class ConversationCaptureRef(BaseModel):
    capture_id: str
    conversation_id: str
    source_key: str
    source_epoch: int
    content_reference: str
    content_hash: str
    original_prefix_hash: str
    complete_line_offset: int
    last_source_ordinal: Optional[int] = None
    parser_version: str
    redaction_version: str
    observed_at: datetime
    coverage: CaptureCoverage
    pending_tail: bool = False
    limitations: List[str] = Field(default_factory=list)


class ConversationMessage(BaseModel):
    id: str
    conversation_id: str
    native_id: Optional[str] = None
    source_ordinal: Optional[int] = None
    byte_locator: Optional[str] = None
    sequence: int
    role: ConversationRole
    origin: ConversationOrigin
    speaker_principal: Optional[str] = None
    source_timestamp: Optional[datetime] = None
    content_hash: str
    content_reference: str
    capture_id: str
    lineage_of: Optional[str] = None  # compaction/fork source reference

    @field_validator("conversation_id")
    @classmethod
    def validate_conversation(cls, v: str) -> str:
        return parse_scoped_id(v, field="conversation_id")


class ConversationImportCursor(BaseModel):
    source_key: str
    source_epoch: int
    complete_line_offset: int
    prefix_hash: str
    last_ordinal: Optional[int] = None
    parser_version: str
    redaction_version: str
    capture_id: str
    published_bundle_id: Optional[str] = None


class MentionResolution(str, Enum):
    EXACT = "EXACT"
    AMBIGUOUS = "AMBIGUOUS"
    UNRESOLVED = "UNRESOLVED"
    SEMANTIC_CANDIDATE = "SEMANTIC_CANDIDATE"


class ConversationMention(BaseModel):
    message_id: str
    capture_id: str
    span: str
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    reference_value: str
    resolution: MentionResolution
    link_method: Literal["API", "MANIFEST", "PARSED_EXPLICIT_REFERENCE", "INFERRED"]
    authority: Literal["CONFIRMED", "CANDIDATE"]
    resolver_version: str

    @model_validator(mode="after")
    def endpoint_binding(self) -> "ConversationMention":
        if self.resolution is MentionResolution.EXACT:
            if self.target_id is None:
                raise ValueError("EXACT mentions require a resolved target_id")
            parse_scoped_id(self.target_id, field="mention target_id")
        if self.resolution is MentionResolution.SEMANTIC_CANDIDATE and self.authority != "CANDIDATE":
            raise ValueError("semantic candidates must remain CANDIDATE authority")
        return self


class DesignDecisionStatus(str, Enum):
    PROPOSED = "PROPOSED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    SUPERSEDED = "SUPERSEDED"


class DesignDecisionRecord(BaseModel):
    id: str
    revision_hash: str
    title: str
    rationale: Optional[str] = None
    alternatives: Optional[str] = None
    supporting_message_ids: List[str] = Field(default_factory=list)
    applicable_entity_ids: List[str] = Field(default_factory=list)
    status: DesignDecisionStatus = DesignDecisionStatus.PROPOSED
    extraction_model_version: Optional[str] = None
    extraction_prompt_version: Optional[str] = None
    review_manifest_version: Optional[str] = None
    reviewer: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    replacement_decision_id: Optional[str] = None

    @model_validator(mode="after")
    def status_authority(self) -> "DesignDecisionRecord":
        if self.status is not DesignDecisionStatus.PROPOSED:
            if not self.review_manifest_version or not self.reviewer:
                raise ValueError(
                    f"{self.status.value} status requires a review manifest version and reviewer"
                )
        if self.status is DesignDecisionStatus.SUPERSEDED and not self.replacement_decision_id:
            raise ValueError("SUPERSEDED decisions require a replacement revision")
        for entity_id in self.applicable_entity_ids:
            parse_scoped_id(entity_id, field="applicable_entity_ids member")
        return self


class ConversationCandidate(BaseModel):
    kind: Literal["CONVERSATION", "DESIGN_DECISION"]
    id: str
    label: str


class ConversationContext(BaseModel):
    """Retrieval context; candidate ambiguity has no selected rationale."""

    project_ids: List[str] = Field(default_factory=list)
    repository_ids: List[str] = Field(default_factory=list)
    selected_conversation_id: Optional[str] = None
    selected_decision_id: Optional[str] = None
    candidates: List[ConversationCandidate] = Field(default_factory=list)
    capture_references: List[ConversationCaptureRef] = Field(default_factory=list)
    message_excerpts: List[ConversationMessage] = Field(default_factory=list)
    decisions: List[DesignDecisionRecord] = Field(default_factory=list)
    mentions: List[ConversationMention] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)
    caps: Dict[str, int] = Field(
        default_factory=lambda: {"conversations": 20, "messages": 50, "decisions": 10}
    )
    overflow: bool = False
    limitations: List[str] = Field(default_factory=list)


class ContextBundle(BaseModel):
    """Request-local evidence bundle passed to the answer model."""

    request_id: str
    resolved_intent: Optional[str] = None
    resolved_entity_ids: List[str] = Field(default_factory=list)
    snapshots: List[Dict[str, str]] = Field(default_factory=list)
    graph_read_set: Dict[str, str] = Field(default_factory=dict)
    facts: List[AnswerFact] = Field(default_factory=list)  # type: ignore[name-defined]
    access_versions: Dict[str, int] = Field(default_factory=dict)
    branch_decision: Optional[dict] = None
    conversation_context: Optional[ConversationContext] = None
    branch_associations: List[dict] = Field(default_factory=list)
    task_summaries: List[dict] = Field(default_factory=list)
    dependency_summaries: List[dict] = Field(default_factory=list)
    document_sections: List[dict] = Field(default_factory=list)
    review_summaries: List[dict] = Field(default_factory=list)
    epic_counts: List[dict] = Field(default_factory=list)
    evidence_items: List[EvidenceItem] = Field(default_factory=list)  # type: ignore[name-defined]
    traversal_steps: List[dict] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
