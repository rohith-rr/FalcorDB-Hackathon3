# Phase 4: decision-model adapters and measured graph exploration

Status: planned. Depends on Phase 3. Follow the [model decision record](decision_models.md); inference improves language handling, while the branch engine remains authoritative.

## Outcome

The system handles evaluated paraphrases, document/task ambiguity and ID-free task/branch association through a typed adapter. Clef evaluates the requested time-window discovery fallback; rules/evidence abstention remain available when it is unavailable. Known graph/branch decisions keep their source-verification requirements.

## Proposed files

```text
backend/app/models/{decision_adapter,rules,laya,jev,clef}.py
backend/app/routing/{questions,candidates,gates}.py
backend/app/associations/{clef,results}.py
evals/decision_routing/{development,held_out}.jsonl
scripts/evaluate_decision_routing.py
reports/decision_model_evaluation.md
tests/models/test_adapter_contracts.py
tests/associations/test_task_branch_discovery.py
```

## Internal adapter contract

`decide(state, questions, budget) -> DecisionBatch`: each result has question ID/type, selected value, provider distribution, optional confidence, provider/model revision, input-budget metadata and duration. `choice` and `score` may have confidence; `noul` retains its probability without inventing a provider confidence field. Validation rejects nonfinite/out-of-range values, unexpected option IDs and malformed shapes. Provider action signals do not grant tool execution.

Keep provider differences in adapters. Pin/check actual SDK and checkpoint versions. Make an integration smoke request before relying on a provider's presumed compatibility. Local Laya startup stays outside request handling; prewarm the selected model if hardware permits, and record cold start separately. Use configured server-side credentials/timeouts for Jev.

## Coding sequence

1. Wrap the Phase 3 rules router in the common interface and retain its output as a comparison baseline.
2. Implement Jev, Clef and/or Laya adapter according to available access. Verify endpoint/SDK request and response fields with a small smoke request. Record missing access as unevaluated.
3. Create intent `choice`: `BRANCH_BASE`, `TASK_CONTEXT`, `BLOCKERS`, `EPIC_PROGRESS`, `INCIDENT_BRIEF`, `INCIDENT_HISTORY`, `OTHER`. Exact identifiers bypass semantic entity selection but not intent resolution when needed.
4. Retrieve authorized candidates before semantic selection. Initial cap is 10 entities/documents per call, with a configured token budget for the chosen provider. Include descriptive option text, types, task purpose and short versioned excerpts. Map selected labels back to known logical IDs.
5. Add `NONE`/`AMBIGUOUS` options and request clarification when choices are incomplete or tied. Selection can narrow narrative context but cannot drop required delivery/verification evidence. If candidate retrieval exceeds budgets, refine scope or perform a measured hierarchical shortlist; do not silently omit the correct candidate.
6. Add optional `noul` judgments for narrative blockers and `score` over `routine`, `blocking current work`, `urgent production impact`. Use multiple independent questions for multiple comments/documents rather than pretending `choice` is multi-select. Ticket priority and policy remain primary.
7. Implement calibrated acceptance gates using the development split. Validate option membership, access and required evidence regardless of confidence. Ordering/label/truncation sensitivity is a measured failure mode.
8. Add provider timeout, exception and malformed-response fallbacks. Exact/rule-resolved requests continue; ambiguous requests return clarification. Log selection method and any fallback.

Batch questions using the same state where the verified provider supports it. If a first selection changes what data is fetched, use a second request with that new state. Known graph edges do not trigger individual model calls.

## Clef task-branch discovery

Implement the [association specification](task_branch_association.md) using Phase 2's work periods, identity bindings and per-head commit/content evidence. Trigger for assigned in-progress tasks without resolving explicit references. Keep explicit associations ahead of inference; overlapping tasks remain competing evidence rather than forcing unique branch ownership.

Call Clef through verified `state`/`questions` with branch choice and abstention/multiple options plus independent pair judgments. Validate suggestion gates/completeness and preserve model/input hashes in `BranchAssociationResult`. After inference, recheck complete discovery read-set equivalence, current task/identity/access inputs and candidate/stable heads under [publication policy](graph_publication.md#final-response-publication). Unrelated generations do not discard equivalent inference. Suggested edges remain INFERRED/CANDIDATE; no promotion, dependency invention or delivery proof.

Clef remains the requested discovery provider even if another handles routing. Missing/failed/malformed inference yields explicit abstention; never relabel rules as Clef. Return request-local suggestions and retain audits outside the graph. Project candidate edges only in a later explicit STRUCTURAL import, retaining original inference tokens/time/expiry and revalidating access/inputs. Producing queries never mutate the graph or trigger rebuilds. Test no self-mutation, equivalent unrelated publication during inference, relevant candidate/input changes, audit failure and expired/denied later projection.

## Evaluation and completion gate

Use the sample counts and gate in the decision record: at least 60 total examples and at least 20 held-out, grouped by scenario. Compare rules and each accessible model on identical inputs. Report intent/candidate accuracy, accepted precision/coverage, missing-option abstentions, p50/p95 latency, cold/warm behavior, token truncation, hardware and costs. Exercise option order changes, neutral/renamed labels, misleading document titles and unrelated questions.

Every branch regression from Phase 3 must pass with each adapter enabled and disabled. An adapter meeting the demo gate can be enabled for supervised semantic routing. A failed/unavailable adapter remains disabled; the completion report explains that outcome and the rules mode. This phase is complete when there is an honest evaluation and a working fallback, not when a model has merely returned valid JSON.

The discovery feature has an additional [association evaluation gate](task_branch_association.md#acceptance-and-evaluation), separate from the 60 routing examples: at least 20 association cases with 10 held-out, rules/Clef comparison, and an actual Clef smoke result before claiming live identification. Include ID-free positive cases and same-person concurrent-task negatives; verify high-scoring inferred-only prerequisite coverage never produces a branch command. Report unavailable inference as an incomplete feature, without disabling known explicit task/Git workflows.

## SRE extension

Add next-node/evidence selection with actual permitted neighbors plus `ASK_FOR_HELP`/`STOP`. Repeated choices use newly retrieved context, while full records remain in the evidence store. Test multiple pending paths, premature stop, absent candidates, source/model disagreement and several operating locations. A failed adapter uses a labeled deterministic/partial investigation. Compare rules, general-LLM navigation and specialized decision models with the same tools, snapshots, budgets and final answer provider. Measure cost per correctly grounded incident brief and missed evidence, not only decision-call price. See the [SRE integration plan](sre_integration_plan.md).

The controller owns `InvestigationCheck` states from [contracts](contracts.md). A premature model STOP yields the next required read while budget remains. Record timeout/provider failure as UNAVAILABLE, complete authoritative absence as MISSING, and unattempted work as NOT_CHECKED. Budget termination returns partial coverage; it cannot create missing-fact evidence or an executable plan.
