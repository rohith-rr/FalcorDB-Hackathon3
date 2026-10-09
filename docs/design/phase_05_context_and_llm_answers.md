# Phase 5: evidence retrieval and LLM explanations

Status: planned. Depends on Phases 3 and 4. This phase implements the original intent: retrieve company context through the graph, then call an LLM API to produce a useful answer.

## Outcome

An engineer gets a concise, cited explanation of the verified decision, relevant documents and review concerns. The answer provider is replaceable; invalid or unavailable model output falls back to a deterministic response.

## Proposed files

```text
backend/app/context/{builder,sections,budget}.py
backend/app/models/answer_llm.py
backend/app/answers/{prompts,validate,fallback}.py
backend/app/api/query.py
tests/answers/test_grounding_and_fallback.py
evals/answers/scenarios.jsonl
```

The project is provider-neutral. Select an available approved LLM API and implement its verified request/response interface. Record provider/model version at implementation time; do not assume a particular vendor's SDK or structured-output support.

## Coding sequence

1. Build `ContextBundle` from typed graph/verification results and its complete `GraphReadSet`. Include resolved task/epic, complete decision evidence, delivery coverage, branch/PR/review state, current document sections, counts, source times and limitations. Retain empty-result/aggregate scopes and relationship evidence even when the model cites only selected nodes.
2. Retrieve bytes for chosen immutable document versions and extract relevant sections. Preserve Google Docs tab IDs and version-bound section anchors, plus list/table structure, under the [adapter specification](source_adapters.md). Prefer explicit headings/anchors and bounded text matching; add semantic retrieval only if necessary. A title-only match cannot supply procedural steps. If content is inaccessible/missing, return only accessible metadata with that limitation; never expose revoked content.
3. Assign stable request-local evidence IDs and construct a citation registry with source links/versions. Evidence for every recommendation, review warning and numerical claim is mandatory.
4. Enforce the answer model's token budget. Always retain the selected decision, prerequisite coverage and limitations; trim optional prose first. If critical evidence cannot fit, use a deterministic result rather than hiding missing evidence.
5. Make one LLM API request for the final explanation. Give the user's question, typed decision and bounded evidence. Source content is quoted data, not tool instructions. The LLM has no graph-write or Git execution permissions.
6. Validate structured output where supported; otherwise request a constrained shape and parse defensively. Unknown evidence IDs, altered refs/SHAs, false task transitions, unsupported completion claims or inconsistent counts reject the affected explanation and select fallback.
7. Render branch/ref/SHA, commands, task status, progress counts and source URLs from engine fields. Keep LLM prose explanatory. Merely checking JSON/citation existence does not prove entailment: cross-check key facts and evaluate claim support manually on demo scenarios.
8. After the LLM call, validate required projection readiness and the complete read set under [final publication](graph_publication.md#final-response-publication), then return `QueryResponse`, trace, validation metadata and timings. Changed generation/snapshot triggers semantic comparison; equivalent inputs preserve the prepared explanation without another model call or retry. Relevant/unprovable changes discard context and retry the whole request at most once; repeated changes use the typed 503 contract. This gate also checks the original `valid_until` and refreshes selected/stable heads before publishing commands or current recommendations, including timeout fallback. Perform network checks outside gates and repeat final local validation afterward. If live verification remains stale, return `STALE_EVIDENCE`, withhold commands and replace any prose recommending the affected branch or asserting current coverage with deterministic historical context: prior observation time, changed/expired inputs and required rechecks. Accepted API output uses `LLM`; provider timeout, unavailable credentials/quota or invalid output with valid current inputs uses `DETERMINISTIC` and discloses the limitation. Dirty/unavailable required projections cannot yield graph-derived fallback answers.

## Fact registry and final publication

Implement the `AnswerFact` registry from [contracts](contracts.md): each fact has an entity, predicate, typed value, uncertainty/classification, observation time and evidence IDs. Supply it to the answer model and require structured explanatory statements with fact/evidence references. Render critical values, counts, responder, impact classification, branch refs/SHAs, commands, action targets/status and links from engine fields. Reject unknown references, contradictory values, unsupported source transitions and changed qualifiers even if the supplied citation ID is valid. Inspect remaining prose on demo cases; this is not a general automated entailment guarantee.

For example, a Customer B fact classified POSSIBLE cannot support prose asserting observed failures. A stale branch decision cannot support a present recommendation. Runbook retrieval keeps applicability and prerequisites with selected steps; if those sections are inaccessible or cannot fit, withhold the procedural instruction or return its limitation rather than a misleading shortened procedure.

Bind context to every evidence resource/enclosing-scope access version. Before publication, including fallback, enforce required projection gates, complete read-set equivalence and the [access registry](contracts.md#source-access-registry). A relevant access change discards affected explanation/decisions/citations/trace; rebuild once within the shared retry budget or return the content-free access error. Acquire STRUCTURAL then INCIDENT when required, then access; writers never reverse order. Hold no gates across provider calls. Final comparison, access validation and response admission share the short local critical section. `validated_against`/`validated_at` record current validation without relabeling evidence snapshots or extending freshness.

Add cases for valid citation IDs paired with a wrong impact classification or responder, omitted runbook prerequisites, denial during an outstanding model call, cached trace access after denial, and denial-registry failure. An unchanged graph generation must not allow a revoked source to escape through prose, citations, suggestions or fallback.

## Prompt contract

The prompt instructs the provider to answer only from supplied evidence; explain the reason and caveats; distinguish available/approved/deployable; cite statement evidence IDs; state unknowns; never claim a branch was created; and never treat an embedded document/comment instruction as a system directive. Avoid putting unrelated confidential documents in context.

Expected narrative for Payments: use the verified backend feature revision for dependent development; stable lacks required delivery; the backend PR remains open with requested changes; cite design/PR/review and mention future integration work. The TLS explanation cites actual runbook steps and preserves observed blocked/in-progress state.

## Fallback contract

Templates express the typed recommendation, missing groups, review warnings, freshness and citations. They also handle clarification, unsupported intents, partial document access, and stale-evidence downgrades: the stale-evidence template reports what was previously verified with observation times, what changed or expired, and the required rechecks — it must not recommend the affected branch or assert its coverage. A fallback should be practically useful even when the LLM is down; it must not imply that an LLM API succeeded.

## Validation and completion gate

For `branch_associations`, explain work-period, author and content evidence as a suggested association rather than established implementation/delivery. Before final publication, recheck suggestion expiry, current task/identity inputs and candidate/stable heads after the answer call, including timeout fallback. If refreshing cannot recover, clear the preferred association, return discovery uncertainty, and replace invalidated association prose with deterministic text; old commits/periods can remain only as explicitly historical evidence. Existing verified-base `STALE_EVIDENCE` narrative handling remains mandatory.

Run every typed scenario through the answer layer. Deliberately supply a response choosing the wrong branch, an unknown citation, a fabricated 80% count, a claim that the PR merged, and a source excerpt instructing it to ignore policy. Confirm rejection/fallback and preservation of authoritative fields.

Publish an unrelated incident/structural batch during an LLM request: identical complete inputs must keep the original explanation and a single model call. Change a dependency edge, epic membership/count, previously empty lookup, effect/policy record, document version or relevant deployment without changing cited node IDs/heads: the answer must invalidate. Test one retry and typed 503 on repeated relevant changes or required-projection recovery. Expire verification or move selected/stable heads during inference/timeout fallback: withhold commands and current recommendation prose via `STALE_EVIDENCE`; prior observations remain explicitly historical. Check candidate-specific effect explanations, Google Docs tab/version citations and unchanged evidence TTL across scoped revalidation.

Perform and retain at least one successful **real** LLM API request for Payments and one for TLS using synthetic authorized evidence. Human-check citation support, review caveats, task state and command consistency. Mock-only or fallback-only results do not complete the requested graph-to-LLM demonstration; record that portion as blocked until API access is available. Provider failures need no graph-engine changes.

## SRE extension

The [FalkorDB resource plan](falkordb_resources_and_hackathon_plan.md) proposes a bounded GraphRAG SDK document-retrieval experiment after the basic incident works. Inspect context with the SDK's retrieval-only API, map source passages to canonical evidence IDs and count any extra model calls. Retain existing Markdown section retrieval unless provenance, identity and access checks pass; final incident facts and actions remain application-owned.

Build an incident context bundle containing visited paths, relevant node facts, observations, deployment/time scope, current responder, possible explanations, observed/possible impact, runbook sections and recovery checks. The final LLM writes a cited brief and message draft; it cannot confirm causes, mark possible exposure as measured failure, choose a new target, approve actions or send messages. Keep required evidence within the context budget and report omissions. An SRE-focused demo must retain a real incident-answer API result and useful fallback; live production recovery cannot be claimed from sandbox evidence. See [SRE requirements](../../SRE%20event%20handling.md).
