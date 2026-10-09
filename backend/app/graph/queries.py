"""Template execution with read-set recording and overflow sentinels.

Every domain template runs through the read-only API, under shared-gate
admission for its declared projections, with `limit = budget + 1` so a
boundary row proves truncation (an incomplete result cannot establish
absence/equivalence). Each execution is recorded in the request's
GraphReadSet with semantic fingerprints.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.graph.client import GraphClient
from app.graph.import_state import GraphRecoveryRequiredError, admit_ordered, read_import_state
from app.graph.read_sets import GraphReadSet
from app.graph.templates import TemplateRegistry, default_registry


class OverflowSentinelExceeded(RuntimeError):
    """Raised when a template returns its sentinel row (incomplete evidence)."""


class GraphQueryService:
    def __init__(
        self,
        client: GraphClient,
        registry: Optional[TemplateRegistry] = None,
        read_set: Optional[GraphReadSet] = None,
    ) -> None:
        self.client = client
        self.registry = registry or default_registry()
        self.read_set = read_set or GraphReadSet()

    def execute(
        self,
        template_id: str,
        params: Dict[str, Any],
        *,
        require_ready: bool = True,
    ) -> List[List[Any]]:
        from app.graph.templates import TEMPLATE_INDEX

        meta = TEMPLATE_INDEX[template_id]
        template = self.registry.get(template_id)
        budget = meta["budget"]

        if require_ready:
            self._require_projections_ready(meta["projections"])
            with admit_ordered(meta["projections"]):
                rows = self.client.ro_query(template, params, timeout_ms=self.client.settings.falkordb_query_timeout_ms)
        else:
            rows = self.client.ro_query(template, params, timeout_ms=self.client.settings.falkordb_query_timeout_ms)

        overflow = len(rows) > budget
        if overflow:
            raise OverflowSentinelExceeded(
                f"template {template_id!r} exceeded its {budget}-row budget; "
                "truncated evidence cannot be used for decisions"
            )
        self.read_set.record(
            template_id,
            "1.0.0",
            params,
            rows,
            limit=budget,
            overflow=overflow,
        )
        return rows

    def _require_projections_ready(self, projections: List[str]) -> None:
        for projection in projections:
            state = read_import_state(self.client, projection)
            if state["state"] != "READY":
                raise GraphRecoveryRequiredError(
                    f"projection {projection} is {state['state']}; graph reads are blocked "
                    "(GRAPH_RECOVERY_REQUIRED)"
                )
