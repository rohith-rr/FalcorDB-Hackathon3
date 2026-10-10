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
    assert state["active_snapshot_id"] == seeded["snapshot_id"]
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
    assert state["active_snapshot_id"] == bundle["snapshot_id"]


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
        "snapshot_id": "snap-structural-004",
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
    branch["snapshot_id"] = "snap-structural-004"
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
            edge["snapshot_id"] = "snap-structural-004"
        elif edge["type"] == "PARENT":
            edge["snapshot_id"] = "snap-structural-004"
    bundle["snapshot_id"] = "snap-structural-004"
    bundle["bundle_id"] = "bundle-structural-snap-structural-004"

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
    assert read_import_state(client, "STRUCTURAL")["active_snapshot_id"] == clean["snapshot_id"]


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


def test_epic_children_returns_distinct_eligible_leaves(client, seeded):
    """Epic progress evidence: the TLS fixture is epic -> TASK-404 -> five
    leaves with four DONE. The template must traverse through the intermediate
    story and return the distinct eligible leaves themselves (4/5 progress),
    never the intermediate with is_leaf=false."""
    from app.graph.queries import GraphQueryService

    service = GraphQueryService(client)
    rows = service.execute(
        "epic_children",
        {"tenant_id": "demo", "epic_id": "demo:jira:tls:Epic-TLS-rotation"},
    )
    ids = [row[0] for row in rows]
    assert len(ids) == len(set(ids)), "members must be distinct"
    assert len(rows) == 5, f"expected the five leaf work items, got {rows}"
    assert "demo:jira:tls:TASK-404" not in ids, \
        "intermediate story with active children is not a leaf and is not counted again"
    expected = {f"demo:jira:tls:TASK-40{n}" for n in (1, 2, 3, 5, 6)}
    assert set(ids) == expected
    done = [row for row in rows if row[1] == "DONE"]
    assert len(done) == 4, "four of the five leaves are DONE"
    assert all(row[2] for row in rows), "raw statuses retained for labeling"


def test_epic_children_keeps_parent_with_cancelled_children_out_of_leaves(
    client, seeded,
):
    """A non-cancelled story whose only subtasks are cancelled is still an
    intermediate parent (all live confirmed children count for parent
    determination): it must not join the eligible-leaf progress denominator,
    and the cancelled subtasks stay excluded from progress."""
    from app.graph.queries import GraphQueryService

    tenant = "demo-cancel-scope"
    epic_id = "demo:cancel:Epic-x"
    story_id = "demo:cancel:TASK-story"
    leaf_id = "demo:cancel:TASK-leaf"
    try:
        client.query(
            "CREATE (e:Epic {id: $id, tenant_id: $tenant, is_deleted: false, "
            "status: 'IN_PROGRESS', raw_status: 'In Progress'})",
            {"id": epic_id, "tenant": tenant},
        )
        for node_id, status in (
            (story_id, "IN_PROGRESS"),
            ("demo:cancel:TASK-cancelled-1", "CANCELLED"),
            ("demo:cancel:TASK-cancelled-2", "CANCELLED"),
            (leaf_id, "DONE"),
        ):
            client.query(
                "CREATE (t:Task {id: $id, tenant_id: $tenant, is_deleted: false, "
                "status: $status, raw_status: $status})",
                {"id": node_id, "tenant": tenant, "status": status},
            )
        for start, end in (
            (epic_id, story_id),
            (story_id, "demo:cancel:TASK-cancelled-1"),
            (story_id, "demo:cancel:TASK-cancelled-2"),
            (epic_id, leaf_id),
        ):
            client.query(
                "MATCH (a {id: $start}), (b {id: $end}) "
                "CREATE (a)-[r:HAS_TASK {id: $edge_id, tenant_id: $tenant, "
                "is_deleted: false, authority: 'CONFIRMED'}]->(b)",
                {
                    "start": start,
                    "end": end,
                    "edge_id": f"demo:cancel:edge:{start}:{end}",
                    "tenant": tenant,
                },
            )
        service = GraphQueryService(client)
        rows = service.execute("epic_children", {"tenant_id": tenant, "epic_id": epic_id})
        ids = [row[0] for row in rows]
        assert ids == [leaf_id], (
            "only the real leaf is eligible: the story with cancelled children "
            "is an intermediate parent, and cancelled subtasks are excluded "
            f"from progress, got {ids}"
        )
    finally:
        client.query(
            "MATCH (n {tenant_id: $tenant}) DETACH DELETE n",
            {"tenant": tenant},
        )


@pytest.fixture
def epic_hierarchy(client, seeded):
    """Isolate synthetic hierarchies from the published fixture tenants."""
    import uuid

    from app.graph.queries import GraphQueryService

    tenant = f"demo-hierarchy-{uuid.uuid4().hex}"

    def create(statuses, links):
        ids = {key: f"{tenant}:jira:test:{key}" for key in ["epic", *statuses]}
        client.query(
            "CREATE (:Epic {id: $id, tenant_id: $tenant, is_deleted: false, "
            "status: 'IN_PROGRESS', raw_status: 'In Progress'})",
            {"id": ids["epic"], "tenant": tenant},
        )
        client.query(
            "UNWIND $tasks AS task "
            "CREATE (:Task {id: task.id, tenant_id: $tenant, is_deleted: false, "
            "status: task.status, raw_status: task.status})",
            {"tenant": tenant, "tasks": [{"id": ids[key], "status": status}
                                         for key, status in statuses.items()]},
        )
        client.query(
            "UNWIND $links AS link "
            "MATCH (a {id: link.start}), (b {id: link.end}) "
            "CREATE (a)-[:HAS_TASK {tenant_id: $tenant, is_deleted: false, "
            "authority: 'CONFIRMED'}]->(b)",
            {"tenant": tenant, "links": [{"start": ids[start], "end": ids[end]}
                                         for start, end in links]},
        )
        return GraphQueryService(client), {"tenant_id": tenant, "epic_id": ids["epic"]}, ids

    try:
        yield create
    finally:
        client.query("MATCH (n {tenant_id: $tenant}) DETACH DELETE n", {"tenant": tenant})


@pytest.mark.parametrize("depth", [5, 9, 50])
def test_epic_children_includes_leaves_beyond_four_hops(epic_hierarchy, depth):
    chain = [f"story-{i}" for i in range(depth - 1)]
    statuses = {key: "IN_PROGRESS" for key in chain}
    statuses.update({"done": "DONE", "todo": "TODO"})
    path = ["epic", *chain, "todo"]
    links = list(zip(path, path[1:])) + [("epic", "done")]
    service, params, ids = epic_hierarchy(statuses, links)
    rows = service.execute("epic_children", params)
    assert {row[0] for row in rows} == {ids["done"], ids["todo"]}
    assert sum(row[1] == "DONE" for row in rows) == 1


def test_epic_children_traverses_cancelled_ancestors(epic_hierarchy):
    service, params, ids = epic_hierarchy(
        {"story": "CANCELLED", "substory": "CANCELLED", "todo": "TODO",
         "cancelled": "CANCELLED", "done": "DONE"},
        [("epic", "story"), ("story", "substory"), ("substory", "todo"),
         ("story", "cancelled"), ("epic", "done"), ("epic", "todo")],
    )
    rows = service.execute("epic_children", params)
    assert {row[0] for row in rows} == {ids["done"], ids["todo"]}
    assert len(rows) == 2, "multiple confirmed paths must not count a leaf twice"


@pytest.mark.parametrize("require_ready", [True, False])
def test_epic_children_handles_converging_paths(epic_hierarchy, require_ready):
    """35 nodes and 66 edges must not enumerate 2**17 hierarchy paths."""
    layers = [[f"layer-{depth}-{side}" for side in range(2)] for depth in range(17)]
    statuses = {key: "IN_PROGRESS" for layer in layers for key in layer}
    statuses.update({layers[-1][0]: "DONE", layers[-1][1]: "TODO"})
    links = [("epic", key) for key in layers[0]]
    links += [(parent, child) for previous, current in zip(layers, layers[1:])
              for parent in previous for child in current]
    service, params, ids = epic_hierarchy(statuses, links)
    rows = service.execute("epic_children", params, require_ready=require_ready)
    assert {row[0] for row in rows} == {ids[key] for key in layers[-1]}
    assert len(rows) == 2


def test_epic_children_pages_wide_intermediate_frontiers(epic_hierarchy):
    """Intermediate stories can exceed the budget while only two leaves qualify."""
    stories = [f"story-{i:03}" for i in range(202)]
    statuses = {key: "IN_PROGRESS" for key in stories}
    statuses.update({"done": "DONE", "todo": "TODO"})
    links = [("epic", key) for key in stories] + [(key, "done") for key in stories]
    links.append((stories[-1], "todo"))
    service, params, ids = epic_hierarchy(statuses, links)
    rows = service.execute("epic_children", params)
    assert rows == [[ids["done"], "DONE", "DONE"], [ids["todo"], "TODO", "TODO"]]
    assert service.read_set.entries[0]["params"] == params
    assert len(service.read_set.entries) == 1


def test_epic_children_terminates_with_cycles(epic_hierarchy):
    service, params, ids = epic_hierarchy(
        {"a": "IN_PROGRESS", "b": "IN_PROGRESS", "done": "DONE"},
        [("epic", "a"), ("a", "b"), ("b", "a"), ("b", "done")],
    )
    assert service.execute("epic_children", params) == [[ids["done"], "DONE", "DONE"]]


@pytest.mark.parametrize("subject, property_name, value", [
    ("edge", "is_deleted", True),
    ("edge", "authority", "CANDIDATE"),
    ("edge", "tenant_id", "foreign"),
    ("node", "is_deleted", True),
    ("node", "tenant_id", "foreign"),
    ("epic", "is_deleted", True),
])
def test_epic_children_filters_every_frontier(
    epic_hierarchy, client, subject, property_name, value,
):
    service, params, ids = epic_hierarchy(
        {"a": "CANCELLED", "b": "CANCELLED", "todo": "TODO", "done": "DONE"},
        [("epic", "a"), ("a", "b"), ("b", "todo"), ("epic", "done")],
    )
    if subject == "edge":
        client.query(
            "MATCH (a:Task {id: $parent})-[r:HAS_TASK]->(b:Task {id: $child}) "
            f"SET r.{property_name} = $value",
            {"parent": ids["b"], "child": ids["todo"], "value": value},
        )
    else:
        client.query(
            f"MATCH (n {{id: $id}}) SET n.{property_name} = $value",
            {"id": ids["epic" if subject == "epic" else "b"], "value": value},
        )
    try:
        expected = [] if subject == "epic" else [[ids["done"], "DONE", "DONE"]]
        assert service.execute("epic_children", params) == expected
    finally:
        # Keep foreign-node exercises inside the fixture's cleanup scope.
        if subject == "node" and property_name == "tenant_id":
            client.query(
                "MATCH (n {id: $id}) SET n.tenant_id = $tenant",
                {"id": ids["b"], "tenant": params["tenant_id"]},
            )


@pytest.mark.parametrize("change", ["status", "overflow"])
def test_epic_children_replays_complete_membership(
    epic_hierarchy, client, monkeypatch, change,
):
    from app.graph.import_state import read_import_state
    from app.graph.queries import GraphSnapshotChanged

    statuses = {f"leaf-{i:03}": "TODO" for i in range(200)}
    statuses.update({"story": "IN_PROGRESS", "overflow": "CANCELLED"})
    links = [("epic", "story")] + [("story", key) for key in statuses if key != "story"]
    service, params, ids = epic_hierarchy(statuses, links)
    state = read_import_state(client, "STRUCTURAL")
    monkeypatch.setattr("app.graph.queries.read_import_state", lambda *_: state)

    rows = service.execute("epic_children", params)
    assert len(rows) == 200
    entry = service.read_set.entries[0]
    assert entry["params"] == params
    state["generation"] += 1
    assert service.execute("epic_children", params) == rows
    assert service.read_set.entries == [entry, entry]

    # A changed deep leaf or a newly eligible 201st leaf invalidates replay.
    client.query(
        "MATCH (t:Task {id: $id}) SET t.status = 'DONE', t.raw_status = 'Done'",
        {"id": ids["leaf-000" if change == "status" else "overflow"]},
    )
    state["generation"] += 1
    with pytest.raises(GraphSnapshotChanged, match="GRAPH_SNAPSHOT_CHANGED"):
        service.execute("epic_children", params)
    assert service.read_set.entries == [entry, entry]


@pytest.mark.parametrize("leaf_count", [200, 201])
def test_epic_children_preserves_overflow_sentinel_at_depth(epic_hierarchy, leaf_count):
    from app.graph.queries import OverflowSentinelExceeded

    chain = [f"story-{i}" for i in range(4)]
    leaves = [f"leaf-{i}" for i in range(leaf_count)]
    statuses = {key: "IN_PROGRESS" for key in chain}
    statuses.update({key: "TODO" for key in leaves})
    path = ["epic", *chain]
    links = list(zip(path, path[1:])) + [(chain[-1], key) for key in leaves]
    service, params, ids = epic_hierarchy(statuses, links)
    if leaf_count > 200:
        with pytest.raises(OverflowSentinelExceeded):
            service.execute("epic_children", params)
        assert service.read_set.entries == []
    else:
        rows = service.execute("epic_children", params)
        assert {row[0] for row in rows} == {ids[key] for key in leaves}


def test_recover_with_bundle_restores_missing_control_state(client, seeded):
    """Operator fallback for missing/empty durable control state: the graph's
    ImportControl is gone (UNINITIALIZED) but a validated full bundle is
    supplied — rebuild writes the projection back through the same gated
    protocol instead of raising an unhandled error."""
    from app.graph.import_state import (
        BundleStore,
        PublicationGateProtocol,
        read_import_state,
    )
    from scripts.seed_graph import merge_structural_bundles

    try:
        if read_import_state(client, "STRUCTURAL")["state"] == "READY":
            # simulate the empty/unreadable control state case
            client.query(
                "MATCH (c:ImportControl {projection_id: 'STRUCTURAL'}) DELETE c",
                {},
            )
        assert read_import_state(client, "STRUCTURAL")["state"] == "UNINITIALIZED"
        bundle = merge_structural_bundles()
        report = PublicationGateProtocol(client, BundleStore()).recover_with_bundle(
            "STRUCTURAL", bundle
        )
        assert report["outcome"] == "RECOVERED"
        state = read_import_state(client, "STRUCTURAL")
        assert state["state"] == "READY"
        assert state["active_snapshot_id"] == bundle["snapshot_id"]
    finally:
        # restore canonical state for subsequent tests regardless of outcome
        PublicationGateProtocol(client, BundleStore()).publish(merge_structural_bundles())
        assert read_import_state(client, "STRUCTURAL")["state"] == "READY"


def test_recover_with_bundle_rejects_cross_projection_bundle(client, seeded):
    """A STRUCTURAL bundle cannot recover INCIDENT (or vice versa): it must be
    rejected before persistence or mutation."""
    from app.graph.import_state import (
        BundleStore,
        PublicationGateProtocol,
        RecoveryRequired,
    )
    from scripts.seed_graph import merge_structural_bundles

    protocol = PublicationGateProtocol(client, BundleStore())
    with pytest.raises(RecoveryRequired, match="not the requested projection"):
        protocol.recover_with_bundle("INCIDENT", merge_structural_bundles())
    # nothing was mutated: INCIDENT stays uninitialized, STRUCTURAL stays READY
    from app.graph.import_state import read_import_state

    assert read_import_state(client, "INCIDENT")["state"] == "UNINITIALIZED"
    assert read_import_state(client, "STRUCTURAL")["state"] == "READY"


def test_retained_bundle_immutability_keeps_recovery_bytes(client, seeded):
    """A conflicting write for an existing bundle ID is rejected instead of
    silently replacing retained recovery bytes (phase_01:45)."""
    import copy

    from app.graph.import_state import (
        BundleConflictError,
        BundleStore,
        PublicationGateProtocol,
    )
    from scripts.seed_graph import merge_structural_bundles

    protocol = PublicationGateProtocol(client, BundleStore())
    bundle = merge_structural_bundles()
    protocol.publish(bundle)  # retains the canonical bytes for this snapshot
    tampered = copy.deepcopy(bundle)
    tampered["coverage"] = dict(tampered.get("coverage") or {}, payments="POLLUTED")
    with pytest.raises(BundleConflictError, match="immutable"):
        protocol.bundles.persist(tampered)
    # the retained bundle still hashes to the acknowledged original bytes
    from app.graph.import_state import read_import_state

    state = read_import_state(client, "STRUCTURAL")
    assert protocol.bundles.hash_of("STRUCTURAL", bundle["bundle_id"]) is not None
    assert state["state"] == "READY"


def test_projection_token_replay_after_publication_between_reads(client, seeded):
    """Tokens are captured under admission and rechecked: an unrelated
    publication between two reads on the SAME service replays the earlier
    reads and proves equivalence instead of mixing generations."""
    from app.graph.import_state import (
        BundleStore,
        PublicationGateProtocol,
        read_import_state,
    )
    from app.graph.queries import GraphQueryService
    from scripts.seed_graph import merge_structural_bundles

    service = GraphQueryService(client)
    params = {
        "tenant_id": "demo",
        "project_id": "demo:jira:payments",
        "task_key": "PAY-103",
    }
    first = service.execute("exact_task_lookup", params)
    assert first[0][0] == "demo:jira:payments:PAY-103"
    tokens_before = dict(service._tokens)

    # An unrelated publication (same evidence, new generation) completes here.
    PublicationGateProtocol(client, BundleStore()).publish(merge_structural_bundles())
    state = read_import_state(client, "STRUCTURAL")
    assert int(state["generation"]) > tokens_before["STRUCTURAL"][0]
    second = service.execute("exact_task_lookup", params)
    assert second == first, "equivalent evidence survives the moved token"
    assert service._tokens["STRUCTURAL"][0] == int(state["generation"]), \
        "validation tokens advanced after proven equivalence"
    # Validation replay must leave the request's evidence entries untouched:
    # the same two-read sequence produces the same number of entries — and the
    # same overall fingerprint — with or without an intervening publication.
    assert len(service.read_set.entries) == 2, (
        "replayed fingerprints must be computed in a temporary read set, "
        f"not appended to the request's entries (got {len(service.read_set.entries)})"
    )
    no_publication = GraphQueryService(client)
    no_publication.execute("exact_task_lookup", params)
    no_publication.execute("exact_task_lookup", params)
    assert len(no_publication.read_set.entries) == 2
    assert no_publication.read_set.fingerprint() == service.read_set.fingerprint(), \
        "an unrelated publication between reads must not change the read-set fingerprint"


def test_relevant_change_between_reads_returns_graph_snapshot_changed(client, seeded):
    """Changed relevant evidence within one request cannot be replayed: the
    service rejects with GRAPH_SNAPSHOT_CHANGED for one whole-request retry."""
    import copy
    import time

    from app.graph.import_state import (
        BundleStore,
        PublicationGateProtocol,
        read_import_state,
    )
    from app.graph.queries import GraphQueryService, GraphSnapshotChanged
    from scripts.seed_graph import merge_structural_bundles

    service = GraphQueryService(client)
    params = {
        "tenant_id": "demo",
        "project_id": "demo:jira:payments",
        "task_key": "PAY-103",
    }
    service.execute("exact_task_lookup", params)

    # Publish a validated bundle whose relevant task changed (new snapshot id).
    bundle = copy.deepcopy(merge_structural_bundles())
    tag = f"{int(time.time())}-{read_import_state(client, 'STRUCTURAL')['generation']}"
    bundle["snapshot_id"] = f"snap-structural-{tag}"
    bundle["bundle_id"] = f"bundle-structural-snap-structural-{tag}"
    task = next(n for n in bundle["nodes"] if n["id"] == "demo:jira:payments:PAY-103")
    task["status"] = "DONE"
    task["raw_status"] = "Done"
    try:
        PublicationGateProtocol(client, BundleStore()).publish(bundle)
        with pytest.raises(GraphSnapshotChanged, match="GRAPH_SNAPSHOT_CHANGED"):
            service.execute("exact_task_lookup", params)
    finally:
        # Restore the canonical fixture snapshot for later tests.
        PublicationGateProtocol(client, BundleStore()).publish(merge_structural_bundles())
    assert read_import_state(client, "STRUCTURAL")["active_snapshot_id"] == seeded["snapshot_id"]


def test_replay_uses_original_params_not_caller_mutations(client, seeded):
    """Replay must compare the exact inputs originally fingerprinted: a
    caller reusing/mutating a list-valued parameter after the read (advancing
    frontier_ids to the next traversal batch) must not change the recorded
    replay scope, so an unrelated equivalent publication still replays
    equivalently instead of raising GRAPH_SNAPSHOT_CHANGED."""
    from app.graph.import_state import BundleStore, PublicationGateProtocol
    from app.graph.queries import GraphQueryService
    from scripts.seed_graph import merge_structural_bundles

    service = GraphQueryService(client)
    frontier = {"tenant_id": "demo", "frontier_ids": ["demo:jira:payments:PAY-103"]}
    first = service.execute("dependency_frontier", frontier)
    assert first, "fixture PAY-103 must have a dependency edge"

    # the caller legitimately reuses the parameter for the next batch
    frontier["frontier_ids"].append("demo:jira:payments:PAY-101")

    # an unrelated equivalent publication completes between reads
    PublicationGateProtocol(client, BundleStore()).publish(merge_structural_bundles())

    # replay of the first read must use the ORIGINAL single-id scope; the
    # mutated scope would fingerprint differently and reject equivalently
    # unchanged evidence with GRAPH_SNAPSHOT_CHANGED
    second = service.execute("dependency_frontier", frontier)
    assert second, "the mutated two-id batch must still read its own evidence"


def test_control_state_read_does_not_invalidate_domain_replay(client, seeded):
    """A control-state read (import_state_read) before domain reads is not
    domain evidence: its transport columns (generation, snapshot ID,
    publication timestamps) are positional and legitimately move on every
    publication, so an otherwise equivalent publication must not fail the
    domain replay with GRAPH_SNAPSHOT_CHANGED."""
    from app.config import get_settings
    from app.graph.import_state import BundleStore, PublicationGateProtocol
    from app.graph.queries import GraphQueryService
    from scripts.seed_graph import merge_structural_bundles

    service = GraphQueryService(client)
    settings = get_settings()
    control = service.execute(
        "import_state_read",
        {"graph_name": settings.falkordb_graph_name, "projection_id": "STRUCTURAL"},
    )
    assert control and control[0][0] == "READY"

    params = {
        "tenant_id": "demo",
        "project_id": "demo:jira:payments",
        "task_key": "PAY-103",
    }
    first = service.execute("exact_task_lookup", params)
    assert first[0][0] == "demo:jira:payments:PAY-103"

    # unrelated equivalent publication (same evidence, new generation)
    PublicationGateProtocol(client, BundleStore()).publish(merge_structural_bundles())

    second = service.execute("exact_task_lookup", params)
    assert second == first, "equivalent domain evidence survives the moved token"


def test_read_set_records_declared_coverage(client, seeded):
    """Authoritative source-scope coverage is fingerprinted with each read
    (READY is coherent publication, not source completeness)."""
    from app.graph.queries import GraphQueryService
    from scripts.seed_graph import merge_structural_bundles

    service = GraphQueryService(client)
    service.execute(
        "exact_task_lookup",
        {"tenant_id": "demo", "project_id": "demo:jira:payments", "task_key": "PAY-103"},
    )
    entry = service.read_set.entries[-1]
    assert entry["coverage"] == {
        "STRUCTURAL": {
            "payments": "COMPLETE",
        }
    }


@pytest.mark.parametrize("task_key", ["PAY-103", "PAY-999"])
def test_lookup_replay_uses_relevant_source_coverage(client, seeded, task_key):
    import uuid

    from app.graph.import_state import BundleStore, PublicationGateProtocol
    from app.graph.queries import GraphQueryService, GraphSnapshotChanged
    from scripts.seed_graph import merge_structural_bundles

    params = {"tenant_id": "demo", "project_id": "demo:jira:payments", "task_key": task_key}
    service = GraphQueryService(client)
    first = service.execute("exact_task_lookup", params)
    protocol = PublicationGateProtocol(client, BundleStore())
    bundle = merge_structural_bundles()
    bundle["coverage"].update({"tls": "PARTIAL", "conversations": "PARTIAL"})
    try:
        tag = uuid.uuid4().hex
        bundle.update(snapshot_id=f"snap-coverage-{tag}", bundle_id=f"bundle-coverage-{tag}")
        protocol.publish(bundle)
        assert service.execute("exact_task_lookup", params) == first
        assert service.read_set.entries[0] == service.read_set.entries[1]

        bundle["coverage"]["payments"] = "PARTIAL"
        tag = uuid.uuid4().hex
        bundle.update(snapshot_id=f"snap-coverage-{tag}", bundle_id=f"bundle-coverage-{tag}")
        protocol.publish(bundle)
        with pytest.raises(GraphSnapshotChanged, match="GRAPH_SNAPSHOT_CHANGED"):
            service.execute("exact_task_lookup", params)
    finally:
        protocol.publish(merge_structural_bundles())


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


def test_read_behind_active_writer_rejects_dirty_without_waiting(client, seeded):
    """A publication holding the exclusive gate with the projection already
    marked DIRTY must fail the read fast with GRAPH_RECOVERY_REQUIRED instead
    of blocking request threads in acquire_shared() behind the import."""
    from app.graph.import_state import (
        BundleStore,
        GraphRecoveryRequiredError,
        PublicationGateProtocol,
        publish_gates,
        read_import_state,
    )
    from app.graph.queries import GraphQueryService
    from scripts.seed_graph import merge_structural_bundles

    protocol = PublicationGateProtocol(client, BundleStore())
    bundle = merge_structural_bundles()
    state = read_import_state(client, "STRUCTURAL")
    # Simulate an in-flight interrupted publication: the exclusive gate is
    # held by the writer while the durable DIRTY fence is already visible.
    with publish_gates(["STRUCTURAL"]):
        protocol._write_control(
            "STRUCTURAL",
            state="DIRTY",
            generation=int(state["generation"]) + 1,
            active_snapshot_id=state["active_snapshot_id"],
            pending_bundle_id=bundle["bundle_id"],
            pending_bundle_hash=None,
        )
        service = GraphQueryService(client)
        with pytest.raises(GraphRecoveryRequiredError):
            service.execute(
                "exact_task_lookup",
                {"tenant_id": "demo", "project_id": "demo:jira:payments", "task_key": "PAY-103"},
            )
    # restore READY for later tests (gated recovery from the retained bundle)
    report = protocol.recover("STRUCTURAL")
    assert report["outcome"] == "RECOVERED"


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
