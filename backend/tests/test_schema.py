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
