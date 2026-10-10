"""Template execution with read-set recording and overflow sentinels.

Every domain template runs through the read-only API, under shared-gate
admission for its declared projections. Readiness is re-checked while the
shared gates are held (an importer must not slip past the check), and the
request's per-projection `(generation, active_snapshot_id)` tokens are
captured under the same admission so later reads on this service are
validated against them (docs/design/phase_01_graph_and_fixtures.md).

`limit = budget + 1` runs a boundary row so a truncated result proves
incompleteness (it cannot establish absence/equivalence). Each execution is
recorded in the request's GraphReadSet with semantic fingerprints and the
source-scope coverage declared by the owning projections (READY is coherent
publication, not source completeness).
"""

from __future__ import annotations

import copy
from collections import deque
from typing import Any, Dict, List, Optional, Tuple

from app.graph.client import GraphClient
from app.graph.import_state import (
    GraphRecoveryRequiredError,
    read_import_state,
    try_admit_ordered,
)
from app.graph.read_sets import GraphReadSet
from app.graph.templates import TemplateRegistry, default_registry


class OverflowSentinelExceeded(RuntimeError):
    """Raised when a template returns its sentinel row (incomplete evidence)."""


class GraphSnapshotChanged(RuntimeError):
    """A required projection's token moved and the recorded read set is no
    longer provably equivalent under the new tokens (HTTP 503
    GRAPH_SNAPSHOT_CHANGED)."""


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
        # Per-projection token captured under shared admission for validated
        # reads: {"STRUCTURAL": (generation, active_snapshot_id), ...}.
        self._tokens: Optional[Dict[str, Tuple[Any, Any]]] = None
        # Earlier validated executions (template, params, entry fingerprint)
        # replayed inside a bounded comparison when a token moves.
        self._history: List[Dict[str, Any]] = []

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

        if not require_ready:
            return self._query_and_record(template_id, template, params, budget, coverage=None)

        # Exclusive publication blocks admission even before its DIRTY fence
        # is written. Never wait behind the publisher or query ungated state;
        # once admitted, recheck durable readiness while holding every gate.
        admission = try_admit_ordered(meta["projections"])
        if admission is None:
            raise GraphRecoveryRequiredError(
                "exclusive publication is active for a required projection; "
                "graph reads are blocked (GRAPH_RECOVERY_REQUIRED)"
            )
        with admission:
            states = {
                projection: read_import_state(self.client, projection)
                for projection in meta["projections"]
            }
            self._require_projections_ready(meta["projections"], states)
            # Recheck captured tokens for this batch of reads; a moved token
            # triggers a bounded semantic read-set comparison, never a silent
            # mix of changed earlier evidence with new reads.
            self._validate_tokens(meta["projections"], states)
            rows = self._query_rows(template_id, template, params, budget)
            overflow = len(rows) > budget
            if overflow:
                raise OverflowSentinelExceeded(
                    f"template {template_id!r} exceeded its {budget}-row budget; "
                    "truncated evidence cannot be used for decisions"
                )
            coverage = self._declared_coverage(meta, states, params)
            entry_hash = self.read_set.record(
                template_id,
                "1.0.0",
                params,
                rows,
                limit=budget,
                overflow=overflow,
                coverage=coverage,
            )
            # Replay history: deep-copied inputs, domain reads only.
            # - Deep copy: callers legitimately reuse and mutate list-valued
            #   parameters after the read (e.g. advancing frontier_ids to the
            #   next traversal batch); a shallow copy would let that mutation
            #   change the recorded replay scope, so replay after a token move
            #   would compare against the modified scope instead of the exact
            #   inputs originally fingerprinted and incorrectly raise
            #   GRAPH_SNAPSHOT_CHANGED.
            # - Domain reads only (templates declaring required projections):
            #   control-state reads (import_state_read) return generation,
            #   snapshot ID and publication timestamps as positional columns;
            #   dictionary-key transport filtering cannot strip positional
            #   columns, and that metadata legitimately moves on EVERY
            #   publication, so a control read can never replay equivalently
            #   across a token move and would reject unchanged domain
            #   evidence with GRAPH_SNAPSHOT_CHANGED.
            if meta["projections"]:
                self._history.append(
                    {
                        "template_id": template_id,
                        "params": copy.deepcopy(params),
                        "fingerprint": entry_hash,
                    }
                )
            return rows

    # -- internals ----------------------------------------------------------------
    def _query_rows(
        self, template_id: str, template: str, params: Dict[str, Any], budget: int,
    ) -> List[List[Any]]:
        if template_id == "epic_children":
            return self._epic_leaf_rows(template, params, budget)
        return self.client.ro_query(
            template, params, timeout_ms=self.client.settings.falkordb_query_timeout_ms
        )

    def _epic_leaf_rows(
        self, template: str, params: Dict[str, Any], budget: int,
    ) -> List[List[Any]]:
        """Expand each member once, keeping depth unbounded and pages bounded.

        Called inside the same projection admission as ordinary queries,
        including snapshot replay. Only the final eligible leaves become a
        read-set entry, so pagination never changes the semantic fingerprint.
        """
        pending = deque([params["epic_id"]])
        visited = {params["epic_id"]}
        leaves: List[List[Any]] = []
        while pending:
            frontier = [pending.popleft() for _ in range(min(budget, len(pending)))]
            after_id = None
            while True:
                rows = self.client.ro_query(
                    template,
                    {**params, "frontier_ids": frontier, "after_id": after_id,
                     "limit": budget + 1},
                    timeout_ms=self.client.settings.falkordb_query_timeout_ms,
                )
                for member_id, status, raw_status, has_live_children in rows:
                    if member_id in visited:
                        continue
                    visited.add(member_id)
                    if has_live_children:
                        # Cancelled ancestors still lead to eligible descendants.
                        pending.append(member_id)
                    elif status is not None and status != "CANCELLED":
                        leaves.append([member_id, status, raw_status])
                        if len(leaves) > budget:
                            # Let the caller apply the global leaf sentinel,
                            # including GraphSnapshotChanged during replay.
                            return sorted(leaves, key=lambda row: row[0])
                if len(rows) <= budget:
                    break
                # Consume the boundary row and continue after it; a wide
                # intermediate frontier must never hide deeper leaves.
                after_id = rows[-1][0]
        return sorted(leaves, key=lambda row: row[0])

    def _query_and_record(
        self,
        template_id: str,
        template: str,
        params: Dict[str, Any],
        budget: int,
        *,
        coverage: Any,
    ) -> List[List[Any]]:
        rows = self._query_rows(template_id, template, params, budget)
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
            coverage=coverage,
        )
        return rows

    @staticmethod
    def _token_of(state: Dict[str, Any]) -> Tuple[Any, Any]:
        return (state["generation"], state["active_snapshot_id"])

    def _require_projections_ready(
        self, projections: List[str], states: Dict[str, Dict[str, Any]]
    ) -> None:
        for projection in projections:
            state = states[projection]
            if state["state"] != "READY":
                raise GraphRecoveryRequiredError(
                    f"projection {projection} is {state['state']}; graph reads are blocked "
                    "(GRAPH_RECOVERY_REQUIRED)"
                )

    @staticmethod
    def _declared_coverage(
        meta: Dict[str, Any], states: Dict[str, Dict[str, Any]], params: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        """Hash authoritative coverage for the template's declared scope.

        Exact project lookups use the native scope in tenant:provider:scope
        IDs, including when no rows match. Missing coverage stays UNKNOWN.
        Templates that can traverse multiple source scopes retain their full
        projection coverage until they declare a narrower scope.
        """
        scope_id = params.get(meta.get("coverage_scope_param"))
        scope = None
        if isinstance(scope_id, str) and scope_id:
            parts = scope_id.split(":", 2)
            if len(parts) == 1:
                scope = scope_id
            elif len(parts) == 3 and parts[0] == params.get("tenant_id") and parts[1]:
                scope = parts[2] or None

        result = {}
        for projection in meta["projections"]:
            declared = dict(states[projection].get("coverage") or {})
            if scope is None:
                result[projection] = declared
                continue
            scoped = {key: declared[key] for key in (scope_id, scope) if key in declared}
            if not scoped:
                scoped = {scope: "UNKNOWN"}
            if "__unknown__" in declared:
                scoped["__unknown__"] = declared["__unknown__"]
            result[projection] = scoped
        return result

    def _validate_tokens(
        self, projections: List[str], states: Dict[str, Dict[str, Any]]
    ) -> None:
        observed: Dict[str, Tuple[Any, Any]] = {
            projection: self._token_of(states[projection]) for projection in projections
        }
        if self._tokens is None:
            self._tokens = observed
            return
        moved = sorted(
            projection
            for projection, token in observed.items()
            if self._tokens.get(projection) != token
        )
        if not moved:
            return
        # Bounded replay: re-run every earlier validated read under the gates
        # we are already holding and compare complete semantic fingerprints.
        # Equivalent evidence survives the moved token (unrelated import);
        # anything changed or unprovable is rejected as GRAPH_SNAPSHOT_CHANGED.
        # Replay fingerprints are computed in a temporary read set: the
        # request's original entries are the evidence observations of this
        # request and must not grow on validation, otherwise the overall
        # fingerprint would depend on how many unrelated publications
        # happened between reads instead of on the evidence itself.
        from app.graph.templates import TEMPLATE_INDEX

        for entry in self._history:
            replay_meta = TEMPLATE_INDEX[entry["template_id"]]
            replay_template = self.registry.get(entry["template_id"])
            replay_states = {
                projection: read_import_state(self.client, projection)
                for projection in replay_meta["projections"]
            }
            self._require_projections_ready(replay_meta["projections"], replay_states)
            budget = replay_meta["budget"]
            rows = self._query_rows(
                entry["template_id"], replay_template, entry["params"], budget,
            )
            overflow = len(rows) > budget
            if overflow:
                raise GraphSnapshotChanged(
                    f"projection(s) {moved} advanced while request {entry['template_id']!r} "
                    "was in progress, and the replay exceeds its row budget; "
                    "equivalence cannot be established (GRAPH_SNAPSHOT_CHANGED)"
                )
            scratch = GraphReadSet()
            fingerprint = scratch.record(
                entry["template_id"],
                "1.0.0",
                entry["params"],
                rows,
                limit=budget,
                overflow=overflow,
                coverage=self._declared_coverage(replay_meta, replay_states, entry["params"]),
            )
            if fingerprint != entry["fingerprint"]:
                raise GraphSnapshotChanged(
                    f"projection(s) {moved} advanced while request "
                    f"{entry['template_id']!r} was in progress and its read set "
                    "changed; retry the whole request (GRAPH_SNAPSHOT_CHANGED)"
                )
        # Advance the validation tokens: unchanged evidence is accepted and
        # later reads validate against the current generation.
        self._tokens.update(observed)
