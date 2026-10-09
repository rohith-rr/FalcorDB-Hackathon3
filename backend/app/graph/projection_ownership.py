"""Projection ownership rules (docs/design/graph_publication.md).

One shared FalkorDB graph; two logical projections with immutable
`projection_owner` on every managed node/edge:

- STRUCTURAL: tasks, epics, repositories, branches, commits, reviews,
  document references, conversations/messages/decisions, verified mappings.
- INCIDENT: alerts, incident lifecycle, deployments, artifacts, runtime
  observations, effective on-call assignments, projected action records.

A relationship belongs to INCIDENT when it originates in an incident-owned
record (including its links to structural entities); other relationships
belong to STRUCTURAL. Structural rebuilds preserve incident-owned records.
"""

from __future__ import annotations

from typing import Any, Dict, Set

from app.graph.schema import GraphValidationError

STRUCTURAL_LABELS = {
    "Epic",
    "Task",
    "Repository",
    "Branch",
    "PullRequest",
    "Review",
    "Commit",
    "TaskWorkPeriod",
    "RevisionEffect",
    "Document",
    "DesignDoc",
    "ProcessDoc",
    "CheckRun",
    "Conversation",
    "Message",
    "DesignDecision",
}

INCIDENT_LABELS = {
    "Alert",
    "Incident",
    "Deployment",
    "Artifact",
    "ServiceInstance",
    "Service",
    "Employee",
    "OnCallAssignment",
    "CustomerObservation",
    "ActionRecord",
}

INCIDENT_EDGE_TYPES = {
    "DEPLOYED_TO",
    "DEPLOYS_ARTIFACT",
    "DEPENDS_ON_RUNTIME",
    "ASSIGNED_TO",
    "OBSERVED_ON",
    "ROUTE_TO",
    "ALERT_FOR",
}

#: Labels whose graph records may never be tombstoned by a structural rebuild
#: when incident-owned links reference them (see loader preserve rules).
STRUCTURAL_ENDPOINTS_PRESERVED = {
    "Task",
    "Commit",
    "Branch",
    "Repository",
    "PullRequest",
    "Document",
    "ServiceInstance",
}


def expected_owner(label: str, edge_type: str = "") -> str:
    if label in INCIDENT_LABELS or edge_type in INCIDENT_EDGE_TYPES:
        return "INCIDENT"
    return "STRUCTURAL"


def validate_owner(node_or_edge: Dict[str, Any], *, is_edge: bool = False) -> None:
    label = node_or_edge.get("label") or ""
    edge_type = node_or_edge.get("type", "") if is_edge else ""
    expected = expected_owner(label, edge_type)
    actual = node_or_edge.get("projection_owner")
    if actual != expected:
        raise GraphValidationError(
            f"record {node_or_edge.get('id')!r} has projection_owner {actual!r}, "
            f"expected {expected!r} (label={label or edge_type})"
        )


def incident_linked_ids(bundle: Dict[str, Any]) -> Set[str]:
    """Structural IDs referenced by incident-owned edges in a bundle."""
    linked: Set[str] = set()
    for edge in bundle.get("edges", []):
        if edge.get("projection_owner") == "INCIDENT":
            linked.add(edge.get("start_id"))
            linked.add(edge.get("end_id"))
    return {x for x in linked if x}


def assert_structural_rebuild_preserves_incident_links(
    structural_bundle: Dict[str, Any], existing_incident_edges: list
) -> None:
    """A structural rebuild cannot delete an endpoint with incident links."""
    tombstones = {
        n["id"]
        for n in structural_bundle.get("nodes", [])
        if n.get("is_deleted")
    }
    keep = incident_linked_ids(
        {"edges": existing_incident_edges}
    ) if existing_incident_edges else set()
    conflicts = tombstones & keep
    if conflicts:
        raise GraphValidationError(
            f"structural rebuild would tombstone endpoints referenced by "
            f"incident-owned links: {sorted(conflicts)}"
        )
