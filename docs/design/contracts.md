# Shared application contracts

Status: proposed. Implement these as Pydantic models in `backend/app/contracts/`. This document is canonical; provider response shapes stay inside adapters.

## Request and resolution

`QueryRequest`: `question`, optional `project_id`, `repository_id`, `task_id`, `incident_id`, `service_id`, `service_instance_id`, `requested_intent`, and optional `clarification_answer` (`token` plus exactly one typed selection — `selected_task_id`, `selected_repository_id`, or `selected_ref`) valid only when resubmitting a prior `NEEDS_CLARIFICATION` question; see [Clarification and continuation](#clarification-and-continuation). Intent values are `BRANCH_BASE`, `TASK_CONTEXT`, `BLOCKERS`, `EPIC_PROGRESS`, `INCIDENT_BRIEF`, `INCIDENT_HISTORY`, `OTHER`. Incident requests also carry an optional event-time window and operating scope; the server validates all scope against the principal.

The server derives `tenant_id` and `principal_id` from authentication/configured demo identity. A client cannot select an arbitrary tenant. Resolve a fully scoped exact task key first; otherwise retrieve accessible candidates. Resolution is `RESOLVED`, `NEEDS_CLARIFICATION`, `NOT_FOUND` or `UNSUPPORTED`. A clarification is the typed `clarification` object described below and includes only accessible candidates and a continuation token; subsequent requests retain original scope.

Clarification may be needed after task resolution when repository bindings or verified branch candidates remain ambiguous. In that case the response retains the resolved task and relevant accessible evidence, sets resolution to `NEEDS_CLARIFICATION`, and leaves the branch decision null until selection is settled.

### Clarification and continuation

`NEEDS_CLARIFICATION` has three variants, distinguished by a `kind` discriminator on the response's `clarification` object — exposed as the nullable `clarification` field of `QueryResponse`:

- `TASK`: the requested task key matched several accessible tasks; candidates are task labels/IDs.
- `REPOSITORY`: a resolved task has multiple repository bindings; candidates are repository IDs/labels, and the response retains the resolved task.
- `BRANCH`: several verified branch candidates qualify and the manifest names no preferred branch; candidates are the exact candidate refs/SHAs from `candidate_results`.

The `clarification` object carries `kind`, `candidates` typed per `kind`, `token`, and `expires_at`. The `token` is an opaque, tenant/principal-scoped value bound to a hash of the original question, resolved scope, `kind`, candidate set, graph generation and mapping/effect/policy versions, with a short expiry. It is never replayable across tenants, across kinds, or after a graph generation change. `expires_at` bounds token validity consistent with evidence freshness windows.

A client answers by resubmitting `POST /query` with the original `question` and scope plus an optional `clarification_answer` on `QueryRequest`: `token` and exactly one typed selection field matching the token's `kind` — `selected_task_id`, `selected_repository_id`, or `selected_ref`. A missing, duplicated or kind-mismatched selection is invalid. No separate continuation endpoint is defined; the same read-only `POST /query` contract applies. An unknown, out-of-scope, or multiply/unselected candidate, a token from another principal, or one whose binding hash no longer matches returns 422 or a fresh `NEEDS_CLARIFICATION`; it never resolves against the guessed candidate set. Task and repository selections narrow the request scope for the resumed resolution — the server revalidates accessibility of the selected task/repository under the original principal scope, and a selection that is no longer accessible or resolvable yields a fresh `NEEDS_CLARIFICATION` or `NOT_FOUND`, never an assumed scope.

Selection is a preference, not verification. For `BRANCH`, on receipt the server revalidates the token binding, refreshes live heads for the selected candidate and stable, and recomputes the full decision — ancestry, revision effects, policy — before recording a recommendation. An expired token yields a new `NEEDS_CLARIFICATION`; a changed, missing or newly ineligible head yields `STALE_EVIDENCE` or refreshed candidates with a new token. Commands are never derived from token-time state alone; the selected branch must pass the same pre-recommendation checks as any other candidate.

### POC incident scope selection

For `INCIDENT_BRIEF`, require one exact, authorized `service_instance_id`, supplied by the alert/incident binding or selected in the UI. Validate that supplied service/environment/region fields agree with that instance; never resolve conflicting fields by model score. `GET /service-instances` returns a bounded list of accessible instance IDs and display labels including environment/region, through the ordinary graph gate. Overflow requires narrower scope. Selection submits a fresh request with the original question and chosen instance; scope and permissions are checked again. The POC does not add a service variant to the task/repository/branch continuation token.

`IncidentScopeError`: HTTP 422 with `request_id`, `code` (`SERVICE_INSTANCE_REQUIRED` or `SERVICE_SCOPE_CONFLICT`) and a generic selection message, without a decision or restricted candidate details. An inaccessible supplied ID uses the normal authorization/not-found policy. A durably accepted alert with unresolved identity still receives its receipt, but enrichment stays pending until an operator submits an authorized instance selection through the existing incident investigation endpoint. Persist the selection and actor in the incident timeline before enqueueing investigation; it cannot overwrite contradictory source identity. Historical queries may use an exact authorized incident binding; requests lacking a resolved subject must ask for explicit scope.

## Snapshot and evidence

`SnapshotRef`: `snapshot_id`, `generation`, `mode` (`FIXTURE`, `IMPORT`, `LIVE`), `observed_at`, `ingested_at`, `scope`, `complete`, `source_version`. Generation is a monotonic import fence, not a source version.

`ImportState`: managed graph identity, `state` (`UNINITIALIZED`, `DIRTY`, `READY`), nonnegative `generation`, nullable `active_snapshot_id`, nullable `pending_bundle_id`, nullable `pending_bundle_hash`, `updated_at`, nullable sanitized `last_failure`. Missing/unreadable state is treated as `UNINITIALIZED`; no application domain read is allowed without `READY` and a validated active snapshot. `DIRTY` is persisted before domain mutation; recovery rebuilds the complete graph before publication. Publication sets the active snapshot, clears pending fields and sets `READY` in one durable graph write. See [Phase 1](phase_01_graph_and_fixtures.md#snapshot-consistency).

`ImportReport`: bundle ID/hash, previous/published snapshot IDs, generation, outcome (`PREPARATION_FAILED`, `RECOVERY_REQUIRED`, `PUBLISHED`), source scopes/coverage, validation conflicts, timestamps and sanitized failure details. An import interrupted after dirty publication cannot report the old snapshot as readable. Source observations retain their age after recovery.

`EvidenceItem`: `evidence_id`, `kind`, `entity_ids`, `source_url` (optional for local fixtures), `source_record_ref`, `source_version`, `observed_at`, `verified_at` (optional), `snapshot_id`, `generation`, `content_hash`, and a bounded `excerpt` or typed `value`. Supported kinds include task fields, confirmed relationship, document section, PR state, review state, branch head, revision effect and Git coverage. Document sections also retain version-bound `tab_id` (nullable for Markdown) and `section_anchor`. Local fixtures link to a visible fixture record instead of an invented company URL.

`TraversalStep`: `step_id`, `template_id`, sanitized `parameters`, `node_ids`, `edge_ids`, `evidence_ids`, `selection_method`, `duration_ms`, `stop_reason`. Record model metadata separately: provider, model/checkpoint revision, question version, option-set hash, probabilities, selected value and abstention reason. Do not log credentials or inaccessible content.

Snapshot completeness, freshness and inference uncertainty are independent. A high model confidence cannot make an incomplete source snapshot complete.

### Source access registry

`SourceAccessRecord`: `tenant_id`, `principal_id` (configured demo identity), provider/credential-scope reference, `resource_id` (or explicit source-scope ID), `access_status` (`ALLOWED`, `DENIED`, `UNAVAILABLE`, `UNKNOWN`), `checked_at`, monotonic `access_version`, and sanitized reason. Persist records in a local transactional store outside graph rebuild deletion. A source-level restriction applies to its children even if a child has an older ALLOWED record. Missing/unreadable access state fails closed for affected live content; fixtures use explicitly configured allowlists. A definitive denial records DENIED; ambiguous 403/404 unavailability records UNAVAILABLE and suppresses retained content without asserting deletion. Transient network/rate-limit failure is a freshness/coverage failure, not evidence of revocation.

Requests, model inputs, caches, association audits and stored traces retain the access versions for their evidence resources and enclosing scopes. Check current access before retrieval, trace display and final publication, independently of graph generation. Serialize the last check/publication with registry updates using a short local gate; hold no gate across network calls. A changed relevant version invalidates the prepared answer: rebuild once from currently permitted evidence within the shared request retry budget, or return HTTP 403 `SOURCE_ACCESS_CHANGED` with no evidence content, decision or commands. Unreadable registry returns HTTP 503 `SOURCE_ACCESS_UNAVAILABLE`. Failure to durably record a known denial blocks affected reads until registry recovery. Only a successful authorized recheck can restore access; graph import success or restart cannot clear a denial. Revocation suppresses future disclosures; it cannot retract text already delivered to a user/provider.

## Task-branch association

These types support the [time-window/Clef fallback](task_branch_association.md), preserving the existing `TASK`, `REPOSITORY` and verified-base `BRANCH` clarification variants.

`IdentityBinding`: `binding_id`, `tenant_id`, `tracker_source`, `tracker_user_id`, native GitHub user ID and/or verified author-email alias references, `mapping_version`, confirming actor/source, and provenance. Match exact configured identities; no display-name inference. Reuse `Employee` identity/edges when the SRE extension is enabled.

`TaskWorkPeriod`: `id`, `task_id`, `assignee_id`, nullable `identity_binding_id`, UTC `valid_from`, nullable `valid_to`, `observed_at`, `time_accuracy` (`EVENT`, `OBSERVED_BOUND`), `coverage` (`COMPLETE`, `PARTIAL`, `UNKNOWN`), and activity/evidence references. Intersect one person's assignment and task `IN_PROGRESS` intervals; observation time bounds open periods. Generic update times cannot supply unknown starts. Missing identity mapping preserves tracker history but prevents author matching.

`BranchAssociationCandidate`: `association_id`, `task_id`, `repository_id`, `ref`, exact observed `head_sha` and `stable_head_sha`, `assignee_ids`, `work_period_ids`, `matching_commit_shas`, bounded changed-path summaries, `evidence_ids`, `link_method=INFERRED`, `authority=CANDIDATE`, nullable `pair_probability`, nullable `choice_probability`, model/question/identity/mapping versions, option/input hashes, `observed_at`, `valid_until`, and `limitations`. Scores concern associations, not delivery coverage or complete implementation.

`BranchAssociationResult`: `task_id`, `repository_id`, `status` (`SUGGESTED`, `AMBIGUOUS`, `NO_MATCH`, `INSUFFICIENT_EVIDENCE`, `PROVIDER_UNAVAILABLE`, `NOT_APPLICABLE`), `candidates`, nullable `preferred_association_id`, `search_window`, `coverage`, snapshot/generation, `evidence_ids`, and `limitations`. Multiple associations remain representable. `NO_MATCH` is limited to the searched window; changed/unverifiable task/head after inference yields `INSUFFICIENT_EVIDENCE` with a stale-evidence limitation and no preferred association. Operator/source manifests may promote associations through ingestion; query selection cannot promote them or create delivery evidence.

`TASK_CONTEXT` and `BRANCH_BASE` responses may include discovery through `branch_associations`; branch-base commands still require confirmed complete delivery evidence. Clef failure is isolated to discovery and does not block explicit mappings or the answer provider.

`AssociationAuditRecord` retains request/association IDs, result, evidence/input hashes, original graph generation, access versions, model metadata and observation/expiry times outside the graph. The query returns request-local results and may append this audit record, but never invokes an import to save its own suggestion. An explicit later ingestion batch can project retained suggestions as INFERRED/CANDIDATE after access/input revalidation; retain original observation generation/time separately from the projection generation. Projection does not refresh expiry, confirm a mapping or make an old result current. Audit-write failure is a disclosed persistence limitation and never triggers a graph write or fabricated receipt.

## Branch decision

`BranchDecision.status` is one of:

| Status | Meaning | Git branch command |
| --- | --- | --- |
| `RECOMMENDED` | One eligible branch covers all confirmed prerequisites | Allowed as a proposal |
| `INTEGRATION_REQUIRED` | No eligible branch covers all prerequisites | Withheld |
| `INSUFFICIENT_EVIDENCE` | Missing/unconfirmed delivery or incomplete dependency evidence | Withheld |
| `STALE_EVIDENCE` | Required live verification expired/failed | Withheld |
| `POLICY_BLOCKED` | Coverage exists but no candidate is permitted | Withheld |
| `DEPENDENCY_CYCLE` | Confirmed cycle prevents a valid plan | Withheld |

Fields: `task_id`, `repository_id`, `stable_ref`, `required_task_ids`, `required_delivery_ids`, `candidate_results`, nullable `selected_ref`, nullable `selected_head_sha`, `development_use_allowed`, `review_readiness` (`APPROVED`, `CHANGES_REQUESTED`, `PENDING`, `UNKNOWN`), `deployment_readiness` (`NOT_EVALUATED`, `READY`, `BLOCKED`, `UNKNOWN`), `warnings`, `evidence_ids`, `verified_at`, `valid_until`, and `proposed_commands`.

Each candidate result carries `repository_id`, `ref`, `head_sha`, `exists`, policy eligibility, and per-delivery coverage: `INCLUDED`, `ABSENT`, `UNKNOWN`, or `REVERTED`. Include verification method, source and time, graph generation, mapping/effect version, `applicable_effect_ids`, `resolved_revert_ids`, and `effect_checks`. Each effect check identifies the effect ID/kind/SHA, candidate head, inclusion (`INCLUDED`, `ABSENT`, `UNKNOWN`), resolution ancestry results and evidence IDs. `INCLUDED` is verified historical delivery evidence with applicable recorded effects evaluated; explicitly record whether semantic preservation was checked. The MVP always sets deployment readiness to `NOT_EVALUATED`; inclusion is insufficient to claim deployment readiness.

`RevisionEffectRecord`: `id`, `repository_id`, `delivery_id`, `effect_kind` (`REVERT`, `REAPPLICATION`), full `effect_commit_sha`, nonempty `affected_revision_shas`, `coverage` (`COMPLETE`, `PARTIAL`, `UNKNOWN`), `authority`, `mapping_version`, `resolves_revert_ids`, and common provenance fields. Reverts have no resolved IDs; reapplications must identify the same-group revert records they address. Restored coverage additionally requires confirmed complete effect/resolving links and a confirmed complete restoration delivery mapping; partial or unconfirmed records remain explicit uncertainty and cannot establish inclusion. The manifest and graph use the same record; provider-native shapes remain internal. Applicability is computed per candidate under the [schema rules](graph_schema.md#revision-effects-and-candidate-history).

`proposed_commands` is an array of argument arrays generated by the engine, never an LLM string. Display shell-quoted forms using the selected client shell. Require `RECOMMENDED`, a full verified SHA, allowed development use, complete coverage and unexpired evidence. Validate the proposed new name with `git check-ref-format --branch`; prevent option injection by rejecting option-like names and using argument arrays. Commands are not executed by `POST /query`.

## Context and answer response

`ContextBundle`: `request_id`, resolved intent/entities, snapshots, typed `AnswerFact` records, evidence resource/scope `access_versions`, nullable branch decision, nullable incident context, `branch_associations` (array of `BranchAssociationResult`, empty when discovery is unused), task/dependency summaries, selected document sections, review summaries, epic counts, evidence items, traversal steps and limitations. Enforce provider token budgets while retaining all decision evidence and coverage counts; omitted narrative content is reported.

Build a request-local `AnswerFact` registry: fact ID, subject/entity IDs, predicate, typed value, uncertainty/impact classification, observation time and evidence IDs. The answer model receives these facts and returns structured explanatory statements referencing fact IDs and evidence IDs. All referenced facts must exist, be currently permitted and retain their value/qualifiers. Render critical fields and source links from the engine; contradictory values or changes from POSSIBLE to OBSERVED reject the explanation even when its citation IDs exist. General prose entailment still requires bounded prompts and manual evaluation; valid JSON is not proof of support. Runbook excerpts retain applicability, prerequisites and required warnings with the selected steps.

`QueryResponse`: `request_id`, `resolution`, nullable `clarification`, `decision`, `branch_associations` (array of `BranchAssociationResult`, empty when unused), `answer`, `citations`, `trace`, `limitations`, and `timings`. `decision` is nullable and explicitly tagged as `BRANCH` or `INCIDENT`; an incident context never masquerades as a branch recommendation. `clarification` is a nullable typed field (`kind` discriminator `TASK`, `REPOSITORY` or `BRANCH`, `candidates` typed per `kind`, `token`, `expires_at`); it is present only when `resolution` is `NEEDS_CLARIFICATION` — see [Clarification and continuation](#clarification-and-continuation) — and then `decision` is null and the answer may not recommend or prefer any candidate. `branch_associations` exposes inferred implementation suggestions separately from verified base decisions and never supplies commands. `answer` contains `mode` (`LLM`, `DETERMINISTIC`), a short summary and explainable statements paired with valid evidence IDs. Branch/ref/SHA, task statuses, progress counts, commands, incident impact states/targets/responders and source URLs are rendered from engine fields. LLM text may explain these facts but is validated against them; rejected output falls back to an engine template.

## HTTP surface

The response's `answer` includes an engine-owned `facts` array of currently permitted `AnswerFact` records and structured `statements` with text, fact IDs and evidence IDs. Its summary follows the same critical-fact/qualifier validation as statements. The client renders critical values from these facts and the typed decision; the model cannot supply replacement values or source links. This extends the answer shape above without granting model write authority.

| Endpoint | Purpose |
| --- | --- |
| `GET /health` | Liveness without secrets |
| `GET /ready` | Database and required configuration readiness; optional providers listed separately |
| `POST /query` | Resolve, retrieve, verify and explain |
| `GET /queries/{request_id}/trace` | Authorized access to stored bounded trace |
| `GET /service-instances` | Scoped instance picker with explicit environment/region and overflow handling |
| `POST /admin/import` | Operator-only snapshot/manifest ingestion; never model-accessible |

Expected uncertainty returns a typed response, not a server crash. Use 401/403 for authentication/authorization errors, 422 for invalid input, and 503 when the core graph is unavailable. Optional decision-provider and answer-provider failures have explicit fallbacks. Prototype trace storage may be local files with bounded retention; enterprise retention is Phase 7.

`GraphAvailabilityError`: `request_id`, `code` (`GRAPH_RECOVERY_REQUIRED`, `GRAPH_SNAPSHOT_CHANGED`), and a plain message, returned as HTTP 503 without a decision, answer or proposed commands. Dirty/uninitialized/unverifiable state or active exclusive import/recovery uses `GRAPH_RECOVERY_REQUIRED`; two generation changes across the one permitted request retry while state remains ready use `GRAPH_SNAPSHOT_CHANGED`. `/ready` returns 503 while imports/recovery block reads; `/health` remains live. Only authorized control-state inspection and operator import/recovery bypass the ordinary domain-read gate. Every graph-backed response, including an LLM answer, rechecks generation and active snapshot under the shared gate before publication; failures cannot fall back to an answer assembled from the invalidated graph.

## Incident and exploration extension

Requirement authority: [SRE event handling](../../SRE%20event%20handling.md). Graph authority: [SRE graph extension](sre_graph_schema.md). Coding sequence: [integration plan](sre_integration_plan.md). These are proposed contract additions, not running endpoints.

`AlertInput`: provider ID/event ID, permitted source scope, signature/deduplication key, occurred/received time, severity/raw state, optional service/instance/environment/region/release IDs and sanitized payload reference. Authentication is transport/provider-specific; an LLM does not authenticate payloads. `AlertReceipt`: alert/episode/job IDs, duplicate flag and durable acceptance time; acknowledgment does not imply completed investigation.

`IncidentState`: `OPEN`, `ACKNOWLEDGED`, `MITIGATED`, `MONITORING`, `RESOLVED`. Preserve provider states and map explicitly. Source/operator events own transitions; the answer model cannot close an incident. Reoccurrence after resolution creates a new episode while retaining a historical relationship.

`InvestigationState`: alert/incident/question, principal and source scope, event-time window, current node, pending nodes/checks, visited nodes/edges, evidence IDs, required-check statuses, call/token/row/depth/time budgets and stop reason. Each `InvestigationCheck` carries check ID, required flag, status (`KNOWN`, `MISSING`, `STALE`, `RESTRICTED`, `UNAVAILABLE`, `NOT_CHECKED`), attempted time, evidence IDs, coverage, and sanitized failure/limitation. MISSING requires a completed authorized lookup with sufficient coverage to establish absence; timeout/provider failure is UNAVAILABLE, and an unattempted check remains NOT_CHECKED. Several paths may remain pending.

The controller owns the required-check queue: instance/scope, incident-time and current deployment, ownership/current on-call, runtime dependencies, customer observations/coverage and current runbook. The model may order eligible reads, but cannot remove checks or change their outcomes. Accept a normal model STOP only when no required check is NOT_CHECKED and all attempted outcomes are recorded. On premature STOP, use a deterministic next required read within the remaining budget. On deadline/budget exhaustion, terminate with an explicit partial stop reason and unresolved checks. A brief may describe MISSING/STALE/RESTRICTED/UNAVAILABLE outcomes; execution requires all action-specific prerequisites to have complete, current, permitted evidence. KNOWN alone does not imply sufficient coverage.

`ExplorationDecision`: allowed action (`EXPLORE_NODE`, `FETCH_EVIDENCE`, `ASK_FOR_HELP`, `STOP`), selected option ID, question/choice-set version, provider/model metadata, optional probabilities/confidence and abstention reason. The exact option maps to a permitted node or supported evidence operation; an invented ID/action is rejected. Stop eligibility is checked in application code. Record each actual graph/evidence read as a `TraversalStep`.

`IncidentContext`: incident state, observations, operating scope, deployment timeline, current responder snapshot, possible explanations, impact assessments, applicable runbook sections, recovery options, message drafts, evidence IDs, required-check coverage and limitations. It has completeness/freshness fields separate from model confidence. It can remain useful when no executable plan is available.

`ResponderSnapshot`: service/escalation level, provider assignment IDs, employee/team IDs when known, effective start/end, override source, retrieved time and coverage. Use current notification time for a contact lookup, event time for historical response reconstruction. Gaps/multiple responders are explicit and never resolved by guessing the commit author.

`PossibleExplanation`: explanation ID, statement, related changes/services, supporting/conflicting evidence IDs, next check, and state (`POSSIBLE`, `SUPPORTED`, `REJECTED`, `CONFIRMED_BY_RESPONDER`). Confirmation requires actor, time and evidence. A stored model suggestion has no confirmation authority.

`ImpactAssessment`: service/feature/customer subject, region/environment, measurement window, state (`OBSERVED`, `POSSIBLE`, `NO_FAILURE_OBSERVED`, `UNKNOWN`), deduplicated source evidence, affected-operation description, optional recorded counts and measurement/mapping coverage. Count scope and sampling are explicit. Limited visibility cannot imply a complete company/customer total.

`RecoveryOption`: action kind, exact target instance, documented source/version, proposed target artifact/config, prerequisites, unresolved checks, expected effect and status (`PROPOSED`, `NEEDS_CHECKS`, `BLOCKED`). No `SAFE` status is inferred from model confidence or sandbox success.

`ActionPlan`: plan ID/version, incident/requester, action kind, environment/account/location/resource, expected deployment/resource version, current/target artifact or configuration, dependency/schema checks, evidence IDs, expiry, approval actor/time, idempotency key, proposed adapter arguments, recovery criteria and execution receipt. Status: `DRAFT`, `READY_FOR_REVIEW`, `APPROVED`, `RUNNING`, `SUCCEEDED`, `FAILED`, `EXPIRED`, `CANCELLED`, `UNKNOWN_OUTCOME`. Operation success and observed service recovery are separate fields. Unknown delivery/outcome requires state reconciliation before retry.

### POC sandbox execution protocol

The only POC operation is `RESTORE_SANDBOX_ARTIFACT` on one allowlisted disposable payments workload, with a healthy and a controlled-failure artifact. A versioned fixture compatibility record binds current/target artifact digests, configuration version and schema version; missing or incompatible evidence blocks READY_FOR_REVIEW. Approval binds the exact plan version, target state, expiry and compatibility record. Store plans and operation receipts in the retained transactional local store, outside graph rebuild deletion.

Use `DRAFT -> READY_FOR_REVIEW -> APPROVED -> RUNNING -> SUCCEEDED/FAILED/UNKNOWN_OUTCOME`. Pre-execution states may expire or be cancelled; changed targets require a new plan/approval rather than editing an approved version. Under a per-target execution gate, recheck permission/access, graph/evidence validity, actual target state, compatibility and expiry. Atomically claim APPROVED to RUNNING and persist a unique operation ID before the first side effect. Duplicate requests for the same plan/version return its current receipt/status; a different plan cannot claim an occupied target. The sandbox adapter is the sole target writer during the demo, including reset operations.

Persist the result and actual artifact identity after mutation. A restart with RUNNING or an uncertain acknowledgment becomes UNKNOWN_OUTCOME and keeps the target reserved for reconciliation. Read actual target state and retained operation evidence before any retry; observing the target artifact alone is insufficient to invent a successful receipt. If outcome cannot be established, retain uncertainty for operator reconciliation; do not automatically repeat the operation. FAILED means a known terminal outcome, not an unobserved timeout. Cancellation before the execution claim prevents mutation; after it, report the actual outcome rather than pretending the change was undone. Do not hold a graph read gate during execution or recovery sampling.

Keep operation outcome separate from recovery observations: send one synthetic request per second for 30 seconds, require all 30 successful responses and the expected served artifact identity for the demo recovery criterion, and retain timestamps/results. An interrupted measurement is incomplete. Operation success with failed/incomplete recovery never implies service recovery or incident closure. The concrete sandbox setup and restart cases are specified in the [SRE integration plan](sre_integration_plan.md#poc-sandbox-recipe).

`MessageDraft`: audience, permitted recipient/channel IDs, content/evidence, snapshot time and draft/send state. Sending authorization is separate from action-plan approval. Draft construction sends nothing.

Additional planned endpoints:

| Endpoint | Behavior |
| --- | --- |
| `POST /webhooks/{provider}` | Authenticate, durably store and enqueue; return 202 for accepted event |
| `GET /incidents/{incident_id}` | Authorized brief/status/timeline lookup |
| `POST /incidents/{incident_id}/investigate` | Validate exact instance scope, record operator selection if resolving a pending alert, then enqueue investigation |
| `POST /incidents/{incident_id}/events` | Authorized responder/provider decisions and lifecycle records |
| `POST /action-plans/{plan_id}/approve` | Approve exact version after target/permission checks |
| `POST /action-plans/{plan_id}/execute` | Revalidate and execute through a vetted adapter; sandbox-only in demo |

Existing `POST /query` remains read-only. Provider callbacks and controlled action executors may write incident audit/source records, but do not grant the navigation/answer model graph-write credentials. Add per-plan version checks and per-target serialization; stale approvals return a conflict/new-plan requirement rather than silently changing the target.

For the demo executor, a changed plan/target or target reserved by another operation returns HTTP 409 with a sanitized reason. An expired plan becomes EXPIRED without execution. Repeated requests for the same plan/version return its stored state and operation ID, including RUNNING or UNKNOWN_OUTCOME, rather than enqueueing another change.
