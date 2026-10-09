"""Fixture coherence tests (Phase 0 gate): no duplicate IDs, no dangling
references, symbolic effect/delivery SHAs only (never fake valid-looking
SHAs), scenario uniqueness."""

from __future__ import annotations

import json

import pytest

from tests.conftest import load_fixture


def collect_ids(node):
    ids = set()
    if isinstance(node, dict):
        for key in ("id", "delivery_id"):
            if isinstance(node.get(key), str) and key == "id":
                ids.add(node[key])
        for value in node.values():
            ids |= collect_ids(value)
    elif isinstance(node, list):
        for item in node:
            ids |= collect_ids(item)
    return ids


def collect_symbolic(node):
    found = set()
    if isinstance(node, dict):
        for value in node.values():
            found |= collect_symbolic(value)
    elif isinstance(node, list):
        for item in node:
            found |= collect_symbolic(item)
    elif isinstance(node, str) and node.startswith("SYMBOLIC:"):
        found.add(node)
    return found


def test_payments_fixture_ids_unique_and_scoped():
    tasks = load_fixture("payments", "tasks.json")
    ids = collect_ids(tasks)
    assert len(ids) == len(set(ids))
    for entity_id in ids:
        if entity_id and not entity_id.startswith("demo:jira:payments:edge"):
            assert entity_id.count(":") >= 3, f"unscoped fixture id {entity_id}"


def test_fixture_revision_references_are_symbolic():
    """Delivery/review revision references must be symbolic labels, not fake
    valid-looking SHAs; the builder resolves them to real SHAs."""
    links = load_fixture("payments", "links.json")
    for delivery in links["deliveries"]:
        assert delivery["implementation_revision"].startswith("SYMBOLIC:"), delivery
    pulls = load_fixture("payments", "pulls.json")
    for pr in pulls["pull_requests"]:
        assert pr["head_sha"].startswith("SYMBOLIC:")
        assert pr["base_sha"].startswith("SYMBOLIC:")
    reviews = load_fixture("payments", "reviews.json")
    for review in reviews["reviews"]:
        assert review["commit_sha"].startswith("SYMBOLIC:")


def test_scenario_manifest_unique_and_typed():
    scenarios = load_fixture("scenarios.json")
    ids = [s["id"] for s in scenarios["scenarios"]]
    assert len(ids) == len(set(ids)), "duplicate scenario IDs"
    for scenario in scenarios["scenarios"]:
        assert "expected" in scenario and "id" in scenario


def test_conversation_expected_manifest_covers_fixture_lines():
    expected = load_fixture("conversations", "expected.json")
    for source_key in ("local_session", "cli_events"):
        ordinals = [
            m["ordinal"] for m in expected["expected_messages"] if m["source_key"] == source_key
        ]
        assert ordinals == sorted(ordinals)
        assert ordinals == list(range(len(ordinals))), f"{source_key} ordinals must be dense"
    # local_session has 11 message records (m1..m11 including the null-id echo)
    local = [m for m in expected["expected_messages"] if m["source_key"] == "local_session"]
    assert len(local) == 11
    origins = {m["origin"] for m in local}
    assert {"HUMAN_INPUT", "ASSISTANT_VISIBLE", "INJECTED_CONTEXT", "UNKNOWN"} <= origins


def test_conversation_fixture_has_no_real_secrets():
    for name in ("local_session.jsonl", "cli_events.jsonl"):
        text = (load_fixture.__globals__["FIXTURES_ROOT"] / "conversations" / name).read_text(
            encoding="utf-8"
        )
        lowered = text.lower()
        for forbidden in ("api_key", "authorization:", "bearer ", "password"):
            assert forbidden not in lowered, f"{name} must not contain {forbidden!r}"


def test_review_manifest_supersession_is_acyclic():
    manifest = load_fixture("conversations", "review_manifest.json")
    by_key = {r["decision_key"]: r for r in manifest["reviews"]}
    for review in manifest["reviews"]:
        replacement = review.get("replacement_decision_key")
        if replacement:
            assert replacement in by_key, "dangling replacement reference"
            assert replacement != review["decision_key"], "self-supersession"


def test_tls_runbook_has_real_steps():
    docs = load_fixture("tls", "documents.json")
    runbook = docs["documents"][0]
    assert runbook["document_type"] == "ProcessDoc"
    anchors = [s["anchor"] for s in runbook["sections"]]
    assert anchors[:5] == ["prerequisites", "step-1-stage", "step-2-rotate", "step-3-verify", "step-4-monitor"]
    assert all(len(s["text"]) > 40 for s in runbook["sections"]), "runbook steps must have real content"


def test_tls_epic_has_five_leaves_four_done():
    tasks = load_fixture("tls", "tasks.json")
    epic = tasks["epics"][0]
    children = [r for r in tasks["hierarchy"] if r["start_id"] == epic["id"]]
    assert len(children) == 1  # epic -> TASK-404 -> five leaves
    task_404 = next(t for t in tasks["tasks"] if t["external_key"] == "TASK-404")
    leaves = [r["end_id"] for r in tasks["hierarchy"] if r["start_id"] == task_404["id"]]
    assert len(leaves) == 5
    by_id = {t["id"]: t for t in tasks["tasks"]}
    done = sum(1 for leaf in leaves if by_id[leaf]["status"] == "DONE")
    assert done == 4
