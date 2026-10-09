"""Contract validation tests (Phase 0 gate): enums, unscoped IDs, malformed
fields, command gating and conversation authority."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.contracts.answer import Answer, AnswerFact, Statement
from app.contracts.conversations import ConversationMention, DesignDecisionRecord, MentionResolution
from app.contracts.decision import BranchDecision, BranchDecisionStatus, ProposedCommand
from app.contracts.import_state import EventBatchPolicy, ImportState, ImportStateCode
from app.contracts.query import ClarificationSelection, Intent, QueryRequest
from app.core.ids import UnscopedIdError, parse_scoped_id


def test_query_request_accepts_scoped_ids():
    request = QueryRequest(
        question="Which branch should I branch from?",
        task_id="demo:jira:payments:PAY-103",
        project_id="demo:jira:payments",
    )
    assert request.requested_intent is None
    assert Intent.BRANCH_BASE.value == "BRANCH_BASE"


def test_query_request_rejects_unscoped_ids():
    with pytest.raises(ValidationError, match="not a scoped application ID"):
        QueryRequest(question="q", task_id="PAY-103")


def test_clarification_selection_requires_exactly_one_field():
    with pytest.raises(ValidationError):
        ClarificationSelection(token="t")
    with pytest.raises(ValidationError):
        ClarificationSelection(token="t", selected_task_id="demo:jira:payments:PAY-101",
                               selected_ref="refs/heads/main")
    selection = ClarificationSelection(token="t", selected_ref="refs/heads/main")
    assert selection.selected_ref == "refs/heads/main"


def test_import_state_ready_requires_snapshot():
    with pytest.raises(ValidationError):
        ImportState(graph_name="g", projection_id="STRUCTURAL", state=ImportStateCode.READY)
    state = ImportState(graph_name="g", projection_id="STRUCTURAL",
                        state=ImportStateCode.READY, active_snapshot_id="snap-1")
    assert state.generation == 0


def test_import_state_log_position_is_incident_only():
    with pytest.raises(ValidationError):
        ImportState(graph_name="g", projection_id="STRUCTURAL",
                    state=ImportStateCode.UNINITIALIZED, published_log_position=5)


def test_event_batch_policy_window_bounds():
    with pytest.raises(ValidationError):
        EventBatchPolicy(window_seconds=10)  # allowed 15-30
    policy = EventBatchPolicy()
    assert policy.window_seconds == 30


def test_evidence_rejects_bad_content_hash():
    from app.contracts.evidence import EvidenceItem

    with pytest.raises(ValidationError):
        EvidenceItem(
            evidence_id="demo:ev:1",
            kind="TASK_FIELDS",
            entity_ids=["demo:jira:payments:PAY-101"],
            source_record_ref="fixture:1",
            observed_at="2026-10-10T00:00:00Z",
            content_hash="not-a-hash",
        )


def test_proposed_commands_reject_option_injection():
    with pytest.raises(ValidationError):
        ProposedCommand(argv=["git", "checkout", "-b", "evil --flag"])
    command = ProposedCommand(argv=["git", "checkout", "refs/heads/main"])
    assert command.argv[0] == "git"


def test_branch_decision_command_gating():
    base = dict(
        task_id="demo:jira:payments:PAY-103",
        repository_id="demo:github:payments:repository:901",
        stable_ref="refs/heads/main",
    )
    with pytest.raises(ValidationError):
        BranchDecision(
            status=BranchDecisionStatus.INSUFFICIENT_EVIDENCE,
            **base,
            proposed_commands=[{"argv": ["git", "checkout", "x"]}],
        )
    with pytest.raises(ValidationError):
        BranchDecision(status=BranchDecisionStatus.RECOMMENDED, **base)
    decision = BranchDecision(
        status=BranchDecisionStatus.RECOMMENDED,
        selected_ref="refs/heads/feature/backend-service",
        selected_head_sha="a" * 40,
        development_use_allowed=True,
        **base,
    )
    assert decision.deployment_readiness.value == "NOT_EVALUATED"


def test_answer_facts_citations_must_resolve():
    fact = AnswerFact(
        fact_id="fact-1",
        subject_ids=["demo:jira:payments:PAY-101"],
        predicate="status",
        value="IN_PROGRESS",
        qualifier="OBSERVED",
        observed_at="2026-10-10T00:00:00Z",
    )
    with pytest.raises(ValidationError):
        Answer(mode="LLM", summary="s", facts=[fact],
               statements=[Statement(text="t", fact_ids=["fact-missing"])])


def test_design_decision_authority():
    with pytest.raises(ValidationError):
        DesignDecisionRecord(
            id="demo:codex:decision:d1",
            revision_hash="0" * 64,
            title="t",
            status="ACCEPTED",
        )
    record = DesignDecisionRecord(
        id="demo:codex:decision:d1",
        revision_hash="0" * 64,
        title="t",
        status="ACCEPTED",
        review_manifest_version="1.0.0",
        reviewer="demo-operator",
    )
    assert record.status.value == "ACCEPTED"


def test_mention_semantic_candidates_stay_candidates():
    with pytest.raises(ValidationError):
        ConversationMention(
            message_id="demo:codex:local_session:msg:0",
            capture_id="capture-local_session-1",
            span="0-10",
            reference_value="PAY-101",
            resolution="SEMANTIC_CANDIDATE",
            link_method="INFERRED",
            authority="CONFIRMED",
            resolver_version="1.0.0",
        )
    mention = ConversationMention(
        message_id="demo:codex:local_session:msg:2",
        capture_id="capture-local_session-1",
        span="20-24",
        target_id="demo:jira:payments:PAY-101",
        reference_value="PAY-101",
        resolution="EXACT",
        link_method="PARSED_EXPLICIT_REFERENCE",
        authority="CONFIRMED",
        resolver_version="1.0.0",
    )
    assert mention.resolution is MentionResolution.EXACT


def test_parse_scoped_id():
    assert parse_scoped_id("demo:github:payments:901:pr:17") == "demo:github:payments:901:pr:17"
    with pytest.raises(UnscopedIdError):
        parse_scoped_id("main")
    with pytest.raises(UnscopedIdError):
        parse_scoped_id("demo::branch")
