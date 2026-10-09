# SRE event handling

Requirement document for the Company Brain incident assistant. Proposed, 2026-10-09. This document and the linked integration plan describe future implementation; they do not claim a working incident system.

## 1. Purpose

When a production problem occurs, help the responding engineer answer five questions quickly: what is failing, who is handling it, which users may be affected, what changed, and what can be done next.

Use the existing Company Brain to connect monitoring events to deployed software, service dependencies, ownership, schedules, tasks, PRs, reviews, runbooks and past incidents. A decision model chooses useful nodes to explore. The application records the evidence it retrieves. An LLM then writes a clear incident brief from that evidence.

The first release gathers information and prepares proposed actions. Engineers remain responsible for production changes and incident decisions. Later releases can carry out approved, narrowly scoped actions.

**Revised pitch:** When an alert arrives, the Company Brain brings together the service's current deployment, dependencies, on-call schedule, recent changes and operating instructions. It shows what is known, which customers may be affected, and the recovery options that have supporting evidence, so an engineer can act without searching across several tools.

## 2. What real SRE work involves

The immediate aim is to reduce harm and restore service. Finding a complete explanation may continue after recovery. Google's incident-response guidance separates restoration from coordination and communication, and recommends mitigation before detailed cause analysis. [Incident response](https://sre.google/workbook/incident-response/).

For this product, support the following work:

| Engineer's task | Useful connected information | Product result |
| --- | --- | --- |
| Check the alert | Failing requests, affected environment/region, monitoring links, recent observations | A concise description of the observed problem |
| Reach the right people | Service owner, current on-call assignment, escalation policy | Current responder and fallback team |
| Establish scope | Services that call the failing service, customer feature usage, regional routing, actual errors | Confirmed effects, possible effects and missing measurements |
| Investigate changes | Deployments, configuration, flags, schema changes, PRs and design decisions | A timeline and possible explanations with evidence |
| Reduce the impact | Current runbook, prior healthy deployment, operating constraints | Recovery options with prerequisites and reasons to withhold an action |
| Coordinate responders | Acknowledgments, assigned incident roles, decisions and handover notes | Shared incident record and suggested next checks |
| Verify recovery | Request success, latency, backlog and agreed checks over time | Recovery evidence; no automatic declaration based on one green alert |
| Prevent recurrence | Past incidents, reviewed explanations and owned follow-up tasks | A post-incident draft and trackable work |

A larger response may need someone coordinating the incident, someone leading technical work and someone handling updates. Smaller teams can combine roles. Keep assignments and handovers explicit rather than creating roles automatically from employee titles. [Managing incidents](https://sre.google/sre-book/managing-incidents/).

Outside incidents, the same data can help with shift handovers, finding missing runbooks, reviewing changes to shared services, and tracking overdue reliability work. Monitoring remains the source of measurements; the graph helps connect those measurements to company context.

## 3. How the supplied PDF is incorporated

Source: [SRE Outage Agent Requirements.pdf](<SRE Outage Agent Requirements.pdf>), 12 pages. The following interpretation supersedes its implementation claims for this project.

| PDF topic | Adopted requirement or correction |
| --- | --- |
| Response roles and scattered information, p. 1 | Preserve responder coordination, communication and linked sources. |
| Incident analysis and research methods, pp. 2-5 | Keep multiple explanations and supporting/rejecting evidence. Research algorithms are later experiments, not MVP dependencies. Do not carry forward unverified success percentages. |
| Commercial product comparison, pp. 5-6 | Treat as background. Do not claim that existing products cannot act, identify owners or connect customers without a current product evaluation. |
| Graph and semantic search, pp. 6-8 | Use explicit relationships for context and optional text search for documents. Remove a universal five-hop limitation and claims of automatic factual certainty. |
| Service, code, task and employee chain, p. 8 | Reuse existing PR/task/commit/review nodes; add deployment history and current on-call assignments. Task assignment does not prove authorship or current on-call responsibility. |
| Error routing and minimum six-hop query, p. 9 | Resolve explicit service IDs first; use model-guided exploration for ambiguous context. Query the relationships needed, regardless of hop count. |
| Exact breaking commit and business impact, p. 9 | Show possible changes and observed impact. Connections alone do not prove cause, actual outage or financial loss. |
| Proposed revert and restricted execution, p. 9 | Prepare an action package. Separate source-code revert from deployment rollback; require deployment-specific checks and explicit authorization before production execution. |
| Updates, permissions and cycles, p. 10 | Preserve history and freshness, restrict access, parameterize queries and bound traversal. Service-call cycles are allowed; an impossible action ordering blocks the proposed sequence. |
| Incident history and learning, pp. 10-11 | Retain observations, decisions and outcomes. Track recovery, incident closure and follow-up completion separately. |
| Sub-second remediation, pp. 9-11 | Measure ingestion, graph reads, model calls, source refresh and final explanation separately. No end-to-end sub-second promise. |

## 4. First release and later scope

First release: synthetic Sentry-style events; one company; one repository; three application services; two regions; two customer organizations; exported deployment/on-call data; current runbooks; recorded measurements; and a sandbox for one approved recovery demonstration. Include a database dependency as a service of kind `DATABASE`. All sample data is labeled synthetic.

Produce an incident brief, evidence paths, a current responder lookup, recent change list, observed/possible customer effects, recovery options, message drafts and incident history. The sandbox demonstration changes a disposable service to a recorded earlier version and checks recovery; it sends no real pages or Slack messages and touches no production environment.

Later: real monitoring/deployment/on-call connectors, an approved test-channel notification, per-user access controls, configuration/flag providers, live customer measurements and controlled production actions. Automated diagnosis from raw telemetry, automatic arbitrary scripts and guaranteed root-cause discovery are outside the first release.

This is an extension of the Company Brain, not a separate graph or a rewrite of the branch-selection use case. See the [shared schema extension](docs/design/sre_graph_schema.md) and [integration plan](docs/design/sre_integration_plan.md).

## 5. Required behavior

### REQ-SRE-01: receive and group events

Validate payloads and producer identity, record provider/event IDs and event/receipt times, store the event durably, and return promptly. Run enrichment in background work so a slow model does not block webhook acknowledgment. Reject unauthorized sources and strip secrets/personal data from model input.

Duplicate deliveries update the existing alert without duplicating the incident or a notification. Group related alerts only when service scope, time window and correlation evidence agree; retain every source event and allow a responder to split/merge groups. Two similar messages in different regions or environments must not be combined automatically. A new occurrence after closure creates a new episode.

Distinguish transport duplication from several services reporting related symptoms. Grouping is a suggestion about a shared investigation, not proof of a common cause. PagerDuty exposes event actions and deduplication keys; preserve provider semantics when a live connector is added. [PagerDuty Events API](https://docs.pagerduty.com/developer/api/reference/events-v2/send-event/create-v2-event).

### REQ-SRE-02: identify service and current responder

Prefer stable provider/service IDs and environment/region tags. If these are absent, retrieve scoped service candidates and let Jev, Clef or an evaluated Laya adapter choose a candidate or request help. A high model score cannot overwrite contradictory source identity.

Resolve the service's current on-call assignment for the relevant time and escalation level. Account for overrides, several responders, schedule gaps and shift handovers. Refresh before any notification. Code authors/reviewers are useful contacts, but they are not automatically the people to page. PagerDuty connects services to schedules through escalation policies. [Schedules and escalation policies](https://support.pagerduty.com/main/docs/escalation-policies-and-schedules), [shift overrides](https://support.pagerduty.com/main/docs/my-on-call-shifts).

### REQ-SRE-03: explore the graph with decision models

The application retrieves authorized neighboring nodes, with relation direction, names, short summaries, source times and scope. The decision model chooses a next node or action from those candidates. Record the choice, question version, available choices and visited path.

Maintain several pending paths. Required checks include current deployment, ownership, relevant measurements, service dependencies and runbook availability. A model chooses exploration order and optional context; it cannot remove mandatory checks or claim complete customer coverage after exploring only one path. Include `ASK_FOR_HELP` and `STOP` choices, with application checks before stopping.

Fetch full relevant node facts and document sections into an evidence store. Send compact summaries to navigation calls and the collected relevant facts/paths to the final LLM. On a limit, model failure or unresolved candidate, return a useful partial brief and mark missing coverage. The final LLM does not need to rediscover the graph to answer.

### REQ-SRE-04: establish what was running and what changed

Identify the deployment and immutable artifact active in the affected environment, region and time window. Retain mixed-version rollouts. Link artifacts to confirmed build revisions and revisions to existing PRs, reviews, tasks and design documents.

List code, configuration, feature-flag, schema and infrastructure changes when source records exist. Show first observed failures alongside change times, with time uncertainty. A change occurring near an alert is a lead, not a conclusion. An unchanged code revision must still permit a configuration or dependency investigation.

### REQ-SRE-05: support explanations without assigning blame

For each possible explanation, record the observation, relevant change/dependency, supporting evidence, conflicting evidence and next check. States are `POSSIBLE`, `SUPPORTED`, `REJECTED` and `CONFIRMED_BY_RESPONDER`. Only an authorized responder can confirm an explanation, with cited evidence; later corrections are recorded.

The running revision is not automatically the failing change. Sentry's suspect-commit feature uses stack-trace information to find candidates, reinforcing why a candidate should remain labeled as such. [Sentry suspect commits](https://sentry.io/changelog/2023-12-4-improvements-to-suspect-commits/).

Show authors and actual review records for context. Avoid wording that identifies an employee as the cause. Distinguish reviewed revision, dismissed review and current implementation. An incident may have several contributing conditions.

### REQ-SRE-06: estimate effects on services and customers

Follow service calls in both useful directions: the services a failing service calls for investigation, and the services that call it for possible effects. Restrict to the affected environment/region and edge validity window. Cycles use visited-node tracking; they do not make impact retrieval impossible.

Connect customer feature use/routing to those paths. Classify each effect as `OBSERVED`, `POSSIBLE`, `NO_FAILURE_OBSERVED` or `UNKNOWN`, with measurement window and coverage. Confirmed request failures or customer reports support observed effects; graph reachability supports possible effects. An absence of sampled errors is not proof of no effect.

Deduplicate customers across paths. Count recorded observations only within their defined measurement/sample scope. Report incomplete customer mappings instead of publishing an exact total. Support tier can help prioritize updates under company policy; contract value is not proof of an outage and cannot turn a guess into revenue loss. Contractual breach calculations require the actual agreement and complete measurement window and are later work.

### REQ-SRE-07: prepare recovery options

Retrieve a current service runbook and related past incidents. Present possible actions such as restoring an earlier deployment, disabling a recently changed flag, pausing a rollout, changing routing or relieving overload when documented and applicable. Similar past symptoms are context, not proof that the same action is suitable today.

Each option identifies its exact target, prerequisite observations, current/target versions, checks, expected effect, approval requirement and reasons it cannot currently be proposed. Compare artifact, configuration, schema and dependency compatibility, current deployment version and available rollback history. Missing required information withholds the executable plan but still shows useful investigation steps.

`git revert` makes a new source-code change; deploying a prior artifact changes the running service. They require different plans. Kubernetes deployment rollback uses rollout revision history and concerns the deployment's Pod template; it does not establish that external configuration or database state was restored. [Kubernetes deployment rollback](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/#rolling-back-a-deployment).

A sandbox result is evidence about that sandbox, not a production safety guarantee. Production plans must be revalidated against actual state immediately before execution.

### REQ-SRE-08: communicate and record progress

Draft an internal responder message and a customer-safe update from evidence. Show recipient/channel, observed problem, relevant times, scope, uncertainty and next update time when a responder supplies it. Do not invent a restoration estimate or customer impact.

Production sending is a separate authorized operation. In this planning task, no messages are sent. Track send attempts and provider outcomes separately from drafts; retry ambiguous delivery only after checking provider receipts. The alerting system remains responsible for existing paging policy until an approved replacement is configured.

### REQ-SRE-09: execute only controlled actions

First-release production behavior is read-only and advisory. Sandbox action execution requires a reviewable plan and explicit operator approval. A future production executor requires a configured allowlist, scoped short-lived credentials, target/version checks, expiry, permissions, per-target serialization, audit history, and recovery checks. Use vetted adapter operations and argument arrays, not an LLM-written shell script.

Duplicate approval/execution requests must not duplicate changes. A changed deployment, expired plan or changed permission invalidates the plan. Partial completion is reported and does not trigger a broad retry or compensating rollback automatically. An approved notification is not authorization to modify a deployment.

### REQ-SRE-10: verify recovery and learn

Use service-specific recovery criteria, including request success, latency and relevant queue/data checks over a defined window. Keep `MITIGATED`, `MONITORING` and `RESOLVED` distinct. Alert closure is one observation; a responder or authoritative incident system determines closure.

Keep a timeline of facts, hypotheses, actions, outcomes and handovers. Draft a post-incident review with separate observed facts and proposed explanations; a human reviews it. Create/link follow-up tasks with owners and due dates only through an authorized operation. Incident closure and completion of preventive work are different milestones. Blameless reviews are intended to improve systems and procedures. [Google postmortem guidance](https://sre.google/sre-book/postmortem-culture/).

## 6. Example

At 10:05 UTC, a synthetic alert reports payment failures in region A. The graph records a payments deployment at 10:00 and an earlier healthy artifact. Checkout calls payments; the database is also investigated. Region B runs an unchanged deployment.

The assistant retrieves the current on-call override, current runbook, observed failures for Customer A, possible dependence for Customer B, and the new artifact's PR/task/review/design records. It reports the recent deployment as a possible explanation while checking database health and configuration.

The brief says: payment errors are observed in region A; Customer A has recorded failed requests; Customer B may be affected but lacks measurements; region B has no failure observed in the available window. It names the current responder and links the evidence. Restoring the earlier artifact is offered only if its required compatibility and deployment-state checks pass. A schema-change variant withholds that plan and requests the missing check.

After an approved sandbox restoration, the assistant records the action and measured recovery. It does not conclude that a specific author caused the incident or that production recovered.

## 7. Acceptance and measurement

Required scenarios: duplicate event, unrelated same-text alert, schedule override/gap/handover, partial rollout, missing deployment revision, configuration-only incident, shared dependency, runtime cycle, observed versus possible customer effect, incomplete customer mapping, unsafe schema rollback, moved deployment, expired/repeated action, model/API failure, source instructions trying to redirect the agent, restricted customer data and recurring incident.

For each, verify correct source links and timestamps, no invented root cause, no false confirmed customer effect, no wrong responder notification, and no unauthorized or stale action. Preserve the original Payments branch/TLS scenarios as regressions. Test examples with a responder so the result answers the practical questions, not only schema checks.

Proposed local demo targets: event acknowledgment under 250 ms at the 95th percentile after durable storage, warm graph-only context retrieval under 1 second, and a complete synthetic brief under 10 seconds with six or fewer navigation calls. Publish actual measurements, including cold start, provider calls, source refresh, graph size, hardware and failures. Limits produce partial results, not false certainty. Do not promise these times for live incidents before measuring them.

Compare direct graph/rules retrieval, LLM-guided navigation, and decision-model-guided navigation using the same cases and final answer model. Measure cost per correctly grounded brief, missed evidence, latency, retries and final-answer tokens. Self-hosted inference includes infrastructure and idle capacity cost. Human time saved is measured separately from inference savings.

## 8. Integration and unresolved setup

The [integration plan](docs/design/sre_integration_plan.md) maps this work to the existing coding phases, defines shared contracts and gives a practical demo sequence. The [graph extension](docs/design/sre_graph_schema.md) defines deployment, ownership and customer relationships without duplicating Company Brain entities.

Before live rollout, select the actual deployment platform and approved connectors, authoritative service catalog, customer routing source, incident policy, recovery checks and allowed actions. These are configuration/organizational decisions; a model cannot infer them reliably from an error message.
