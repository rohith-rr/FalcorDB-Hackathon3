# Design revision record

Date: 2026-10-09. Scope: approved design corrections, live adapter planning, requested Clef task-branch discovery, embedded POC core fixes and Codex conversation integration. Application implementation has not started. The workspace is now a Git repository; earlier validation notes below retain their historical context.

## Workspace storage and deferred credential setup

Date: 2026-10-10. The user requested that required container/dependency downloads stay within `E:\FalcorDB Hackathon` to avoid filling C:, and that all external tokens, OAuth and logins wait until after Phase 2 implementation. [Workspace setup](workspace_setup.md) is the canonical policy for project-local runtimes/environments/caches/temp, Docker Desktop engine disks/WSL swap, state/content storage and verification before downloads and after restart. Windows/OS metadata and existing installed host tools are explicitly distinguished from new project artifacts; a Compose file on E: is not proof of image storage relocation.

Phases 0-2 now use complete adapter implementations, synthetic/sanitized responses, mocked HTTP/authentication transports, local Git and fixture/export imports. The Phase 2 implementation gate can pass with provider secrets unset. Account provisioning, tokens/OAuth and real Plane/Google Docs/GitHub read/refresh/citation checks are a separate milestone after Phase 2 implementation; record `LIVE_VALIDATION_DEFERRED` separately and allow Phase 3 implementation to proceed. Final demo acceptance still requires actual live evidence. These instructions supersede the earlier records' placement of live smoke evidence inside Phase 2 implementation completion, without changing historical results or claiming a live check passed.

Aligned the master/index, Phases 0-2 and 6, source adapters, SRE/resource plans and local backlog guidance. Added ignore rules for generated artifacts and future local secrets. Existing seed payload/receipts and the archived original are preserved. This revision changes plans only; it downloads no dependencies/images, moves no Docker/WSL data, configures no credentials and makes no provider calls. Host executables were discoverable, but Docker CLI inspection could not read the existing user configuration; the actual engine-disk location remains unverified until Phase 0 preflight.

Documentation validation passed across 30 Markdown files: 323 local links, 93 heading anchors, balanced fenced blocks and one parsed JSON example. SHA-256 checks confirm the archived original and three existing demo artifacts are unchanged. Git ignore checks exclude future local downloads/disks/caches/secrets, virtual environments and frontend dependencies while allowing `.env.example`; `git diff --check` passed. These checks verify the plans, not runtime storage placement, adapter behavior or live compatibility.

## Requested Codex conversation integration

Date: 2026-10-09. The user requested embedding local Codex chat JSONL ingestion in the design. [Codex conversations](codex_conversations.md) now owns the source-registration, versioned dialect/origin parser, sanitized capture/identity, deduplication, complete-line cursor/recovery, scoped mention, reviewed decision, retrieval/citation and access rules. The master/index, canonical schema/contracts, source adapters/publication, Phases 0–7, model/association policy and SRE/demo instructions consume this specification.

The extension adds STRUCTURAL `Conversation`, `Message` and `DesignDecision` records, `CONVERSATION_CONTEXT`, message/review evidence and authorized transcript views. Models propose decisions; versioned operator reviews record accepted/rejected/superseded intent. Chat statements never confirm task/delivery/incident facts, approve actions or supply independent corroboration of their own generated claims. Local sessions remain IMPORT, synthetic inputs FIXTURE; no third projection or per-line rebuild is introduced. Manual repeatable import is the POC path, automated watching/extraction optional. The existing live-source, branch, incident and action gates remain; the eighteen-task seed catalog, receipts and archived draft are preserved.

This revision edits specifications only. No runtime importer/model/UI, source imports, external task writes or chat copying were performed. Runtime acceptance checks remain future work.

Documentation validation passed across 29 Markdown files: 306 local links, 88 heading anchors, balanced code fences, one parsed JSON example and three parsed JSON files. The archived original SHA-256 is unchanged, existing demo JSON/receipts were not edited, and `git diff --check` passed. These results include the existing untracked POC review and the new conversation specification; they verify documents, not runtime ingestion or retrieval.

## Review findings resolved in the specifications

| Finding | Revised requirement | Future implementation evidence |
| --- | --- | --- |
| P2: interrupted imports can expose overwritten records under the old marker | [Phase 1](phase_01_graph_and_fixtures.md#snapshot-consistency) persists dirty state/generation before mutation, blocks reads across restart, and requires a full validated rebuild | Failure halfway through upserts, between nodes/edges and before publication; application/database restart; failed and repeated recovery; concurrent request invalidation |
| P2: global delivery reversion rejects usable feature histories | [Schema](graph_schema.md#revision-effects-and-candidate-history) records revert/reapplication revisions and evaluates applicability against each candidate head | Stable merge/revert plus unchanged feature; explicit complete restoration; later revert; partial/ambiguous effects; cache invalidation |
| Missing Plane/Google Docs integration planning | [Source adapters](source_adapters.md) specifies required live reads, provider identities/mappings, multi-assignee tasks, versioned document tabs/sections, failure behavior and labeled exports | Both actual live smoke checks and source-backed task/document citations; export-only fallback leaves the full gate incomplete |

The [contracts](contracts.md), master design, implementation index, all phase gates and SRE/resource guidance carry these requirements. The archived original draft is preserved.

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

## Removed sprint time constraints

Date: 2026-10-09. The 48-hour sprint boundary and all per-phase hour timeboxes were removed from the master design, implementation index, phase plans, SRE integration plan, FalkorDB resource plan and decision record. Phase completion is now defined only by each phase's completion gate; effort is re-estimated after the recovery/persistence and live-adapter compatibility checks rather than committed to hour figures in advance. The demo scope and cut policy remain in the implementation index's scope boundary and the SRE plan's practical demo allocation, retaining the prior prioritization guidance without time claims.

The archived original draft keeps its 48-hour sprint reference unchanged, per the revision gate. The two dated reviews under docs/reviews retain their original text as historical records; their schedule-related findings refer to the removed constraint and no longer reflect current planning. No runtime behavior, gates or acceptance criteria were changed by this revision.

## Design risk fixes

Date: 2026-10-09. The user requested fixes for confirmed/applicable findings from the subsequent repository review. [Graph publication](graph_publication.md) is the canonical detailed policy; [contracts](contracts.md) and the affected phases, master/index, source/SRE schema and incident requirements now consume it.

- Separate STRUCTURAL/INCIDENT ownership, durable control records and gates in the shared FalkorDB graph. Incident inputs retain durable receipts/jobs and publish bounded deltas in fixed 30-second windows (configurable 15-30), with a minimum 15-second READY interval, durable log positions, restart reconciliation and pre-acceptance backpressure. Recovery preserves other owners and cross-projection identities.
- Replace global-generation-only answer invalidation with complete semantic read-set equivalence, including edges, aggregates, empty results, coverage and relevant policy/mapping/effect/access versions. Preserve equivalent LLM output across unrelated changes; retain original TTL/observations and live-head checks. Relevant changes share the existing one-request retry budget.
- Bind clarification to original tenant/principal/question/scope/kind/candidate set and TTL; revalidate selected candidates and recompute current decisions rather than rejecting unrelated generations.
- Make execute return 202 only after durable target reservation/claim/receipt/job commit. Worker mutation and 30 probes run asynchronously; authorized GET plan lookup exposes separate operation/recovery states, queued restart and unknown-outcome reconciliation.
- Remove the three exact master-document duplicates. Replace 32 hardcoded Drive-path links across both reviews and the open-question backlog with relative targets, removing obsolete file-line suffixes. Annotate historical review guidance where superseded.

The intentional global frontier overflow sentinel and required relationship filters remain; the review did not establish those as correctness/performance defects. Live Plane/Google Docs and requested Clef completion criteria are retained. Application implementation, stream measurements, database/Git/provider checks and sandbox actions remain future work. The archived original and existing demo seed changes are preserved.

Documentation validation passed: 27 Markdown files, 269 local links, 82 heading anchors, balanced code fences and one parsed JSON example. Exact duplicate checks, hardcoded-path scan, obsolete active invalidation-rule scan and contract/phase policy checks passed. The archived original SHA-256 is unchanged, and `git diff --check` passed. These are document checks, not runtime acceptance results.
