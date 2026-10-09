# Phase 6: query UI, evaluation and hackathon demo

Status: planned. Depends on Phase 5.

## Outcome

The Company Brain can be demonstrated from a natural-language question to a cited recommendation and its graph path. An engineer can see which data supported the answer, whether it is fresh, and why a command was withheld.

## Proposed files

```text
frontend/package.json
frontend/src/{App,api,types}.tsx
frontend/src/components/{QueryForm,AnswerPanel,DecisionCard,SourceList,TracePanel}.tsx
tests/end_to_end/test_company_brain.py
scripts/run_scenario_suite.py
reports/demo_acceptance.md
docs/demo_script.md
```

Add a small graph-path view using returned node/edge IDs, or a simple ordered path for the first implementation. FalkorDB Browser remains part of the presentation for the overall graph. The application trace is the authority for the actual traversed path; browser layout alone does not prove what the engine checked.

## Coding sequence

1. Build a question box with project/repository scope, sample Payments/TLS prompts and loading/error states. Keep credentials and raw provider configuration out of the client.
2. Render typed decisions with selected branch and pinned SHA, prerequisite coverage, applicable revert/reapplication evidence per candidate, observed review state, warnings and verification time. Label each source's data mode (`FIXTURE`, `IMPORT`, `LIVE`) and answer mode separately; a live document must not relabel fixture relationships as live.
3. Display exact task/design/runbook/PR/review source links and excerpts with versions. Provide accessible candidate selection when resolution requests clarification.
   Retain the signed original token/question/scope across unrelated background imports. Submit exactly one selected candidate; current candidate/access/head checks run on continuation. Expiry/removal returns fresh choices or NOT_FOUND without automatically choosing a replacement.
   In task context, display `branch_associations` as suggested implementation branches, with assignment/work period, author commits, changed paths, model score and limitations. Keep these suggestions distinct from verified base recommendations; a clarification selection does not confirm an inferred association.
4. Show proposed Git commands only for eligible unexpired results. Include expected repository/remote and fetched SHA. Disable command copying after expiry until refresh; the query has not created a branch.
5. Show evidence path and verification detail on demand. Model probabilities are a routing signal, not code readiness. Distinguish stale source data, incomplete context and provider fallback using plain language. Handle HTTP 503 import/recovery and snapshot-change errors with a clear retry state, suppressing decisions/command copying from invalidated requests.
6. Add basic browser integration or a demo path query for Payments and TLS. Keep graph access local/configured for the prototype. Never expose unrestricted database credentials in browser code.
7. Run the full scenario suite and rehearse using seeded data and prewarmed services. Retain a fallback presentation mode if the network/provider fails; state its limitations visibly.

## Acceptance matrix

| Scenario | Required visible behavior |
| --- | --- |
| Payments, unmerged backend | Verified feature base; current review warning; exact implementation evidence |
| Backend fully integrated into stable | Stable base and complete coverage |
| Closed-unmerged, missing/partial mapping | Limited answer; no unsupported stable/feature command |
| Multiple independent dependencies | Explain integration need; no single-base command |
| Cycle, row/depth overflow or cross-repository prerequisite | Explicit inability to complete branch plan |
| Stale/moved/deleted ref | Refresh or withhold command; show observation state |
| Stable merge/revert; unchanged feature | Show stable `REVERTED`, feature `INCLUDED`, and candidate-specific evidence |
| Complete reapplication, then another revert | Restore stable eligibility, then block it after the new revert |
| Partial/ambiguous effects or missing history | Explain unknown coverage; no command |
| Interrupted import and restart | Show recovery-required state; no graph answer/command until full rebuild |
| Unrelated publication during an answer | Preserve equivalent context/prose with one LLM call; show original observation and current validation times |
| Relevant dependency/aggregate/absence/effect changes during an answer | Discard affected context; one retry, then typed 503 if relevant changes persist |
| Clarification waits across unrelated imports | Accept the same token/selection; recompute current resolution and branch checks |
| Clarification candidate removed/access revoked/head moved | Show current candidates/NOT_FOUND/stale result without guessed scope or token-time commands |
| Continuous incident events / incident recovery | Show pending-event freshness and bounded publication; structural-only questions remain usable |
| Live Plane plus Google Docs context | Actual task/document citations, all document tabs/sections and source-specific modes |
| Live source unavailable | Clearly labeled export fallback; full live demo gate remains incomplete |
| Ambiguous/out-of-scope question | Clarification or unsupported result |
| Task context | Current documents, PRs and individual review evidence |
| No task ID in branch/commits | Suggested Clef association with matched person/time/content evidence |
| Same author on concurrent tasks/branches | Ambiguous/multiple associations remain visible; no invented exclusive ownership |
| Incomplete identity/time history or Clef failure | Explain discovery abstention; no inferred delivery or branch command |
| TLS process | Actual cited steps, unchanged task status and justified progress counts |
| Decision model down | Working rules/clarification and labeled routing fallback |
| Answer LLM down or invalid | Deterministic response and labeled answer mode |

Also verify keyboard use, readable source links, handling of long branch names, concurrent requests and cancellation. The frontend must not reinterpret policy or construct Git commands independently.

## Measurement

Measure resolution, graph retrieval, live verification, decision inference and answer inference separately, plus end-to-end p50/p95. Record hardware, graph size, fixture/live mode, cold/warm cache, provider/model revision and sample count. Proposed demo targets: warm fixture/rules decisions under 1 second p95 and total answers under 5 seconds p95. These are targets to measure, not provider guarantees; publish actual misses and their causes.

Test authorization using configured allowed/denied demo scopes, ensure traces cannot be fetched across scopes, and ensure logs contain no secrets. Publish counts for branch correctness, inappropriate-command incidents, supported citations, model acceptance/abstention and fallback rate. No inappropriate branch command is allowed in the controlled acceptance suite; passing it does not establish general production reliability.

## Demo script and completion gate

1. Display Epic-Payments with backend/UI/API, design, PR and review relationships in FalkorDB Browser.
2. Ask which base to use for Public API; show the dependency path, Git coverage and open-review warning, followed by the cited LLM explanation.
3. Switch to a prebuilt merged-delivery scenario, clearly label the scenario change, and show stable selection.
4. Show an independent-dependencies example where no single-base command is issued.
5. Ask Task-404's TLS question; show runbook content, unchanged task state and the evidence behind 4/5 progress.
6. Show a provider failure with a useful labeled fallback.
7. Show stable's reverted delivery alongside the still-usable feature candidate, then its confirmed reapplication. Expose the effect commits and ancestry evidence.
8. Demonstrate an interrupted import/restart: readiness and graph reads stay blocked until full rebuild; no mixed-snapshot output appears.
9. Retrieve actual live Plane task context and an allowlisted Google Doc, including multiple tabs and a table. Show source-backed citations and source-specific modes using the [adapter smoke gate](source_adapters.md#acceptance-and-completion-record).

Completion requires the scenario report, tested startup/seed/recovery instructions, successful real API answer evidence from Phase 5, both live Plane/Google Docs adapter smoke results, a replayable demo, and an explicit list of unfinished production capabilities. Export-only fallback or unavailable live credentials leaves this full gate incomplete. Do not call the system production-ready at this gate. These are future implementation checks, not results of the design revision.

## SRE extension

Use the [FalkorDB resource plan](falkordb_resources_and_hackathon_plan.md) for the focused demonstration, query/submission inventory and optional `@falkordb/canvas` UI. Show actual retrieved paths, one approved sandbox restoration and a variant where changed evidence blocks the action. Record measured latency/cost, transport usage and synthetic/live modes; graph visuals must correspond to backend evidence.

Show an incident view with current responder, operating scope, time-ordered changes, observed versus possible effects, evidence paths and unresolved checks. Display and separately approve an exact sandbox action plan, then record actual execution and recovery observations. The executor operates only on a disposable local target; no production changes or real notifications belong to the demo. Replay duplicate alerts, configuration-only failure, unsafe schema rollback, runtime cycles, moved targets and provider failure. An advisory-only demo must not claim demonstrated action execution. The [SRE plan](sre_integration_plan.md) gives the alternative demo scope and cuts.

Use an explicit service-instance picker backed by `GET /service-instances`, displaying service, environment and region. Submit a fresh scoped query; show SERVICE_INSTANCE_REQUIRED/SERVICE_SCOPE_CONFLICT without guessed results. Display check status including UNAVAILABLE and NOT_CHECKED so timeout and skipped work never look like evidence of absence. Render critical answer facts from backend fields and show model prose only after validation. Source-access errors clear affected results and disable stale actions; trace retrieval enforces current access too.

The action review shows exact version, target/current/desired artifact, compatibility and expiry. Execute receives 202 with the operation receipt/plan Location; poll authorized `GET /action-plans/{plan_id}` every second initially, backing off to at most five seconds while hidden or on transient failure. Stop polling on view cancellation/unmount or settled operation/recovery; UNKNOWN_OUTCOME shows reconciliation without resubmitting execution. Repeated clicks reuse the existing operation. Render known operation outcome separately from 30-sample recovery progress and PASSED/FAILED/INCOMPLETE/NOT_REQUIRED status, including SUCCEEDED restoration with failed probes. Polling starts no action and does not depend on graph READY. Follow the [sandbox recipe](sre_integration_plan.md#poc-sandbox-recipe). Include prompt receipt/progress, durable enqueue failure, duplicate/restart/unknown-outcome and access-denied polling cases alongside existing incident/grounding regressions. Cached historical results never become new current recommendations.
