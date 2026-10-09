# Phase 1: graph schema, fixtures and query templates

Status: planned. Depends on Phase 0.

## Outcome

FalkorDB contains an inspectable Payments/TLS graph with provenance and repeatable imports. Scoped read queries recover the exact relationships needed for branch and document workflows.

## Proposed files

```text
backend/app/graph/{client,schema,loader,queries}.py
backend/app/graph/import_state.py
backend/app/graph/{projection_ownership,read_sets}.py
backend/app/graph/templates/*.cypher
backend/app/storage/documents.py
scripts/seed_graph.py
tests/integration/test_graph_queries.py
tests/integration/test_graph_loader.py
```

Use the [canonical schema](graph_schema.md); do not invent a separate demo ontology. Individual `Review` and `Commit` nodes are required. `CheckRun` is optional in the demo. Resolve symbolic fixture revisions through the Phase 0 Git builder before ingestion; graph commits use real full SHAs. Live branch verification is implemented in Phase 3.

## Coding sequence

1. Connect using the pinned FalkorDB client and implement separate read/write methods. Reads use the database's read-only query API; writes are only reachable from ingestion/operator paths.
2. Validate normalized nodes, edge endpoints and immutable `projection_owner` under [graph publication](graph_publication.md#projection-ownership). Reject duplicate logical IDs, invalid cross-tenant links and cross-owner writes. Enforce one active branch head and one active PR target; a current review is not flattened into an unversioned string.
3. Create indexes supported by the pinned database on IDs, scoped task keys and relevant lookup fields. Do not assume Neo4j index/constraint syntax is compatible.
4. Implement the durable import protocol below before exposing logical-ID upserts. Write nodes before edges; preserve source ownership and tombstone removed associations. Do not create placeholder nodes that look verified.
5. Store document content separately with content hash, version and section anchors; store graph references. Populate real TLS runbook steps in the synthetic fixture, not just its title.
6. Add templates for exact task lookup, epic children, one dependency frontier, task delivery groups and revision effects, implementation PR/branch links, work periods and scoped inferred association candidates, current documents, individual reviews and candidate heads. The candidate-evidence template keeps inferred suggestions out of confirmed delivery traversal.
7. Load fixtures and inspect graph topology in FalkorDB Browser. Verify the direction of `DEPENDS_ON` and incoming document edges against the schema.

## Snapshot consistency

The prototype uses one application process and a durable `ImportState` plus read/write gate for each STRUCTURAL/INCIDENT projection in the shared graph. A published snapshot ID alone does not protect records overwritten by an interrupted update. [Graph publication](graph_publication.md) defines ownership, gate order, event batching and scoped equivalence; [contracts](contracts.md) define states and errors.

Run one application writer/worker for the POC; background investigations share its projection gates. Online import/seed/reset scripts invoke the controlled operator path rather than opening a competing writer. Offline seeding requires the application stopped and uses the same durable protocol. MCP reads pass through the application gateway; Browser inspection uses read-only access. Finish initial scenario publication before investigation, then schedule accepted events through the [fixed 30-second incident batching policy](graph_publication.md#durable-incident-batching), with retained receipts and a minimum READY read interval. Incident batches update affected incident-owned records; they never rebuild the structural graph after every alert, query or suggestion.

Retain source receipts, incident lifecycle records, action plans/receipts, source-access registry and association audits in a local transactional store outside graph rebuild deletion. Immutable bundle/document bytes stay in versioned content storage. These retained records are not permission to bypass graph publication for graph-backed conclusions. Source-access checks additionally apply outside graph generation, as defined in [contracts](contracts.md#source-access-registry).

1. Fetch and normalize sources without changing the graph. Validate logical identities, endpoint types, manifests, ownership and content references. Persist an immutable full rebuild bundle for each affected projection with its hash, source observations, tombstones, coverage declarations and document bytes before mutation. Allocate each bundle ID as its future snapshot ID. Durably flush manifest/content before dirty publication. A targeted refresh reconciles into the full retained bundle for its owner; it cannot erase other source scopes. Never overwrite versioned content referenced by previous evidence.
2. Acquire projection gates in STRUCTURAL, INCIDENT order according to [ownership rules](graph_publication.md#projection-ownership). Recheck prepared bundle base tokens; reject or reconcile again if a required publication won. Persist DIRTY, increment the affected projection generation, and record its pending bundle ID/hash before its first domain write; coordinated updates fence all affected owners. Continue only after durable acknowledgment. Configure and verify pinned-database write durability (for example, persistent AOF with synchronous fsync); a process-local flag or periodic backup is insufficient.
3. Rebuild only the affected owned projection from its retained bundle, using logical-ID upserts, retiring stale owned records and restoring its relationships. Exclude control records, other owners and retained incident links; preserve/tombstone referenced structural endpoints. Ordinary incident batches use idempotent deltas; interrupted updates recover through a complete INCIDENT-only rebuild. Source receipts, lifecycle/action audit records and operator confirmations live in separate retained storage and contribute to their owner's bundle.
4. Check topology, active-head/target uniqueness, provenance, snapshot IDs and content hashes. In one final graph write, publish `active_snapshot_id`, clear pending fields, and set `READY` without decreasing the generation. Confirm durable acknowledgment before releasing the gate or admitting readers. `READY` means coherent publication; source completeness remains a separate coverage field.
5. Any failure after dirty-state publication leaves reads requiring that projection blocked. On application/database restart, inspect each durable state; missing, unreadable or DIRTY state requires recovery. Recovery uses the same gated path and repeats a complete affected-projection rebuild from its retained bundle with a new generation. Never merely clear the flag. Missing/invalid bundles require new validated full bundles; unrelated READY STRUCTURAL remains usable during INCIDENT recovery.

Initial seeding follows the same protocol; no active snapshot is readable until publication succeeds. A failure during preparation leaves the prior snapshot readable at its original observation age. After mutation begins, the prior marker is audit metadata only. An ambiguous write acknowledgment blocks reads until durable state can be reconciled; startup verifies the published bundle/snapshot before readiness.

Application reads use nonblocking shared-gate admission for all projections declared by the template and require READY, capturing their `(generation, active_snapshot_id)` tokens together. Active exclusive publication or dirty/missing required state returns 503 `GRAPH_RECOVERY_REQUIRED`. Record every read in `GraphReadSet`, including relationship membership, aggregate/empty-result scope and completeness. Recheck tokens for later batches and final publication; a moved token triggers bounded semantic read-set comparison, not automatic discard. Equivalent inputs survive unrelated imports without another LLM call. Changed/unprovable inputs permit one whole-request retry; repeated relevant change while READY returns `GRAPH_SNAPSHOT_CHANGED`. Preserve original evidence observations plus current validation tokens. Neither error returns a decision/command. Hold no graph gate across provider/LLM network calls. Follow [final publication](graph_publication.md#final-response-publication).

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

Verify direct/MCP reads, the picker and stored evidence routes use the same projection admission rules. Seed/reset scripts cannot bypass them. During a provider call, unrelated publication may finish and an equivalent read set may publish; changed dependencies, aggregates, absence results, effects or permitted content must invalidate it. Include INCIDENT DIRTY with structural queries still working, cross-owner recovery preserving links, and unrelated/relevant generation changes during traversal and inference. Retained records survive rebuild/restart. Run the [publication acceptance cases](graph_publication.md#required-implementation-evidence); startup instructions declare ownership, single writer, cadence/caps and gate order.

The [FalkorDB resource plan](falkordb_resources_and_hackathon_plan.md) supplies the incident query inventory and an illustrative deployment read. Keep actual tested `.cypher` templates and evidence outputs in the implementation repository. SDK extraction/deduplication must not modify canonical operational identities without a reviewed compatibility implementation.

## SRE extension

Load the [SRE graph additions](sre_graph_schema.md) with the same task/PR/commit identities. Add temporal deployment/assignment and location-specific dependency queries, permitted neighbor reads, customer-feature paths and observation references. Validate current versus historical state and mixed-version rollouts. A runtime call cycle is a supported retrieval case; task planning cycle rules do not apply to it. Verify that customer exposure paths do not automatically become observed-failure facts. See the [integration plan](sre_integration_plan.md) for seed/gates.
