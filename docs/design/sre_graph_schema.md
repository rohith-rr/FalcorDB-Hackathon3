# SRE additions to the Company Brain graph

Status: proposed schema extension, 2026-10-09. Applies with the identity, permissions, source ownership and evidence rules in the [canonical schema](graph_schema.md). Product behavior is defined in [SRE event handling](../../SRE%20event%20handling.md).

## Shared entities and names

Reuse `Repository`, `Commit`, `PullRequest`, `Review`, `Task`, `Epic` and `Document`; do not copy them into an incident database with new identities. Use `Service` for applications and dependencies, with a `service_kind` such as `APPLICATION`, `DATABASE`, `QUEUE` or `EXTERNAL`. A microservice is a service, not a separate identity. Use `Employee` for verified company identities and `Customer` for customer organizations; an enterprise tier is a property, not a different customer identity.

Existing task/PR direction stays `Task-[:IMPLEMENTED_BY]->PullRequest`. Source aliases such as PDF `PullRequest-[:IMPLEMENTS]->Task` normalize to that direction. Existing review nodes retain state and reviewed revision; a shorthand employee-to-PR edge cannot replace them.

## Additional nodes

All nodes retain the canonical source reference, tenant, snapshot and observation fields. IDs use source-native identifiers; do not merge services by display name across accounts/environments.

| Node | Required operational properties |
| --- | --- |
| `Alert` | provider event/issue IDs, deduplication identity, signature, occurred/received times, raw state/severity, sanitized payload reference, service-resolution status |
| `Incident` | episode ID, lifecycle state, opened/acknowledged/mitigated/resolved times when known, source owner, assigned roles, severity policy version |
| `Service` | catalog ID, name, service kind, repository bindings, ownership source, applicability scope |
| `ServiceInstance` | logical workload ID, service ID, provider account/cluster/namespace or equivalent, environment, region, current state/version observation |
| `Deployment` | provider deployment/revision ID, started/completed times, observed outcome, target instance, change reference, rollback-history availability |
| `Artifact` | immutable deployed package/image ID or digest, build provenance reference, build revisions, provenance completeness |
| `Change` | source change ID, kind (`CODE`, `CONFIG`, `SCHEMA`, `FEATURE_FLAG`, `INFRASTRUCTURE`), effective time, bounded before/after references, affected scope |
| `Team` | directory ID, name, escalation/service ownership references |
| `Employee` | verified directory ID, provider identity mappings and access scope; no guessed email-to-user match |
| `OnCallAssignment` | provider assignment ID, service/escalation level, person, effective start/end, override source, retrieved time |
| `ProductFeature` | stable feature ID, name, customer-visible operation and routing/source reference |
| `Customer` | stable customer ID, authorized display name, optional support tier, usage-mapping source/coverage |
| `Observation` | kind, source, subject, measurement start/end, sample/coverage description, value or content reference |
| `IncidentEvent` | event ID, incident ID, event kind, actor/provider, occurred/recorded times, evidence references |
| `ActionPlan` | plan ID/version, kind, exact target, expected state, proposed state, prerequisites, approval status, expiry and outcome references |

An artifact is the deployable image/package with a fixed identifier. A service instance represents a workload in a particular operating location, not every temporary process. An individual process can be linked later if its identity is needed for diagnosis.

Keep bulk logs and metric series in their source systems. Store bounded observation summaries and retrievable references, not every log line as a graph node. Runbooks reuse `Document:ProcessDoc` with `document_role = RUNBOOK`; post-incident reports use `Document:Postmortem` and retain reviewed/draft status.

## Relationships

| From | Edge | To | Meaning |
| --- | --- | --- | --- |
| `Alert` | `FIRED_ON` | `Service` | Confirmed logical service identity |
| `Alert` | `OBSERVED_ON` | `ServiceInstance` | Location-specific signal, when known |
| `Alert` | `PART_OF` | `Incident` | Investigation episode, with grouping evidence |
| `Service` | `HAS_INSTANCE` | `ServiceInstance` | Environment/region workload |
| `ServiceInstance` | `DEPENDS_ON` | `ServiceInstance` | Caller needs destination; includes required/optional/fallback behavior |
| `Deployment` | `DEPLOYED_TO` | `ServiceInstance` | Rollout record, including valid interval and known served fraction |
| `Deployment` | `DEPLOYS_ARTIFACT` | `Artifact` | Exact deployed package/image |
| `Artifact` | `BUILT_FROM` | `Commit` | Verified build revision; may include several repositories |
| `PullRequest` | `CONTAINS` | `Commit` | Source-owned PR commit membership, not automatically squash equivalence |
| `Commit` | `AUTHORED_BY` | `Employee` | Verified author mapping |
| `Review` | `SUBMITTED_BY` | `Employee` | Actual individual reviewer |
| `Task` | `ASSIGNED_TO` | `Employee` | Tracker assignment; distinct from authorship |
| `Service` | `OWNED_BY` | `Team` | Catalog ownership |
| `Employee` | `MEMBER_OF` | `Team` | Directory membership |
| `OnCallAssignment` | `COVERS` | `Service` | Service/escalation responsibility |
| `OnCallAssignment` | `ASSIGNS` | `Employee` | Effective responder assignment |
| `Customer` | `USES` | `ProductFeature` | Current usage/entitlement mapping, with scope and coverage |
| `ProductFeature` | `SERVED_BY` | `ServiceInstance` | Feature routing in the relevant environment/region |
| `Observation` | `OBSERVED_ON` | `ServiceInstance` | Runtime measurement/report subject |
| `Observation` | `FOR_CUSTOMER` | `Customer` | Known customer scope, only when source records it |
| `Change` | `AFFECTS` | `ServiceInstance` | Effective runtime change scope |
| `Change` | `LINKED_PR` | `PullRequest` | Optional explicit code/config change provenance |
| `Document:ProcessDoc` | `RUNBOOK_FOR` | `Service` | Operating instructions with applicability/version |
| `Incident` | `HAS_EVENT` | `IncidentEvent` | Timeline and decision history |
| `Incident` | `HAS_PLAN` | `ActionPlan` | Proposed/approved/completed action record |
| `Incident` | `HAS_OBSERVATION` | `Observation` | Evidence collected in investigation |
| `Document:Postmortem` | `DESCRIBES` | `Incident` | Reviewed/draft analysis |
| `Incident` | `FOLLOWED_UP_BY` | `Task` | Owned reliability work in the existing tracker |

Incident roles are versioned assignment records within `IncidentEvent`, with employee IDs, role, start/end and source. Avoid a permanent employee role edge implying responsibility for every incident.

## Time, truth and permissions

Runtime relations and assignments add `valid_from`, nullable `valid_to`, `recorded_at`, `time_accuracy`, scope and completeness. These are separate from ingestion time. Reconstruct the workload at the alert's time; query on-call at the proposed notification time. Keep both old/new deployments during partial rollouts; unknown served fraction remains unknown. Do not collapse everything into a timeless `Service-RUNS_COMMIT->Commit` edge.

Dependency directions are explicit: checkout depends on payments; a payments failure may affect checkout. That path establishes possible exposure. Observations determine whether failures were recorded. Optional dependencies and fallback behavior may reduce effects; reachability alone cannot calculate exact impact.

Confirmed catalog/build/provider mappings support operational conclusions. Model-inferred connections remain candidates until source/operator confirmation. A traversed path does not become a confirmed cause edge. Customer counts carry permission/coverage limits; restricted names or total counts cannot leak through a path or aggregate.

Runtime call cycles are valid facts; use visited IDs and budgets for investigation. Existing task dependency cycles still block a code plan. A requested multi-step recovery sequence needs its own valid ordering/compatibility constraints; a cyclic or unknown action ordering blocks execution, not evidence retrieval.

## Authority and minimum seed

Monitoring owns alerts/observations; deployment controller and build records own deployment/artifact mappings; catalog/tracing owns service relationships with declared coverage; directory owns identity; on-call provider owns effective assignments; customer usage/routing records own customer paths. The Company's existing source ownership for tasks, reviews and documents is unchanged. Incident decisions and approvals are explicit authored records, not generated facts.

Minimum synthetic seed: checkout, payments, inventory and a database dependency; region A and B instances; a healthy and a newer payments artifact; known rollout/time records; one PR/task/design path; individual reviewer and author identities; a current on-call override; two customer-feature paths; a current runbook; observation records and an older reviewed incident. Add configuration-only and partial-rollout variants.

No data provider or graph transport is configured by writing this schema. Executable query/index compatibility and fixtures must be checked during coding.
