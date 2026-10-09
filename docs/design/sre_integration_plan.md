# SRE integration plan for the Company Brain

Status: planned, 2026-10-09. This is a coding plan and documentation integration, not an implemented agent or connected account. Requirements: [SRE event handling](../../SRE%20event%20handling.md). Data model: [SRE graph extension](sre_graph_schema.md). Reuse [contracts](contracts.md) and [existing phases](README.md).

## 1. Architecture decision

One Company Brain supports development questions and incident questions through the same entity identities, source adapters, permissions, decision-model interface, evidence store, traversal trace and answer LLM.

For incidents, use **model-guided graph exploration**. The decision model selects a next node or evidence request from application-provided choices. Application code fetches those choices, tracks several pending paths, enforces mandatory checks and records evidence. Known factual joins remain ordinary queries; there is no need to ask a model which commit a deployment record identifies.

```mermaid
flowchart TD
    Event[Monitoring event or engineer question] --> Receive[Validate, store and group events]
    Receive --> Resolve[Resolve service and operating location]
    Resolve --> Pending[Gather neighboring nodes and pending checks]
    Pending --> Model[Jev, Clef or evaluated Laya: choose next exploration]
    Model --> Read[Fetch facts and relevant document sections]
    Graph[Shared FalkorDB graph] --> Read
    Read --> Evidence[Store evidence and record visited paths]
    Evidence --> Pending
    Evidence --> Check[Check required coverage and source freshness]
    Check --> Brief[LLM writes cited incident brief]
    Brief --> Review[Engineer reviews next steps and action plan]
    Review --> Sandbox[Approved operation in disposable environment]
    Sandbox --> Outcome[Measure recovery and record outcome]
    Outcome --> Graph
```

Webhook acceptance and investigation are separate operations. Graph ingestion writes occur through source adapters. Investigation reads cannot change service state, close an incident or send a page. Action execution is a separately authorized operation, with a narrower interface than a general agent tool.

## 2. Graph access and MCP

Provide one `GraphReader` interface for exact lookup, permitted neighbors and approved read templates. Offer a direct FalkorDB adapter and a FalkorDB MCP adapter behind it. The [official MCP server](https://github.com/FalkorDB/FalkorDB-MCPServer) documents graph reads and writes, including read-only queries; that capability is not a reason to expose every tool to an incident model.

For the requested MCP path, pin the server version, use authenticated local transport, set/read-check supported read-only behavior and allowlist only the required graph/read operations. Validate request scope and parameters before the adapter call. Prevent graph creation/deletion and arbitrary write access from investigation. Test that malicious payloads cannot inject queries or access another company. Model outputs are IDs/action choices, never executable Cypher strings.

An MCP timeout returns partial investigation status; it does not trigger broader tool access. The direct adapter is a labeled fallback for availability/comparison, not a claim that MCP ran. Database schema/index operations remain operator-only.

## 3. Node exploration and stop conditions

For the POC, alerts identify an exact service instance. Interactive questions use the authorized `GET /service-instances` picker with labels such as `Payments / Demo / Region A`; selecting an instance submits a fresh query with existing scope fields. Validate all supplied IDs/environment/region together. An ambiguous or conflicting subject returns the typed 422 scope error in [contracts](contracts.md#poc-incident-scope-selection), without investigation conclusions. An accepted unresolved alert remains durably pending; an authorized explicit selection through the incident investigation endpoint is recorded before enrichment starts. Task/repository/branch continuation tokens remain unchanged.

Store `InvestigationState` with question/alert, operating scope, current node, pending candidate/check queue, visited node/edge IDs, retrieved evidence IDs, source snapshot, required-check status, token/call/time budget and stop reason.

Allow `EXPLORE_NODE`, `FETCH_EVIDENCE`, `ASK_FOR_HELP`, `STOP`. An option maps to an accessible actual neighbor or a supported evidence adapter. Candidate descriptions include relation direction, type, name, relevance summary and observation age. Model selection is validated against the exact current choice set.

Start with up to 10 choices per call, six navigation calls, 200 visited entities and eight relationship levels as configurable demo budgets. Related independent questions can be batched against the same state. A selected node may expose new choices requiring another request. Avoid repeatedly sending full documents; the evidence store retains their relevant sections for the final answer.

Mandatory checks: service/environment resolution, current and incident-time deployment coverage, ownership/current on-call, runtime dependencies within declared scope, customer evidence coverage and current runbook lookup. Initialize application-owned `InvestigationCheck` records before exploration. The model selects among eligible reads or optional context; it cannot remove a required check or set its outcome. Known joins execute in bounded templates. Record status, coverage, attempted time, evidence and sanitized failure for each check.

Use KNOWN for retrieved facts, MISSING only for an adequately complete authoritative lookup establishing absence, STALE for expired evidence, RESTRICTED for access denial, UNAVAILABLE for a failed/timed-out lookup, and NOT_CHECKED for unattempted work. Normal model STOP is accepted only when every required check has an attempted outcome; premature STOP selects the next required read deterministically while budget remains. Repeated STOP cannot create an unbounded model loop. On budget/deadline exhaustion, end with a partial stop reason and expose remaining NOT_CHECKED checks. A partial brief is useful; an action requires complete, current, permitted evidence for every action prerequisite. A recorded KNOWN status alone is insufficient. Optional PR discussion, similar incidents and design context remain model-prioritized.

When budget, access or a source fails, produce a partial brief with unresolved checks. Do not report full impact or an executable recovery plan from incomplete prerequisite data. Service-call cycles use visited tracking and can still be explored; they are not confused with an invalid task/action dependency ordering.

## 4. Shared-phase coding map

The earlier documents are plans, not completed code. Start with their common infrastructure rather than assuming it exists. The following describes the SRE deliverables in those same phases.

| Existing phase | Incident work to add | Completion evidence |
| --- | --- | --- |
| 0: foundation | Incident contracts, source scope and event/deployment fixtures | Payload examples and valid time/identity mappings |
| 1: graph | New labels/edges, versioned deployment/assignment records, read templates | Repeatable seed and incident-time queries |
| 2: ingestion | Event receiver, durable job record, duplicate handling, deployment/on-call manifests, observations | One repeated event; one incident; no duplicate proposed effects |
| 3: traversal | Neighbor reader, several pending paths, required-check coverage, customer exposure and action checks | Correct observed/possible outcomes and blocked incomplete plans |
| 4: models | Jev/Clef/Laya navigation choices, stopping/uncertainty, LLM-navigation comparison | Measured routing precision, missed evidence, cost and latency |
| 5: answers | Incident bundle, cited brief, recipient/action drafts and fallback | Real LLM explanation preserving facts/uncertainty |
| 6: demo | Incident page, timeline, evidence view and approved sandbox action | Replayed incident, reviewed plan and measured sandbox recovery |
| 7: production | Actual source integration, permissions, notification delivery and restricted production executor | Access/freshness/action checks plus operational readiness review |

## 5. Ordered coding work

Shared Phase 1 durable import recovery and Phase 2 live Plane/Google Docs gates apply to this incident path as well. Every direct or MCP graph read uses the same readiness/generation gate; dirty state or an invalidated snapshot cannot produce an incident brief, fallback answer or recovery proposal. Keep event receipts, lifecycle records and action audits in durable retained storage outside graph-projection rebuild deletion. Graph updates from accepted events use the serialized import protocol; webhook acceptance itself need not wait for graph recovery. The [source adapters](source_adapters.md) define live task/document coverage and labeled exports.

### Step A: seed and shared graph

Create proposed files `fixtures/sre/`, `backend/app/contracts/incident.py`, `backend/app/graph/templates/sre/`, `scripts/seed_sre.py` and `tests/integration/test_incident_time_graph.py`. Seed the requirements example using real generated Git revisions or explicit synthetic artifact IDs; never invent a supposedly verified production SHA. Preserve existing task/PR identities and query semantics.

Gate: the graph finds the correct historical rollout, current on-call override, current runbook and two customer paths. Region B is not folded into region A. Replay does not overwrite earlier deployment facts. Phase 1 interruption/restart recovery preserves the retained incident inputs and blocks reads until a full coherent rebuild succeeds.

### Step B: event handling and evidence adapters

Create `backend/app/ingestion/alerts.py`, `backend/app/incidents/{grouping,jobs,timeline}.py` and `backend/app/connectors/{monitoring,deployment,oncall,customer_usage}.py`. First use structured synthetic/exported records. Verify a real provider's payload/authentication contract before enabling its live receiver; do not label a mock receiver as a working Sentry integration.

Gate: duplicate delivery and retries converge on one alert/episode; unrelated alerts remain separate; accepted events survive a worker restart; redacted payloads and timestamps are retained; failed enrichment remains visible and retryable. A durable single-worker job table/file journal is sufficient for the demo; distributed production queue/failover semantics are Phase 7, while dirty graph recovery is required in Phase 1. Both shared live Plane/Google Docs smoke gates must pass; deployment/monitoring/on-call/customer inputs may remain explicitly synthetic/exported.

### Step C: exploration and conclusions

Create `backend/app/traversal/{neighbors,investigation}.py`, `backend/app/incidents/{changes,impact,responders,recovery_options}.py` and `backend/app/graph/mcp_reader.py`. Reuse the decision interface and extend it with a Clef adapter when accessible. Resolve known IDs first; ask the decision model for exploration ordering and ambiguity.

Gate: several dependency paths are retained; optional selection cannot drop required checks; a code deploy remains a possible explanation without confirming evidence; configuration-only failures are investigated; observed customer evidence is separate from possible exposure; runtime cycles terminate within limits; unauthorized results do not reach a model.

### Step D: brief and proposed action

Create `backend/app/context/incident_bundle.py`, `backend/app/answers/incident.py` and `backend/app/actions/{plans,validate}.py`. Use the existing evidence IDs and citations. Render targets, version IDs, current responder, impact states and action state from typed fields. The LLM explains; it cannot promote a hypothesis, approve a plan or invent a command.

Gate: real answer API output supports every factual claim with supplied evidence; injected source instructions, unavailable models and unknown citations trigger useful fallback. Plans bind exact service instance, environment, observed deployment state and target artifact; missing schema/config compatibility blocks execution. Message drafts remain drafts.

### Step E: sandbox and responder demonstration

Create `backend/app/actions/sandbox.py`, `frontend/src/components/{IncidentPage,IncidentTimeline,ImpactList,ActionReview}.tsx`, `scripts/replay_incident.py` and `tests/end_to_end/test_sre_incident.py`. The sandbox adapter accepts only a vetted deployment restoration in a disposable local environment. Display an explicit confirmation and record approval separately from execution.

Gate: approved operation changes the intended disposable target once; repeated requests do not repeat it; changed state/expired approval refuses execution; recovery checks show actual sandbox results; no production credentials or outbound messaging tools are used. Verify cancellation, partial failure and actual-state re-read before retries.

### POC sandbox recipe

Implement one `RESTORE_SANDBOX_ARTIFACT` adapter for a disposable local payments workload. Build two immutable artifact versions: one healthy and one with a controlled request failure. Retain their digests and actual served version identity. The fixture manifest supplies a versioned compatibility record for current/target artifact, configuration and schema. Unknown/incompatible combinations cannot produce a review-ready plan. A second scenario changes schema compatibility and must block the same proposed restoration.

Use the [canonical execution protocol](contracts.md#poc-sandbox-execution-protocol). Store exact plan version, approval actor/time, target state, expiry, compatibility record and unique operation ID in retained transactional local storage. The sandbox adapter is the only target writer; route reset through it as a separately controlled demo operation when no execution/reconciliation is active. The per-target gate serializes recheck and execution; no model-written scripts or mutable target substitutions are accepted.

After permission, evidence, target-state and expiry checks, atomically claim APPROVED to RUNNING and persist the operation before mutation. Repeated requests return existing status/receipts. Persist terminal outcome and actual artifact identity afterward. On process restart or ambiguous acknowledgment, retain UNKNOWN_OUTCOME and reserve the target until actual-state/receipt reconciliation succeeds. Do not infer successful execution solely from a matching target digest or automatically retry an unobserved operation. An unresolved case requires operator reconciliation. Pre-claim cancellation prevents changes; post-claim cancellation cannot claim the operation was undone.

Verify recovery with one synthetic request per second for 30 seconds. All 30 must succeed and the expected artifact identity must be confirmed for the demo criterion; retain timestamped samples. Interrupted sampling is incomplete, and failed checks do not erase an otherwise known execution outcome. Display operation outcome and recovery result separately; neither closes the incident automatically.

Required cases: approved restoration, missing approval, duplicate/concurrent execution, expired plan, moved target, incompatible/unknown schema, cancellation before claim, crash after RUNNING but before mutation, crash after mutation before receipt, receipt persistence failure and interrupted/failed recovery sampling. Resume from durable records rather than repeating a side effect. These are future implementation gates, not passed tests.

## 6. Practical sprint allocation

The original SRE-focused 48-hour estimate used the same 36-hour planning envelope: 2 hours foundation, 4 graph, 6 ingestion, 8 traversal/checks, 5 model evaluation, 4 answers, 7 UI/sandbox/rehearsal, plus 12 hours recovery. These estimates are provisional under the required recovery/live-adapter scope and must be re-estimated after compatibility checks. This is an alternative demo allocation, not an extra 36 hours added to the original plan.

Delivering every development workflow and every incident workflow within that window is not promised. Keep shared schema/contract compatibility and retain development fixtures for regression when those workflows are implemented. If time runs short, cut additional live operational connectors, optional design-discussion retrieval and elaborate visuals. Preserve durable recovery, candidate-specific revision effects, live Plane/Google Docs task/document reads, evidence correctness and a real model-guided traversal-to-LLM example. Export fallback cannot pass the full live gate. If sandbox action remains unfinished, label the result as advisory and do not claim Track 01 action execution was demonstrated.

Track 01/03 alignment has been checked against the public event pages on 2026-10-09. The [FalkorDB resource plan](falkordb_resources_and_hackathon_plan.md) records current track guidance, submission requirements and the user's reported organizer permission to code early. It recommends a focused incident/recovery demonstration and maps the official SDK/tools to these same phases. Recheck any announced rule changes before submission.

## 7. Acceptance suite and evaluation

Seed at least 20 distinct incident scenarios covering the requirements list, with expected source scope, responder, deployment, possible/observed customer effects, plan eligibility and stop reason. Keep scenario variants in the same evaluation split to avoid teaching on the test case. Human review of briefs is necessary alongside contract tests.

Compare three navigators: direct graph/rules baseline, a general LLM selecting from the same allowed neighbors, and a decision model selecting from those neighbors. Keep source snapshots, permitted tools, mandatory checks, budgets, final answer model and evidence expectations constant. Compare cost per correctly grounded brief, missed paths, wrong selections, source reads, retries, answer-input size, latency and operator time. Report unavailable providers as unevaluated and synthetic cases as synthetic.

Record any failure that calls a hypothesis a confirmed cause, calls possible exposure an observed failure, chooses the wrong responder, sends a duplicate message or executes an unapproved/stale plan. None are acceptable in the controlled demo suite. Passing the suite is not proof of safe unattended production operation.

## 8. Live-release prerequisites

Select authoritative deployment/catalog/on-call/customer sources and approved actions. Add provider-specific authenticated receivers, reconciliation, access revocation, redacted telemetry, bounded retention, current-state checks and audit storage. Production notifications require verified recipients and organization policy. Production changes require scoped credentials, approvals, per-target locks, idempotency and recovery observations. Existing source monitoring/paging continues to work when the assistant is down.

Reliability follow-up tasks and reviewed incident history become ordinary Company Brain knowledge. Preserve correction history and source authority so an old model explanation does not become a trusted fact merely because it was stored.
