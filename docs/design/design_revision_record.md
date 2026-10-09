# Design revision record

Date: 2026-10-09. Scope: approved design corrections, live adapter planning, requested Clef task-branch discovery and embedded POC core fixes. Application implementation has not started. The workspace is now a Git repository; earlier validation notes below retain their historical context.

## Review findings resolved in the specifications

| Finding | Revised requirement | Future implementation evidence |
| --- | --- | --- |
| P2: interrupted imports can expose overwritten records under the old marker | [Phase 1](phase_01_graph_and_fixtures.md#snapshot-consistency) persists dirty state/generation before mutation, blocks reads across restart, and requires a full validated rebuild | Failure halfway through upserts, between nodes/edges and before publication; application/database restart; failed and repeated recovery; concurrent request invalidation |
| P2: global delivery reversion rejects usable feature histories | [Schema](graph_schema.md#revision-effects-and-candidate-history) records revert/reapplication revisions and evaluates applicability against each candidate head | Stable merge/revert plus unchanged feature; explicit complete restoration; later revert; partial/ambiguous effects; cache invalidation |
| Missing Plane/Google Docs integration planning | [Source adapters](source_adapters.md) specifies required live reads, provider identities/mappings, multi-assignee tasks, versioned document tabs/sections, failure behavior and labeled exports | Both actual live smoke checks and source-backed task/document citations; export-only fallback leaves the full gate incomplete |

The [contracts](contracts.md), master design, implementation index, all phase gates and SRE/resource guidance carry these requirements. Original sprint estimates are provisional. The archived original draft is preserved.

## Documentation validation

Initial revision documentation checks passed: 20 Markdown documents, 110 relative links, 12 heading anchors and one JSON example; fenced blocks were balanced. An obsolete-guidance scan found no active global delivery-reversion flag, marker-only recovery or optional-live adapter completion policy. Required import/effect/adapter contract and acceptance coverage was also checked. A final semantic pass confirmed partial reapplication records remain representable as uncertainty rather than being rejected or treated as complete restoration.

Archived original SHA-256: `5152b97014014fcbd28a1527a60dd078266e483ccaed9dc95ed149551a04b0a6`.

Runtime database/Git tests and live adapter calls were not part of that documentation revision and did not pass or run. No provider accounts, source records, notifications or deployed services were changed. At that earlier revision the workspace had no Git repository, so no diff/commit was reported.

## Requested task-branch discovery addition

Added [temporal Clef association](task_branch_association.md) for assigned in-progress tasks with missing task identifiers. The design reconstructs assignment/status work periods, resolves author identity, retrieves per-head commit/content evidence and asks Clef to distinguish likely, multiple, ambiguous or absent associations. It preserves explicit mappings and stores inference as candidate evidence with expiry, provenance and a separate response field. Missing history, shared commits, concurrent tasks, stale inputs and provider failure cause visible uncertainty rather than delivery claims.

Aligned source adapters, schema/contracts, ingestion, Phase 4 evaluation, task context, final answer freshness, foundation scenarios, demo cases, master design and index. Existing task/repository/verified-base clarification and stale-narrative requirements remain in force. Addition documentation checks passed across 21 Markdown documents, 128 local links, 16 heading anchors and one JSON example. Checked canonical response fields, retained clarification selections, temporal association requirements, post-answer freshness and archive preservation. Runtime implementation, tests and actual Clef calls remain future phase work; documentation checks are not runtime regression results.

## Approved hackathon POC core fixes

The user approved embedding C-01 through C-07 from the POC core review. The [implementation index](README.md#poc-core-decisions) maps each decision to its owning specification. Curated manifests remain valid POC inputs; automated maintenance and enterprise operation remain in the separate open-question backlog.

- C-01: inference returns request-local suggestions, retains audits outside the graph and projects candidates only in a later explicit ingestion batch. Original observation/generation/expiry survives projection.
- C-02: exact incident-instance IDs or an authorized picker submit fresh scoped requests; unresolved alerts remain durable/pending. Typed 422 errors replace guessed scope.
- C-03: the controller owns required checks and STOP eligibility; UNAVAILABLE distinguishes failed reads from authoritative absence and NOT_CHECKED work.
- C-04: AnswerFact references and qualifier/value validation constrain explanations; critical fields remain engine-rendered, with invalid prose falling back.
- C-05: durable source-access records invalidate content, traces and in-flight answers independently of import success and graph generation.
- C-06: one sandbox restoration uses exact-version approval, a durable atomic execution claim, per-target serialization, unknown-outcome reconciliation and a separate 30-sample recovery check.
- C-07: one writer publishes scenario batches; direct/MCP reads share readiness/generation gates and retained control/audit storage survives graph rebuild.

Updated canonical contracts, association/schema, source adapters, Phases 0-6, SRE requirements/plan, master/index and the review/backlog status. These are documentation changes only: the newly specified acceptance cases have not run, no providers were called and no action was executed. The archived original remains unchanged. Documentation validation passed across 24 Markdown files: 194 local references, 47 heading anchors, balanced fenced blocks and one JSON example. Cross-document consistency checks and `git diff --check` also passed. These checks do not establish runtime correctness.
