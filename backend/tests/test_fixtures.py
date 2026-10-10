"""Fixture coherence tests (Phase 0 gate): no duplicate IDs, no dangling
references, symbolic effect/delivery SHAs only (never fake valid-looking
SHAs), scenario uniqueness."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

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


@pytest.fixture
def conversation_builder(tmp_path, monkeypatch, fixtures_root):
    from app.fixtures import build

    inputs = tmp_path / "fixtures"
    shutil.copytree(fixtures_root / "conversations", inputs / "conversations")
    monkeypatch.setattr(build, "FIXTURES_ROOT", inputs)
    monkeypatch.setattr(build, "WORKSPACE_ROOT", tmp_path / "workspace")
    return build


def test_cli_event_messages_match_normalization_expectations(conversation_builder):
    bundle = conversation_builder.build_conversation_bundle()
    messages = [n for n in bundle["nodes"] if n["label"] == "Message"
                and n["conversation_id"] == "demo:codex:cli_events"]
    expected = conversation_builder.load_fixture("conversations", "expected.json")
    assertions = [m for m in expected["expected_messages"] if m["source_key"] == "cli_events"]
    assert len(messages) == len(assertions) == 2
    assert [m["native_id"] for m in messages] == ["e2", "e4"]
    capture = json.loads(Path(messages[0]["content_reference"]).read_text(encoding="utf-8"))
    assert capture["coverage"] == "COMPLETE"
    assert len(capture["messages"]) == 2
    for message, captured, assertion in zip(messages, capture["messages"], assertions):
        assert message["source_ordinal"] == assertion["ordinal"]
        assert message["role"] == assertion["role"]
        assert message["origin"] == assertion["origin"]
        assert assertion["content_contains"] in captured["content"]
        assert message["source_timestamp"] == captured["source_timestamp"]
    source_records = [json.loads(line) for line in (
        conversation_builder.FIXTURES_ROOT / "conversations" / "cli_events.jsonl"
    ).read_text(encoding="utf-8").splitlines()]
    timestamps = {r.get("id"): r.get("timestamp") for r in source_records}
    assert all(m["source_timestamp"] == timestamps[m["native_id"]] for m in messages)
    assert len([e for e in bundle["edges"] if e["type"] == "HAS_MESSAGE"
                and e["start_id"] == "demo:codex:cli_events"]) == 2
    assert any(e["type"] == "NEXT_MESSAGE" and e["start_id"] == messages[0]["id"]
               and e["end_id"] == messages[1]["id"] for e in bundle["edges"])
    assert conversation_builder.build_conversation_bundle() == bundle


def test_cli_filters_nonvisible_events_and_preserves_repeated_utterances(conversation_builder):
    path = conversation_builder.FIXTURES_ROOT / "conversations" / "cli_events.jsonl"
    records = [
        {"type": "event", "event": "agent.message.completed", "role": "system", "content": "private"},
        {"type": "event", "event": "agent.message.completed", "role": "developer", "content": "private"},
        {"type": "event", "event": "item.completed", "role": "assistant", "content": "reasoning"},
        {"type": "event", "event": "turn.completed", "role": "assistant", "content": "echo", "echo_of": "e2"},
        {"type": "event", "event": "agent.message.completed", "role": "user", "id": "repeat-1", "content": "Repeated"},
        {"type": "event", "event": "agent.message.completed", "role": "user", "id": "repeat-2", "content": "Repeated"},
    ]
    with path.open("a", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record) + "\n")
    bundle = conversation_builder.build_conversation_bundle()
    messages = [n for n in bundle["nodes"] if n["label"] == "Message"
                and n["conversation_id"] == "demo:codex:cli_events"]
    assert [m["native_id"] for m in messages] == ["e2", "e4", "repeat-1", "repeat-2"]
    first, second = messages[-2:]
    assert first["id"] != second["id"]
    assert first["content_hash"] == second["content_hash"]
    assert first["source_timestamp"] is second["source_timestamp"] is None


def test_corrected_parser_preserves_previous_immutable_capture(conversation_builder):
    from app.storage.conversation_captures import ConversationCaptureStore

    store = ConversationCaptureStore(
        conversation_builder.WORKSPACE_ROOT / ".local/state/conversations",
        conversation_builder.WORKSPACE_ROOT / ".local/state/retained",
    )
    previous = store.write_capture(
        "capture-cli_events-1", "cli_events", 1, [], "1.0.0", "1.0.0", "COMPLETE", [""],
    )
    previous_path = Path(previous["content_reference"])
    previous_bytes = previous_path.read_bytes()
    bundle = conversation_builder.build_conversation_bundle()
    message = next(n for n in bundle["nodes"] if n["label"] == "Message"
                   and n["conversation_id"] == "demo:codex:cli_events")
    assert message["capture_id"] != previous["capture_id"]
    assert previous_path.read_bytes() == previous_bytes
    current = json.loads(Path(message["content_reference"]).read_text(encoding="utf-8"))
    assert current["parser_version"] == "1.0.1"
    assert len(current["messages"]) == 2


def test_corrected_seed_allocates_a_new_immutable_bundle(conversation_builder, tmp_path, fixtures_root):
    from app.graph.import_state import BundleStore
    from scripts import seed_graph

    for scope in ("payments", "tls"):
        shutil.copytree(fixtures_root / scope, conversation_builder.FIXTURES_ROOT / scope)
    store = BundleStore(tmp_path / "bundles")
    previous = {
        "projection_id": "STRUCTURAL", "bundle_id": "bundle-structural-snap-structural-003",
        "snapshot_id": "snap-structural-003", "nodes": [], "edges": [],
    }
    previous_hash = store.persist(previous)
    corrected = seed_graph.merge_structural_bundles()
    assert corrected["snapshot_id"] != previous["snapshot_id"]
    assert corrected["bundle_id"] != previous["bundle_id"]
    current_hash = store.persist(corrected)
    assert store.persist(corrected) == current_hash
    assert store.persist(previous) == previous_hash


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
