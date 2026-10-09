"""Fixture normalization: fixture JSON -> canonical graph bundles.

Fixture manifests may use symbolic revision labels (`SYMBOLIC:<label>`); the
Phase 0 Git builder resolves them to real full SHAs before validation or
ingestion (never fake valid-looking SHAs). All nodes/edges carry the canonical
provenance fields and immutable projection_owner.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

_WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
_BACKEND_ROOT = _WORKSPACE_ROOT / "backend"
for _p in (str(_WORKSPACE_ROOT), str(_BACKEND_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from app.core.ids import SHA_RE
from app.graph.schema import SCHEMA_VERSION
from scripts.build_git_fixtures import (
    GitFixtureError,
    build_payments_fixture,
    resolve_symbol,
)
WORKSPACE_ROOT = _WORKSPACE_ROOT
FIXTURES_ROOT = WORKSPACE_ROOT / "fixtures"
GIT_MANIFEST = WORKSPACE_ROOT / ".local" / "state" / "git" / "git_fixture_manifest.json"

OBSERVED_AT = "2026-10-10T00:00:00Z"
INGESTED_AT = "2026-10-10T00:00:00Z"


def load_fixture(*relative: str) -> Dict[str, Any]:
    path = FIXTURES_ROOT.joinpath(*relative)
    return json.loads(path.read_text(encoding="utf-8"))


def load_git_manifest() -> Dict[str, Any]:
    if not GIT_MANIFEST.is_file():
        build_payments_fixture()
    return json.loads(GIT_MANIFEST.read_text(encoding="utf-8"))


def resolve_git_revisions(value: str, manifest: Dict[str, Any]) -> str:
    return resolve_symbol(value, manifest)


def _base(tenant: str, snapshot_id: str, owner: str = "STRUCTURAL") -> Dict[str, Any]:
    return {
        "tenant_id": tenant,
        "projection_owner": owner,
        "source_system": "fixture",
        "source_record_ref": "",
        "source_url": None,
        "source_updated_at": None,
        "observed_at": OBSERVED_AT,
        "ingested_at": INGESTED_AT,
        "snapshot_id": snapshot_id,
        "schema_version": SCHEMA_VERSION,
        "is_deleted": False,
    }


def _node(label: str, node_id: str, fields: Dict[str, Any], tenant: str, snapshot_id: str,
          source_system: str, ref: str) -> Dict[str, Any]:
    node = _base(tenant, snapshot_id)
    node.update({"label": label, "id": node_id, "source_system": source_system, "source_record_ref": ref})
    node.update(fields)
    return node


def _edge(edge_type: str, edge_id: str, start: str, end: str, fields: Dict[str, Any],
          tenant: str, snapshot_id: str, source_system: str, ref: str,
          link_method: str = "MANIFEST", authority: str = "CONFIRMED") -> Dict[str, Any]:
    edge = _base(tenant, snapshot_id)
    edge.update({
        "type": edge_type,
        "id": edge_id,
        "start_id": start,
        "end_id": end,
        "source_system": source_system,
        "source_record_ref": ref,
        "link_method": link_method,
        "authority": authority,
    })
    edge.update(fields)
    return edge


def build_structural_bundle(snapshot_id: str = "snap-payments-001") -> Dict[str, Any]:
    """Normalize Payments + TLS fixtures into a STRUCTURAL bundle.

    Resolves symbolic revision labels through the Git builder manifest before
    validation. Raises GitFixtureError for unresolved labels.
    """
    git_manifest = load_git_manifest()

    tasks_fx = load_fixture("payments", "tasks.json")
    pulls_fx = load_fixture("payments", "pulls.json")
    reviews_fx = load_fixture("payments", "reviews.json")
    documents_fx = load_fixture("payments", "documents.json")
    links_fx = load_fixture("payments", "links.json")
    tls_tasks_fx = load_fixture("tls", "tasks.json")
    tls_docs_fx = load_fixture("tls", "documents.json")
    tls_links_fx = load_fixture("tls", "links.json")

    tenant = tasks_fx["tenant_id"]
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []

    # --- Repositories / branches / commits ------------------------------------
    repo_ref = pulls_fx["repositories"][0]
    repo_id = repo_ref["id"]
    repo_path = str(git_manifest["repositories"][repo_id]["path"])  # type: ignore[index]
    stable_ref = repo_ref["stable_ref"]
    nodes.append(_node("Repository", repo_id, {
        "provider_id": repo_ref["provider_id"],
        "owner_name": repo_ref["owner_name"],
        "clone_url": repo_path,
        "stable_ref": stable_ref,
        "default_ref": repo_ref["default_ref"],
    }, tenant, snapshot_id, pulls_fx["source_system"], "github:payments:repo:901"))

    def commit_node(commit_label: str, info: Dict[str, Any]) -> str:
        sha = info["sha"]
        node_id = f"demo:git:payments:commit:{sha}"
        if any(n["id"] == node_id for n in nodes):
            return node_id
        nodes.append(_node("Commit", node_id, {
            "repository_id": repo_id,
            "sha": sha,
            "message": f"fixture commit {commit_label}",
            "committed_at": "2026-10-09T12:00:00Z",
            "history_complete": False,  # bounded imported history
        }, tenant, snapshot_id, "git-fixture", f"git:payments:commit:{commit_label}"))
        return node_id

    commits = git_manifest["commits"]  # type: ignore[index]
    commit_ids: Dict[str, str] = {}
    for label, info in commits.items():  # type: ignore[union-attr]
        node_id = commit_node(label, info)  # type: ignore[arg-type]
        commit_ids.setdefault(info["sha"], node_id)  # type: ignore[index]
    for label, info in commits.items():  # type: ignore[union-attr]
        parent_sha = info.get("parent")  # type: ignore[union-attr]
        if parent_sha:
            edges.append(_edge("PARENT", f"demo:git:payments:edge:parent:{label}",
                               commit_ids[info["sha"]], commit_ids[parent_sha], {}, tenant,
                               snapshot_id, "git-fixture",
                               f"git:payments:parent:{label}", link_method="API"))

    for branch in pulls_fx["branches"]:
        branch_id = branch["id"]
        head_symbol = branch["head_sha"]
        sha = resolve_git_revisions(head_symbol, git_manifest)
        label = sha[:7]
        nodes.append(_node("Branch", branch_id, {
            "repository_id": branch["repository_id"],
            "ref": branch["ref"],
            "head_sha": sha,
            "exists": branch["exists"],
            "is_protected": branch["is_protected"],
        }, tenant, snapshot_id, pulls_fx["source_system"], f"github:payments:branch:{branch['ref']}"))
        edges.append(_edge("HAS_BRANCH", f"demo:github:payments:edge:has_branch:{branch['ref']}",
                           repo_id, branch_id, {}, tenant, snapshot_id,
                           pulls_fx["source_system"], f"github:payments:has_branch:{branch['ref']}", link_method="API"))
        commit_ids.setdefault(f"head:{branch['ref']}", commit_ids[resolve_git_revisions(head_symbol, git_manifest)])
        head_commit_id = commit_ids[f"head:{branch['ref']}"]
        edges.append(_edge("HEAD_AT", f"demo:github:payments:edge:head_at:{branch['ref']}",
                           branch_id, head_commit_id, {}, tenant, snapshot_id,
                           pulls_fx["source_system"], f"github:payments:head:{branch['ref']}", link_method="API"))

    for pr in pulls_fx["pull_requests"]:
        pr_id = pr["id"]
        head_sha = resolve_git_revisions(pr["head_sha"], git_manifest)
        base_sha = resolve_git_revisions(pr["base_sha"], git_manifest)
        nodes.append(_node("PullRequest", pr_id, {
            "repository_id": pr["repository_id"],
            "head_repository_id": pr["head_repository_id"],
            "number": pr["number"],
            "title": pr["title"],
            "state": pr["state"],
            "draft": pr["draft"],
            "merged_at": pr["merged_at"],
            "merge_commit_sha": pr["merge_commit_sha"],
            "base_ref": pr["base_ref"],
            "head_ref": pr["head_ref"],
            "head_sha": head_sha,
            "base_sha": base_sha,
        }, tenant, snapshot_id, pulls_fx["source_system"], f"github:payments:pr:{pr['number']}"))
        # Branch HAS_PR (head branch) and PR TARGETS base branch, IN_REPOSITORY.
        head_branch_id = f"demo:github:payments:901:branch:{pr['head_ref'].split('refs/heads/')[1]}"
        base_branch_id = f"demo:github:payments:901:branch:{pr['base_ref'].split('refs/heads/')[1]}"
        edges.append(_edge("HAS_PR", f"demo:github:payments:edge:has_pr:{pr['number']}",
                           head_branch_id, pr_id, {}, tenant, snapshot_id,
                           pulls_fx["source_system"], f"github:payments:has_pr:{pr['number']}", link_method="API"))
        edges.append(_edge("TARGETS", f"demo:github:payments:edge:targets:{pr['number']}",
                           pr_id, base_branch_id, {}, tenant, snapshot_id,
                           pulls_fx["source_system"], f"github:payments:targets:{pr['number']}", link_method="API"))
        edges.append(_edge("IN_REPOSITORY", f"demo:github:payments:edge:in_repo:{pr['number']}",
                           pr_id, pr["repository_id"], {}, tenant, snapshot_id,
                           pulls_fx["source_system"], f"github:payments:in_repo:{pr['number']}", link_method="API"))

    # --- Epics/tasks/hierarchy/dependencies (Payments) --------------------------
    for epic in tasks_fx["epics"]:
        nodes.append(_node("Epic", epic["id"], {
            "project_id": epic["project_id"],
            "external_key": epic["external_key"],
            "title": epic["title"],
            "status": epic["status"],
            "raw_status": epic["raw_status"],
        }, tenant, snapshot_id, tasks_fx["source_system"], f"jira:payments:epic:{epic['external_key']}"))
    for task in tasks_fx["tasks"]:
        nodes.append(_node("Task", task["id"], {
            "project_id": task["project_id"],
            "external_key": task["external_key"],
            "title": task["title"],
            "work_item_type": task["work_item_type"],
            "status": task["status"],
            "raw_status": task["raw_status"],
            "priority": task.get("priority"),
            "assignee_ids": task["assignee_ids"],
            "repository_ids": task["repository_ids"],
        }, tenant, snapshot_id, tasks_fx["source_system"], f"jira:payments:{task['external_key']}"))
    for rel in tasks_fx["hierarchy"]:
        edges.append(_edge("HAS_TASK", rel["id"], rel["start_id"], rel["end_id"], {},
                           tenant, snapshot_id, tasks_fx["source_system"], rel["source_record_ref"], link_method="API"))
    for dep in tasks_fx["dependencies"]:
        edges.append(_edge("DEPENDS_ON", dep["id"], dep["start_id"], dep["end_id"],
                           {"dependency_kind": dep["dependency_kind"]},
                           tenant, snapshot_id, "relationship-manifest", dep["source_record_ref"]))

    # --- TLS tasks/epic ---------------------------------------------------------
    for epic in tls_tasks_fx["epics"]:
        nodes.append(_node("Epic", epic["id"], {
            "project_id": epic["project_id"],
            "external_key": epic["external_key"],
            "title": epic["title"],
            "status": epic["status"],
            "raw_status": epic["raw_status"],
        }, tenant, snapshot_id, tls_tasks_fx["source_system"], f"jira:tls:epic:{epic['external_key']}"))
    for task in tls_tasks_fx["tasks"]:
        nodes.append(_node("Task", task["id"], {
            "project_id": task["project_id"],
            "external_key": task["external_key"],
            "title": task["title"],
            "work_item_type": task["work_item_type"],
            "status": task["status"],
            "raw_status": task["raw_status"],
            "priority": task.get("priority"),
            "assignee_ids": task["assignee_ids"],
            "repository_ids": task["repository_ids"],
        }, tenant, snapshot_id, tls_tasks_fx["source_system"], f"jira:tls:{task['external_key']}"))
    for rel in tls_tasks_fx["hierarchy"]:
        edges.append(_edge("HAS_TASK", rel["id"], rel["start_id"], rel["end_id"], {},
                           tenant, snapshot_id, tls_tasks_fx["source_system"], rel["source_record_ref"], link_method="API"))
    for dep in tls_tasks_fx["dependencies"]:
        edges.append(_edge("DEPENDS_ON", dep["id"], dep["start_id"], dep["end_id"],
                           {"dependency_kind": dep["dependency_kind"]},
                           tenant, snapshot_id, "relationship-manifest", dep["source_record_ref"]))

    # --- Reviews -----------------------------------------------------------------
    for review in reviews_fx["reviews"]:
        review_id = review["id"]
        reviewed_sha = resolve_git_revisions(review["commit_sha"], git_manifest)
        nodes.append(_node("Review", review_id, {
            "provider_review_id": review["provider_review_id"],
            "reviewer_id": review["reviewer_id"],
            "state": review["state"],
            "submitted_at": review["submitted_at"],
            "commit_sha": reviewed_sha,
            "body_excerpt": review["body"][:200],
            "dismissal_type": review["dismissal_type"],
            "dismissal_reason": review["dismissal_reason"],
        }, tenant, snapshot_id, reviews_fx["source_system"], f"github:payments:review:{review['provider_review_id']}"))
        edges.append(_edge("REVIEWS", f"demo:github:payments:edge:reviews:{review['provider_review_id']}",
                           review_id, review["pull_request_id"], {}, tenant, snapshot_id,
                           reviews_fx["source_system"], f"github:payments:reviews:{review['provider_review_id']}", link_method="API"))
        edges.append(_edge("REVIEWED_COMMIT", f"demo:github:payments:edge:reviewed_commit:{review['provider_review_id']}",
                           review_id, f"demo:git:payments:commit:{reviewed_sha}", {}, tenant, snapshot_id,
                           reviews_fx["source_system"], f"github:payments:reviewed:{review['provider_review_id']}", link_method="API"))

    # --- Implementation / delivery links ------------------------------------------
    for link in links_fx["implementation_links"]:
        edges.append(_edge("IMPLEMENTED_IN" if link["end_id"].find("branch") >= 0 else "IMPLEMENTED_BY",
                           link["id"], link["start_id"], link["end_id"], {},
                           tenant, snapshot_id, "relationship-manifest", link["source_record_ref"],
                           link_method=link["link_method"], authority=link["authority"]))
    for delivery in links_fx["deliveries"]:
        revision = resolve_git_revisions(delivery["implementation_revision"], git_manifest)
        commit_id = f"demo:git:payments:commit:{revision}"
        edges.append(_edge("DELIVERED_BY", f"demo:payments:edge:delivered_by:{delivery['delivery_id']}",
                           delivery["task_id"], commit_id, {
                               "delivery_id": delivery["delivery_id"],
                               "role": delivery["role"],
                               "implementation_revision": revision,
                               "coverage": delivery["coverage"],
                               "pr_id": delivery.get("pr_id"),
                               "equivalent_to_delivery_id": None,
                           }, tenant, snapshot_id, "relationship-manifest",
                           f"manifest:payments:delivery:{delivery['delivery_id']}"))
    for effect in links_fx["revision_effects"]:
        pass  # advanced histories arrive in Phase 3

    # --- Documents (content stored separately; graph stores references) -----------
    from app.storage.documents import DocumentStore, content_hash
    doc_store = DocumentStore(WORKSPACE_ROOT / ".local" / "state" / "content")

    def document_nodes(doc_fx: Dict[str, Any], source_system: str) -> None:
        doc_id = doc_fx["id"]
        version = doc_fx["version"]
        stored = doc_store.register(
            document_id=doc_id,
            version=version,
            title=doc_fx["title"],
            document_type=doc_fx["document_type"],
            doc_status=doc_fx["doc_status"],
            sections=doc_fx["sections"],
            source_url=doc_fx.get("source_url"),
            source_record_ref=doc_fx["source_record_ref"],
            observed_at=OBSERVED_AT,
        )
        nodes.append(_node("Document", doc_id, {
            "title": doc_fx["title"],
            "document_type": doc_fx["document_type"],
            "version": version,
            "content_hash": stored["content_hash"],
            "content_path": stored["content_path"],
            "doc_status": doc_fx["doc_status"],
        }, tenant, snapshot_id, source_system, doc_fx["source_record_ref"]))
        # add subtype label via document_type (loader maps Document:DesignDoc)
        target_field = "specifies" if doc_fx["document_type"] == "DesignDoc" else "governs"
        edge_type = "SPECIFIES" if target_field == "specifies" else "GOVERNS_PROCESS"
        for task_id in doc_fx.get(target_field, []):
            edges.append(_edge(edge_type, f"demo:markdown:edge:{edge_type.lower()}:{doc_id.split(':')[-1]}:{task_id.split(':')[-1]}",
                               doc_id, task_id, {}, tenant, snapshot_id,
                               source_system, f"manifest:document:{doc_id}", link_method="MANIFEST"))

    for doc_fx in documents_fx["documents"]:
        document_nodes(doc_fx, documents_fx["source_system"])
    for doc_fx in tls_docs_fx["documents"]:
        document_nodes(doc_fx, tls_docs_fx["source_system"])
    for link in tls_links_fx["document_links"]:
        edges.append(_edge("GOVERNS_PROCESS", link["id"], link["start_id"], link["end_id"], {},
                           tenant, snapshot_id, "relationship-manifest", link["source_record_ref"],
                           link_method=link["link_method"], authority=link["authority"]))

    bundle = {
        "projection_id": "STRUCTURAL",
        "bundle_id": f"bundle-structural-{snapshot_id}",
        "snapshot_id": snapshot_id,
        "tenant_id": tenant,
        "label": "SYNTHETIC FIXTURE structural bundle",
        "source_scopes": [
            {"source": "jira-export", "scope": "payments+tls", "mode": "FIXTURE"},
            {"source": "github-snapshot", "scope": "payments", "mode": "FIXTURE"},
            {"source": "markdown-export", "scope": "payments+tls", "mode": "FIXTURE"},
            {"source": "relationship-manifest", "scope": "confirmed-mappings", "mode": "FIXTURE"},
        ],
        "coverage": {"payments": "COMPLETE", "tls": "COMPLETE"},
        "nodes": nodes,
        "edges": edges,
    }
    return bundle


def build_conversation_bundle(snapshot_id: str = "snap-conversations-001") -> Dict[str, Any]:
    """Normalize the synthetic Codex conversation fixtures into STRUCTURAL
    nodes/edges (Conversation, Message, DesignDecision) per codex_conversations.md."""
    expected = load_fixture("conversations", "expected.json")
    review_manifest = load_fixture("conversations", "review_manifest.json")

    tenant = expected["tenant_id"]
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []

    from app.storage.conversation_captures import ConversationCaptureStore
    store = ConversationCaptureStore(
        WORKSPACE_ROOT / ".local" / "state" / "conversations",
        WORKSPACE_ROOT / ".local" / "state" / "retained",
    )

    conversations: Dict[str, str] = {}
    capture_refs: Dict[str, Dict[str, Any]] = {}
    for source in expected["sources"]:
        source_key = source["source_key"]
        conversation_id = f"demo:codex:{source_key}"
        conversations[source_key] = conversation_id
        nodes.append(_node("Conversation", conversation_id, {
            "source_instance": expected["source_instance"],
            "native_session_id": source_key,
            "source_key": source_key,
            "source_epoch": 1,
            "project_ids": expected["bindings"]["project_ids"],
            "repository_ids": expected["bindings"]["repository_ids"],
            "title": f"Synthetic session {source_key}",
            "mode": "FIXTURE",
            "dialect": expected["dialect"],
            "producer_version": expected["dialect_version"],
            "parser_version": expected["parser_version"],
            "redaction_version": expected["redaction_version"],
        }, tenant, snapshot_id, "codex-fixture", f"codex:{source_key}"))

        # Persist the sanitized capture and bind graph message content to it.
        jsonl_path = FIXTURES_ROOT / "conversations" / source["file"]
        raw_lines = jsonl_path.read_text(encoding="utf-8").splitlines(keepends=True)
        messages: List[Dict[str, Any]] = []
        ordinal = 0
        for line_no, line in enumerate(raw_lines):
            complete_line = line.endswith("\n")
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                if complete_line:
                    raise ValueError(f"malformed complete JSONL line {line_no} in {source_key}")
                break  # partial tail: deferred, cursor does not advance past it
            if record.get("type") == "message":
                origin = {
                    "injected": "INJECTED_CONTEXT",
                }.get(str(record.get("origin_hint", "")), None)
                if origin is None:
                    if record.get("record_kind") == "compaction_summary":
                        origin = "ASSISTANT_VISIBLE"
                    else:
                        origin = "HUMAN_INPUT" if record.get("role") == "user" else "ASSISTANT_VISIBLE"
                messages.append({
                    "ordinal": ordinal,
                    "native_id": record.get("id"),
                    "role": "USER" if record.get("role") == "user" else "ASSISTANT",
                    "origin": origin,
                    "record_kind": record.get("record_kind"),
                    "source_timestamp": record.get("timestamp"),
                    "content": record.get("content"),
                })
                ordinal += 1
        capture_ref = store.write_capture(
            capture_id=f"capture-{source_key}-1",
            source_key=source_key,
            epoch=1,
            messages=messages,
            parser_version=expected["parser_version"],
            redaction_version=expected["redaction_version"],
            coverage=source["coverage"],
            limitations=["synthetic fixture; pending tail" if source["pending_tail"] else ""],
        )
        capture_refs[source_key] = capture_ref

        prev_message_id: Optional[str] = None
        for msg in messages:
            import hashlib

            message_id = f"demo:codex:{source_key}:msg:{msg['ordinal']}"
            content_hash_value = hashlib.sha256(
                str(msg["content"]).encode("utf-8")
            ).hexdigest()
            nodes.append(_node("Message", message_id, {
                "conversation_id": conversation_id,
                "native_id": msg["native_id"],
                "source_ordinal": msg["ordinal"],
                "sequence": msg["ordinal"],
                "role": msg["role"],
                "origin": msg["origin"],
                "record_kind": msg["record_kind"],
                "source_timestamp": msg["source_timestamp"],
                "content_hash": content_hash_value,
                "capture_id": capture_ref["capture_id"],
                "content_reference": capture_ref["content_reference"],
            }, tenant, snapshot_id, "codex-fixture", f"codex:{source_key}:msg:{msg['ordinal']}"))
            edges.append(_edge("HAS_MESSAGE", f"demo:codex:edge:has_message:{source_key}:{msg['ordinal']}",
                               conversation_id, message_id, {}, tenant, snapshot_id,
                               "codex-fixture", f"codex:{source_key}:has_message:{msg['ordinal']}", link_method="PARSED_EXPLICIT_REFERENCE"))
            if prev_message_id:
                edges.append(_edge("NEXT_MESSAGE", f"demo:codex:edge:next_message:{source_key}:{msg['ordinal']}",
                                   prev_message_id, message_id, {}, tenant, snapshot_id,
                                   "codex-fixture", f"codex:{source_key}:next:{msg['ordinal']}", link_method="PARSED_EXPLICIT_REFERENCE"))
            prev_message_id = message_id

        # Store the retained cursor (acknowledged only after READY by importer).
        store.save_cursor({
            "source_key": source_key,
            "source_epoch": 1,
            "complete_line_offset": len(raw_lines) if not source["pending_tail"] else len(raw_lines) - 1,
            "prefix_hash": capture_ref["content_hash"],
            "last_ordinal": ordinal - 1,
            "parser_version": expected["parser_version"],
            "redaction_version": expected["redaction_version"],
            "capture_id": capture_ref["capture_id"],
            "published_bundle_id": None,
        })

    # Design decisions from the reviewed manifest (titles from the
    # normalization expectations; status authority from the review manifest).
    decision_titles = {d["decision_key"]: d["title"] for d in expected["expected_decisions"]}
    decisions: Dict[str, str] = {}
    for entry in review_manifest["reviews"]:
        import hashlib

        decision_id = f"demo:codex:decision:{entry['decision_key']}"
        decisions[entry["decision_key"]] = decision_id
        title = decision_titles.get(entry["decision_key"], entry["decision_key"])
        revision_hash = hashlib.sha256(
            (entry["decision_key"] + title).encode("utf-8")
        ).hexdigest()
        nodes.append(_node("DesignDecision", decision_id, {
            "decision_key": entry["decision_key"],
            "revision_hash": revision_hash,
            "title": title,
            "status": entry["status"],
            "reviewer": entry["reviewer"],
            "reviewed_at": entry["reviewed_at"],
            "review_manifest_version": review_manifest["manifest_version"],
        }, tenant, snapshot_id, "codex-fixture", f"codex:decision:{entry['decision_key']}"))
        for support in entry["supporting_messages"]:
            source_key, ordinal = support.split(":")
            message_id = f"demo:codex:{source_key}:msg:{int(ordinal)}"
            edges.append(_edge("SUPPORTED_BY", f"demo:codex:edge:supported_by:{entry['decision_key']}:{support.replace(':', '-')}",
                               decision_id, message_id, {}, tenant, snapshot_id,
                               "codex-fixture", f"codex:supported_by:{entry['decision_key']}", link_method="MANIFEST"))
        for entity in entry["applicable_entities"]:
            edges.append(_edge("APPLIES_TO", f"demo:codex:edge:applies_to:{entry['decision_key']}:{entity.split(':')[-1]}",
                               decision_id, entity, {}, tenant, snapshot_id,
                               "codex-fixture", f"codex:applies:{entry['decision_key']}", link_method="MANIFEST"))
    for entry in review_manifest["reviews"]:
        if entry["status"] == "SUPERSEDED" and entry.get("replacement_decision_key"):
            edges.append(_edge("SUPERSEDES", f"demo:codex:edge:supersedes:{entry['decision_key']}",
                               decisions[entry["decision_key"]],
                               decisions[entry["replacement_decision_key"]], {}, tenant, snapshot_id,
                               "codex-fixture", f"codex:supersedes:{entry['decision_key']}", link_method="MANIFEST"))

    return {
        "projection_id": "STRUCTURAL",
        "bundle_id": f"bundle-structural-{snapshot_id}",
        "snapshot_id": snapshot_id,
        "tenant_id": tenant,
        "label": "SYNTHETIC FIXTURE conversation bundle",
        "source_scopes": [{"source": "codex-fixture", "scope": "synthetic sessions", "mode": "FIXTURE"}],
        "coverage": {"conversations": "COMPLETE"},
        "nodes": nodes,
        "edges": edges,
    }
