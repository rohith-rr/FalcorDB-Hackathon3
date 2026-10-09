# Phase 7: production Company Brain and controlled actions

Status: planned after the hackathon. Depends on Phase 6. No fixed sprint timebox. Split this phase into separate releases; completion of earlier phases does not authorize or implement these operations.

## Outcome

Expand the demonstrated graph into a reliable company service, then allow an engineer to create a branch from a verified recommendation through a controlled action. Maintain the same evidence and decision contracts as additional sources are connected.

## Release 7A: access and reliable sources

Proposed files: `backend/app/auth/`, `backend/app/permissions/`, `backend/app/jobs/`, `backend/app/connectors/jira.py`, document-provider adapters, database migrations and operational runbooks.

1. Add company identity/SSO and repository/project/document permissions. Enforce authorization before retrieval, during expansion, before answer construction and before trace access. Inaccessible prerequisites produce a scoped incomplete result without leaking titles, counts or URLs.
2. Implement source-specific ACL synchronization and revocation invalidation, including affected caches, content stores and traces. Decide approved hosted-model data handling per organization; local decision inference does not automatically make answer-LLM egress acceptable.
3. Extend the existing live Plane/Google Docs/GitHub adapters with live Jira and additional document providers, source-specific mappings, pagination and incremental cursors. Verify webhook signatures, deduplicate deliveries and reconcile periodically so missed events do not leave permanent stale facts. Per-user ACL synchronization builds on the demo's configured identity/scope.
4. Introduce a durable job queue and retry/dead-letter handling. Preserve the Phase 1 durable dirty-state/rebuild invariant until coherent versioned publication or transactional updates are validated across workers. Multiworker reads cannot rely on the prototype's process-local gate; add distributed admission/fencing before enabling them. Interrupted-import recovery is a Phase 1 requirement, not deferred production work.
5. Track mapping health: unknown deliveries, ambiguous task links, stale source scopes and conflicts. Offer an operator review workflow for inferred relationships; retain confirming evidence and source authority.
6. Add backup/restore drills, versioned schema migrations, retention/deletion policy, provider quota management, bounded resource use and monitoring for stale/incorrect recommendations.

Gate: source revocation removes access within an agreed measured SLO; duplicate/out-of-order events converge correctly; partial imports do not publish authoritative complete snapshots; restore and source-refresh failure exercises pass. Repeat interruption/restart and mixed-generation checks across workers; never serve a dirty graph after failover. Required Git/delivery correctness and candidate-specific revision-effect semantics remain independent of model availability.

## Release 7B: create a branch from a decision

Proposed files: `backend/app/actions/{plans,git,github,audit}.py` and client action review/confirmation UI. Querying stays read-only; a separate action endpoint consumes an expiring verified plan.

1. Create an action plan bound to principal, repository, selected base ref/SHA, new branch name, evidence IDs, policy version and expiry. Validate permissions and uniqueness.
2. Let the engineer review the exact proposed action and submit a separate authorized action request. Preserve confirmation in the audit record; do not infer authorization from a model score or source document text.
3. Re-fetch the relevant heads, check dependency coverage, reviews and policy, and verify the plan has not expired. If anything invalidates the plan, return a new reviewable plan instead of silently changing the base.
4. Create a local branch or a remote ref from the explicit SHA using the appropriate controlled adapter. Use argument arrays or the provider's typed API. Use idempotency keys and preserve a clear result on duplicate submission.
5. Verify the created ref points at the planned SHA and record source evidence, user, timestamps and provider outcome. Never automatically merge, rebase, force-push or delete a branch as part of branch creation.

Gate: duplicate action requests create one ref; unauthorized/expired/moved-head plans fail without side effects; the created branch has the exact verified SHA; the engineer can inspect the result and audit trail. Add integration tests against a disposable repository. Branch creation does not imply deployment readiness.

## Release 7C: broader company context and better retrieval

Extend the graph deliberately with services, owners, incidents, releases and approved document sources when those entities support defined company questions. Preserve entity/edge provenance and source permissions. Add hybrid full-text/embedding retrieval for long-document section discovery; use the graph to supply relationships and implementation evidence. Embedding similarity must not create confirmed task dependencies or complete delivery mappings.

Collect labeled domain failures with appropriate access controls, compare simple classifiers and Jev/Clef/Laya, and evaluate optional fine-tuning/calibration on scenario-separated held-out data. Version prompts, mappings and checkpoints and support rollback. Add broader tests for reversions, partial feature delivery, cross-repository version compatibility, stale approvals and long histories. Semantic preservation beyond commit ancestry requires explicit delivery/test/change evidence; do not turn it into an unverified model assertion.

Gate: each new question family has a contract, authoritative sources, permissions, regression scenarios and measurable quality/latency targets. Source growth must not weaken the original Payments branch-selection or TLS provenance behavior.

## Production release decision

Publish measured service SLOs, access controls, data coverage limits, restore procedures, provider dependencies and action failure behavior. Review operational readiness using actual evidence. The Company Brain is ready for a wider rollout only when its source freshness, authorization and decision correctness can be maintained outside curated demo fixtures.

## SRE extension

Promote the [incident requirements](../../SRE%20event%20handling.md) through actual monitoring/deployment/on-call/customer connectors, coverage reconciliation and per-user access controls. Treat draft notification, approved send, approved production action and incident closure as separate permissions. Production execution requires an exact expiring plan, current-state revalidation, scoped credentials, per-target serialization, idempotency, audit/outcome records and service-specific recovery checks. Verify provider receipts/actual state before retrying ambiguous outcomes. Store human-reviewed incident explanations and owned follow-up tasks without promoting generated text to trusted facts. See the [SRE integration plan](sre_integration_plan.md).
