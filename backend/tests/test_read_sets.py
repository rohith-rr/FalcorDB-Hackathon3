"""Read-set fingerprint semantics (Phase 1): added prerequisites/members change
the fingerprint even when cited IDs are unchanged; unrelated metadata does
not."""

from __future__ import annotations

from app.graph.read_sets import GraphReadSet, semantic_hash


def test_identical_rows_hash_identically():
    a = GraphReadSet()
    b = GraphReadSet()
    rows = [[1, "demo:jira:payments:PAY-101"], [2, "demo:jira:payments:PAY-103"]]
    a.record("dependency_frontier", "1.0.0", {"frontier_ids": ["x"]}, rows)
    b.record("dependency_frontier", "1.0.0", {"frontier_ids": ["x"]}, rows)
    assert a.fingerprint() == b.fingerprint()


def test_added_dependency_changes_fingerprint():
    a = GraphReadSet()
    b = GraphReadSet()
    base_rows = [["t1", "e1", "CODE", "d1"]]
    a.record("dependency_frontier", "1.0.0", {"frontier_ids": ["t1"]}, base_rows)
    b.record(
        "dependency_frontier", "1.0.0", {"frontier_ids": ["t1"]},
        base_rows + [["t1", "e2", "CODE", "d-new"]],
    )
    assert a.fingerprint() != b.fingerprint()


def test_transport_metadata_excluded():
    a = GraphReadSet()
    b = GraphReadSet()
    rows = [["t1", "e1", "d1"]]
    a.record("dependency_frontier", "1.0.0", {"frontier_ids": ["t1"], "generation": 1}, rows)
    b.record("dependency_frontier", "1.0.0", {"frontier_ids": ["t1"], "generation": 2}, rows)
    # generation is transport-only: it must not invalidate equivalence
    assert a.fingerprint() == b.fingerprint()


def test_empty_results_hash_with_scope():
    a = GraphReadSet()
    b = GraphReadSet()
    a.record("exact_task_lookup", "1.0.0", {"tenant_id": "demo", "task_key": "PAY-999"}, [])
    b.record("exact_task_lookup", "1.0.0", {"tenant_id": "demo", "task_key": "PAY-998"}, [])
    assert a.fingerprint() != b.fingerprint(), "negative-result scope must be part of the hash"
