"""Schema validation tests (Phase 1): bundle coherence before mutation."""

from __future__ import annotations

import pytest

from app.fixtures.build import build_structural_bundle
from app.graph.schema import GraphValidationError, validate_bundle


def test_structural_bundle_validates():
    bundle = build_structural_bundle()
    validate_bundle(bundle)
    assert bundle["projection_id"] == "STRUCTURAL"
    labels = {n["label"] for n in bundle["nodes"]}
    assert {"Repository", "Branch", "Commit", "Task", "Epic", "PullRequest",
            "Review", "Document", "Epic"} <= labels


def test_bundle_rejects_duplicate_logical_ids():
    bundle = build_structural_bundle()
    bundle["nodes"].append(dict(bundle["nodes"][0]))
    with pytest.raises(GraphValidationError, match="duplicate logical node ID"):
        validate_bundle(bundle)


@pytest.mark.parametrize("node_id", ["demo:PAY-103", "demo::payments", "demo:jira:"])
def test_bundle_rejects_incomplete_scoped_node_ids(node_id):
    bundle = build_structural_bundle()
    bundle["nodes"][0]["id"] = node_id
    with pytest.raises(GraphValidationError, match="not a scoped application ID"):
        validate_bundle(bundle)


def test_bundle_rejects_dangling_edge_endpoints():
    bundle = build_structural_bundle()
    edge = dict(bundle["edges"][0])
    edge["id"] = edge["id"] + ":dangling"
    edge["end_id"] = "demo:jira:payments:MISSING"
    bundle["edges"].append(edge)
    with pytest.raises(GraphValidationError, match="outside the bundle"):
        validate_bundle(bundle)


def test_bundle_rejects_cross_tenant_nodes():
    bundle = build_structural_bundle()
    bundle["nodes"][0]["tenant_id"] = "other-tenant"
    with pytest.raises(GraphValidationError, match="[Cc]ross-tenant"):
        validate_bundle(bundle)


def test_bundle_rejects_two_active_heads():
    bundle = build_structural_bundle()
    feature = next(n for n in bundle["nodes"] if n["label"] == "Branch"
                   and n["ref"].endswith("feature/backend-service"))
    stable = next(n for n in bundle["nodes"] if n["label"] == "Branch"
                  and n["ref"].endswith("/main"))
    heads = [e for e in bundle["edges"] if e["type"] == "HEAD_AT"]
    # duplicate the stable head edge onto the feature branch (second active head)
    extra = dict(heads[0])
    extra["id"] = extra["id"] + ":dup"
    extra["start_id"] = feature["id"]
    extra["end_id"] = next(
        e["end_id"] for e in heads if e["start_id"] == stable["id"]
    )
    bundle["edges"].append(extra)
    with pytest.raises(GraphValidationError, match="more than one active HEAD_AT"):
        validate_bundle(bundle)


def test_bundle_rejects_invalid_dependency_kind():
    bundle = build_structural_bundle()
    dep = next(e for e in bundle["edges"] if e["type"] == "DEPENDS_ON")
    dep["dependency_kind"] = "MAYBE"
    with pytest.raises(GraphValidationError, match="DEPENDS_ON"):
        validate_bundle(bundle)


def test_bundle_rejects_wrong_canonical_node_owner():
    """A STRUCTURAL bundle carrying a Task marked INCIDENT passes node checks
    but must fail ownership validation before any publication."""
    from app.graph.projection_ownership import expected_owner

    bundle = build_structural_bundle()
    task = next(n for n in bundle["nodes"] if n["label"] == "Task")
    task["projection_owner"] = "INCIDENT"
    assert expected_owner("Task") == "STRUCTURAL"
    with pytest.raises(GraphValidationError, match="projection_owner 'INCIDENT', expected 'STRUCTURAL'"):
        validate_bundle(bundle)


def test_bundle_rejects_wrong_canonical_edge_owner():
    bundle = build_structural_bundle()
    edge = next(e for e in bundle["edges"] if e["type"] == "HAS_TASK")
    edge["projection_owner"] = "INCIDENT"
    with pytest.raises(GraphValidationError, match="projection_owner 'INCIDENT', expected 'STRUCTURAL'"):
        validate_bundle(bundle)


def test_bundle_rejects_cross_owner_records():
    """A record canonically owned by one projection cannot be published
    through the other projection's bundle (no cross-owner writes)."""
    bundle = build_structural_bundle()
    branch = next(n for n in bundle["nodes"] if n["label"] == "Branch")
    branch["projection_owner"] = "INCIDENT"
    with pytest.raises(
        GraphValidationError,
        match="(projection_owner 'INCIDENT', expected 'STRUCTURAL'|owned by 'INCIDENT')",
    ):
        validate_bundle(bundle)


def test_bundle_rejects_pr_with_two_active_targets():
    """Every TARGETS edge records its first active target so a later,
    different target for the same PR fails during preparation — before
    graph mutation can leave a projection DIRTY."""
    bundle = build_structural_bundle()
    targets = next(e for e in bundle["edges"] if e["type"] == "TARGETS")
    other = next(
        n for n in bundle["nodes"]
        if n["label"] == "Branch" and n["id"] != targets["end_id"]
    )
    second = dict(targets)
    second["id"] = targets["id"] + ":dup"
    second["end_id"] = other["id"]
    bundle["edges"].append(second)
    with pytest.raises(GraphValidationError, match="targets more than one active branch"):
        validate_bundle(bundle)
