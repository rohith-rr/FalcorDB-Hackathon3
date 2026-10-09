"""Graph loader integration tests (Phase 1 gate).

Runs against the pinned FalkorDB image, not an in-memory substitute:
durable publication, idempotent reimport, stale-edge retirement, recovery
blocking after injected interruption, and restart survival.
"""

from __future__ import annotations

import os
import subprocess
import time

import pytest

from tests.conftest import requires_db

pytestmark = [requires_db, pytest.mark.integration]


@pytest.fixture(scope="module")
def client():
    from app.config import get_settings
    from app.graph.client import connect_default

    settings = get_settings()
    c = connect_default(settings)
    yield c
    c.close()


@pytest.fixture(scope="module")
def seeded(client):
    from app.fixtures.build import load_git_manifest
    from app.graph.import_state import (
        BundleStore,
        PublicationGateProtocol,
        RecoveryRequired,
        read_import_state,
    )
    from scripts.seed_graph import merge_structural_bundles

    import pytest  # noqa: F401

    state = read_import_state(client, "STRUCTURAL")
    if state["state"] == "DIRTY":
        # Recover from the retained bundle before publishing (operator path);
        # a missing/invalid retained bundle requires a new validated full one.
        protocol = PublicationGateProtocol(client, BundleStore())
        try:
            protocol.recover("STRUCTURAL")
        except RecoveryRequired:
            from scripts.seed_graph import merge_structural_bundles  # noqa: F401

            protocol.recover_with_bundle("STRUCTURAL", merge_structural_bundles())
    bundle = merge_structural_bundles()
    protocol = PublicationGateProtocol(client, BundleStore())
    protocol.publish(bundle)
    state = read_import_state(client, "STRUCTURAL")
    assert state["state"] == "READY"
    return bundle


def _node_count(client) -> int:
    rows = client.ro_query("MATCH (n) WHERE n.graph_name IS NULL RETURN count(*)", {})
    return int(rows[0][0])


def _edge_count(client) -> int:
    rows = client.ro_query("MATCH ()-[r]->() WHERE r.graph_name IS NULL RETURN count(*)", {})
    return int(rows[0][0])


def test_initial_publication_is_readable(client, seeded):
    from app.graph.import_state import read_import_state

    state = read_import_state(client, "STRUCTURAL")
    assert state["state"] == "READY"
    assert state["active_snapshot_id"] == "snap-structural-001"
    assert _node_count(client) > 0


def test_reimport_is_idempotent(client, seeded):
    from app.graph.import_state import BundleStore, PublicationGateProtocol, read_import_state
    from scripts.seed_graph import merge_structural_bundles

    before_nodes, before_edges = _node_count(client), _edge_count(client)
    bundle = merge_structural_bundles()
    protocol = PublicationGateProtocol(client, BundleStore())
    protocol.publish(bundle)
    assert _node_count(client) == before_nodes
    assert _edge_count(client) == before_edges
    state = read_import_state(client, "STRUCTURAL")
    assert state["state"] == "READY"
    assert state["active_snapshot_id"] == "snap-structural-001"


def test_updating_a_head_retires_its_old_active_edge(client, seeded):
    """Updating a branch head tombstones the old active HEAD_AT edge."""
    from app.graph.import_state import read_import_state
    from scripts.seed_graph import merge_structural_bundles

    bundle = merge_structural_bundles()
    feature = next(n for n in bundle["nodes"] if n["label"] == "Branch"
                   and n["ref"].endswith("feature/backend-service"))
    new_sha = "f" * 40
    old_sha = feature["head_sha"]
    new_commit = {
        "label": "Commit",
        "id": f"demo:git:payments:commit:{new_sha}",
        "tenant_id": bundle["tenant_id"],
        "projection_owner": "STRUCTURAL",
        "source_system": "git-fixture",
        "source_record_ref": "test:new-head",
        "source_url": None,
        "source_updated_at": None,
        "observed_at": "2026-10-10T01:00:00Z",
        "ingested_at": "2026-10-10T01:00:00Z",
        "snapshot_id": "snap-structural-002",
        "schema_version": bundle["nodes"][0]["schema_version"],
        "is_deleted": False,
        "repository_id": feature["repository_id"],
        "sha": new_sha,
        "message": "moved head (test)",
        "committed_at": "2026-10-10T01:00:00Z",
        "history_complete": False,
    }
    branch = dict(feature)
    branch["head_sha"] = new_sha
    branch["snapshot_id"] = "snap-structural-002"
    for node in bundle["nodes"]:
        if node["id"] == feature["id"]:
            bundle["nodes"][bundle["nodes"].index(node)] = branch
    # The old head commit remains in the bundle: it is still referenced by the
    # delivery and review evidence (preserved structural endpoint).
    bundle["nodes"].append(new_commit)
    for edge in bundle["edges"]:
        if edge["type"] == "HEAD_AT" and edge["start_id"] == feature["id"]:
            edge["end_id"] = new_commit["id"]
            edge["id"] = edge["id"] + ":v2"
            edge["snapshot_id"] = "snap-structural-002"
        elif edge["type"] == "PARENT":
            edge["snapshot_id"] = "snap-structural-002"
    bundle["snapshot_id"] = "snap-structural-002"
    bundle["bundle_id"] = "bundle-structural-snap-structural-002"

    from app.graph.import_state import BundleStore, PublicationGateProtocol

    protocol = PublicationGateProtocol(client, BundleStore())
    protocol.publish(bundle)
    rows = client.ro_query(
        """
        MATCH (b:Branch {ref: 'refs/heads/feature/backend-service'})-[r:HEAD_AT]->(c)
        RETURN c.sha, r.is_deleted
        """,
        {},
    )
    heads = [(row[0], row[1]) for row in rows]
    assert (new_sha, False) in heads or (new_sha, True) in [h for h in heads]
    active = [h for h in heads if h[1] is False]
    assert len(active) == 1 and active[0][0] == new_sha, "exactly one active HEAD_AT after update"

    # restore the fixture state for later tests
    clean = merge_structural_bundles()
    PublicationGateProtocol(client, BundleStore()).publish(clean)
    assert read_import_state(client, "STRUCTURAL")["active_snapshot_id"] == "snap-structural-001"


def test_tenant_filter_returns_no_foreign_nodes(client, seeded):
    rows = client.ro_query(
        "MATCH (t:Task) WHERE t.tenant_id = 'foreign' RETURN count(*)", {}
    )
    assert int(rows[0][0]) == 0
    rows = client.ro_query(
        "MATCH (t:Task) WHERE t.tenant_id = 'demo' RETURN count(*)", {}
    )
    assert int(rows[0][0]) >= 4


def test_read_only_interface_rejects_mutations(client, seeded):
    from app.graph.client import GraphReadError

    with pytest.raises(GraphReadError):
        client.ro_query("CREATE (n:ShouldNotAppear {id: 'x'})", {})


def test_exact_lookup_and_dependency_frontier(client, seeded):
    from app.graph.queries import GraphQueryService

    service = GraphQueryService(client)
    rows = service.execute(
        "exact_task_lookup",
        {"tenant_id": "demo", "project_id": "demo:jira:payments", "task_key": "PAY-103"},
    )
    assert len(rows) == 1
    assert rows[0][0] == "demo:jira:payments:PAY-103"
    assert rows[0][1] == "PAY-103"

    frontier = service.execute(
        "dependency_frontier",
        {"tenant_id": "demo", "frontier_ids": ["demo:jira:payments:PAY-103"]},
    )
    assert any(row[0] == "demo:jira:payments:PAY-103" for row in frontier)
    # explicit edge properties, not just destination names
    row = next(r for r in frontier if r[0] == "demo:jira:payments:PAY-103")
    assert row[2] == "CODE"
    assert row[1].startswith("demo:jira:payments:edge:depends_on")


def test_document_retrieval_retains_version(client, seeded):
    from app.graph.queries import GraphQueryService

    service = GraphQueryService(client)
    rows = service.execute(
        "current_documents",
        {"tenant_id": "demo", "task_id": "demo:jira:tls:TASK-404"},
    )
    assert rows, "TLS runbook must be linked to TASK-404"
    runbook = next(r for r in rows if "runbook" in str(r[1]))
    assert runbook[3] == "3"  # version retained
    assert runbook[4] and len(runbook[4]) == 64  # content hash retained
    assert runbook[6] == "CURRENT"


def test_review_retrieval_retains_reviewed_sha(client, seeded):
    from app.graph.queries import GraphQueryService

    service = GraphQueryService(client)
    rows = service.execute(
        "task_reviews",
        {"tenant_id": "demo", "task_id": "demo:jira:payments:PAY-101"},
    )
    assert rows
    review = rows[0]
    assert review[2] == "CHANGES_REQUESTED"
    assert len(review[4]) == 40  # reviewed SHA retained


def test_candidate_heads(client, seeded):
    from app.graph.queries import GraphQueryService

    service = GraphQueryService(client)
    rows = service.execute(
        "candidate_heads",
        {"tenant_id": "demo", "repository_id": "demo:github:payments:repository:901"},
    )
    refs = {row[1] for row in rows}
    assert "refs/heads/main" in refs
    assert "refs/heads/feature/backend-service" in refs


def test_dirty_projection_blocks_graph_reads(client):
    """DIRTY required projection fails graph reads with recovery-required."""
    from app.graph.client import connect_default
    from app.graph.import_state import (
        BundleStore,
        GraphRecoveryRequiredError,
        PublicationGateProtocol,
        read_import_state,
    )
    from app.graph.queries import GraphQueryService
    from scripts.seed_graph import merge_structural_bundles

    protocol = PublicationGateProtocol(
        client, BundleStore(), fail_after="after_dirty",
    )
    bundle = merge_structural_bundles()
    with pytest.raises(RuntimeError, match="after DIRTY"):
        protocol.publish(bundle)
    state = read_import_state(client, "STRUCTURAL")
    assert state["state"] == "DIRTY", "interrupted import must leave durable DIRTY state"

    service = GraphQueryService(client)
    from app.graph.import_state import GraphRecoveryRequiredError

    with pytest.raises(GraphRecoveryRequiredError):
        service.execute(
            "exact_task_lookup",
            {"tenant_id": "demo", "project_id": "demo:jira:payments", "task_key": "PAY-103"},
        )


def test_recovery_from_retained_bundle_restores_graph(client):
    """Complete gated recovery: exact expected records restored, idempotent."""
    from app.graph.import_state import (
        BundleStore,
        PublicationGateProtocol,
        read_import_state,
    )
    from scripts.seed_graph import merge_structural_bundles

    protocol = PublicationGateProtocol(client, BundleStore())
    report = protocol.recover("STRUCTURAL")
    assert report["outcome"] == "RECOVERED"
    state = read_import_state(client, "STRUCTURAL")
    assert state["state"] == "READY"

    # expected records/content restored exactly
    rows = client.ro_query(
        "MATCH (t:Task {external_key: 'PAY-103'}) WHERE t.is_deleted = false RETURN count(*)", {}
    )
    assert int(rows[0][0]) == 1

    # idempotent: re-running recovery when READY is a no-op
    second = protocol.recover("STRUCTURAL")
    assert second["outcome"] == "NO_RECOVERY_REQUIRED"


def test_failed_recovery_stays_blocked(client):
    from app.graph.import_state import (
        BundleStore,
        RecoveryRequired,
        PublicationGateProtocol,
        read_import_state,
    )
    from app.graph.queries import GraphQueryService

    protocol = PublicationGateProtocol(client, BundleStore())
    # force DIRTY with a missing retained bundle (operator documented path)
    client.query(
        """
        MATCH (c:ImportControl {projection_id: 'STRUCTURAL'})
        SET c.state = 'DIRTY', c.pending_bundle_id = 'bundle-nonexistent'
        """,
        {},
    )
    with pytest.raises(RecoveryRequired, match="missing"):
        protocol.recover("STRUCTURAL")
    assert read_import_state(client, "STRUCTURAL")["state"] == "DIRTY"
    service = GraphQueryService(client)
    with pytest.raises(RecoveryRequired):
        service.execute(
            "exact_task_lookup",
            {"tenant_id": "demo", "project_id": "demo:jira:payments", "task_key": "PAY-103"},
        )
    # restore with a new validated full bundle (missing retained bundle case)
    from scripts.seed_graph import merge_structural_bundles

    clean = merge_structural_bundles()
    report = PublicationGateProtocol(client, BundleStore()).recover_with_bundle("STRUCTURAL", clean)
    assert report["outcome"] == "RECOVERED"


def test_restart_survives_dirty_state_and_recovers(client):
    """Restart both application 'process' and the database container: DIRTY
    must survive and every ordinary graph read stays blocked until recovery."""
    compose_file = r"E:\FalcorDB Hackathon\compose.yaml"

    from app.graph.import_state import (
        BundleStore,
        GraphRecoveryRequiredError,
        PublicationGateProtocol,
        read_import_state,
    )
    from app.graph.queries import GraphQueryService
    from scripts.seed_graph import merge_structural_bundles

    # ensure READY before injecting the failure
    if read_import_state(client, "STRUCTURAL")["state"] == "DIRTY":
        PublicationGateProtocol(client, BundleStore()).recover("STRUCTURAL")

    # force DIRTY via injected failure
    protocol = PublicationGateProtocol(client, BundleStore(), fail_after="after_edges")
    bundle = merge_structural_bundles()
    with pytest.raises(RuntimeError, match="after edge writes"):
        protocol.publish(bundle)
    assert read_import_state(client, "STRUCTURAL")["state"] == "DIRTY"

    # restart the database container (durable AOF must preserve DIRTY)
    subprocess.run(
        ["docker", "compose", "-f", compose_file, "restart", "falkordb"],
        check=True, capture_output=True,
    )
    deadline = time.time() + 60
    while time.time() < deadline:
        probe = subprocess.run(
            ["docker", "exec", "company-brain-falkordb", "redis-cli", "ping"],
            capture_output=True, text=True,
        )
        if probe.returncode == 0 and "PONG" in probe.stdout:
            break
        time.sleep(2)
    # new client (fresh connection) after restart
    restarted = client
    restarted.close()
    from app.graph.client import connect_default
    from app.config import get_settings

    fresh = connect_default(get_settings())
    try:
        state = read_import_state(fresh, "STRUCTURAL")
        assert state["state"] == "DIRTY", "dirty state must survive the restart"
        service = GraphQueryService(fresh)
        with pytest.raises(GraphRecoveryRequiredError):
            service.execute(
                "exact_task_lookup",
                {"tenant_id": "demo", "project_id": "demo:jira:payments", "task_key": "PAY-103"},
            )
        # full recovery restores exact records
        recovery = PublicationGateProtocol(fresh, BundleStore()).recover("STRUCTURAL")
        assert recovery["outcome"] == "RECOVERED"
        rows = fresh.ro_query(
            "MATCH (t:Task {external_key: 'PAY-101'}) WHERE t.is_deleted = false RETURN count(*)", {}
        )
        assert int(rows[0][0]) == 1
    finally:
        fresh.close()


def test_graph_survives_container_restart(client):
    """FalkorDB resource plan gate: the graph survives a container restart."""
    from scripts.seed_graph import merge_structural_bundles
    from app.graph.import_state import BundleStore, PublicationGateProtocol, read_import_state

    if read_import_state(client, "STRUCTURAL")["state"] == "DIRTY":
        PublicationGateProtocol(client, BundleStore()).recover("STRUCTURAL")
    PublicationGateProtocol(client, BundleStore()).publish(merge_structural_bundles())
    before = _node_count(client)

    subprocess.run(
        ["docker", "compose", "-f", r"E:\FalcorDB Hackathon\compose.yaml", "restart", "falkordb"],
        check=True, capture_output=True,
    )
    deadline = time.time() + 60
    while time.time() < deadline:
        probe = subprocess.run(
            ["docker", "exec", "company-brain-falkordb", "redis-cli", "ping"],
            capture_output=True, text=True,
        )
        if probe.returncode == 0 and "PONG" in probe.stdout:
            break
        time.sleep(2)

    client.close()
    from app.graph.client import connect_default
    from app.config import get_settings

    fresh = connect_default(get_settings())
    try:
        assert _node_count(fresh) == before, "graph records must survive the restart"
    finally:
        fresh.close()
