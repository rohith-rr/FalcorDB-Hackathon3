# Canonical graph schema

Status: proposed core schema version 1, with the proposed [SRE extension](sre_graph_schema.md). Use application-owned IDs, not FalkorDB internal numeric node IDs. Application validators enforce edge endpoints, required fields and uniqueness; confirm database constraint/index support against the pinned release during implementation.

## Identity, provenance and source ownership

IDs are namespaced by tenant, provider and native scope. Examples: `demo:jira:PAY:PAY-API`, `demo:github:repository:123`, `demo:github:123:branch:feature/backend-service`, `demo:github:123:pr:17`, and `demo:git:123:commit:<full-sha>`. A branch's identity includes its repository and exact case-sensitive ref. Reviews use their provider-native review ID. Document identity is stable across versions; store its version/content hash separately.

Required common node properties: `id`, `tenant_id`, immutable `projection_owner` (`STRUCTURAL`, `INCIDENT`), `source_system`, `source_record_ref`, optional `source_url`, `source_updated_at`, `observed_at`, `ingested_at`, owning `snapshot_id`, `schema_version`, `is_deleted`. A source without update times explicitly marks that time unavailable; observation time is not fabricated as source update time. Fixtures use a fixed observation clock. [Publication ownership](graph_publication.md#projection-ownership) keeps both projections in one graph and preserves referenced structural identities during rebuilds.

Required common edge properties: `id`, `tenant_id`, immutable `projection_owner`, `source_record_ref`, owning `snapshot_id`, `observed_at`, `link_method` (`API`, `MANIFEST`, `PARSED_EXPLICIT_REFERENCE`, `INFERRED`), `authority` (`CONFIRMED`, `CANDIDATE`), `is_deleted`. Store the confirming record or operator identity for promoted links. Active traversal excludes tombstones and candidates. Nodes and edges cannot cross tenants. Incident-origin relationships to structural entities belong to INCIDENT; structural catalog relationships retain STRUCTURAL ownership.

Canonical authority: the configured task provider (Plane or Jira/export) owns task fields and explicit hierarchy; a verified provider relation or manifest owns typed dependencies. GitHub owns PR/review/ref metadata, Git owns ancestry, and the document source (Google Docs or Markdown/export) owns content/version. A relationship manifest owns explicit cross-system mappings and confirmed revision effects. Preserve conflicting records; mark unresolved conflicts instead of using an LLM to choose a fact. Provider normalization is specified in [source adapters](source_adapters.md).

## Node properties

| Label | Required domain fields |
| --- | --- |
| `Epic` | `project_id`, `external_key`, `title`, normalized status and raw status |
| `Task` | `project_id`, `external_key`, `title`, `work_item_type` (`STORY`, `TASK`, `SUBTASK`), normalized/raw status, priority, nullable `assignee_ids` array, explicit `repository_ids`, dependency/delivery coverage flags |
| `Repository` | provider native ID, owner/name, clone URL, configured `stable_ref`, default ref, repository access scope |
| `Branch` | `repository_id`, full `ref`, `head_sha`, `exists`, `is_protected`; observed ref state |
| `PullRequest` | base `repository_id`, number, title, `state` (`OPEN`, `CLOSED`), `draft`, nullable `merged_at`, nullable `merge_commit_sha`, `head_repository_id`, head/base refs and SHAs |
| `Review` | provider ID, reviewer ID, state, `submitted_at`, reviewed `commit_sha`, bounded body/content reference, dismissal metadata when available |
| `Commit` | `repository_id`, full SHA, nullable committed time/message, `history_complete` |
| `TaskWorkPeriod` | `task_id`, `assignee_id`, nullable `identity_binding_id`, `valid_from`, nullable `valid_to`, `time_accuracy` (`EVENT`, `OBSERVED_BOUND`), `coverage`, activity/evidence references; normalized state is `IN_PROGRESS` |
| `RevisionEffect` | `repository_id`, `delivery_id`, `effect_kind` (`REVERT`, `REAPPLICATION`), `effect_commit_sha`, nonempty `affected_revision_shas`, `coverage` (`COMPLETE`, `PARTIAL`, `UNKNOWN`), `authority`, `mapping_version`; common provenance fields |
| `Document` plus `DesignDoc` or `ProcessDoc` | title, version, content hash, content path/reference, document status (`CURRENT`, `SUPERSEDED`, `DRAFT`), access scope |
| `CheckRun` | provider ID, repository ID, SHA, name, status, nullable conclusion and completed time |

Missing values remain unknown. Normalize task statuses to `TODO`, `IN_PROGRESS`, `BLOCKED`, `DONE`, `CANCELLED`, `UNKNOWN`, preserving provider values. GitHub `CLOSED` is not synonymous with merged; derive merged presentation from authoritative merge fields. `IMPLEMENTED_IN` is descriptive association, not proof of completion.

For assignees, `null` means retrieval is unknown and `[]` means known unassigned. Normalize a single legacy assignee into a one-element array; preserve all Plane assignees without selecting an arbitrary primary person. Source-native UUIDs, rather than task display keys, establish Plane identities; Google Docs identities use native document IDs with tenant/provider scope.

A branch query requires one resolved repository from the task's explicit bindings and request scope. Multiple bindings require clarification; a process-only task may have none. The manifest confirms task-to-repository bindings for new work before any branch exists. Fork PRs retain separate head/base repository identities; a same-named ref in the base repository cannot stand in for the fork source.

For [task-branch discovery](task_branch_association.md), retain separate authored/committed timestamps and native author identity/binding references on commits when available. Tracker activity establishes assignment/in-progress windows. `TaskWorkPeriod` identity includes provider/task/assignee/transition references and interval accuracy; unknown intervals cannot be treated as complete.

Inferred `IMPLEMENTED_IN` edges reference `association_id`, candidate/stable head SHAs, work-period/evidence IDs and model/identity/mapping versions, with `link_method=INFERRED` and `authority=CANDIDATE`. A scoped candidate read may retrieve them as task-context suggestions; confirmed traversal/delivery decisions still exclude them. Promotion requires source/operator evidence, and a promoted branch association alone is not complete delivery proof.

Discovery first returns request-local candidates and retains association audit records outside the graph. An explicit subsequent import can project these edges, with original inference observation time/generation/expiry preserved separately from the projection snapshot. Projection never refreshes an expired inference or confirms delivery. Source-access records, action receipts and audit storage remain outside projection rebuild deletion; their canonical contracts are in [contracts](contracts.md).

## Relationships and direction

| From | Edge | To | Meaning |
| --- | --- | --- | --- |
| `Epic` | `HAS_TASK` | `Task` | Epic child |
| `Task` | `HAS_TASK` | `Task` | Story/task hierarchy |
| `Task` | `DEPENDS_ON` | `Task` | Source needs destination; includes dependency kind |
| `Task` | `IMPLEMENTED_IN` | `Branch` | Planned/observed implementation branch |
| `Task` | `HAS_WORK_PERIOD` | `TaskWorkPeriod` | Intersection of assignment and in-progress intervals for one assignee |
| `Task` | `IMPLEMENTED_BY` | `PullRequest` | Explicitly linked implementation change |
| `Task` | `DELIVERED_BY` | `Commit` | Confirmed required delivery revision, with fields below |
| `Repository` | `HAS_BRANCH` | `Branch` | Repository ref |
| `Branch` | `HEAD_AT` | `Commit` | Observed current head, one active edge per branch |
| `Branch` | `HAS_PR` | `PullRequest` | Source/head branch of PR |
| `PullRequest` | `TARGETS` | `Branch` | Base ref in base repository |
| `PullRequest` | `IN_REPOSITORY` | `Repository` | Repository owning the PR |
| `Review` | `REVIEWS` | `PullRequest` | Individual review |
| `Review` | `REVIEWED_COMMIT` | `Commit` | Version that was reviewed |
| `Commit` | `PARENT` | `Commit` | Immediate parent; bounded imported history |
| `RevisionEffect` | `EFFECT_AT` | `Commit` | Commit whose effect is evaluated against each candidate head |
| `RevisionEffect` | `AFFECTS_REVISION` | `Commit` | Explicit implementation/integration revisions affected within the delivery group |
| `RevisionEffect:REAPPLICATION` | `RESOLVES_REVERT` | `RevisionEffect:REVERT` | Confirmed complete restoration of this specific revert |
| `Document:DesignDoc` | `SPECIFIES` | `Task` | Architectural requirements |
| `Document:ProcessDoc` | `GOVERNS_PROCESS` | `Task` | Operational instructions |
| `CheckRun` | `CHECKS_COMMIT` | `Commit` | Result for a specific revision |

Code-ready dependency traversal follows `DEPENDS_ON` with kind `CODE`; operational dependencies use kind `PROCESS` and remain visible in blockers. Unknown kinds prevent assuming a complete code plan. Inferred hierarchy/dependency cycles are rejected at promotion; imported confirmed cycles are surfaced rather than hidden.

These cycle rules concern task/hierarchy planning. The SRE extension also uses `ServiceInstance-[:DEPENDS_ON]->ServiceInstance`; runtime call cycles are valid and use bounded visited-node traversal. Define dependency meaning by endpoint types and relation properties. Do not reject a runtime cycle as an invalid incident graph.

## Delivery mappings

Each `DELIVERED_BY` edge includes `delivery_id`, `implementation_revision`, `role` (`IMPLEMENTATION`, `INTEGRATION`), optional `pr_id`, optional `equivalent_to_delivery_id`, and `coverage` (`COMPLETE`, `PARTIAL`, `UNKNOWN`). An integration revision is an alternative representation of the same delivery after squash/rebase; it is not an additional prerequisite. Delivery identity is scoped to its task/repository. Reversion is computed per candidate; there is no delivery-level reversion boolean.

A task can require multiple delivery groups, all of which must be covered. Within a delivery group, a confirmed complete implementation revision OR its confirmed complete integration alternative satisfies historical inclusion. Partial mappings cannot stand in for the complete task. A current PR head does not automatically prove the accepted task implementation; an explicit mapping confirms the needed revision(s). Additional work added later to a branch is not implicitly included in an old integration mapping.

Store provider merge metadata as evidence, then validate the mapped integration revision against the requested candidate. A merge into another ref does not establish availability on stable. Missing history, force-pushed-away revisions, uncertain squash mappings or unresolved effect mappings produce unknown coverage; a confirmed complete applicable revert has the distinct `REVERTED` outcome below. Limit imported ancestry; the live verification adapter is authoritative when graph history is incomplete.

### Revision effects and candidate history

`RevisionEffect` nodes use application-owned IDs scoped by tenant/repository/delivery/effect commit. Add the subtype label `REVERT` or `REAPPLICATION` matching `effect_kind`. Their effect/affected commit edges must match the stored SHAs. Reapplications require nonempty `RESOLVES_REVERT` references to reversions of the same delivery and repository. Validate these references, endpoint types and completeness declarations before publication. To establish restored coverage, the reapplication and resolving links must be confirmed and complete, with a confirmed complete delivery mapping for the restoration revision; a commit message or a generic revert-of-revert label is insufficient. Partial restoration records may be retained but cannot establish inclusion. Unconfirmed effects remain candidates and cannot establish restoration; their unresolved evidence must remain visible through delivery coverage/import limitations even when ordinary traversal filters candidate edges out.

For each exact candidate head, verify original/integration delivery inclusion, effect-commit inclusion and causal ancestry. A revert affects usable coverage only when its commit is in that candidate history. Within the delivery group, it vetoes every historical alternative until explicitly resolved; choosing the original revision instead of its integration mapping cannot bypass it. A confirmed complete reapplication resolves a revert only if both commits are included and the reapplication descends from that revert. Every reachable confirmed revert requires resolution; a later revert needs its own restoring record. Order by Git ancestry, not observation or commit time.

With complete verifiable history and consistent complete mappings, historical delivery plus an unresolved reachable complete revert is `REVERTED`; restored delivery is `INCLUDED`. A revert absent from the candidate history has no effect there. Partial effects, missing objects/history, contradictory mappings, or included but causally ambiguous restoration produce `UNKNOWN` rather than a usable inclusion. Complete history with no included delivery alternative is `ABSENT`, unless contradictory effect evidence requires `UNKNOWN`. Absence of recorded effects does not prove semantic preservation after arbitrary later edits.

Example: stable conventionally merges delivery D then includes revert R, while the feature head contains D without R. Stable is `REVERTED`; feature is `INCLUDED`. A confirmed complete A descending from R and restoring D makes stable `INCLUDED` again. Another revert after A makes that candidate `REVERTED` until separately restored. Record effect IDs, SHAs and ancestry evidence in each candidate result.

## Content, access and progress

Store document bytes and section anchors in local content storage for the prototype; graph nodes store references, versions and hashes. Source URLs are separate from local content paths. Every selected excerpt carries its document version. Titles alone are insufficient to explain a procedure.

Demo access is a configured single demo identity with explicitly allowed project/repository/document scopes. Reject unconfigured sources. Future per-user ACL filtering applies before candidate retrieval, every traversal and context construction; never rely on the final LLM to redact data. If authorized scope hides prerequisites, return incomplete context without leaking hidden names/counts.

Epic progress uses distinct non-cancelled leaf work items under confirmed hierarchy: completed count / eligible count. Empty denominator yields unavailable progress. `UNKNOWN` statuses remain in the denominator and make completion a known-completed lower bound; show unknown count. Parent stories are not counted again. Filtered/incomplete visibility is labeled partial and never described as whole-epic progress.

## Query templates

Exact task lookup:

```cypher
MATCH (t:Task {tenant_id: $tenant_id, project_id: $project_id, external_key: $task_key})
WHERE t.is_deleted = false
RETURN t
LIMIT 2
```

One frontier step for iterative dependency traversal:

```cypher
MATCH (t:Task)-[r:DEPENDS_ON]->(d:Task)
WHERE t.id IN $frontier_ids AND t.tenant_id = $tenant_id
  AND d.tenant_id = $tenant_id AND r.tenant_id = $tenant_id
  AND t.is_deleted = false AND d.is_deleted = false AND r.is_deleted = false
  AND r.authority = 'CONFIRMED'
RETURN t.id, r, d
LIMIT 201
```

201 is a detection sentinel for a 200-row frontier budget; never silently truncate into a recommendation. The application applies project/repository permissions to every returned frontier before expansion and records restricted/incomplete status. Use repeated bounded queries so depth, cycle detection, authorization and provenance are explicit.

Parameterize values and use the read-only query API for reads. FalkorDB documents both [parameterized queries](https://docs.falkordb.com/commands/graph.query) and [read-only queries](https://docs.falkordb.com/commands/graph.ro-query). Index application IDs, scoped task keys, repository IDs and document titles using syntax supported by the pinned version. These illustrative templates require executable validation in Phase 1.

Execute every domain template through the [Phase 1 projection gates](phase_01_graph_and_fixtures.md#snapshot-consistency). Declare each template's read projections and record semantic result/coverage fingerprints in `GraphReadSet`, including empty queries, edge membership and aggregates. `ImportState` is reserved per-projection control metadata outside domain traversal/deletion. [Scoped validation](graph_publication.md#request-read-set) proves equivalence after publication; read-only execution alone does not. Preserve the 201-row global overflow sentinel and relationship evidence rather than silently slicing dependency collections.

## Incident schema integration

The [SRE graph extension](sre_graph_schema.md) is canonical for additional entities, temporal fields and source authority. It reuses these task/code/document IDs and adds verified authorship/assignment/reviewer edges, deployment/artifact history, service-instance dependencies, effective on-call assignments and customer-feature observations. New runtime relations must preserve environment, region and validity intervals. Incident explanations remain authored records with evidence; storing a model hypothesis does not promote it to a confirmed fact.
