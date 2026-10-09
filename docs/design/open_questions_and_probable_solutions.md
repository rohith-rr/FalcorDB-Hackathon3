# Open questions and probable solutions

Date: 2026-10-09. Scope: unresolved details outside the core hackathon POC. Status: proposed future decisions; no implementation claimed.

The user clarified that the immediate goal is a hackathon proof of concept. A curated, explicitly linked dataset is sufficient to demonstrate the graph reasoning. Automated company-wide knowledge maintenance, enterprise access management and production operations are not prerequisites for that demonstration.

The [POC core logic review](D:/FalcorDB-Hackathon/docs/reviews/poc_core_logic_review.md) records the core verdict and implementation details that still matter to the demo. This document contains the deferred questions. Several topics are already named in [Phase 7](D:/FalcorDB-Hackathon/docs/design/phase_07_production_and_actions.md); the gaps here are the unresolved mechanisms, policies and ownership beneath those requirements, not an assertion that the design ignores them entirely.

The probable solutions below are design proposals. Each entry states a workable POC assumption and the condition that would make a fuller solution necessary. Existing source labels, evidence rules, live-adapter completion gates and sandbox approval requirements remain applicable to the features being demonstrated.

The seven POC core fixes have since been approved and embedded into their owning contracts and phase plans; see the [core decision index](README.md#poc-core-decisions). Only the broader future questions below remain deferred. The single-identity access registry, one-writer publication protocol and one sandbox action are now specified POC mechanisms rather than unresolved production prerequisites.

**OQ-01 — Who maintains confirmed cross-system mappings as the company changes?**

Existing coverage: the [adapter design](D:/FalcorDB-Hackathon/docs/design/source_adapters.md) uses a verified manifest; Phase 7 proposes operator review of inferred relationships. Missing detail: responsibility, confirmation procedure and revalidation triggers.

Open question: who owns task dependencies, complete delivery mappings, document applicability, service ownership and customer routing, and when must those confirmations be reviewed?

Probable solution: make mappings versioned records with source, confirming actor, confirmation time, scope and relevant source versions. Assign an owner by mapping type. Source changes flag affected mappings for review; a commit-head change alone should not invalidate an unchanged historical delivery mapping. Add a small review queue that can confirm, reject or replace candidate links while preserving history. Measure the fraction of queries answerable with confirmed data and the effort needed to maintain it.

POC assumption: a participant authors and checks a small manifest against the demo records. It is a valid source of curated evidence and is labeled as such. Build the maintenance workflow when other users start adding or changing mappings.

**OQ-02 — How should continuous updates be published without repeatedly interrupting answers?**

Existing coverage: durable read blocking and rebuild recovery in [Phase 1](D:/FalcorDB-Hackathon/docs/design/phase_01_graph_and_fixtures.md). Missing detail: event batching, publication cadence and acceptable read unavailability under sustained ingestion.

Open question: what event volume, freshness delay and blocked-read rate must a live service support?

Probable solution: retain source events durably, deduplicate them and coalesce related updates into bounded batches. Track accepted-event and published-event positions separately so freshness is measurable. Give investigations a bounded opportunity to complete between publications. If measured rebuild downtime becomes unacceptable, evaluate versioned graph publication or transactional incremental updates with explicit cross-worker consistency tests.

POC assumption: replay one incident or scenario batch, finish its import, then investigate. Preserve dirty-state recovery; avoid a continuously running high-frequency import loop. Revisit before real monitoring streams are enabled.

**OQ-03 — How will per-user access and revocation propagate across stored evidence?**

Existing coverage: source allowlists in the POC and per-user ACL synchronization in Phase 7. Missing detail: the authorization-version model, propagation target and invalidation of content, traces and cached results.

Open question: how quickly must revoked access take effect, and which retained artifacts must become inaccessible?

Probable solution: maintain authorization state independently of successful graph imports. Bind cached evidence and final responses to an authorization version as well as a graph generation. Update a source-denial registry immediately on known permission loss; check it before retrieval, trace access and publication. Define a measured revocation target and a retention policy for previously accessible content.

POC assumption: one configured demo identity and allowlisted data. Full enterprise ACL synchronization can wait. A known denial from a live source must still suppress its retained content immediately; the minimal handling is described in the core review. Revisit before introducing multiple users or confidential shared data.

**OQ-04 — How should late or conflicting source records change incident history?**

Existing coverage: effective times, recorded times, partial rollouts and override sources in the [SRE schema](D:/FalcorDB-Hackathon/docs/design/sre_graph_schema.md). Missing detail: reconciliation precedence and the meaning of a historical query after corrections.

Open question: should a historical brief show the best reconstruction available now, or the information available when the original brief was written?

Probable solution: support both views explicitly. Preserve original source events and their revisions; append corrections with effective and recorded times. Define precedence per source type and use source sequence/version information where available. Contradictory deployment intervals or equally authoritative on-call overrides remain unresolved until reconciled. Preserve old briefs with their original evidence versions; issue a revised brief when relevant facts change.

POC assumption: fixture histories have checked intervals and explicit overrides. Reject contradictory fixture inputs. Revisit when replaying out-of-order events from real operational providers.

**OQ-05 — What freshness and resource budgets apply to each source?**

Existing coverage: per-operation retries, traversal limits and a branch-evidence TTL. Missing detail: a combined request budget, source-specific freshness policy and scheduling across simultaneous users.

Open question: which facts require a live refresh, which may be displayed as historical, and what happens when the overall deadline expires?

Probable solution: define freshness by evidence type and intended use. A displayed historical deployment can retain its timestamp; an action target needs immediate revalidation. Use a shared request deadline, provider-specific rate/concurrency budgets, SHA-keyed Git caches and background history synchronization. Track cold synchronization separately from warm query latency. Exhausted budgets produce explicit incomplete results.

POC assumption: a small repository and prepared history; bounded live rechecks for displayed current decisions. Existing freshness checks still apply. Revisit when cold scans or multiple queries materially delay the demo-sized workload.

**OQ-06 — What infrastructure owns production jobs, graph publication and recovery?**

Existing coverage: a single-process gate for the POC; distributed jobs and fencing are deferred in Phase 7. Missing detail: storage selection, ownership transfer, failover and coordinated backup.

Open question: which state is authoritative after a worker crashes or two workers attempt the same job?

Probable solution: use a transactional durable store for source receipts, jobs, approvals and execution receipts, with explicit unique keys and bounded worker leases. Treat the graph as a projection of retained inputs. Introduce a fencing token for publication ownership and ensure every reader checks the published generation. Version schema and mapping formats. Back up the durable inputs, content and graph metadata coherently, and test restore before enabling multiple writers.

POC assumption: one application writer, a durable local journal and retained rebuild bundles. All graph mutations use the same controlled import path. Revisit before multiple application workers or failover are introduced.

**OQ-07 — How can recovery actions be validated across real deployment platforms?**

Existing coverage: approvals, exact targets, idempotency, expiry and UNKNOWN_OUTCOME in [contracts](D:/FalcorDB-Hackathon/docs/design/contracts.md). Missing detail: platform adapters and the source of compatibility evidence.

Open question: who defines compatible artifact/configuration/schema combinations, and how does an executor prevent a concurrent deployment from invalidating its checks?

Probable solution: create an explicit action catalog with typed arguments, permitted targets, compatibility evidence, preconditions and recovery criteria. Use platform-supported conditional state changes where available. Retain a durable operation identity and reconcile actual target state after ambiguous outcomes before retrying. Require service owners to maintain compatibility records. Add credentials, approval roles and auditing separately for each production action family.

POC assumption: one disposable single-writer workload and one vetted restore operation with explicit fixture compatibility. Approval, stale-target rejection, duplicate handling and actual recovery checks remain core if execution is demonstrated. Revisit before any production action or additional action family.

**OQ-08 — How will real incident notifications be delivered and reconciled?**

Existing coverage: message drafts, separate sending authorization and receipt checks in the [SRE requirements](D:/FalcorDB-Hackathon/SRE%20event%20handling.md). Missing detail: channel ownership, escalation behavior and ambiguous delivery recovery.

Open question: which system controls recipients, escalation, retries and acknowledgment when the assistant participates in incident communication?

Probable solution: leave existing paging policy authoritative. Approved sends enter a durable outbox keyed by incident, message version and destination. Retain provider receipts and reconcile uncertain sends before retrying. Refresh recipients before sending and version responder acknowledgment/handovers separately from incident closure. Customer updates require an explicit approved audience and content policy.

POC assumption: render message drafts only. No live paging or messaging integration is needed. Revisit when the first real test-channel notification is requested.

**OQ-09 — What evidence is sufficient to enable models for wider use?**

Existing coverage: rules baselines, held-out examples and supervised demo gates in [decision models](D:/FalcorDB-Hackathon/docs/design/decision_models.md). Missing detail: real-data evaluation ownership, release thresholds and drift monitoring.

Open question: what improvement over deterministic retrieval justifies enabling each model-assisted feature outside the controlled examples?

Probable solution: evaluate candidate retrieval separately from selection, and selection separately from final prose. Use scenario-grouped real examples with missing mappings and ambiguity. Measure accepted precision, abstention, useful-evidence recall, latency and total cost. Version prompts and mappings; stage rollout with a rules fallback and disable features whose quality falls below agreed thresholds. Choose one initial provider before widening comparisons.

POC assumption: run the applicable controlled evaluation and show actual choices and failures. Broad claims about model superiority or reliability can wait. Revisit when supporting questions outside the demonstration set.

**OQ-10 — How should past incidents be retrieved without treating old explanations as current facts?**

Existing coverage: reviewed postmortems, incident events and explanation authority in the SRE design. Missing detail: historical retrieval ranking, applicability checks and handling corrected lessons.

Open question: which historical incidents are relevant, and what makes their recovery advice applicable to the current version and environment?

Probable solution: retrieve by service, symptom, operating scope and change type; prioritize reviewed records with compatible versions. Preserve rejected explanations and correction history. Return prior actions as historical evidence with current applicability checks, and let a responder record whether the lesson helped. A similarity score must not confirm the current cause or authorize the old action.

POC assumption: explicitly link one reviewed synthetic prior incident and show its history. General historical matching and continuous learning can wait until multiple real incidents are available.

**Items that belong in the core implementation review.** Suggestion writes invalidating their own query, basic handling of ambiguous service identity, omitted mandatory investigation checks, incorrect customer-impact claims, invalidated answer prose and duplicate/stale sandbox actions can break a small demo. They are addressed in the [core review](D:/FalcorDB-Hackathon/docs/reviews/poc_core_logic_review.md), rather than deferred here as production work.
