# Decision record: models within graph retrieval

Status: proposed; incident exploration and Clef documentation added 2026-10-09. No model inference or Company Brain benchmark has been run. This is a design recommendation inferred from provider capabilities and the problem structure.

## Decision

Use model-guided graph exploration within application-controlled reads and state verification. Evaluate specialized decision models for next-node/evidence selection, intent/entity/document routing and optional narrative judgments. Maintain several pending paths and required-check coverage. Use a separate LLM API after evidence retrieval to explain results. Ship labeled rules routing if a model fails evaluation; do not replace source facts with probabilistic judgments.

Add the requested [Clef task-branch association](task_branch_association.md): assignment/in-progress windows and mapped author activity retrieve candidates; Clef compares task purpose, commit messages and changed paths when explicit identifiers are absent. Evaluate this separately from routing, with competing simultaneous tasks and multiple possible branches. Model output establishes a candidate association, never verified delivery or unique branch ownership. The feature requires its own actual Clef smoke/evaluation result; using Jev/Laya for other routing does not demonstrate it.

## Verified provider capabilities

TypeSafe's [introduction](https://docs.typesafe.ai/introduction) describes its System One decision approach. Its [primitives documentation](https://docs.typesafe.ai/primitives) defines `choice` as selecting from supplied options, `score` as an ordered-level value, and `noul` as a yes probability. Choice/Score return distributions and confidence; Noul has no separate confidence field. Same-request questions see the same state independently; dependent questions require a subsequent request. Include an escape option when a choice set may be incomplete.

Laya's [maintained repository](https://github.com/NandhaKishorM/laya) documents non-autoregressive decisions, a Python runtime, model routing and local serving. The [publisher's model card](https://huggingface.co/convaiinnovations/laya) documents open Apache-2.0 weights, English/multilingual/typed-decision variants, bounded context and option budgets. Its stated limits include weak base-checkpoint results on some typed workflows, overconfidence, sensitivity of `noul` to option labels, and a low-information action signal. Use short, scoped inputs, evaluate calibration on this domain, and do not use `action.act_probability` as an execution gate.

These are publisher claims/capabilities, not independently measured Company Brain results. Do not transfer published speed/accuracy numbers to our hardware or compare mismatched provider benchmarks. Local inference has compute/operations cost even when weights are free. Recheck current access, license, versions, endpoint schema and data handling before implementation.

Cloudflare documents [Clef](https://developers.cloudflare.com/workers-ai/models/clef/) and [Clef-flash](https://developers.cloudflare.com/workers-ai/models/clef-flash/) as decision models that accept state and typed questions and return option probabilities. Evaluate either through the same internal adapter. They differ in model size and operating cost; this design does not assume that a specialized decision model is necessarily small or cheapest. [Cloudflare's explanation](https://blog.cloudflare.com/clef-decision-models/) describes non-autoregressive decision scoring. End-to-end cost and latency still include graph reads, source refresh, final answer inference and retries.

## Options to evaluate

| Option | Role in this project | Benefit | Cost or limitation |
| --- | --- | --- | --- |
| Exact lookup + rule router | Baseline and fallback | Reproducible; best for IDs and explicit state | Limited paraphrases and ambiguous titles |
| Laya | Semantic routing and rubric judgments | Can run in a controlled local deployment | Hardware/setup; context and choice budgets; domain accuracy must be measured |
| Jev | Same semantic adapter contract | Hosted operation avoids local model setup | Credentials, provider/network dependence and organizational data policy |
| Clef / Clef-flash | Node/evidence selection through the shared decision interface | Alternative hosted or approved local decision-model deployment | Test choice accuracy, truncation, access, hardware and actual total cost |
| Small embedding/classifier baseline | Candidate retrieval or domain intent classifier | Useful simple comparison for a narrow ontology | Needs relevance evaluation; cannot establish graph relationships |
| Structured-output answer LLM as router | Optional experimental comparator | Broader language interpretation | Added latency/cost and variable outputs; still needs validation |

Implement the rules baseline and at least one accessible Jev, Clef or Laya provider. Compare others when available; otherwise record them as unavailable/unevaluated. Do not train a new model for the demo. Add a domain classifier or fine-tuning only after collecting consented labeled failures in Phase 7.

## Traverse with small semantic decisions

1. Scope the question and resolve explicit identifiers without inference.
2. For paraphrases, choose from the development and incident intents in the [shared contracts](contracts.md), including `OTHER`.
3. Retrieve candidate tasks/documents structurally or with bounded text search.
4. Provide IDs mapped to descriptive labels, task purpose, document type, current version and short authorized excerpts. Never provide only arbitrary opaque IDs or an entire company corpus.
5. Select a candidate, several relevant items through independent questions, or abstain. The server verifies membership and access before use.
6. Traverse known edge patterns in code; assemble newly retrieved evidence for a second model call only when necessary.

For incident questions, repeat a bounded next-node/evidence-choice loop as new neighbors appear. Options include actual permitted nodes, supported evidence reads, `ASK_FOR_HELP` and `STOP`. Store full relevant context outside navigation calls. The [SRE integration plan](sre_integration_plan.md) specifies the pending queue, mandatory checks and stop conditions. Models decide exploration order, not whether a dependency exists, who is currently on-call or whether a customer actually has failures.

`choice` picks one option; it cannot supply all prerequisites or all relevant documents. Dependency closure and document completeness remain structural responsibilities. `noul` may classify review language, but review state/merge state comes from provider records. `score` can refine narrative urgency only after explicit priority and blocker policy.

## Evaluation and release gate

Create at least 60 labeled routing/selection examples with paraphrases, duplicate titles, missing candidates, unrelated intents and review-text judgments. Use a development split to tune thresholds; retain at least 20 held-out examples grouped by scenario/entity to reduce leakage. Small samples are a smoke evaluation, not broad reliability evidence.

Track intent/candidate accuracy, candidate retrieval recall, precision among accepted selections, abstention/coverage, ordering sensitivity, label sensitivity, context truncation, Brier score/calibration where meaningful, and end-to-end p50/p95 latency. Track score error/ranking agreement separately from classification. Preserve provider, model revision, prompts, option lists, token counts, hardware, cold/warm timings and cost.

Proposed demo gate: every structural branch regression passes; held-out accepted selections have no observed wrong-entity selections, with at least 70% acceptance coverage; missing-candidate and out-of-scope examples abstain; routine held-out intent accuracy reaches 90%. These small-sample thresholds permit a supervised demo, not autonomous actions. Compare accepted precision/coverage with rules and show sample counts. If the adapter fails, disable it and explain the measured limits.

Thresholds are configuration chosen on the development split, not inherent probability guarantees. Candidate validity, permissions, source freshness and delivery coverage always take precedence over model output. Provider timeout, malformed output or exceeded input budget yields rules fallback or clarification. [Phase 4](phase_04_decision_model_integration.md) specifies implementation work.

For SRE navigation, add incident cases with several useful paths, unchanged-code/configuration failures, runtime cycles, conflicting identity, absent customer measurements and premature-stop temptations. Compare direct graph/rules, general-LLM navigation and decision-model navigation using identical allowed neighbors, mandatory checks, snapshots and final answer model. Report cost per correctly grounded brief, missed evidence, retries, final context size and timing. A cheaper individual decision is not proof of a cheaper correct end-to-end answer.
