"""GraphReadSet recording and fingerprinting.

Template fingerprints cover ALL rows and relationship evidence within the
declared bound (not just cited nodes), canonical ordering, application IDs
only, coverage/completeness metadata and empty-result scope. Transport-only
metadata (generation, snapshot ID, ingestion time) is excluded, so unrelated
publications preserve equivalent read sets while added prerequisites, epic
members, effects or negative results change the fingerprint.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional

#: Materialization/transport metadata that must never contribute to a
#: semantic fingerprint (graph_publication.md #request-read-set).
TEMPLATE_TRANSPORT_KEYS = {"generation", "active_snapshot_id", "snapshot_id", "ingested_at"}


def canonical(value: Any) -> Any:
    """Canonicalize a row value for fingerprinting.

    Transport-only materialization metadata (projection generation, snapshot
    IDs, ingestion time) is excluded wherever it appears — top-level
    parameters and node/relationship properties alike — so unrelated
    publications preserve equivalent read sets (docs/design/
    graph_publication.md #request-read-set)."""
    if hasattr(value, "properties"):  # FalkorDB Node/Edge objects
        props = dict(value.properties)
        props.setdefault("label_or_type", getattr(value, "label", None) or getattr(value, "type", None))
        return canonical(props)
    if isinstance(value, dict):
        return {
            str(k): canonical(v)
            for k, v in sorted(value.items())
            if k not in TEMPLATE_TRANSPORT_KEYS
        }
    if isinstance(value, (list, tuple)):
        return [canonical(v) for v in value]
    if isinstance(value, (int, float, str, bool)) or value is None:
        return value
    return str(value)


def _row_order_key(row: Any) -> str:
    """Stable sort key over serialized value (documented ordering in
    graph_publication.md #request-read-set: canonical ordering, application
    IDs, never incidental row order)."""
    return json.dumps(_row_order_key_value(row), sort_keys=True, separators=(",", ":"), default=str)


def _row_order_key_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(k): _row_order_key_value(v)
            for k, v in sorted(value.items())
            if k not in TEMPLATE_TRANSPORT_KEYS
        }
    if isinstance(value, (list, tuple)):
        return [_row_order_key_value(v) for v in value]
    return value


def canonicalize_rows(rows: List[Any]) -> List[Any]:
    """Canonicalize a query result for fingerprinting.

    - Rows are order-insensitive membership: result row order depends on
      execution/relationship recreation, so rows are sorted by canonical key.
    - Within a row, column order matters (template schema), but nested lists
      collected inside a column (DISTINCT aggregates, relationship-id
      membership) are unordered membership and are canonicalized too.
    """
    if not isinstance(rows, list):
        return canonical(rows)
    canonicalized = [_canonical_row(row) for row in rows]
    return sorted(canonicalized, key=_row_order_key)


def _canonical_row(row: Any) -> Any:
    if isinstance(row, list):
        return [_canonical_unordered(value) for value in row]
    return _canonical_unordered(row)


def _canonical_unordered(value: Any) -> Any:
    if isinstance(value, list):
        items = [_canonical_unordered(item) for item in value]
        return sorted(items, key=_row_order_key)
    if isinstance(value, dict):
        # Transport-only metadata (generation, snapshot IDs, ingestion time) is
        # stripped BEFORE row and nested-membership sort keys are computed:
        # sorting on values that still carry it would let a generation change
        # reverse the sorted order of semantically identical records and
        # produce a different fingerprint for identical semantic content.
        return {
            str(k): _canonical_unordered(v)
            for k, v in sorted(value.items())
            if k not in TEMPLATE_TRANSPORT_KEYS
        }
    return canonical(value)


def semantic_hash(value: Any) -> str:
    payload = json.dumps(canonical(value), sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def transport_free(params: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in params.items() if k not in TEMPLATE_TRANSPORT_KEYS}


class GraphReadSet:
    """Accumulates per-template semantic fingerprints for one request."""

    def __init__(self) -> None:
        self.entries: List[Dict[str, Any]] = []

    def record(
        self,
        template_id: str,
        template_version: str,
        params: Dict[str, Any],
        rows: List[Any],
        *,
        limit: Optional[int] = None,
        overflow: bool = False,
        coverage: Any = "COMPLETE",
    ) -> str:
        # Publication recreates relationships and several templates have no
        # deterministic row ordering, so canonicalize unordered membership
        # before fingerprinting: an unrelated import must not invalidate
        # equivalent evidence by changing incidental row order.
        entry = {
            "template_id": template_id,
            "template_version": template_version,
            "params": canonical(transport_free(params)),
            "rows": canonicalize_rows(rows),
            "limit": limit,
            "overflow": overflow,
            "coverage": canonical(coverage),
        }
        self.entries.append(entry)
        return semantic_hash(entry)

    def fingerprint(self) -> str:
        return semantic_hash(self.entries)

    def to_dict(self) -> Dict[str, str]:
        return {"fingerprint": self.fingerprint(), "templates": str(len(self.entries))}
