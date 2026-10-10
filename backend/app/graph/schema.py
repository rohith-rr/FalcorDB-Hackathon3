"""Canonical graph schema validation (docs/design/graph_schema.md).

The loader validates normalized nodes/edges against this schema before any
graph mutation; application validators enforce edge endpoints, required
fields and uniqueness. FalkorDB internal numeric node IDs are never used as
application identity.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple

from app.core.ids import SHA_RE, UnscopedIdError, is_scoped_id

SCHEMA_VERSION = "1.0.0"

#: Managed labels with their label-specific required domain fields.
NODE_LABELS: Dict[str, Set[str]] = {
    "Epic": {"project_id", "external_key", "title", "status", "raw_status"},
    "Task": {
        "project_id",
        "external_key",
        "title",
        "work_item_type",
        "status",
        "raw_status",
        "assignee_ids",
        "repository_ids",
    },
    "Repository": {"provider_id", "owner_name", "clone_url", "stable_ref"},
    "Branch": {"repository_id", "ref", "head_sha", "exists"},
    "PullRequest": {
        "repository_id",
        "number",
        "title",
        "state",
        "draft",
        "head_repository_id",
        "base_ref",
        "head_sha",
        "base_sha",
    },
    "Review": {"reviewer_id", "state", "submitted_at", "commit_sha"},
    "Commit": {"repository_id", "sha", "message", "committed_at", "history_complete"},
    "TaskWorkPeriod": {"task_id", "assignee_id", "valid_from", "time_accuracy", "coverage"},
    "RevisionEffect": {
        "repository_id",
        "delivery_id",
        "effect_kind",
        "effect_commit_sha",
        "affected_revision_shas",
        "coverage",
        "authority",
        "mapping_version",
    },
    "Document": {"title", "version", "content_hash", "content_path", "doc_status"},
    "DesignDoc": set(),
    "ProcessDoc": set(),
    "Conversation": {"source_key", "source_epoch", "parser_version", "redaction_version"},
    "Message": {
        "conversation_id",
        "sequence",
        "role",
        "origin",
        "content_hash",
        "capture_id",
    },
    "DesignDecision": {"revision_hash", "title", "status"},
    "ImportControl": set(),  # control metadata, not domain data
}

WORK_ITEM_TYPES = {"STORY", "TASK", "SUBTASK"}
TASK_STATUSES = {"TODO", "IN_PROGRESS", "BLOCKED", "DONE", "CANCELLED", "UNKNOWN"}
LINK_METHODS = {"API", "MANIFEST", "PARSED_EXPLICIT_REFERENCE", "INFERRED"}
AUTHORITIES = {"CONFIRMED", "CANDIDATE"}
PROJECTIONS = {"STRUCTURAL", "INCIDENT"}
EFFECT_KINDS = {"REVERT", "REAPPLICATION"}
EFFECT_COVERAGE = {"COMPLETE", "PARTIAL", "UNKNOWN"}

#: Allowed (source label, edge type, destination label) triples.
EDGE_ENDPOINTS: Dict[str, Set[Tuple[str, str]]] = {
    "HAS_TASK": {("Epic", "Task"), ("Task", "Task")},
    "DEPENDS_ON": {("Task", "Task")},
    "IMPLEMENTED_IN": {("Task", "Branch")},
    "HAS_WORK_PERIOD": {("Task", "TaskWorkPeriod")},
    "IMPLEMENTED_BY": {("Task", "PullRequest")},
    "DELIVERED_BY": {("Task", "Commit")},
    "HAS_BRANCH": {("Repository", "Branch")},
    "HEAD_AT": {("Branch", "Commit")},
    "HAS_PR": {("Branch", "PullRequest")},
    "TARGETS": {("PullRequest", "Branch")},
    "IN_REPOSITORY": {("PullRequest", "Repository"), ("Conversation", "Repository")},
    "REVIEWS": {("Review", "PullRequest")},
    "REVIEWED_COMMIT": {("Review", "Commit")},
    "PARENT": {("Commit", "Commit")},
    "EFFECT_AT": {("RevisionEffect", "Commit")},
    "AFFECTS_REVISION": {("RevisionEffect", "Commit")},
    "RESOLVES_REVERT": {("RevisionEffect", "RevisionEffect")},
    "SPECIFIES": {("DesignDoc", "Task"), ("Document", "Task")},  # Document carries the subtype label
    "GOVERNS_PROCESS": {("ProcessDoc", "Task"), ("Document", "Task")},
    "CHECKS_COMMIT": {("CheckRun", "Commit")},
    "HAS_MESSAGE": {("Conversation", "Message")},
    "NEXT_MESSAGE": {("Message", "Message")},
    "MENTIONS": {
        ("Message", "Task"),
        ("Message", "Repository"),
        ("Message", "Branch"),
        ("Message", "PullRequest"),
        ("Message", "Commit"),
        ("Message", "Document"),
        ("Message", "DesignDecision"),
    },
    "SUPPORTED_BY": {("DesignDecision", "Message")},
    "APPLIES_TO": {
        ("DesignDecision", "Task"),
        ("DesignDecision", "Repository"),
        ("DesignDecision", "Branch"),
        ("DesignDecision", "PullRequest"),
        ("DesignDecision", "Commit"),
        ("DesignDecision", "Document"),
    },
    "SUPERSEDES": {("DesignDecision", "DesignDecision")},
}

DEPENDENCY_KINDS = {"CODE", "PROCESS"}


class GraphValidationError(ValueError):
    """Bundle/schema validation failure (pre-mutation)."""


def _require(node: Dict[str, Any], key: str, label: str) -> Any:
    value = node.get(key)
    if value is None or value == "":
        raise GraphValidationError(f"{label} node {node.get('id')!r} missing required field {key!r}")
    return value


def validate_node(node: Dict[str, Any]) -> None:
    label = node.get("label")
    if label not in NODE_LABELS:
        raise GraphValidationError(f"unknown node label {label!r}")
    node_id = node.get("id")
    if not node_id:
        raise GraphValidationError(f"{label} node without id")
    if not is_scoped_id(node_id):
        raise GraphValidationError(f"{label} node id {node_id!r} is not a scoped application ID")
    for field in (
        "tenant_id",
        "projection_owner",
        "source_system",
        "source_record_ref",
        "observed_at",
        "ingested_at",
        "snapshot_id",
        "schema_version",
    ):
        _require(node, field, label)
    if node.get("projection_owner") not in PROJECTIONS:
        raise GraphValidationError(f"node {node_id!r} has invalid projection_owner")
    if node.get("schema_version") != SCHEMA_VERSION:
        raise GraphValidationError(
            f"node {node_id!r} schema_version {node.get('schema_version')!r} != {SCHEMA_VERSION}"
        )
    if not isinstance(node.get("is_deleted"), bool):
        raise GraphValidationError(f"node {node_id!r} requires boolean is_deleted")
    for field in NODE_LABELS[label]:
        _require(node, field, label)
    if label == "Task":
        if node["work_item_type"] not in WORK_ITEM_TYPES:
            raise GraphValidationError(f"task {node_id!r} invalid work_item_type")
        if node["status"] not in TASK_STATUSES:
            raise GraphValidationError(f"task {node_id!r} invalid normalized status")
        assignees = node.get("assignee_ids")
        if not (assignees is None or isinstance(assignees, list)):
            raise GraphValidationError(f"task {node_id!r} assignee_ids must be null or a list")
    if label == "Branch":
        if not SHA_RE.match(str(node.get("head_sha", ""))):
            raise GraphValidationError(f"branch {node_id!r} head_sha must be a full 40-char SHA")
    if label == "Commit":
        if not SHA_RE.match(str(node["sha"])):
            raise GraphValidationError(f"commit {node_id!r} sha must be a full 40-char SHA")
    if label == "RevisionEffect":
        if node["effect_kind"] not in EFFECT_KINDS:
            raise GraphValidationError(f"revision effect {node_id!r} invalid effect_kind")
        if not node.get("affected_revision_shas"):
            raise GraphValidationError(f"revision effect {node_id!r} requires affected_revision_shas")
        if node["coverage"] not in EFFECT_COVERAGE:
            raise GraphValidationError(f"revision effect {node_id!r} invalid coverage")


def _edge_key(edge: Dict[str, Any]) -> Tuple[str, str, str]:
    return (str(edge.get("type")), str(edge.get("start_id")), str(edge.get("end_id")))


def validate_edge(edge: Dict[str, Any], node_labels: Dict[str, str]) -> None:
    edge_type = edge.get("type")
    if edge_type not in EDGE_ENDPOINTS:
        raise GraphValidationError(f"unknown edge type {edge_type!r}")
    for field in (
        "id",
        "tenant_id",
        "projection_owner",
        "source_record_ref",
        "snapshot_id",
        "observed_at",
        "link_method",
        "authority",
    ):
        if edge.get(field) in (None, ""):
            raise GraphValidationError(f"edge {edge.get('id')!r} missing required field {field!r}")
    if edge.get("projection_owner") not in PROJECTIONS:
        raise GraphValidationError(f"edge {edge.get('id')!r} has invalid projection_owner")
    if edge.get("link_method") not in LINK_METHODS:
        raise GraphValidationError(f"edge {edge.get('id')!r} invalid link_method")
    if edge.get("authority") not in AUTHORITIES:
        raise GraphValidationError(f"edge {edge.get('id')!r} invalid authority")
    if not isinstance(edge.get("is_deleted"), bool):
        raise GraphValidationError(f"edge {edge.get('id')!r} requires boolean is_deleted")
    start_id, end_id = edge.get("start_id"), edge.get("end_id")
    if not start_id or not end_id:
        raise GraphValidationError(f"edge {edge.get('id')!r} missing start_id/end_id")
    if start_id not in node_labels or end_id not in node_labels:
        raise GraphValidationError(
            f"edge {edge.get('id')!r} references an endpoint outside the bundle: {start_id!r} -> {end_id!r}"
        )
    src_label, dst_label = node_labels[start_id], node_labels[end_id]
    if (src_label, dst_label) not in EDGE_ENDPOINTS[edge_type]:
        raise GraphValidationError(
            f"edge {edge.get('id')!r}: {src_label}-{edge_type}->{dst_label} violates the canonical schema"
        )
    if edge_type == "DEPENDS_ON" and edge.get("dependency_kind") not in DEPENDENCY_KINDS:
        raise GraphValidationError(f"DEPENDS_ON edge {edge.get('id')!r} requires a CODE/PROCESS kind")
    if edge_type == "RESOLVES_REVERT" and edge.get("authority") != "CONFIRMED":
        # Reapplications require confirmed resolving links (graph_schema.md).
        raise GraphValidationError("RESOLVES_REVERT edges must be CONFIRMED")


def validate_bundle(bundle: Dict[str, Any]) -> None:
    """Validate a full projection bundle before persistence/mutation."""
    projection = bundle.get("projection_id")
    if projection not in PROJECTIONS:
        raise GraphValidationError(f"bundle has invalid projection_id {projection!r}")
    if not bundle.get("bundle_id") or not bundle.get("snapshot_id"):
        raise GraphValidationError("bundle requires bundle_id and snapshot_id")
    nodes: List[Dict[str, Any]] = bundle.get("nodes", [])
    edges: List[Dict[str, Any]] = bundle.get("edges", [])

    node_labels: Dict[str, str] = {}
    seen: Set[str] = set()
    tenant: Optional[str] = None
    # Ownership validation (docs/design/graph_publication.md): every record
    # must be canonically owned (derived from label/edge type) and actually
    # owned by the bundle's projection. Without this, a STRUCTURAL bundle can
    # carry an INCIDENT-owned Task and later overwrite immutable ownership.
    from app.graph.projection_ownership import validate_owner  # local import: module cycle

    for node in nodes:
        validate_node(node)
        validate_owner(node)
        node_id = node["id"]
        if node_id in seen:
            raise GraphValidationError(f"duplicate logical node ID {node_id!r}")
        if node["projection_owner"] != projection:
            raise GraphValidationError(
                f"node {node_id!r} owned by {node['projection_owner']!r} cannot be "
                f"published through a {projection} bundle"
            )
        seen.add(node_id)
        node_labels[node_id] = node["label"]
        if tenant is None:
            tenant = node["tenant_id"]
        elif node["tenant_id"] != tenant:
            raise GraphValidationError(f"cross-tenant node {node_id!r} in single bundle")

    edge_ids: Set[str] = set()
    for edge in edges:
        validate_edge(edge, node_labels)
        validate_owner(edge, is_edge=True)
        if edge["id"] in edge_ids:
            raise GraphValidationError(f"duplicate logical edge ID {edge['id']!r}")
        if edge["projection_owner"] != projection:
            raise GraphValidationError(
                f"edge {edge['id']!r} owned by {edge['projection_owner']!r} cannot be "
                f"published through a {projection} bundle"
            )
        edge_ids.add(edge["id"])
        if edge["tenant_id"] != tenant:
            raise GraphValidationError(f"cross-tenant edge {edge['id']!r}")

    # One active branch head / one active PR target per branch (schema rules).
    active_heads: Dict[str, str] = {}
    active_targets: Dict[str, str] = {}
    for edge in edges:
        if edge.get("is_deleted") or edge.get("authority") != "CONFIRMED":
            continue
        etype = edge["type"]
        if etype == "HEAD_AT":
            branch_id = edge["start_id"]
            if branch_id in active_heads and active_heads[branch_id] != edge["end_id"]:
                raise GraphValidationError(f"branch {branch_id!r} has more than one active HEAD_AT")
            active_heads[branch_id] = edge["end_id"]
        elif etype == "TARGETS":
            pr_id = edge["start_id"]
            if pr_id in active_targets and active_targets[pr_id] != edge["end_id"]:
                raise GraphValidationError(f"PR {pr_id!r} targets more than one active branch")
            # Record the first active target so a second, different target for
            # the same PR is detected; the malformed bundle must fail during
            # preparation, before any graph mutation (readable prior snapshot).
            active_targets[pr_id] = edge["end_id"]

    # Resolve-effect consistency: REAPPLICATION edges must reference a REVERT.
    effects = {n["id"]: n for n in nodes if n["label"] == "RevisionEffect"}
    for edge in edges:
        if edge["type"] == "RESOLVES_REVERT":
            src = effects.get(edge["start_id"])
            dst = effects.get(edge["end_id"])
            if src is None or dst is None:
                raise GraphValidationError(f"RESOLVES_REVERT {edge['id']!r} has dangling endpoint")
            if src.get("effect_kind") != "REAPPLICATION" or dst.get("effect_kind") != "REVERT":
                raise GraphValidationError(
                    f"RESOLVES_REVERT {edge['id']!r} must go REAPPLICATION -> REVERT"
                )
            if src.get("repository_id") != dst.get("repository_id"):
                raise GraphValidationError(f"RESOLVES_REVERT {edge['id']!r} crosses repositories")


def validate_reimport_shape(bundle: Dict[str, Any]) -> None:
    """Light re-validation used for idempotent reimports (see loader)."""
    validate_bundle(bundle)
