"""Read-set fingerprint semantics (Phase 1): added prerequisites/members change
the fingerprint even when cited IDs are unchanged; unrelated metadata does
not."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.graph.queries import GraphQueryService, GraphSnapshotChanged
from app.graph.import_state import GraphRecoveryRequiredError, publish_gates
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


def test_reordered_result_rows_hash_identically():
    """Publication recreates relationships, so reordered result rows must not
    invalidate equivalent evidence (docs/design/graph_publication.md:48)."""
    a = GraphReadSet()
    b = GraphReadSet()
    rows = [
        ["t1", "e1", "CODE", "d1"],
        ["t1", "e2", "CODE", "d2"],
    ]
    reordered = list(reversed(rows))
    a.record("dependency_frontier", "1.0.0", {"frontier_ids": ["t1"]}, rows)
    b.record("dependency_frontier", "1.0.0", {"frontier_ids": ["t1"]}, reordered)
    assert a.fingerprint() == b.fingerprint()


def test_reordered_nested_membership_hash_identically():
    """Collected DISTINCT aggregates inside one row are unordered membership:
    their incidental order must not change the fingerprint."""
    a = GraphReadSet()
    b = GraphReadSet()
    row_a = [["e1", ["sha-b", "sha-a"], ["rv-2", "rv-1"]]]
    row_b = [["e1", ["sha-a", "sha-b"], ["rv-1", "rv-2"]]]
    a.record("revision_effects", "1.0.0", {"delivery_ids": ["d1"]}, row_a)
    b.record("revision_effects", "1.0.0", {"delivery_ids": ["d1"]}, row_b)
    assert a.fingerprint() == b.fingerprint()


def test_row_column_order_still_matters():
    """Canonicalization must not mask genuine changes: a changed column value
    (different evidence) still invalidates the read set."""
    a = GraphReadSet()
    b = GraphReadSet()
    a.record("dependency_frontier", "1.0.0", {"frontier_ids": ["t1"]}, [["t1", "e1", "CODE", "d1"]])
    # same columns, permuted as a nested list would be misleading; a REAL
    # change is a different target/edge, which keeps the fingerprint distinct
    b.record("dependency_frontier", "1.0.0", {"frontier_ids": ["t1"]}, [["t1", "e2", "CODE", "d1"]])
    assert a.fingerprint() != b.fingerprint()


def test_declared_coverage_recorded_not_assumed():
    """Bundle coverage is fingerprinted (READY is coherent publication, not
    source completeness). COMPLETE vs PARTIAL must differ."""
    a = GraphReadSet()
    b = GraphReadSet()
    rows = [["t1", "e1", "CODE", "d1"]]
    hash_a = a.record("dependency_frontier", "1.0.0", {"frontier_ids": ["t1"]}, rows,
                      coverage={"STRUCTURAL": {"payments": "COMPLETE"}})
    hash_b = b.record("dependency_frontier", "1.0.0", {"frontier_ids": ["t1"]}, rows,
                      coverage={"STRUCTURAL": {"payments": "PARTIAL"}})
    assert hash_a != hash_b, "coverage change must invalidate equivalence"
    hash_a2 = a.record("dependency_frontier", "1.0.0", {"frontier_ids": ["t1"]}, rows,
                       coverage={"STRUCTURAL": {"payments": "COMPLETE"}})
    assert hash_a2 == hash_a, "identical declared coverage hashes identically"


def test_transport_metadata_does_not_change_row_sort_order():
    """Transport fields are stripped BEFORE row sorting: changing only the
    generations of records a and b from (1, 2) to (3, 2) must not reverse
    their sorted order and fingerprint identical semantic content
    differently."""
    a = GraphReadSet()
    b = GraphReadSet()
    rows_a = [
        {"id": "a", "generation": 1},
        {"id": "b", "generation": 2},
    ]
    rows_b = [
        {"id": "a", "generation": 3},
        {"id": "b", "generation": 2},
    ]
    a.record("exact_task_lookup", "1.0.0", {"task_key": "PAY-101"}, rows_a)
    b.record("exact_task_lookup", "1.0.0", {"task_key": "PAY-101"}, rows_b)
    assert a.fingerprint() == b.fingerprint()

    # nested membership collected inside one row sorts transport-free too
    c = GraphReadSet()
    d = GraphReadSet()
    row_c = [["e1", [{"id": "a", "generation": 1}, {"id": "b", "generation": 2}]]]
    row_d = [["e1", [{"id": "a", "generation": 3}, {"id": "b", "generation": 2}]]]
    c.record("task_reviews", "1.0.0", {"task_id": "t1"}, row_c)
    d.record("task_reviews", "1.0.0", {"task_id": "t1"}, row_d)
    assert c.fingerprint() == d.fingerprint()


def test_transport_metadata_excluded_inside_records():
    """snapshot_id/ingested_at are materialization metadata even inside node
    properties: a republished snapshot must not invalidate equivalence."""
    a = GraphReadSet()
    b = GraphReadSet()
    rows_a = [{"id": "t1", "status": "IN_PROGRESS", "snapshot_id": "snap-1", "ingested_at": "t0"}]
    rows_b = [{"id": "t1", "status": "IN_PROGRESS", "snapshot_id": "snap-2", "ingested_at": "t9"}]
    a.record("exact_task_lookup", "1.0.0", {"task_key": "PAY-101"}, rows_a)
    b.record("exact_task_lookup", "1.0.0", {"task_key": "PAY-101"}, rows_b)
    assert a.fingerprint() == b.fingerprint()
    rows_c = [{"id": "t1", "status": "DONE", "snapshot_id": "snap-2", "ingested_at": "t9"}]
    c_changed = GraphReadSet()
    c_changed.record("exact_task_lookup", "1.0.0", {"task_key": "PAY-101"}, rows_c)
    assert a.fingerprint() != c_changed.fingerprint()


@pytest.fixture
def scoped_lookup(monkeypatch):
    state = {
        "state": "READY", "generation": 1, "active_snapshot_id": "snap-1",
        "coverage": {"payments": "COMPLETE", "tls": "COMPLETE", "conversations": "COMPLETE"},
    }
    monkeypatch.setattr("app.graph.queries.read_import_state", lambda *_: state)
    params = {"tenant_id": "demo", "project_id": "demo:jira:payments", "task_key": "PAY-103"}

    def make_service(rows):
        client = SimpleNamespace(
            settings=SimpleNamespace(falkordb_query_timeout_ms=1000),
            ro_query=lambda *_args, **_kwargs: rows,
        )
        return GraphQueryService(client)

    return make_service, state, params


@pytest.mark.parametrize("durable_state", ["READY", "DIRTY", "UNINITIALIZED"])
def test_exclusive_publication_rejects_reads_without_waiting(
    scoped_lookup, monkeypatch, durable_state,
):
    make_service, state, params = scoped_lookup
    state["state"] = durable_state
    state_reader = Mock(return_value=state)
    monkeypatch.setattr("app.graph.queries.read_import_state", state_reader)
    service = make_service([])
    service.client.ro_query = Mock(return_value=[])

    # Bound the wait and release the gate even if admission regresses to a
    # blocking call, so the test fails without leaving a parked worker.
    with ThreadPoolExecutor(max_workers=1) as pool:
        with publish_gates(["STRUCTURAL"]):
            result = pool.submit(service.execute, "exact_task_lookup", params)
            with pytest.raises(GraphRecoveryRequiredError, match="GRAPH_RECOVERY_REQUIRED"):
                result.result(timeout=1)
            state_reader.assert_not_called()
            service.client.ro_query.assert_not_called()
            assert service.read_set.entries == []

    state["state"] = "READY"
    assert service.execute("exact_task_lookup", params) == []


def test_incident_publication_preserves_structural_read_admission(scoped_lookup):
    make_service, _, params = scoped_lookup
    service = make_service([])
    with publish_gates(["INCIDENT"]):
        assert service.execute("exact_task_lookup", params) == []


@pytest.mark.parametrize("rows", [[], [["demo:jira:payments:PAY-103", "PAY-103", "TODO"]]])
@pytest.mark.parametrize("scope", ["tls", "conversations"])
def test_unrelated_coverage_change_preserves_scoped_lookup(scoped_lookup, rows, scope):
    make_service, state, params = scoped_lookup
    service = make_service(rows)
    assert service.execute("exact_task_lookup", params) == rows
    entry = service.read_set.entries[0]
    assert entry["coverage"] == {"STRUCTURAL": {"payments": "COMPLETE"}}

    state["coverage"][scope] = "PARTIAL"
    state["generation"] += 1
    state["active_snapshot_id"] = "snap-2"
    assert service.execute("exact_task_lookup", params) == rows
    assert service.read_set.entries == [entry, entry]
    assert service._tokens["STRUCTURAL"] == (2, "snap-2")


@pytest.mark.parametrize("rows", [[], [["demo:jira:payments:PAY-103", "PAY-103", "TODO"]]])
@pytest.mark.parametrize("coverage", ["PARTIAL", None])
def test_relevant_coverage_change_invalidates_scoped_lookup(scoped_lookup, rows, coverage):
    make_service, state, params = scoped_lookup
    service = make_service(rows)
    service.execute("exact_task_lookup", params)
    if coverage is None:
        del state["coverage"]["payments"]
    else:
        state["coverage"]["payments"] = coverage
    state["generation"] += 1
    with pytest.raises(GraphSnapshotChanged, match="GRAPH_SNAPSHOT_CHANGED"):
        service.execute("exact_task_lookup", params)
    assert len(service.read_set.entries) == 1


@pytest.mark.parametrize("coverage_key", ["payments", "demo:jira:payments"])
def test_missing_negative_lookup_coverage_remains_unknown(scoped_lookup, coverage_key):
    make_service, state, params = scoped_lookup
    state["coverage"].pop("payments")
    service = make_service([])
    service.execute("exact_task_lookup", params)
    assert service.read_set.entries[0]["coverage"] == {"STRUCTURAL": {"payments": "UNKNOWN"}}

    state["coverage"][coverage_key] = "COMPLETE"
    state["generation"] += 1
    with pytest.raises(GraphSnapshotChanged, match="GRAPH_SNAPSHOT_CHANGED"):
        service.execute("exact_task_lookup", params)


def test_cross_scope_traversal_retains_projection_coverage(scoped_lookup):
    make_service, state, _ = scoped_lookup
    service = make_service([])
    params = {"tenant_id": "demo", "frontier_ids": ["demo:jira:payments:PAY-103"]}
    service.execute("dependency_frontier", params)
    assert service.read_set.entries[0]["coverage"] == {"STRUCTURAL": state["coverage"]}
    state["coverage"]["tls"] = "PARTIAL"
    state["generation"] += 1
    with pytest.raises(GraphSnapshotChanged, match="GRAPH_SNAPSHOT_CHANGED"):
        service.execute("dependency_frontier", params)
