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


def canonical(value: Any) -> Any:
    """Canonicalize a row value for fingerprinting."""
    if hasattr(value, "properties"):  # FalkorDB Node/Edge objects
        props = dict(value.properties)
        props.setdefault("label_or_type", getattr(value, "label", None) or getattr(value, "type", None))
        return canonical(props)
    if isinstance(value, dict):
        return {str(k): canonical(v) for k, v in sorted(value.items())}
    if isinstance(value, (list, tuple)):
        return [canonical(v) for v in value]
    if isinstance(value, (int, float, str, bool)) or value is None:
        return value
    return str(value)


def semantic_hash(value: Any) -> str:
    payload = json.dumps(canonical(value), sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


TEMPLATE_TRANSPORT_KEYS = {"generation", "active_snapshot_id", "snapshot_id", "ingested_at"}


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
        coverage: str = "COMPLETE",
    ) -> str:
        entry = {
            "template_id": template_id,
            "template_version": template_version,
            "params": canonical(transport_free(params)),
            "rows": canonical(rows),
            "limit": limit,
            "overflow": overflow,
            "coverage": coverage,
        }
        self.entries.append(entry)
        return semantic_hash(entry)

    def fingerprint(self) -> str:
        return semantic_hash(self.entries)

    def to_dict(self) -> Dict[str, str]:
        return {"fingerprint": self.fingerprint(), "templates": str(len(self.entries))}
