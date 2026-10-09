# Phase 1: graph schema, fixtures and query templates

Status: planned. Depends on Phase 0. Original sprint timebox: 4 hours, provisional pending recovery and live-adapter implementation estimates.

## Outcome

FalkorDB contains an inspectable Payments/TLS graph with provenance and repeatable imports. Scoped read queries recover the exact relationships needed for branch and document workflows.

## Proposed files

```text
backend/app/graph/{client,schema,loader,queries}.py
backend/app/graph/import_state.py
backend/app/graph/templates/*.cypher
backend/app/storage/documents.py
scripts/seed_graph.py
tests/integration/test_graph_queries.py
tests/integration/test_graph_loader.py
```

Use the [canonical schema](graph_schema.md); do not invent a separate demo ontology. Individual `Review` and `Commit` nodes are required. `CheckRun` is optional in the sprint. Resolve symbolic fixture revisions through the Phase 0 Git builder before ingestion; graph commits use real full SHAs. Live branch verification is implemented in Phase 3.

## Coding sequence

1. Connect using the pinned FalkorDB client and implement separate read/write methods. Reads use the database's read-only query API; writes are only reachable from ingestion/operator paths.
2. Validate normalized nodes and edge endpoints. Reject duplicate logical IDs and invalid cross-tenant links before writes. Enforce one active branch head and one active PR target; a current review is not flattened into an unversioned string.
3. Create indexes supported by the pinned database on IDs, scoped task keys and relevant lookup fields. Do not assume Neo4j index/constraint syntax is compatible.
4. Implement the durable import protocol below before exposing logical-ID upserts. Write nodes before edges; preserve source ownership and tombstone removed associations. Do not create placeholder nodes that look verified.
5. Store document content separately with content hash, version and section anchors; store graph references. Populate real TLS runbook steps in the synthetic fixture, not just its title.
6. Add templates for exact task lookup, epic children, one dependency frontier, task delivery groups and revision effects, implementation PR/branch links, current documents, individual reviews and candidate heads.
7. Load fixtures and inspect graph topology in FalkorDB Browser. Verify the direction of `DEPENDS_ON` and incoming document edges against the schema.

## Snapshot consistency

The prototype uses one application process, a shared read/write gate, and a durable `ImportState` control record per managed graph. A published snapshot ID alone does not protect records overwritten by an interrupted import. The [contracts](contracts.md) define states, generation and errors.

1. Fetch and normalize sources without changing the graph. Validate logical identities, endpoint types, manifests, ownership and content references. Persist an immutable full rebuild bundle with its hash, source observations, tombstones, coverage declarations and document bytes before graph mutation. Allocate the bundle ID as its future snapshot ID so the published marker resolves to that retained bundle after pending fields are cleared. Durably flush the bundle manifest and content before dirty publication. A targeted refresh reconciles into the full retained bundle; it cannot replace other source scopes with an empty dataset. Never overwrite versioned document content referenced by previous evidence.
2. Acquire the exclusive graph gate. Recheck that the prepared bundle was reconciled against the current generation; reject or reconcile again if another import won. Persist `DIRTY`, increment `generation`, and record the pending bundle ID/hash before the first domain write. Continue only after durable acknowledgment. Configure and verify write durability on the pinned database (for example, persistent AOF with synchronous fsync); a process-local flag or periodic backup is insufficient.
3. Rebuild the complete managed graph projection from the retained bundle, using logical-ID upserts, removing stale records and restoring all active relationships. Delete/reconcile only application-managed domain records; the import-control record is excluded. Durable source receipts, incident lifecycle/action audit records and operator confirmations live in separate retained storage and contribute to the bundle when projected into the graph.
4. Check topology, active-head/target uniqueness, provenance, snapshot IDs and content hashes. In one final graph write, publish `active_snapshot_id`, clear pending fields, and set `READY` without decreasing the generation. Confirm durable acknowledgment before releasing the gate or admitting readers. `READY` means coherent publication; source completeness remains a separate coverage field.
5. Any failure after dirty-state publication leaves reads blocked. On application or database restart, inspect durable state before serving queries; missing, unreadable or `DIRTY` state requires recovery. Recovery uses the same exclusive path and repeats a complete rebuild from the retained bundle with a new generation. It never just clears the flag or assumes the old marker still describes the overwritten records. If the bundle is missing or invalid, require a new validated full bundle and remain blocked.

Initial seeding follows the same protocol; no active snapshot is readable until publication succeeds. A failure during preparation leaves the prior snapshot readable at its original observation age. After mutation begins, the prior marker is audit metadata only. An ambiguous write acknowledgment blocks reads until durable state can be reconciled; startup verifies the published bundle/snapshot before readiness.

Application reads use nonblocking shared-gate admission and require `READY`, capturing `(generation, active_snapshot_id)`. An exclusive import/recovery in progress refuses ordinary read admission with HTTP 503 `GRAPH_RECOVERY_REQUIRED`; readers do not wait indefinitely for a rebuild. All traversal, document selection, direct/MCP graph reads and caches retain that token. Recheck it for subsequent read batches and before response publication under the shared gate; discard mismatched evidence and retry the whole request once within its budget. A dirty or missing state returns HTTP 503 `GRAPH_RECOVERY_REQUIRED`; a repeated change while ready returns HTTP 503 `GRAPH_SNAPSHOT_CHANGED`. No decision or command is returned with either error. Do not hold the graph gate during provider or LLM network calls.

`/health` remains available; `/ready` fails during import/recovery. Operator import/recovery and state inspection are permitted while ordinary reads are blocked. This protocol deliberately pauses read availability and does not promise rollback to the old snapshot. Phase 7 replaces the process-local gate for multiworker operation; durable recovery is required now. Live verification additionally records the actual SHAs/times observed.

## Required query behavior

- A scoped task key returns zero/one result; duplicate matches become a data conflict.
- Dependency reads return explicit edge properties, not only destination names.
- Document retrieval retains version, type and source references.
- Review retrieval retains reviewed SHA and provider state, including dismissal.
- Frontier/row limits use a sentinel to detect overflow; truncation produces incomplete evidence.
- Empty results distinguish no known relationships from incomplete ingestion via coverage metadata.

## Validation and completion gate

Run database integration tests against the pinned image, not only an in-memory substitute. Loading the same fixture twice leaves node/edge counts and active relationships unchanged. Updating a head retires its old active edge. Exact lookup, dependency, document and review queries return expected IDs/evidence. Tenant-filter tests return no foreign nodes. Read templates reject attempted mutations through the read-only interface.

Inject failure halfway through node upserts, after nodes/before edges, and immediately before publication. Restart both the application and database/container: dirty state must survive and every ordinary graph read must return `GRAPH_RECOVERY_REQUIRED`. Verify successful full recovery restores exact expected records/content, retires stale associations and is idempotent; a failed recovery remains blocked. Exercise missing bundle/control state, uncertain write acknowledgments, preparation failure with the old snapshot still readable, and concurrent queries crossing a generation. No mixed-snapshot answer or command may escape. Retain actual persistence configuration and restart-test output; no Phase 1 completion without this evidence.

Retain seed commands, expected counts and a browser screenshot/path export for the demo. Phase 2 starts when schema and query compatibility have been verified.

The [FalkorDB resource plan](falkordb_resources_and_hackathon_plan.md) supplies the incident query inventory and an illustrative deployment read. Keep actual tested `.cypher` templates and evidence outputs in the implementation repository. SDK extraction/deduplication must not modify canonical operational identities without a reviewed compatibility implementation.

## SRE extension

Load the [SRE graph additions](sre_graph_schema.md) with the same task/PR/commit identities. Add temporal deployment/assignment and location-specific dependency queries, permitted neighbor reads, customer-feature paths and observation references. Validate current versus historical state and mixed-version rollouts. A runtime call cycle is a supported retrieval case; task planning cycle rules do not apply to it. Verify that customer exposure paths do not automatically become observed-failure facts. See the [integration plan](sre_integration_plan.md) for seed/gates.
