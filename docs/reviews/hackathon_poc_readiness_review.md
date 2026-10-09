# Hackathon POC readiness review

Date: 2026-10-09. Scope: the full repository as an initial hackathon proof of concept. Revised to exclude delivery-time constraints at the user's request. This is an independent review of the current files, including the earlier reviews and their subsequent design corrections. Recommendations below do not change existing requirements or completion gates.

**Verdict: the full proposed development and incident workflows are technically feasible within the stated POC boundaries. No fundamental architectural impossibility was identified.** Explicit relationships in FalkorDB, bounded retrieval, deterministic checks, real model calls and cited explanations make a credible POC. Curated mappings and synthetic operational data are appropriate inputs. Automated company-wide knowledge maintenance is not a prerequisite. The remaining concerns are unimplemented integrations, specification clarity, runtime failure handling and claims that exceed the available evidence. This is a design-level assessment, not proof that the complete system works.

The repository currently contains 26 Markdown documents, three JSON preparation artifacts and two background PDFs. There is no application source, dependency manifest, Compose configuration, executable graph template, runnable UI or test suite. Proposed file lists are specifications, not implemented modules. Consequently, this review identifies implementation gaps and planning problems; it cannot establish runtime correctness, performance or integration success.

## Findings and implementation notes, excluding delivery constraints

### 1. Implementation note: shared completion gates cover the full product

Evidence: [dependency catalog](../demo/plane_project_seed_instructions.md), lines 250-259; [seed payload](../../demo/plane_seed_payload.json), lines 316-381.

T11, the shared answer task, requires both T09 branch verification and T14 incident investigation. T12, the UI task, requires T10 branch discovery and T16 sandbox execution as well. T18 therefore has all seventeen other tasks in its prerequisite closure. The catalog explicitly permits basic UI work to begin earlier, so this is not a dependency cycle or a claim that coding cannot start. It is a completion structure that prevents a narrow milestone from being declared complete independently.

**Revised assessment:** with no delivery deadline, this coupling is not a feasibility defect and does not justify cutting branch discovery or sandbox execution. Completing both workflows is a valid goal. Intermediate end-to-end milestones can help verify integration, but the full completion gate can remain as written.

### 2. Medium: incident-only scope and mandatory branch requirements disagree

Evidence: [SRE allocation](../design/sre_integration_plan.md), line 120, versus [resource-plan cuts](../design/falkordb_resources_and_hackathon_plan.md), line 192.

The SRE plan says every development workflow need not be delivered, but its cut policy still preserves candidate-specific revision effects. The resource plan calls Public API branching optional. Someone following the SRE gate can reasonably implement the full merge/squash/revert/reapplication engine before an incident demo, even though incident-time deployed-artifact retrieval does not require that engine.

**POC recommendation:** publish one requirement-to-demo matrix identifying shared requirements, development-specific requirements and incident-specific requirements. If the intended POC includes both workflows, mark both sets required and implement them. This is documentation clarity, not a recommendation to remove branching. Do not simplify an enabled branch feature into an unsupported command generator.

### 3. High: the live demonstration data and access are unproven

Evidence: [seed report](../../demo/seed_report.md), [relationship manifest](../../demo/project_relationships.json), and [live-adapter gate](../design/source_adapters.md).

The committed receipts record zero external creations. All 22 native ID mappings are null; there are no Google Docs links or implementation/delivery/effect mappings. These omissions are truthfully labeled and are valid for preparation. However, these files cannot yet seed a source-backed application graph without native-ID resolution, normalization and actual evidence. There are also no incident fixtures, generated Git histories or healthy/failing sandbox artifacts.

**POC recommendation:** make one authenticated read from each required source and one call to the chosen model providers an early setup milestone. Build the graph workflow on a small checked fixture dataset while source setup proceeds. Do not infer current connector availability from an old blocked receipt, and do not claim that a prepared payload proves integration.

The current design requires live Plane and Google Docs for full completion. Those gates remain unmet and should be implemented. Fixtures can verify the reasoning before live setup is complete; they cannot pass the live-adapter gate. The [official event rules](https://www.wemakedevs.org/hackathons/falkordb/rules) permit synthetic data and require FalkorDB to perform central product work; they do not require these particular connectors. The project's stronger integration requirements remain applicable.

### 4. Implementation note: broad evaluation is feasible; historical estimates are excluded

Evidence: [phase order and sprint boundary](../design/README.md), [foundation scope](../design/phase_00_foundation.md), [Phase 4 evaluation](../design/phase_04_decision_model_integration.md), and [SRE evaluation](../design/sre_integration_plan.md).

The implementation includes durable publication/recovery, retained storage, access invalidation, three live adapters, branch semantics, activity-based discovery, incident jobs, two model roles, UI and an action executor. Evaluation includes 60 routing examples, 20 separate association examples and at least 20 incident cases, with multiple navigator comparisons. These are substantial but implementable tasks, not theoretical blockers.

The earlier objection to fitting this work into the historical sprint allocation is withdrawn from the current assessment. No delivery estimate or deadline-based scope reduction is proposed.

**POC recommendation:** retain the intended features and their applicable tests. Verify provider interfaces before building adapters and separate retrieval quality, model selection quality and answer support in evaluation. Intermediate working slices help expose integration errors; they are an implementation order, not a reduction in final scope. Optional SDK or model additions should be justified by measured value rather than included solely because they are available.

### 5. Medium: latency limits do not yet form an enforceable end-to-end deadline

This concerns request behavior and bounded resource use, not the time allowed to build the project. The user's removal of delivery constraints does not turn an unbounded request or stale action into an acceptable runtime behavior.

Evidence: [adapter retry policy](../design/source_adapters.md), line 13; [discovery scan](../design/task_branch_association.md), line 19; [incident timing targets](../../SRE%20event%20handling.md), line 160.

An adapter operation can spend up to 60 seconds retrying. Discovery can inspect 20 branches with 1,000 commits per branch plus file details. An incident can make six sequential navigation calls and a final answer call. These bounds do not establish a brief within ten seconds, even if graph reads are fast. The documents correctly call the times targets; the remaining implementation gap is how the controller cancels or cuts work when the overall budget expires.

**POC recommendation:** prepare Git history and graph inputs before questions, propagate one absolute request deadline to all source/model calls, and stop optional exploration when it expires. Measure synchronization, warm retrieval, inference and the 30-second recovery observation separately. A partial brief should appear promptly with unresolved checks. Repeated provider retries must not leave the UI waiting indefinitely.

### 6. Medium: the value of repeated model navigation is an experiment, not an established benefit

Evidence: [mandatory investigation scheduler](../design/sre_integration_plan.md), lines 45-51, and [model evaluation policy](../design/decision_models.md).

Required deployment, responder, customer, dependency and runbook checks already have deterministic templates. A model ordering every required read can add calls without changing the final evidence. Typed choices constrain selections but do not establish correctness, speed or cost savings. The design acknowledges this; the POC must make that role observable.

**POC recommendation:** fetch required facts directly. Use the decision model for a concrete optional choice, such as which related change or historical incident to inspect next. Show its actual options, choice and resulting evidence. Compare useful evidence, calls and time with the same deterministic baseline. If the extra call adds no value, report that result and keep the workflow operational.

Cloudflare's [Clef documentation](https://developers.cloudflare.com/workers-ai/models/clef/) confirms the proposed state/typed-question interface. It does not prove domain quality or access through the team's account. No authenticated smoke call was performed in this review.

## Claims that the POC cannot establish

These are boundaries to retain, not newly discovered defects in the revised Markdown. Most are already corrected there; stronger versions persist in the archived draft and background material.

| Claim | Practical limit | Credible POC demonstration |
| --- | --- | --- |
| A graph identifies the exact breaking commit | Relationships and nearby timestamps do not prove causality | Show related changes as leads, with supporting/conflicting observations |
| All affected customers or revenue loss can be calculated from paths | Reachability establishes possible exposure; measurements and mapping coverage are needed for observed impact | Show one measured failure and one possible exposure, with coverage labels |
| Typed outputs and citations eliminate hallucinations | Valid IDs and JSON do not prove that prose follows from evidence | Render critical facts in code, constrain prose, and demonstrate rejection/fallback |
| Commit ancestry proves a feature still works | It establishes historical inclusion; later edits, configuration or environment can change behavior | Show exact revision coverage and its disclosed limits; run a relevant smoke check when claiming behavior |
| Assignment and commit times reveal the original implementation branch | Git commits do not record an original branch; concurrent tasks and shared histories can be indistinguishable | Return a candidate or abstain; prefer explicit mappings for the primary demo |
| A previous artifact is universally safe to restore | Schema, configuration, dependencies and data may have changed | One controlled compatible restore plus an incompatible case that blocks it |
| Graph reads imply sub-second investigation or recovery | Network calls, inference and observation windows are separate work | Publish measured stage timings without transferring database benchmarks |
| A six-hop path or more sponsor libraries makes the design better | Hop count and tool count are not evidence of product value | Change one relevant fact and show the resulting decision change |

The [Git ancestry interface](https://git-scm.com/docs/git-merge-base) supports the planned historical check. Its documented purpose is ancestry, which is why behavior needs separate evidence. The revised answer contract also explicitly disclaims a general prose-entailment guarantee; do not describe its validator as one.

## Implementation sequence for the full POC

This follows the repository's incident-led direction while retaining the development workflow. The sequence is for validation and integration; it is not a deadline-based cut list or a rewrite of approved scope.

1. Start one API process and FalkorDB with a small, versioned dataset and repeatable seeding. Preserve coherent reads and retained inputs; finish each scenario import before investigation.
2. Select an exact payments instance and retrieve incident-time deployment, current responder, customer paths and actual runbook sections through parameterized queries.
3. Return typed facts, evidence paths and missing-check status. Make one real answer-model call with deterministic fallback. Add one useful bounded decision-model choice.
4. Display a brief showing Customer A's measured failures and Customer B's possible exposure. Show source mode per record and meaningful source references.
5. Change compatibility evidence and demonstrate that the recovery proposal changes. Build the actual local workload and retain approval, exact target checks, duplicate handling, durable outcome reconciliation and the specified recovery probe for the intended execution demonstration.
6. Add required live task/document/code context to complete the existing integration gate. Implement branch recommendations and candidate-specific revision effects using real Git histories, then add ID-free discovery with its separate evaluation and inference limits. Evaluate optional SDK retrieval and additional model providers on their measured benefit. Production connectors remain outside the initial POC's stated scope.

For a fixture-first milestone, no enterprise ACL service, automated mapping UI, production causal-discovery system or continuous telemetry pipeline is needed. If live content or action execution is enabled, its existing access and action requirements still apply.

A credible rehearsal should show the ordinary result, a changed-evidence result, missing evidence, model failure, wrong regional scope and an interrupted import. For execution, also show missing approval, stale/duplicate requests and uncertain-outcome recovery. A rehearsed small suite establishes those cases only; it does not replace the larger required suites or prove production reliability.

## Concrete decisions and evidence still needed

- Select and pin the database/client/MCP versions, retained transactional storage and actual sandbox runtime. The protocols are specified, but these components have not been selected and verified in implementation.
- Resolve actual provider identities and demonstrate authorized source/model access. Cross-system mappings need checked endpoints and provenance; a model cannot supply absent authoritative mappings.
- Make current-review policy, source-specific freshness and request cancellation concrete in code. Preserve the distinction between historical evidence and evidence valid for a current recommendation or action.
- Reject conflicting deployment intervals and on-call fixtures. General reconciliation of late or contradictory live operational records remains future work; the POC may use checked histories as already documented.
- Demonstrate the C-01 through C-07 protocols with their intended failure cases. Written state machines, diagrams and acceptance criteria are not execution evidence.

These are normal implementation obligations for the planned POC. They do not require a core redesign or a production-grade knowledge-maintenance system.

## Checks actually performed

- Inventoried the complete workspace and reviewed all existing Markdown specifications/reviews, all three JSON artifacts and extracted text from both background PDFs. PDF visual layout was not evaluated because no PDF was edited and layout is not material to these findings.
- Parsed every JSON artifact. Confirmed four epics, eighteen unique tasks, eighteen hierarchy links and forty-one unique dependency edges. Payload and relationship manifest agree; the dependency graph is acyclic with no unknown task endpoints. Every task has a dependency-coverage entry.
- Computed prerequisite closures: T11 has eleven prerequisites, T12 has fifteen, and T18 has seventeen. This substantiates the release-coupling finding.
- Checked Markdown file targets; no missing local file targets were found. Heading-anchor validity was not part of that check. The master still repeats its association paragraph, model table row and acceptance bullet; this is low-priority editorial drift.
- Checked current primary documentation for the key Git, Plane activity, Google Docs, Clef, FalkorDB durability and MCP interfaces. Account access, pinned-version compatibility and performance remain untested.

One concrete setup trap: the current [official MCP repository](https://github.com/FalkorDB/FalkorDB-MCPServer#docker-compose) documents a Compose volume/data-directory mismatch that can lose persistence on container removal. Verify the chosen mount and preservation after container recreation as well as restart. Its [default read-only setting](https://github.com/FalkorDB/FalkorDB-MCPServer#read-only-mode-for-replica-instances) is overridable per query; the existing application allowlist requirement remains necessary. These are upstream setup observations, not defects reproduced in this repository.

No application tests, authenticated source/model calls, database crash tests, benchmarks or sandbox actions ran. The earlier C-01 through C-07 concerns have been addressed in specifications; they should not be reported as still-missing design decisions. Their implementations and acceptance evidence remain absent. Existing requirements, seed records and source systems were not changed by this review.
