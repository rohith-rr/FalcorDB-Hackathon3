# Phase 3: traversal controller and verified branch decisions

Status: planned. Depends on Phase 2. This is the core product milestone and should work before decision-model or answer-LLM integration.

## Outcome

The API returns a typed branch recommendation or an explicit inability to select a single base. It can also retrieve task context, procedural blockers and epic counts. Every result exposes the graph path and verification evidence.

## Proposed files

```text
backend/app/traversal/{controller,resolver,dependencies,documents,progress}.py
backend/app/decisions/{branch_policy,review_policy,commands}.py
backend/app/verification/{git,provider,coverage}.py
scripts/build_git_fixtures.py
tests/decisions/test_branch_scenarios.py
tests/integration/test_git_coverage.py
tests/traversal/test_dependency_limits.py
```

## Controller and boundaries

Implement `RESOLVE -> RETRIEVE -> VERIFY -> DECIDE -> BUILD_CONTEXT` for the known branch workflow. A rules router initially maps explicit intents/IDs and a small set of phrases to templates. Ambiguous resolution returns accessible candidate choices. Query code controls reads and required checks. The incident extension uses a separate bounded model-guided exploration loop; neither workflow needs generated Cypher or unrestricted tools.

Defaults: maximum dependency depth 8, maximum 200 visited tasks, maximum 200 rows per frontier, and at most 20 branch candidates. Limits are configurable and visible in trace output. Exceeding any completeness-critical bound produces `INSUFFICIENT_EVIDENCE`; a partial traversal cannot issue a command. Retrieval may show partial context with that limitation.

All graph reads, including direct/MCP incident exploration, use the Phase 1 gates for their declared projections. Capture READY tokens and a complete `GraphReadSet`; compare accumulated semantic inputs when tokens change between batches and before publication. Equivalent unrelated changes do not consume a retry. Required DIRTY state returns `GRAPH_RECOVERY_REQUIRED`; repeated relevant changes/unprovable equivalence after one retry use `GRAPH_SNAPSHOT_CHANGED`. No availability failure produces cached commands or graph-derived fallback answers. Follow [scoped validation](graph_publication.md#request-read-set).

Task context may include Phase 4's [Clef association suggestions](task_branch_association.md) through the separate `branch_associations` contract. Retrieve inferred links only in a scoped candidate-evidence path; do not feed them into confirmed implementation/delivery traversal. A likely implementation branch does not establish prerequisite coverage. Missing delivery mappings remain `INSUFFICIENT_EVIDENCE`, while known complete explicit evidence continues to work independently of discovery.

## Branch algorithm

1. Resolve the target within permitted project/repository scope. Resolve stable from repository configuration. Unknown or inaccessible repository mapping stops branch planning.
2. Fetch all confirmed outgoing prerequisite relationships through bounded frontier queries. Record the induced graph and use directed cycle detection/topological ordering. A shared ancestor in a diamond-shaped DAG is not a cycle. Do not skip prerequisites merely because the tracker calls them `DONE`.
3. Separate code dependencies from process dependencies. Unknown dependency kind or incomplete dependency coverage prevents assuming a complete code plan. Process blockers remain visible and can affect policy, without inventing a Git revision for a runbook.
4. Build required delivery groups for every code prerequisite. Require confirmed complete mappings. All groups must be covered; complete implementation/integration alternatives within one group are OR choices. Unknown and partial deliveries prevent a verified recommendation.
5. Enumerate stable and confirmed implementation branches in the requested repository; optionally include an explicit integration branch from the manifest. Refresh live ref existence/heads and relevant PR/review records. Candidate overflow cannot silently drop the correct branch.
6. For each candidate, verify each delivery group against its exact head. A Git ancestry result establishes historical inclusion. A confirmed squash/rebase integration mapping can satisfy the same group; PR merge metadata by itself cannot prove the requested stable head contains it.
7. Evaluate confirmed revision effects per candidate under the [canonical effect rules](graph_schema.md#revision-effects-and-candidate-history). Check each effect commit against the exact candidate head; ignore effects verified absent from that history. A reachable complete revert vetoes all alternatives of the delivery group unless an included confirmed complete reapplication explicitly resolves it and descends from it. Resolve every applicable revert; a subsequent revert requires separate restoration. Partial/ambiguous restoration, missing effect history or contradictory mappings produce `UNKNOWN`. Preserve candidate-specific effect/ancestry evidence. If preservation after arbitrary later edits is not checked, disclose that limit; never equate ancestry with tested behavior.
8. Apply development policy and compute review readiness separately. Default demo policy permits local dependent development on an available feature branch with requested changes, but always displays the review warning. Draft/missing review and failing checks, if ingested, are warnings or policy exclusions; they are not merge-state evidence. Deployment readiness remains `NOT_EVALUATED`.
9. Select stable if it covers every group and policy allows it. Otherwise select the single eligible complete-coverage feature/integration candidate. Where several remain, use an explicit preferred branch in the manifest; absent that preference, return `NEEDS_CLARIFICATION` with candidates and no command. A semantic score does not break an operational tie.
10. If no candidate covers everything but dependencies have separate available implementations, return `INTEGRATION_REQUIRED` with source branches, missing groups and an advisory integration order. Cross-repository dependencies require version/package/service integration; branching from another repository cannot supply them.
11. Before recommendation, refresh selected/stable heads outside graph gates, then validate required READY projections and the complete semantic read set under the shared/access gates. A token change alone does not invalidate equivalent inputs; relevant changes discard affected evidence and permit one whole-request retry. Graph unavailability uses typed 503; repeated live-head changes produce stale evidence. Phase 5 repeats scoped validation, original `valid_until` and head checks after any LLM/fallback work before publishing commands or recommendation prose. Record exact SHAs, original observations and current validation tokens without extending freshness.

Use explicit outcome precedence: a detected cycle returns `DEPENDENCY_CYCLE`; missing scope/mappings or incomplete traversal returns `INSUFFICIENT_EVIDENCE`; failed required refresh returns `STALE_EVIDENCE`; complete coverage with all candidates excluded by policy returns `POLICY_BLOCKED`; fully verified separate dependencies without one covering candidate return `INTEGRATION_REQUIRED`. Unknown stable coverage withholds a definitive base recommendation instead of asserting stable lacks the code. Candidate ambiguity uses response resolution `NEEDS_CLARIFICATION` with a null branch decision and no commands.

No code prerequisites with confirmed complete dependency scope permits stable as the default new-work base, after ref/policy verification. Absence of edges in an incomplete import is not that condition.

## Git verification

Use an adapter with argument arrays and a configured repository mirror. Never pass user questions into a shell. Clone/fetch only allowlisted repository identities and remote refs. Validate revision syntax/existence and ensure mirror paths remain in application storage.

```text
git merge-base --is-ancestor <required-full-sha> <candidate-full-sha>
```

The [Git manual](https://git-scm.com/docs/git-merge-base) defines exit 0 as ancestor, 1 as not ancestor, and other errors as failures. Return `UNKNOWN` for missing objects, provider errors or incomplete/shallow history; fetch needed history before a negative decision. Squash/rebase uses a confirmed integration alternative, not a guessed patch. Use the same adapter for effect inclusion and revert-to-reapplication ordering. Cache candidate decisions by repository, required revisions, exact heads, semantic read-set fingerprint and mapping/effect/policy versions; stored generation tokens trigger revalidation rather than unconditional cache misses. Never cache by branch name alone. Pure Git ancestry may be reused by SHA; changed effect records require recomputation.

A repository-wide clone may be expensive; the demo can use a small allowlisted repository and targeted history. If provider ancestry queries are used instead of Git, validate equivalent semantics and record the method. The algorithm cannot treat a compare timeout as proof of absence.

## Proposed commands

Generate engine-owned argument arrays, for example:

```text
git fetch --no-tags origin refs/heads/feature/backend-service
git rev-parse --verify FETCH_HEAD
git switch -c feature/public-api <verified-full-sha>
```

The UI states the expected fetched SHA and requires stopping if it differs; the final command uses the observed full SHA. Show repository identity/remote and validate the new ref name. A formatted command is a proposal, not an operation performed by the query endpoint. Warn that creating dependent work on an open implementation may require future updates. Deleted refs are ineligible even if a historical graph node survives.

## Other workflows

Task context follows confirmed document/implementation/review edges. Procedural retrieval selects current accessible runbooks and retrieves their contents. A found process never updates task state. Epic aggregation deduplicates eligible leaves, excludes cancelled leaves, handles empty sets, and reports unknown/partial status coverage using the schema formula.

## Validation and completion gate

Create actual temporary Git repositories for conventional merges, unmerged feature work, squash mappings, independent features, transitive coverage, force pushes and reverts. Fixtures generate real SHAs and overwrite symbolic manifest labels before graph import. Run these through the same coverage adapter as live queries.

Pass all Phase 0 branch scenarios. Include diamond DAG versus cycle, configured stable ref other than main, multiple repositories sharing a branch name, partial task delivery, PR merged into a different target, later unmerged branch additions, deleted feature with stable coverage, and review dismissal/current-head differences. Confirm no denied/incomplete/stale case yields a command. Payments selects the backend feature with review warnings; a verified complete stable delivery selects stable. Retain typed output and trace for Phase 4 comparisons.

Add real Git histories where stable conventionally merges then reverts a delivery while feature is unchanged: stable must be `REVERTED` and feature `INCLUDED`. Verify complete restoration and later reversions, squash/rebase alternatives that cannot bypass same-group effects, unrelated reversions, partial/incomparable restoration, missing objects and conflicts. Ambiguity returns `UNKNOWN` with no command. Changed mapping/effect inputs invalidate caches with unchanged heads; unrelated publications preserve equivalent accumulated inputs. Include 201 rows concentrated on one frontier task: overflow must remain explicit and cannot yield a complete recommendation or silently omit other tasks.

## SRE extension

Follow the [FalkorDB resource plan](falkordb_resources_and_hackathon_plan.md) for the constrained MCP reader, transport receipts and query diagnostics. Start with time-filtered Cypher/frontier retrieval. A native algorithm can be added after proving direction, time/access scope and equivalence; a single shortest path cannot establish complete exposure.

Implement neighbor/evidence operations and `InvestigationState` from [contracts](contracts.md), retaining several pending paths. Required source checks and permissions remain deterministic; the model selects exploration order. Check historical/current deployment, current responder, dependency scope, customer observations and runbook context. Emit possible explanations and observed/possible impact separately. Runtime cycles use visited tracking; incomplete or cyclic action ordering blocks an executable plan. Action checks bind exact target and deployment state, distinguish source revert from deployment restoration, and account for schema/config compatibility. See the [SRE plan](sre_integration_plan.md).

Use the POC exact-instance picker/request validation before traversal. Initialize the controller-owned `InvestigationCheck` queue and enforce the canonical STOP rule: unattempted required checks cause the next deterministic read while budget remains. Timeouts are UNAVAILABLE, not MISSING; budget termination preserves NOT_CHECKED items in a partial brief. Rehearse duplicate service names across regions, immediate/repeated model STOP, source timeout, missing runbook and incomplete customer coverage. Only complete, current, permitted action prerequisites can enable an executable sandbox plan.
