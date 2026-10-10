# Phase 0: foundation, contracts and scenarios

Status: planned. Depends on the [master design](../../requirement_doc.md), [contracts](contracts.md) and [schema](graph_schema.md).

## Outcome

A developer can start the API and FalkorDB, inspect configuration, and load a coherent scenario definition without model credentials. This phase creates the scaffolding used by later phases; it does not implement question answering.

Apply the [workspace storage and deferred-credentials policy](workspace_setup.md) before any download. All new project dependencies, caches, temporary files and Docker engine data belong under `E:\FalcorDB Hackathon`. External tokens, OAuth, account logins and cloud provisioning are deferred until after Phase 2 implementation; local database/application secrets require no external account.

## Proposed files

```text
compose.yaml
.env.example
.gitignore
backend/pyproject.toml
backend/app/main.py
backend/app/config.py
backend/app/contracts/{query,evidence,decision,answer}.py
backend/app/contracts/conversations.py
fixtures/conversations/{local_session,cli_events}.jsonl
fixtures/conversations/{expected,review_manifest}.json
fixtures/payments/{tasks,pulls,reviews,documents,links}.json
fixtures/tls/{tasks,documents,links}.json
fixtures/scenarios.json
scripts/build_git_fixtures.py
scripts/Enter-ProjectEnvironment.ps1
scripts/Test-ProjectStorage.ps1
reports/workspace_setup.md
tests/conftest.py
README.md
```

Keep runtime snapshots, credentials, local caches and provider output out of committed fixtures. Add the future frontend directory in Phase 6. Pin a tested FalkorDB image/client and Python dependencies; record them in the completion artifact instead of guessing latest versions here.

## Coding sequence

1. Implement the project environment/storage preflight and verify all destinations before dependency downloads. Use a project-local Python runtime and `backend/.venv`, a dependency lock, and workspace package caches/temp directories. Configure FastAPI, Pydantic, the graph client and pytest. Document Windows PowerShell startup commands through the project environment using its Python executable; retain effective paths and disk-space observations.
2. Configure and verify Docker Desktop's host engine disk under `.local/docker` before pulling the pinned image; a Compose file on E: does not relocate image storage. Add Docker Compose with explicit project storage, a health check and local-only ports. Configure write durability for the Phase 1 import fence, including its persistence/fsync acknowledgment behavior; verify against the pinned image rather than assuming a mounted volume is enough. Keep locally generated database credentials in ignored environment configuration. Configure the browser using the pinned image's supported setup. Follow the workspace policy for WSL swap and bounded container logs.
3. Implement canonical configuration/contracts: source modes/scope, stable ref, traversal/freshness budgets, immutable projection ownership, per-projection import tokens, `GraphReadSet`, `EventBatchPolicy`/durable positions, retained bundles/content, revision effects, clarification TTL and independent model providers. Add durable action jobs/receipts/status and Plane/Google settings from [source adapters](source_adapters.md). Secrets stay server-only.
4. Implement `/health` and per-projection `/ready`. Database failure or dirty/uninitialized required projections fails aggregate readiness; routes declare and enforce their own projection requirements. Optional provider failures do not prevent startup. Graph reads require Phase 1 READY publication for their inputs; retained action-status lookup checks current access independently. Operator seeding/recovery remains available.
5. Define fixture IDs and source snapshots. Payments contains backend, UI and API tasks, a backend design document, an open backend PR and an individual changes-requested review. TLS includes current procedural content and a five-leaf-task epic with four completed tasks.
6. Define named scenarios and expected typed outcomes. Create a minimal Git fixture builder now for a stable commit and an unmerged backend delivery; expand it with advanced histories in Phase 3. Source manifests can use symbolic labels such as `backend_delivery`, but the builder resolves them to real full SHAs before validation or graph ingestion. Never use fake valid-looking SHAs.

## Scenario inventory

| Scenario | Expected behavior |
| --- | --- |
| Backend open and available on feature | Recommend feature; changes-requested warning |
| Backend delivered to stable | Recommend stable |
| PR closed without merge | Do not treat closure as delivery |
| Squash delivery with confirmed mapping | Verify integration revision and select stable |
| Squash mapping absent | Insufficient evidence |
| Independent dependency branches | Integration required |
| Transitive dependencies | Cover the entire prerequisite closure |
| Dependency cycle | Explicit cycle outcome |
| Deleted/force-pushed implementation ref | Refresh; withhold unsupported recommendation |
| Stale or inaccessible evidence | Withhold command; explain limited context |
| TLS runbook | Cite actual steps; retain task state; show 4/5 progress |
| Ambiguous task or missing candidate | Clarify or abstain |
| Model or LLM provider down | Explicit rules or deterministic fallback |
| Stable merge then revert; feature unchanged | Stable `REVERTED`, feature `INCLUDED`; recommend eligible feature |
| Confirmed complete reapplication | Restored stable `INCLUDED`; prefer stable |
| Revert after reapplication | Candidate `REVERTED` until separately restored |
| Partial/ambiguous restoration or missing effect history | `UNKNOWN`; withhold command |
| Import interrupted during mutation, then restart | Reads blocked until complete durable recovery |
| Import preparation failure | Previous snapshot remains readable at its original age |
| Query crosses unrelated publication | Equivalent complete read set survives without another inference |
| Query inputs change across publication | Discard affected context; one retry or typed 503, no invalid command |
| Added prerequisite/epic member/negative-result match | Read-set fingerprint changes even with unchanged cited IDs/heads |
| Clarification waits through unrelated import | Token remains valid; selected candidate and current evidence are rechecked |
| Continuous incident stream and worker restart | Durable bounded windows/positions; no per-alert structural rebuild |
| Asynchronous sandbox request | Durable 202 receipt, one worker operation and authorized status/recovery polling |
| Plane pagination/status/type/assignee coverage | Preserve IDs, all assignees and gaps; no inferred dependencies |
| Google Docs tabs/table/version change | Preserve content/anchors; retry race or reject required live import |
| Live adapter unavailable | Labeled export fallback; live integration gate incomplete |
| ID-free branch with assigned in-progress author activity | Clef suggests a candidate association with work-period/commit evidence |
| Same person, simultaneous tasks/unrelated commits | Content evidence distinguishes tasks or reports ambiguity |
| Reassigned/reopened/multi-assignee task | Separate work periods; do not attribute past work to the new assignee |
| Missing activity history/author identity or Clef outage | Explicit discovery abstention; retain explicit mappings |
| Inferred-only prerequisite implementation | No confirmed delivery coverage or branch-base command |

Fixtures are synthetic and labeled as such. No external provider account access is required through Phase 2 implementation. Plane/Google Docs/GitHub credentials and live smoke checks are scheduled in the separate onboarding step after Phase 2 implementation; final live demo acceptance still requires actual provider evidence.

## Validation and completion gate

- Startup instructions work on the implementation machine; API liveness and core readiness are observable.
- Storage preflight proves the actual Docker host disk, runtime, dependency/cache/temp and application-state locations are within the workspace before downloads, and rechecks them after install/restart. Unknown/C:-resident project storage fails this gate; preserve the OS exceptions and observations in the setup report.
- Contracts reject invalid enums, unscoped IDs and malformed command/evidence fields.
- Import states/errors, source-specific modes, multi-assignee tasks and revision-effect references have explicit contracts; fixture effect SHAs are resolved before ingestion.
- Scenarios and manifests contain no duplicate IDs or dangling references.
- The minimal Git fixture builder produces actual commit objects and resolves symbolic delivery labels for the Phase 1 seed.
- A settings example contains names/defaults with empty external secret values; startup/local readiness and checks work without provider credentials or interactive login through Phase 2 implementation.

Include the approved POC core decisions in foundation contracts/fixtures: `SourceAccessRecord` and its independent versions/errors, retained `AssociationAuditRecord`, `AnswerFact` references, exact incident-instance scope errors/picker, `InvestigationCheck` with UNAVAILABLE distinct from MISSING/NOT_CHECKED, and the durable sandbox execution state machine. Configure one application writer plus retained transactional local storage outside graph projection deletion. Add scenarios for discovery without generation mutation, denied content after failed import/restart, two same-named regional instances, premature STOP, a timed-out required check, false impact prose with a valid citation, and action crashes before/after mutation. Runtime behavior is checked in the owning phases, not by contract validation alone.

Record tested versions, startup commands and fixture inventory. Phase 1 starts when the runtime is ready and shared contract choices are settled.

Apply the [FalkorDB resource plan](falkordb_resources_and_hackathon_plan.md): verify the pinned image's actual persistence directory and its E:-resident backing storage, prove that the graph survives a container restart, and record the server/client/MCP compatibility matrix. A hosted demo is optional, configured only after Phase 2 implementation, and retains working local instructions.

## Codex conversation extension

Implement the configuration and typed [conversation contracts](contracts.md#codex-conversation-extension) from [the source specification](codex_conversations.md). Register allowlisted sources and explicit tenant/project/repository bindings, dialect/producer/parser/redaction versions, caps, capture storage and cursor policy. Add `CONVERSATION_CONTEXT`, optional exact IDs, message/review evidence and nullable `conversation_context` without changing existing clarification tokens or BRANCH/INCIDENT decision types.

Create sanitized synthetic JSONL fixtures alongside the expected normalization/review manifest. Cover visible user/assistant messages, injected user-role context, echoes, distinct repeated utterances, null IDs/times, partial tails, unsupported records, compaction/forks and missing attachments. Keep real personal session logs, hidden reasoning and credentials out of committed fixtures. Gate: configuration/contract checks reject arbitrary file paths and conflicting scope; fixture expectations distinguish proposed, accepted and superseded intent from verified operational facts. This gate prepares inputs; it does not claim a working importer.

## SRE extension

For an incident-focused build, follow [SRE event handling](../../SRE%20event%20handling.md) and the [integration plan](sre_integration_plan.md). Add incident contracts and synthetic alerts, deployment history, on-call overrides, runbook content, customer routing and observations. Service identifiers include environment/region; deployment/artifact IDs are explicit. Keep code authors, reviewers, owners and current responders distinct. Document permitted source scope and sandbox-only action policy. This is the same foundation phase, not a separate one.
