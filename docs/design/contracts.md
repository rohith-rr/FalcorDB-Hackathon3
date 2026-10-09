# Shared application contracts

Status: proposed. Implement these as Pydantic models in `backend/app/contracts/`. This document is canonical; provider response shapes stay inside adapters.

## Request and resolution

`QueryRequest`: `question`, optional `project_id`, `repository_id`, `task_id`, `incident_id`, `service_id`, `service_instance_id`, and `requested_intent`. Intent values are `BRANCH_BASE`, `TASK_CONTEXT`, `BLOCKERS`, `EPIC_PROGRESS`, `INCIDENT_BRIEF`, `INCIDENT_HISTORY`, `OTHER`. Incident requests also carry an optional event-time window and operating scope; the server validates all scope against the principal.

The server derives `tenant_id` and `principal_id` from authentication/configured demo identity. A client cannot select an arbitrary tenant. Resolve a fully scoped exact task key first; otherwise retrieve accessible candidates. Resolution is `RESOLVED`, `NEEDS_CLARIFICATION`, `NOT_FOUND` or `UNSUPPORTED`. A clarification includes only accessible candidate labels/IDs and a continuation token; subsequent requests retain original scope.

Clarification may be needed after task resolution when repository bindings or verified branch candidates remain ambiguous. In that case the response retains the resolved task and relevant accessible evidence, sets resolution to `NEEDS_CLARIFICATION`, and leaves the branch decision null until selection is settled.

## Snapshot and evidence

`SnapshotRef`: `snapshot_id`, `generation`, `mode` (`FIXTURE`, `IMPORT`, `LIVE`), `observed_at`, `ingested_at`, `scope`, `complete`, `source_version`. Generation is a monotonic import fence, not a source version.

`ImportState`: managed graph identity, `state` (`UNINITIALIZED`, `DIRTY`, `READY`), nonnegative `generation`, nullable `active_snapshot_id`, nullable `pending_bundle_id`, nullable `pending_bundle_hash`, `updated_at`, nullable sanitized `last_failure`. Missing/unreadable state is treated as `UNINITIALIZED`; no application domain read is allowed without `READY` and a validated active snapshot. `DIRTY` is persisted before domain mutation; recovery rebuilds the complete graph before publication. Publication sets the active snapshot, clears pending fields and sets `READY` in one durable graph write. See [Phase 1](phase_01_graph_and_fixtures.md#snapshot-consistency).

`ImportReport`: bundle ID/hash, previous/published snapshot IDs, generation, outcome (`PREPARATION_FAILED`, `RECOVERY_REQUIRED`, `PUBLISHED`), source scopes/coverage, validation conflicts, timestamps and sanitized failure details. An import interrupted after dirty publication cannot report the old snapshot as readable. Source observations retain their age after recovery.

`EvidenceItem`: `evidence_id`, `kind`, `entity_ids`, `source_url` (optional for local fixtures), `source_record_ref`, `source_version`, `observed_at`, `verified_at` (optional), `snapshot_id`, `generation`, `content_hash`, and a bounded `excerpt` or typed `value`. Supported kinds include task fields, confirmed relationship, document section, PR state, review state, branch head, revision effect and Git coverage. Document sections also retain version-bound `tab_id` (nullable for Markdown) and `section_anchor`. Local fixtures link to a visible fixture record instead of an invented company URL.

`TraversalStep`: `step_id`, `template_id`, sanitized `parameters`, `node_ids`, `edge_ids`, `evidence_ids`, `selection_method`, `duration_ms`, `stop_reason`. Record model metadata separately: provider, model/checkpoint revision, question version, option-set hash, probabilities, selected value and abstention reason. Do not log credentials or inaccessible content.

Snapshot completeness, freshness and inference uncertainty are independent. A high model confidence cannot make an incomplete source snapshot complete.

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

`ContextBundle`: `request_id`, resolved intent/entities, snapshots, typed facts, nullable branch decision, nullable incident context, task/dependency summaries, selected document sections, review summaries, epic counts, evidence items, traversal steps and limitations. Enforce provider token budgets while retaining all decision evidence and coverage counts; omitted narrative content is reported.

`QueryResponse`: `request_id`, `resolution`, `decision`, `answer`, `citations`, `trace`, `limitations`, and `timings`. `decision` is nullable and explicitly tagged as `BRANCH` or `INCIDENT`; an incident context never masquerades as a branch recommendation. `answer` contains `mode` (`LLM`, `DETERMINISTIC`), a short summary and explainable statements paired with valid evidence IDs. Branch/ref/SHA, task statuses, progress counts, commands, incident impact states/targets/responders and source URLs are rendered from engine fields. LLM text may explain these facts but is validated against them; rejected output falls back to an engine template.

## HTTP surface

| Endpoint | Purpose |
| --- | --- |
| `GET /health` | Liveness without secrets |
| `GET /ready` | Database and required configuration readiness; optional providers listed separately |
| `POST /query` | Resolve, retrieve, verify and explain |
| `GET /queries/{request_id}/trace` | Authorized access to stored bounded trace |
| `POST /admin/import` | Operator-only snapshot/manifest ingestion; never model-accessible |

Expected uncertainty returns a typed response, not a server crash. Use 401/403 for authentication/authorization errors, 422 for invalid input, and 503 when the core graph is unavailable. Optional decision-provider and answer-provider failures have explicit fallbacks. Prototype trace storage may be local files with bounded retention; enterprise retention is Phase 7.

`GraphAvailabilityError`: `request_id`, `code` (`GRAPH_RECOVERY_REQUIRED`, `GRAPH_SNAPSHOT_CHANGED`), and a plain message, returned as HTTP 503 without a decision, answer or proposed commands. Dirty/uninitialized/unverifiable state or active exclusive import/recovery uses `GRAPH_RECOVERY_REQUIRED`; two generation changes across the one permitted request retry while state remains ready use `GRAPH_SNAPSHOT_CHANGED`. `/ready` returns 503 while imports/recovery block reads; `/health` remains live. Only authorized control-state inspection and operator import/recovery bypass the ordinary domain-read gate. Every graph-backed response, including an LLM answer, rechecks generation and active snapshot under the shared gate before publication; failures cannot fall back to an answer assembled from the invalidated graph.

## Incident and exploration extension

Requirement authority: [SRE event handling](../../SRE%20event%20handling.md). Graph authority: [SRE graph extension](sre_graph_schema.md). Coding sequence: [integration plan](sre_integration_plan.md). These are proposed contract additions, not running endpoints.

`AlertInput`: provider ID/event ID, permitted source scope, signature/deduplication key, occurred/received time, severity/raw state, optional service/instance/environment/region/release IDs and sanitized payload reference. Authentication is transport/provider-specific; an LLM does not authenticate payloads. `AlertReceipt`: alert/episode/job IDs, duplicate flag and durable acceptance time; acknowledgment does not imply completed investigation.

`IncidentState`: `OPEN`, `ACKNOWLEDGED`, `MITIGATED`, `MONITORING`, `RESOLVED`. Preserve provider states and map explicitly. Source/operator events own transitions; the answer model cannot close an incident. Reoccurrence after resolution creates a new episode while retaining a historical relationship.

`InvestigationState`: alert/incident/question, principal and source scope, event-time window, current node, pending nodes/checks, visited nodes/edges, evidence IDs, required-check statuses, call/token/row/depth/time budgets and stop reason. A check is `KNOWN`, `MISSING`, `STALE`, `RESTRICTED` or `NOT_CHECKED`; several possible paths can remain pending. Partial output records unresolved checks.

`ExplorationDecision`: allowed action (`EXPLORE_NODE`, `FETCH_EVIDENCE`, `ASK_FOR_HELP`, `STOP`), selected option ID, question/choice-set version, provider/model metadata, optional probabilities/confidence and abstention reason. The exact option maps to a permitted node or supported evidence operation; an invented ID/action is rejected. Stop eligibility is checked in application code. Record each actual graph/evidence read as a `TraversalStep`.

`IncidentContext`: incident state, observations, operating scope, deployment timeline, current responder snapshot, possible explanations, impact assessments, applicable runbook sections, recovery options, message drafts, evidence IDs, required-check coverage and limitations. It has completeness/freshness fields separate from model confidence. It can remain useful when no executable plan is available.

`ResponderSnapshot`: service/escalation level, provider assignment IDs, employee/team IDs when known, effective start/end, override source, retrieved time and coverage. Use current notification time for a contact lookup, event time for historical response reconstruction. Gaps/multiple responders are explicit and never resolved by guessing the commit author.

`PossibleExplanation`: explanation ID, statement, related changes/services, supporting/conflicting evidence IDs, next check, and state (`POSSIBLE`, `SUPPORTED`, `REJECTED`, `CONFIRMED_BY_RESPONDER`). Confirmation requires actor, time and evidence. A stored model suggestion has no confirmation authority.

`ImpactAssessment`: service/feature/customer subject, region/environment, measurement window, state (`OBSERVED`, `POSSIBLE`, `NO_FAILURE_OBSERVED`, `UNKNOWN`), deduplicated source evidence, affected-operation description, optional recorded counts and measurement/mapping coverage. Count scope and sampling are explicit. Limited visibility cannot imply a complete company/customer total.

`RecoveryOption`: action kind, exact target instance, documented source/version, proposed target artifact/config, prerequisites, unresolved checks, expected effect and status (`PROPOSED`, `NEEDS_CHECKS`, `BLOCKED`). No `SAFE` status is inferred from model confidence or sandbox success.

`ActionPlan`: plan ID/version, incident/requester, action kind, environment/account/location/resource, expected deployment/resource version, current/target artifact or configuration, dependency/schema checks, evidence IDs, expiry, approval actor/time, idempotency key, proposed adapter arguments, recovery criteria and execution receipt. Status: `DRAFT`, `READY_FOR_REVIEW`, `APPROVED`, `RUNNING`, `SUCCEEDED`, `FAILED`, `EXPIRED`, `CANCELLED`, `UNKNOWN_OUTCOME`. Operation success and observed service recovery are separate fields. Unknown delivery/outcome requires state reconciliation before retry.

`MessageDraft`: audience, permitted recipient/channel IDs, content/evidence, snapshot time and draft/send state. Sending authorization is separate from action-plan approval. Draft construction sends nothing.

Additional planned endpoints:

| Endpoint | Behavior |
| --- | --- |
| `POST /webhooks/{provider}` | Authenticate, durably store and enqueue; return 202 for accepted event |
| `GET /incidents/{incident_id}` | Authorized brief/status/timeline lookup |
| `POST /incidents/{incident_id}/investigate` | Enqueue a scoped read investigation |
| `POST /incidents/{incident_id}/events` | Authorized responder/provider decisions and lifecycle records |
| `POST /action-plans/{plan_id}/approve` | Approve exact version after target/permission checks |
| `POST /action-plans/{plan_id}/execute` | Revalidate and execute through a vetted adapter; sandbox-only in demo |

Existing `POST /query` remains read-only. Provider callbacks and controlled action executors may write incident audit/source records, but do not grant the navigation/answer model graph-write credentials. Add per-plan version checks and per-target serialization; stale approvals return a conflict/new-plan requirement rather than silently changing the target.
