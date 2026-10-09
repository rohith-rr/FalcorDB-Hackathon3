# Core logic review for the hackathon POC

Date: 2026-10-09. Scope: architectural reasoning for a controlled demonstration. Status: design review; runtime behavior has not been tested.

Follow-up design corrections: [graph publication](../design/graph_publication.md) now specifies per-projection recovery, fixed event windows, complete scoped answer checks and generation-independent clarification. [Sandbox execution](../design/contracts.md#poc-sandbox-execution-protocol) returns durable 202 receipts with background execution/probes and authorized status polling. Original review decisions below remain context; these canonical specifications own the revised behavior. No runtime results are claimed.

**Verdict: the core design is sound enough to implement as a hackathon POC.** A curated graph, explicit mappings, bounded model choices, deterministic checks and a cited explanation form a coherent product. The schema can represent the facts required by the worked scenarios. Automated maintenance of those facts is future product work and is not a reason to block the POC.

This review applies the user's clarified POC goal to the [earlier feasibility review](feasibility_review_2026-10-09.md). In particular, the earlier mapping-maintenance concern is not a core blocker when a participant supplies a checked manifest. Deferred questions and probable solutions are recorded separately in [open questions and probable solutions](../design/open_questions_and_probable_solutions.md).

The review assumes one configured organization/project/repository, small declared source scopes, curated operational fixtures and a disposable sandbox if actions are demonstrated. Live Plane/Google Docs/GitHub reads, real provider demonstrations and the existing recovery gates keep their stated completion criteria. POC scope does not turn an unimplemented integration into a passing result. The user subsequently approved the seven fixes below for embedding into the design. They now appear in the canonical contracts and phase plans; see the [core decision index](../design/README.md#poc-core-decisions). No runtime implementation is claimed.

**The central reasoning chain is coherent.**

```text
Question or alert
  -> resolve permitted entity and operating scope
  -> retrieve explicit graph relationships and source evidence
  -> let a decision model prioritize allowed optional exploration
  -> verify required facts, coverage and freshness in application code
  -> assemble typed conclusions and evidence
  -> use an LLM to explain those conclusions with citations
  -> recheck validity and display the result
  -> separately review/approve an exact sandbox action, if demonstrated
```

The graph provides relationships that the answer needs. The decision model has a useful bounded role in selecting additional context. Application checks determine whether the evidence permits a conclusion. The answer model provides readable explanation. This division can work without an autonomous graph-building pipeline or a new graph ontology.

| Core area | Assessment | Reason |
| --- | --- | --- |
| Entity identity and curated mappings | Sound | Stable provider IDs and manifest-owned cross-system links support the demo's joins. |
| Branch dependency and delivery logic | Sound within its declared limits | All code prerequisite groups require coverage; alternatives within a group are OR choices. Review readiness is separate. |
| Candidate-specific reverts | Sound | A revert on stable does not incorrectly invalidate an unchanged feature branch; restoration needs its own evidence. |
| TLS context and epic progress | Sound | Actual runbook sections supply instructions; task state remains source-owned; leaf counts are deduplicated. |
| Incident scope and time | Sound with validated fixtures | Incident-time deployment, current responder and environment/region are separate facts. |
| Customer impact | Sound | Graph reachability supports possible exposure; customer-linked observations support observed failure. |
| Model-guided traversal | Sound with controller enforcement | Mandatory checks cannot be dropped by a model's path choice or early STOP. |
| Explanation and fallback | Sound with a bounded claim surface | Critical values come from typed fields; invalid model output has a deterministic fallback. |
| Sandbox execution | Feasible, concrete recipe still needed | The approval and version-bound plan model is appropriate; one runtime/operation must be selected. |

**Branch reasoning checked against the design.** The [branch algorithm](../design/phase_03_traversal_and_branch_decisions.md) has the right decision structure: resolve the task/repository; obtain complete prerequisite scope; verify each required delivery group against exact candidate heads and recorded effects; apply policy; prefer stable when eligible; otherwise choose a verified feature or ask for clarification. Lack of a single covering branch produces an integration proposal, not an invented base.

| Evidence change | Expected result |
| --- | --- |
| Backend delivery exists only on one eligible feature branch | Recommend that exact feature head, with review warnings. |
| Stable receives a confirmed complete delivery | Prefer stable after verification. |
| Two dependencies exist on separate branches and no candidate contains both | INTEGRATION_REQUIRED; no single-base command. |
| Stable reverts the delivery while feature history is unchanged | Stable is REVERTED; the feature can remain INCLUDED. |
| A dependency/delivery mapping is missing or only inferred | INSUFFICIENT_EVIDENCE; a model score cannot supply the missing proof. |
| No code dependencies, and dependency scope is confirmed complete | Verified stable is a valid default for new work. |
| Relevant head/read-set inputs change while an answer is generated | Retry within budget or withhold the recommendation/prose; equivalent unrelated publications preserve it. |

These are design walkthroughs, not executed tests. They show that the policy handles the main counterexamples coherently. Commit inclusion remains historical evidence; the POC should not describe it as a guarantee that every required behavior still works.

**Incident reasoning checked against the design.** In the payments example, the graph can connect region A's alert to its active deployment, artifact, code/task context, responder and runbook. Incoming caller dependencies lead to potentially affected features/customers. An observation for Customer A supports observed failure; Customer B's path without measurements supports possible exposure. Region B's recorded measurements are evaluated separately. Changing the compatibility evidence must change whether restoration is proposed. A recent deployment remains a possible explanation until further evidence or a responder supports confirmation.

This gives the graph a substantive role in the POC. The answer should change when the underlying graph or measurements change, without changing the question or hardcoding a different response.

**Core decisions adopted for implementation**

| ID | Applicable feature | Adopted POC decision and rationale | Evidence needed |
| --- | --- | --- | --- |
| C-01 | Clef branch discovery | Persisting a suggestion through a full import during its own query changes the generation and invalidates the answer. Return request-local evidence and retain its audit record outside the graph. Project candidates only in an explicit later ingestion batch, preserving original observation/expiry; later reuse revalidates access and inputs. The association contract now defines this sequencing. | One successful discovery completes without a self-triggered retry, and its inferred link never supplies delivery coverage. |
| C-02 | Incident identity resolution | Shared clarification supports TASK/REPOSITORY/BRANCH only. For the POC, require exact service-instance/environment/region identifiers in alerts or an explicit UI selection that submits a fresh request using existing service fields. Ambiguous identity pauses investigation; do not guess. Add a typed service continuation only if demonstrating conversational disambiguation. | Two same-named instances in different regions cannot be silently combined or selected. |
| C-03 | Incident traversal | Make the mandatory-check scheduler concrete. Gather known deployment, responder, dependency, customer and runbook facts through bounded templates. Maintain check status independently of model choices. Use the model for optional branches or prioritization; budget exhaustion yields a partial brief. | A deliberately premature STOP cannot hide pending checks or produce an executable plan with missing prerequisites. |
| C-04 | LLM explanation | Define which facts are engine-rendered: refs/SHAs, task states, counts, responder, impact classification and action target/status. Keep model prose constrained and attach evidence IDs. Reject contradicting prose and use fallback. Preserve runbook prerequisites when excerpting instructions. | Wrong facts with valid citation IDs are rejected; invalid or stale recommendations disappear from prose as well as commands. |
| C-05 | Live source retrieval | If a live source returns a known access denial, record that denial independently of the aborted import and suppress its retained content. A small durable disabled-source record with a version check is enough for one demo identity; full enterprise ACL machinery can wait. | A previously imported document is not shown after access denial, including from an outstanding answer or stored trace. |
| C-06 | Sandbox action | Pick one target, one restore operation and checked compatibility inputs. Use a durable plan/receipt record, an atomic execution claim and a single permitted sandbox writer. On ambiguous outcome, reconcile the actual target before any retry. | Approval required; duplicate/expired/moved-target requests do not repeat or redirect execution; recovery is actually measured. |
| C-07 | Graph publication | Keep one writer and complete scenario imports before requesting investigation. Route all direct/MCP reads through the same ready/generation checks and keep source/audit records outside rebuild deletion. | Interrupted import remains blocked across restart; a query cannot publish mixed-generation evidence. |

C-01 is relevant when discovery is enabled; C-06 is relevant when action execution is shown. They are not reasons to block an unrelated read-only workflow. C-03, C-04 and C-07 largely make existing requirements concrete rather than introduce new architecture. Full production versions of these mechanisms are unnecessary for the POC.

**Adopted sandbox recipe.** Use a disposable local payments service with two identifiable artifact versions: one healthy and one with a controlled failure. Record the current and proposed artifact, configuration version and schema compatibility in the fixture manifest. Only the sandbox adapter may change the target during the demonstration. Bind the approved plan to the observed target version and refuse unknown compatibility. The demo recovery criterion sends one synthetic request per second for 30 seconds and requires all 30 to succeed with the expected served artifact identity. This is a demo criterion, not a production SLO. A schema-incompatible fixture must block the same restore proposal. Unknown execution outcomes retain the target reservation until actual state and retained receipts can be reconciled; matching artifact state alone cannot manufacture a success receipt. The [SRE recipe](../design/sre_integration_plan.md#poc-sandbox-recipe) and [canonical protocol](../design/contracts.md#poc-sandbox-execution-protocol) own the implementation details.

**Minimum POC rehearsal evidence.** The following establishes the main claims; it is not a declaration that the full phase suites have passed or a replacement for their completion gates.

1. A question retrieves real graph relationships and displays the returned evidence path.
2. A real decision-provider call selects among actual allowed choices; mandatory facts are still checked by the controller.
3. A real answer-provider call produces a cited explanation, and a provider failure produces a labeled fallback.
4. Changing a delivery or compatibility fact changes the branch recommendation or recovery proposal.
5. Missing evidence and ambiguous scope produce an explicit limitation instead of a guessed fact.
6. Customer A's measured failure and Customer B's possible exposure stay distinct.
7. Source mode is visible per source; curated mappings remain manifest evidence even when linked records are live.
8. If discovery is shown, suggestions remain inferred; if execution is shown, approval, freshness, duplicate handling and measured sandbox outcome are demonstrated.
9. Required-projection recovery or changed semantic inputs cannot yield a current answer from invalid evidence; unrelated publication preserves equivalent complete inputs.

The next step is implementing the selected workflows with these boundaries. No core redesign is indicated by this review. Automated mapping maintenance, continuous ingestion at scale, broad model reliability and production operations can stay in the separate open-question backlog.
