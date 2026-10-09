"""Durable per-projection import protocol (Phase 1 snapshot consistency).

One application writer; per-projection durable `ImportState` in the shared
graph plus process-local shared/exclusive gates. Write durability is provided
by the pinned database's AOF with synchronous fsync (`appendfsync always`):
each acknowledged write command has been fsynced before the reply, so a
returned graph write is a durable acknowledgment. A process-local flag or
periodic backup is NOT used.

Protocol (phase_01_graph_and_fixtures.md "Snapshot consistency"):
  1. prepare + persist immutable bundle (hash) before mutation
  2. acquire projection gates in STRUCTURAL, INCIDENT order; recheck base tokens
  3. persist DIRTY + generation bump + pending bundle id/hash BEFORE first domain write
  4. write nodes, then edges; tombstone stale owned records
  5. validate topology/provenance/hashes
  6. one final graph write publishes snapshot + READY (generation not decreased)
  7. readback-verify durable state; release gates

Any failure after DIRTY leaves reads requiring that projection blocked until a
complete gated recovery rebuild; the flag is never merely cleared.
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config import get_settings
from app.core.ids import SHA_RE
from app.graph.schema import GraphValidationError, validate_bundle

logger = logging.getLogger(__name__)


class RecoveryRequired(RuntimeError):
    """Raised when a projection is DIRTY/uninitialized and needs recovery."""


class GraphRecoveryRequiredError(RecoveryRequired):
    """Domain-read analogue: HTTP 503 GRAPH_RECOVERY_REQUIRED."""


# ---------------------------------------------------------------------------
# Gates: process-local shared/exclusive per projection (Phase 7 replaces this
# with a multiworker-safe mechanism; single-writer durability is required now).
# ---------------------------------------------------------------------------
class _RWLock:
    def __init__(self) -> None:
        self._condition = threading.Condition()
        self._readers = 0
        self._writer = False

    def acquire_shared(self) -> None:
        with self._condition:
            while self._writer:
                self._condition.wait()
            self._readers += 1

    def release_shared(self) -> None:
        with self._condition:
            self._readers -= 1
            if self._readers == 0:
                self._condition.notify_all()

    def acquire_exclusive(self) -> None:
        with self._condition:
            while self._writer or self._readers:
                self._condition.wait()
            self._writer = True

    def release_exclusive(self) -> None:
        with self._condition:
            self._writer = False
            self._condition.notify_all()


class ProjectionGate:
    """Per-projection gate. `admit` wraps domain reads; `publish` wraps writes."""

    def __init__(self, projection_id: str) -> None:
        self.projection_id = projection_id
        self._lock = _RWLock()

    def admit(self) -> "_Shared":
        return _Shared(self._lock)

    def publish(self) -> "_Exclusive":
        return _Exclusive(self._lock)


class _Shared:
    def __init__(self, lock: _RWLock) -> None:
        self._lock = lock
        self.acquired = False

    def __enter__(self) -> "_Shared":
        self._lock.acquire_shared()
        self.acquired = True
        return self

    def __exit__(self, *exc: Any) -> None:
        if self.acquired:
            self._lock.release_shared()
            self.acquired = False


class _Exclusive:
    def __init__(self, lock: _RWLock) -> None:
        self._lock = lock
        self.acquired = False

    def __enter__(self) -> "_Exclusive":
        self._lock.acquire_exclusive()
        self.acquired = True
        return self

    def __exit__(self, *exc: Any) -> None:
        if self.acquired:
            self._lock.release_exclusive()
            self.acquired = False


_PROJECTIONS = ("STRUCTURAL", "INCIDENT")
_GATES: Dict[str, ProjectionGate] = {
    name: ProjectionGate(name) for name in _PROJECTIONS
}


def gates() -> Dict[str, ProjectionGate]:
    return _GATES


def admit_ordered(required: List[str]) -> "OrderedSharedAdmission":
    """Acquire shared gates in STRUCTURAL, INCIDENT order for a domain read."""
    return OrderedSharedAdmission([name for name in _PROJECTIONS if name in required])


class OrderedSharedAdmission:
    def __init__(self, ordered: List[str]) -> None:
        self._ordered = ordered
        self._shared: List[_Shared] = []

    def __enter__(self) -> "OrderedSharedAdmission":
        for name in self._ordered:
            shared = _GATES[name].admit()
            shared.__enter__()
            self._shared.append(shared)
        return self

    def __exit__(self, *exc: Any) -> None:
        for shared in reversed(self._shared):
            shared.__exit__(None, None, None)
        self._shared = []


def publish_gates(affected: List[str]) -> "ExclusiveGateSet":
    """Acquire exclusive publication gates in canonical order."""
    ordered = [name for name in _PROJECTIONS if name in affected]
    if set(ordered) != set(affected):
        raise ValueError(f"unknown projections in {affected}")
    return ExclusiveGateSet(ordered)


class ExclusiveGateSet:
    def __init__(self, ordered: List[str]) -> None:
        self._ordered = ordered
        self._exclusive: List[_Exclusive] = []

    def __enter__(self) -> "ExclusiveGateSet":
        for name in self._ordered:
            excl = _GATES[name].publish()
            excl.__enter__()
            self._exclusive.append(excl)
        return self

    def __exit__(self, *exc: Any) -> None:
        for excl in reversed(self._exclusive):
            excl.__exit__(None, None, None)
        self._exclusive = []


# ---------------------------------------------------------------------------
# Durable ImportState persisted in the shared graph (control records outside
# domain traversal). Reads use ro_query; writes only from the loader/operator.
# ---------------------------------------------------------------------------
STATE_UPSERT = """
MERGE (c:ImportControl {graph_name: $graph_name, projection_id: $projection_id})
SET c.state = $state,
    c.generation = $generation,
    c.active_snapshot_id = $active_snapshot_id,
    c.pending_bundle_id = $pending_bundle_id,
    c.pending_bundle_hash = $pending_bundle_hash,
    c.published_log_position = $published_log_position,
    c.last_published_at = $last_published_at,
    c.updated_at = $updated_at,
    c.last_failure = $last_failure
RETURN c.generation AS generation, c.state AS state
"""

STATE_READ = """
MATCH (c:ImportControl {graph_name: $graph_name, projection_id: $projection_id})
RETURN c.state AS state, c.generation AS generation,
       c.active_snapshot_id AS active_snapshot_id,
       c.pending_bundle_id AS pending_bundle_id,
       c.pending_bundle_hash AS pending_bundle_hash,
       c.last_published_at AS last_published_at,
       c.updated_at AS updated_at,
       c.last_failure AS last_failure
"""


def read_import_state(
    client: Any, projection_id: str, graph_name: Optional[str] = None
) -> Dict[str, Any]:
    """Durable state readback. Missing/unreadable state = UNINITIALIZED."""
    from app.config import get_settings

    graph = client.select_graph(graph_name)
    settings = get_settings()
    rows = client.ro_query(
        STATE_READ, {"graph_name": settings.falkordb_graph_name, "projection_id": projection_id}
    )
    if not rows:
        return {
            "projection_id": projection_id,
            "state": "UNINITIALIZED",
            "generation": 0,
            "active_snapshot_id": None,
            "pending_bundle_id": None,
            "pending_bundle_hash": None,
            "last_published_at": None,
            "updated_at": None,
            "last_failure": None,
        }
    row = rows[0]
    return {
        "projection_id": projection_id,
        "state": str(row[0]),
        "generation": int(row[1]),
        "active_snapshot_id": row[2],
        "pending_bundle_id": row[3],
        "pending_bundle_hash": row[4],
        "last_published_at": row[5],
        "updated_at": row[6],
        "last_failure": row[7],
    }


def _now() -> datetime:
    return datetime.now(timezone.utc)


class BundleStore:
    """Immutable retained bundles under `.local/state/bundles/<projection>/`.

    Bundle IDs are allocated as their future snapshot IDs; the manifest and
    content are durably flushed before DIRTY publication.
    """

    def __init__(self, root: Optional[Path] = None) -> None:
        self.root = root or get_settings().bundles_root

    def _path(self, projection_id: str, bundle_id: str) -> Path:
        return self.root / projection_id / f"{bundle_id}.json"

    def persist(self, bundle: Dict[str, Any]) -> str:
        import hashlib

        bundle_id = bundle["bundle_id"]
        projection = bundle["projection_id"]
        path = self._path(projection, bundle_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(bundle, sort_keys=True, separators=(",", ":"))
        # Write then fsync the manifest file for durable flush.
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(payload)
            fh.flush()
            import os

            os.fsync(fh.fileno())
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return digest

    def load(self, projection_id: str, bundle_id: str) -> Optional[Dict[str, Any]]:
        path = self._path(projection_id, bundle_id)
        if not path.is_file():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return data

    def hash_of(self, projection_id: str, bundle_id: str) -> Optional[str]:
        path = self._path(projection_id, bundle_id)
        if not path.is_file():
            return None
        import hashlib

        payload = path.read_bytes()
        return hashlib.sha256(payload).hexdigest()

    def exists(self, projection_id: str, bundle_id: str) -> bool:
        return self._path(projection_id, bundle_id).is_file()


class PublicationGateProtocol:
    """Loader-side durable publication implementing the snapshot protocol."""

    def __init__(
        self,
        client: Any,
        bundle_store: Optional[BundleStore] = None,
        fail_after: Optional[str] = None,
    ) -> None:
        """`fail_after` injects failures for restart/durability tests:
        'after_prepare' | 'after_dirty' | 'after_nodes' | 'after_edges' |
        'before_publication'."""
        self.client = client
        self.bundles = bundle_store or BundleStore()
        self.fail_after = fail_after

    # -- protocol steps -------------------------------------------------------
    def publish(self, bundle: Dict[str, Any]) -> Dict[str, Any]:
        validate_bundle(bundle)
        projection = bundle["projection_id"]
        snapshot_id = bundle["snapshot_id"]

        # 1. Persist the immutable bundle first; preparation failure leaves the
        #    previous snapshot readable at its original age.
        bundle_hash = self.bundles.persist(bundle)
        if self.fail_after == "after_prepare":
            raise RuntimeError("injected failure after bundle preparation")

        affected = [projection]
        # Coordinated cross-projection updates mark every affected projection.
        with publish_gates(affected):
            state = read_import_state(self.client, projection)
            if state["state"] == "DIRTY":
                raise RecoveryRequired(
                    f"{projection} is DIRTY; run recovery before publishing"
                )
            previous_generation = int(state["generation"])
            previous_snapshot = state["active_snapshot_id"]

            # 3. DIRTY before the first domain write; generation is a fence.
            generation = previous_generation + 1
            self._write_control(
                projection,
                state="DIRTY",
                generation=generation,
                active_snapshot_id=state["active_snapshot_id"],
                pending_bundle_id=bundle["bundle_id"],
                pending_bundle_hash=bundle_hash,
            )
            if self.fail_after == "after_dirty":
                raise RuntimeError("injected failure after DIRTY publication")

            # 4. Mutate: nodes before edges, then tombstones of stale records.
            self._write_nodes(bundle)
            if self.fail_after == "after_nodes":
                raise RuntimeError("injected failure after node writes")
            self._write_edges(bundle)
            self._tombstone_stale_edges(bundle)
            if self.fail_after == "after_edges":
                raise RuntimeError("injected failure after edge writes")
            self._tombstone_stale(bundle)
            if self.fail_after == "before_publication":
                raise RuntimeError("injected failure before READY publication")

            # 5. Validate topology after mutation (cheap readback checks).
            self._validate_published_topology(bundle)

            # 6. One final graph write publishes snapshot + READY. Generation
            #    never decreases.
            published_at = _now().isoformat()
            self._write_control(
                projection,
                state="READY",
                generation=generation,
                active_snapshot_id=snapshot_id,
                pending_bundle_id=None,
                pending_bundle_hash=None,
                last_published_at=published_at,
            )

            # 7. Durable readback acknowledgment before releasing the gate.
            ack = read_import_state(self.client, projection)
            if ack["state"] != "READY" or ack["active_snapshot_id"] != snapshot_id:
                raise RecoveryRequired(
                    f"publication acknowledgment mismatch for {projection}: {ack}"
                )

        return {
            "projection_id": projection,
            "bundle_id": bundle["bundle_id"],
            "bundle_hash": bundle_hash,
            "previous_snapshot_id": previous_snapshot,
            "published_snapshot_id": snapshot_id,
            "generation": generation,
            "outcome": "PUBLISHED",
        }

    def recover(self, projection: str, operator: str = "operator") -> Dict[str, Any]:
        """Gated recovery: complete affected-projection rebuild from the
        retained bundle with a new generation. Never merely clears the flag."""
        state = read_import_state(self.client, projection)
        if state["state"] == "READY":
            return {"projection_id": projection, "outcome": "NO_RECOVERY_REQUIRED"}
        if state["state"] == "UNINITIALIZED":
            raise RecoveryRequired(
                f"{projection} is UNINITIALIZED with no active snapshot; "
                "operator must publish a full validated bundle"
            )
        bundle_id = state.get("pending_bundle_id")
        if not bundle_id:
            raise RecoveryRequired(f"{projection} DIRTY without pending bundle id")
        bundle = self.bundles.load(projection, bundle_id)
        if bundle is None:
            raise RecoveryRequired(
                f"retained bundle {bundle_id!r} missing for {projection}; "
                "a new validated full bundle is required "
                "(pass it to recover_with_bundle)"
            )
        stored_hash = state.get("pending_bundle_hash")
        actual_hash = self.bundles.hash_of(projection, bundle_id)
        if stored_hash and actual_hash and stored_hash != actual_hash:
            raise RecoveryRequired(
                f"retained bundle {bundle_id!r} hash mismatch for {projection}"
            )
        return self._gated_rebuild(projection, bundle, state, operator=operator)

    def recover_with_bundle(
        self, projection: str, bundle: Dict[str, Any], operator: str = "operator"
    ) -> Dict[str, Any]:
        """Recovery from a NEW validated full bundle when the retained bundle
        is missing/invalid (operator path)."""
        validate_bundle(bundle)
        bundle_hash = self.bundles.persist(bundle)
        state = read_import_state(self.client, projection)
        if state["state"] == "READY":
            return {"projection_id": projection, "outcome": "NO_RECOVERY_REQUIRED"}
        return self._gated_rebuild(
            projection, bundle, state, bundle_hash=bundle_hash, operator=operator
        )

    def _gated_rebuild(
        self,
        projection: str,
        bundle: Dict[str, Any],
        state: Dict[str, Any],
        bundle_hash: Optional[str] = None,
        operator: str = "operator",
    ) -> Dict[str, Any]:
        if bundle_hash is None:
            bundle_hash = self.bundles.hash_of(projection, bundle["bundle_id"])
        bundle_id = bundle["bundle_id"]
        logger.info("recovering projection %s from retained bundle %s (%s)", projection, bundle_id, operator)

        with publish_gates([projection]):
            generation = int(state["generation"]) + 1
            self._write_control(
                projection,
                state="DIRTY",
                generation=generation,
                active_snapshot_id=None,
                pending_bundle_id=bundle_id,
                pending_bundle_hash=bundle_hash,
            )
            # Full affected-projection rebuild: clear owned records, re-upsert.
            self._clear_owned(projection)
            self._write_nodes(bundle)
            self._write_edges(bundle)
            self._tombstone_stale_edges(bundle)
            self._tombstone_stale(bundle)
            self._validate_published_topology(bundle)
            published_at = _now().isoformat()
            self._write_control(
                projection,
                state="READY",
                generation=generation,
                active_snapshot_id=bundle["snapshot_id"],
                pending_bundle_id=None,
                pending_bundle_hash=None,
                last_published_at=published_at,
            )
            ack = read_import_state(self.client, projection)
            if ack["state"] != "READY":
                raise RecoveryRequired(f"recovery acknowledgment mismatch for {projection}")
        return {
            "projection_id": projection,
            "outcome": "RECOVERED",
            "bundle_id": bundle_id,
            "generation": generation,
            "published_snapshot_id": bundle["snapshot_id"],
        }

    # -- internals --------------------------------------------------------------
    def _write_control(
        self,
        projection: str,
        *,
        state: str,
        generation: int,
        active_snapshot_id: Optional[str],
        pending_bundle_id: Optional[str],
        pending_bundle_hash: Optional[str],
        last_published_at: Optional[str] = None,
    ) -> None:
        settings = get_settings()
        self.client.query(
            STATE_UPSERT,
            {
                "graph_name": settings.falkordb_graph_name,
                "projection_id": projection,
                "state": state,
                "generation": generation,
                "active_snapshot_id": active_snapshot_id,
                "pending_bundle_id": pending_bundle_id,
                "pending_bundle_hash": pending_bundle_hash,
                "published_log_position": None,
                "last_published_at": last_published_at,
                "updated_at": _now().isoformat(),
                "last_failure": None,
            },
        )

    def _write_nodes(self, bundle: Dict[str, Any]) -> None:
        for node in bundle["nodes"]:
            props: Dict[str, Any] = {k: v for k, v in node.items() if k != "label"}
            props["label"] = node["label"]  # keep for SET-based upsert
            set_clause = ", ".join(f"n.{k} = ${k}" for k in props if k not in ("label", "id"))
            # Upsert by application-owned ID; extra labels appended below.
            extra = node["label"]
            if node["label"] in ("Document",):
                subtype = node.get("document_type")
                if subtype in ("DesignDoc", "ProcessDoc"):
                    extra = f"Document:{subtype}"
            self.client.query(
                f"""
                MERGE (n:{extra} {{id: $id}})
                SET {set_clause or 'n.id = $id'}
                """,
                props,
            )

    def _write_edges(self, bundle: Dict[str, Any]) -> None:
        """Upsert edges by application-owned ID. DELETE-then-CREATE handles
        endpoint changes under a stable ID (relationship endpoints cannot be
        updated in place)."""
        for edge in bundle["edges"]:
            props = {k: v for k, v in edge.items() if k not in ("type", "start_id", "end_id")}
            self.client.query(
                f"""
                MATCH (a {{id: $start_id}}), (b {{id: $end_id}})
                OPTIONAL MATCH (a)-[old:{edge['type']} {{id: $id}}]->()
                DELETE old
                CREATE (a)-[r:{edge['type']} {{id: $id}}]->(b)
                SET r = $props
                """,
                {
                    "start_id": edge["start_id"],
                    "end_id": edge["end_id"],
                    "id": edge["id"],
                    "props": props,
                },
            )

    def _tombstone_stale(self, bundle: Dict[str, Any]) -> None:
        """Retire records owned by this projection that the bundle no longer
        contains. Tombstones preserve identity for retained links; they never
        create placeholder records that look verified."""
        keep_ids = [n["id"] for n in bundle["nodes"]]
        self.client.query(
            """
            MATCH (n)
            WHERE n.projection_owner = $projection
              AND n.graph_name IS NULL
              AND coalesce(n.is_deleted, false) = false
              AND NOT n.id IN $keep_ids
            SET n.is_deleted = true, n.tombstoned_at = $snapshot_id
            """,
            {
                "projection": bundle["projection_id"],
                "keep_ids": keep_ids,
                "snapshot_id": bundle["snapshot_id"],
            },
        )

    def _tombstone_stale_edges(self, bundle: Dict[str, Any]) -> None:
        """Retire relationships owned by this projection that the bundle no
        longer contains (e.g. an old active HEAD_AT after a head update)."""
        keep_ids = [e["id"] for e in bundle["edges"]]
        self.client.query(
            """
            MATCH ()-[r]->()
            WHERE r.projection_owner = $projection
              AND r.graph_name IS NULL
              AND coalesce(r.is_deleted, false) = false
              AND NOT r.id IN $keep_ids
            SET r.is_deleted = true, r.tombstoned_at = $snapshot_id
            """,
            {
                "projection": bundle["projection_id"],
                "keep_ids": keep_ids,
                "snapshot_id": bundle["snapshot_id"],
            },
        )

    def _clear_owned(self, projection: str) -> None:
        """Recovery rebuild prelude: tombstone everything owned by the
        projection, then re-upsert from the retained bundle (which restores
        is_deleted=false on live records)."""
        self.client.query(
            """
            MATCH (n)
            WHERE n.projection_owner = $projection
              AND n.graph_name IS NULL
              AND coalesce(n.is_deleted, false) = false
            SET n.is_deleted = true
            """,
            {"projection": projection},
        )

    def _validate_published_topology(self, bundle: Dict[str, Any]) -> None:
        from app.config import get_settings

        settings = get_settings()
        # Active head uniqueness across the graph for confirmed HEAD_AT.
        # FalkorDB (pinned v4.20.7) does not support HAVING; counts are
        # checked in application code.
        rows = self.client.ro_query(
            """
            MATCH (b:Branch)-[r:HEAD_AT]->(c:Commit)
            WHERE r.is_deleted = false AND r.authority = 'CONFIRMED'
              AND b.tenant_id = $tenant
            RETURN b.id, count(r) AS cnt
            ORDER BY b.id
            LIMIT 201
            """,
            {"tenant": settings.tenant_id},
        )
        multiple = [row[0] for row in rows if int(row[1]) > 1]
        if multiple:
            raise GraphValidationError(f"multiple active HEAD_AT edges for {multiple}")
        rows = self.client.ro_query(
            """
            MATCH (p:PullRequest)-[r:TARGETS]->(b:Branch)
            WHERE r.is_deleted = false AND r.authority = 'CONFIRMED'
              AND p.tenant_id = $tenant
            RETURN p.id, count(r) AS cnt
            ORDER BY p.id
            LIMIT 201
            """,
            {"tenant": settings.tenant_id},
        )
        multiple = [row[0] for row in rows if int(row[1]) > 1]
        if multiple:
            raise GraphValidationError(f"PRs target multiple branches: {multiple}")

    # -- index management --------------------------------------------------------
    def create_indexes(self, labels_and_fields: List[tuple]) -> List[str]:
        """Create indexes supported by the pinned database (not Neo4j syntax).
        Returns the successfully created index descriptions."""
        created = []
        for label, field in labels_and_fields:
            try:
                self.client.query(
                    f"CREATE INDEX FOR (n:{label}) ON (n.{field})",
                    {},
                )
                created.append(f"{label}.{field}")
            except Exception as exc:  # already exists / unsupported
                message = str(exc)
                if "already indexed" in message or "An equivalent index" in message:
                    created.append(f"{label}.{field} (existing)")
                else:
                    logger.warning("index %s.%s not created: %s", label, field, exc)
        return created
