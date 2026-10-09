# Create Company Brain's implementation backlog and demo evidence

Use this file as instructions for an agent with access to Plane and this repository. The tasks represent real work building Company Brain. As developers implement them, their actual branches, commits, PRs and reviews become data for the app's own demo.

This is a creation recipe, not a record that tasks or PRs already exist. Local keys such as `T01` are seed identifiers, not Plane issue keys. Start with task creation only. PR creation belongs to later, explicitly requested implementation work, after real changes exist.

## Copy-paste prompt

> Read `docs/demo/plane_project_seed_instructions.md`. Execute the initial Plane seeding workflow in the existing Plane project named **Falcor DB hackathon**. Resolve its actual workspace and project ID through the connected tools; if multiple projects match that name, ask which workspace to use. Do not create a new project. Create or reuse the four parent epics and eighteen implementation tasks in that project, including the specified task dependencies, and write the local receipts and relationship manifest. Use the supplied descriptions and acceptance criteria without expanding the scope. Do not implement code, create placeholder PRs, or manufacture completed work. Reuse existing records on reruns. Ask only for required scope or access information that cannot be resolved from the supplied configuration or connected tools. Report the resolved workspace/project, actual created/reused IDs, and any incomplete items.

## Inputs to resolve once

| Input | Value / rule |
| --- | --- |
| Repository | Expected remote: `https://github.com/rohith-rr/FalcorDB-Hackathon`; verify against the checkout before using it |
| Plane instance | Resolve from the user's connection/configuration; do not assume hosted versus self-hosted |
| Workspace | Exact workspace slug and native ID; ask if not supplied and multiple choices exist |
| Project | Existing project named **Falcor DB hackathon**. Resolve its native ID and workspace through connected tools; ask for the workspace only if matches are ambiguous. If no match is accessible, report the missing scope/access rather than creating a project or choosing a similarly named one. |
| Assignees | Use supplied or explicitly selected native user IDs; otherwise leave tasks unassigned |
| State IDs | Inspect the project's actual states; map its backlog/unstarted state to initial `TODO` |
| Type IDs | Inspect configured work-item types; use real epic/task types where supported |
| Stable ref | Read the repository's configured/default branch; do not assume `main` |
| Seed namespace | `company-brain-poc-v1`; keep it unchanged on reruns |

Use the available Plane connector first. If an API script is needed, inspect the current instance/API documentation and supported operations before writing it. Read credentials from configured secret storage/environment; never put tokens in descriptions, output files or source control. If there is no writable connection, prepare the local payload/manifest and state clearly that external creation is blocked. Do not invent receipts.

Do not create users, invite people, change project settings, send messages, or modify unrelated work items. The seeding request authorizes the requested task records and their descriptions/relationships. It does not authorize a bulk status reset of existing work.

## Initial seeding workflow

1. Read this file and the [design index](../design/README.md). The linked task specifications are authoritative for implementation; this catalog intentionally summarizes them. Read only the relevant specification when needed, rather than loading every design document.
2. Inspect the selected project's states/types and existing work items, including all pages. Resolve project scope before mutations. Find records by their exact seed marker and saved native IDs, never by title alone.
3. Create/reuse the four epic records, then the eighteen leaf tasks below. Use each record's exact title, supplied scope and acceptance criteria. Initial state is the project's backlog/unstarted state; priorities and due dates are optional and must not be invented as commitments.
4. Add the marker `Seed-Key: company-brain-poc-v1:<E01|T01|...>` to each description. Add the parent, specifications and dependency list to task descriptions. A repeated marker on multiple records is a conflict: report it instead of creating another record or choosing arbitrarily.
5. Save a creation receipt immediately after every successful creation. If a create request times out, list/reconcile by marker before retrying. On rerun, reuse IDs, preserve human edits and real status/assignment/history, and fill only missing seed-owned information. Record differences rather than silently overwriting them.
6. Set real parent relationships when supported. If native epic/task hierarchy is unavailable, retain explicit logical parent IDs/types in the manifest and report the adapter mapping needed. A module/cycle or generic relation must not silently become an epic or dependency.
7. Write the directional dependencies from the table below into a verified local manifest. Native dependency relations are optional if their semantics are verified; the app's design uses the manifest as the authoritative POC dependency source. Description text alone is not a graph mapping.
8. Read back every created/reused record and verify its native ID, key, URL, parent, state and assignment. Leave all new tasks `TODO`. A task is not `DONE` because its seed record exists.
9. Produce the receipts, mapping and short report described below. Stop initial seeding here; no Git branches, PRs, fake reviews, incident events or backdated activities are needed.

## Parent epics

| Key | Exact title | Description | Children |
| --- | --- | --- | --- |
| E01 | Build the Company Brain runtime and graph foundation | Provide the local runtime, shared contracts, durable graph publication and bounded reads required by all workflows. Complete when its four child tasks meet their acceptance criteria. | T01–T04 |
| E02 | Connect project evidence and verify development decisions | Read real tracker/document/Git evidence, import explicit relationships, verify branch bases and evaluate inferred task-to-branch associations. | T05–T10 |
| E03 | Deliver cited answers and a reproducible demo | Explain engine facts, present evidence and decisions, document the demo procedure and retain measured acceptance results. | T11, T12, T17, T18 |
| E04 | Investigate incidents and restore a disposable sandbox | Resolve exact runtime scope, investigate with bounded checks, and demonstrate one approved restoration with measured recovery. | T13–T16 |

## Leaf task catalog

For each task, use the paragraph as its description and the bullets as acceptance criteria. Include the specification links as repository-relative paths in Plane if a reliable rendered repository URL is unavailable; do not fabricate published document URLs.

### T01 — Bootstrap the local API and FalkorDB runtime

Create the Python API, pinned dependencies, local Compose configuration, environment example and startup instructions. This task establishes startup, not graph-backed question answering.

- The documented PowerShell startup works; `/health` exposes liveness and `/ready` distinguishes an unavailable/uninitialized graph.
- Database storage survives restart using the tested image configuration; secrets are absent from responses and committed examples.
- Record tested versions and actual startup checks.

Specification: [Phase 0](../design/phase_00_foundation.md).

### T02 — Define shared query, evidence and incident contracts

Implement the canonical typed request/response records and validation, including source access, association audits, answer facts, graph availability, investigation checks and sandbox action states.

- Invalid IDs/enums and unscoped requests are rejected; clarification and uncertainty have typed outcomes.
- `UNAVAILABLE`, `MISSING` and `NOT_CHECKED` remain distinct; inferred associations cannot masquerade as delivery.
- Schema examples and focused contract validation agree with the canonical specification.

Specification: [Contracts](../design/contracts.md), [Phase 0](../design/phase_00_foundation.md).

### T03 — Publish graph snapshots with durable import recovery

Implement one writer, validated batch imports, the durable import fence and generation/readiness checks. Keep control records and retained content outside disposable graph projection storage.

- Interrupted mutation and restart block reads until a complete validated rebuild succeeds.
- Preparation failure preserves the prior snapshot at its original age; publication increments generation consistently.
- Direct and MCP-backed reads use the same gate; graph rebuild does not erase access records, association audits or action receipts.

Specification: [Phase 1](../design/phase_01_graph_and_fixtures.md).

### T04 — Add bounded graph queries and traversal evidence

Implement parameterized, scoped templates for task context, dependencies, documents, progress and runtime neighbors, with evidence and coverage metadata.

- Queries obey tenant/project/repository scope and configured row/depth limits; overflow is visible.
- A diamond dependency graph is not a cycle; real task cycles are reported; runtime cycles use visited tracking.
- Return stable evidence IDs and graph paths; no generated unrestricted Cypher or model writes.

Specification: [Schema](../design/graph_schema.md), [Phase 1](../design/phase_01_graph_and_fixtures.md), [Phase 3](../design/phase_03_traversal_and_branch_decisions.md).

### T05 — Read Plane tasks, assignees and activity history

Build the read-only Plane adapter for this project's actual tasks, metadata, parents, statuses, assignees and activity pages. Reconstruct usable assignment/in-progress intervals without invented start times.

- Preserve native IDs, all assignees, source timestamps and pagination coverage; unknown types/states stay explicit.
- Read back at least one seeded task through the live adapter and retain sanitized evidence.
- Incomplete activity history prevents unsupported temporal association; source access handling uses T08's shared registry when integrated.

Specification: [Source adapters](../design/source_adapters.md), [Association](../design/task_branch_association.md).

### T06 — Read versioned Google Docs content and anchors

Build the allowlisted read-only document adapter, preserving tabs, headings, lists and tables with immutable normalized content and versioned citations.

- A document changed during retrieval is retried once or rejected as incomplete; unsupported content is reported.
- A live document with multiple tabs and a table produces verifiable sections/citations.
- Source access handling uses T08's shared registry when integrated; unavailable live access never silently becomes fixture success.

Specification: [Source adapters](../design/source_adapters.md), [Phase 2](../design/phase_02_ingestion_and_sync.md).

### T07 — Collect Git and GitHub implementation evidence

Read allowed repository refs, full commit identities, PR state, individual reviews and bounded changed-file evidence. Support actual Git verification separately from provider metadata.

- Preserve author versus committer identity/time, exact heads and PR targets; `closed` is not automatically `merged`.
- Missing objects, incomplete history or failed fetches produce uncertainty, not absence.
- Retain real implementation and integration SHAs only when observed; never use placeholder hashes.

Specification: [Schema](../design/graph_schema.md), [Phase 2](../design/phase_02_ingestion_and_sync.md), [Phase 3](../design/phase_03_traversal_and_branch_decisions.md).

### T08 — Import verified relationships and retain source access state

Normalize adapter snapshots and the operator-reviewed manifest into graph batches. Implement the durable source access registry independently of successful imports and graph generations.

- Validate explicit task/repository/document/dependency mappings, endpoint scope and source-specific `LIVE`/`IMPORT`/`FIXTURE` modes.
- Denied content stays suppressed after failed import/restart, including traces and audits; transient transport failure is not automatically revocation.
- Later candidate projection preserves inference observation/expiry and never confirms delivery or triggers a query-owned rebuild.

Specification: [Phase 2](../design/phase_02_ingestion_and_sync.md), [Access contract](../design/contracts.md#source-access-registry).

### T09 — Verify prerequisite coverage and recommend a branch base

Implement the deterministic branch policy over the full confirmed prerequisite closure and exact Git heads, including delivery groups, squash mappings, candidate-specific reverts and final freshness checks.

- Prefer verified stable coverage; otherwise select an eligible covering feature or request clarification.
- Independent branches, unknown/partial mappings, cycles and stale evidence yield the appropriate outcome without unsupported commands.
- Review warnings remain separate from delivery; real generated Git histories cover merge, squash, revert and reapplication cases.

Specification: [Phase 3](../design/phase_03_traversal_and_branch_decisions.md).

### T10 — Discover likely implementation branches from work activity

Use mapped assignee identities, observed work periods and bounded commit/content evidence to evaluate likely branches when explicit task references are absent. Integrate Clef with deterministic validation and visible abstention.

- Concurrent similar work can remain ambiguous; missing identity/history or provider availability is disclosed.
- Suggestions carry exact observed heads, evidence, model metadata and expiry; they never establish code delivery.
- Return request-local suggestions, retain audits outside the graph and evaluate actual model results against a held-out set as specified.

Specification: [Association](../design/task_branch_association.md), [Phase 4](../design/phase_04_decision_model_integration.md).

### T11 — Generate cited answers from engine-owned facts

Build bounded context and typed facts, call an answer LLM, validate referenced facts and qualifications, and fall back to deterministic output when needed.

- Critical values/commands/statuses are engine-rendered; possible impact is never promoted to observed impact by prose.
- Keep runbook prerequisites and warnings with steps; source-access and graph/head freshness gates run after inference.
- Retain one real retrieval-to-LLM result; invalid citations, changed access or provider failure produce the specified safe fallback/error.

Specification: [Phase 5](../design/phase_05_context_and_llm_answers.md).

### T12 — Present scoped questions, decisions and evidence in the UI

Create the query UI with task/repository clarification, exact service-instance selection, cited answers, evidence paths, source modes and decision validity.

- Display branch coverage/review warnings and distinguish inferred associations from verified bases.
- Handle partial incident checks, unavailable sources, graph recovery and expired decisions; copying commands requires current eligibility.
- Render action state and recovery state separately when T16 is integrated; show unknown outcomes without offering a blind retry.

Specification: [Phase 6](../design/phase_06_ui_evaluation_and_demo.md).

### T13 — Retain incident events and resolve exact service scope

Accept and deduplicate permitted incident events durably, retain incident timelines, and resolve an exact environment/region/service instance before investigation.

- Two same-named regional services require exact authorized identity or picker selection; the model cannot guess.
- Unresolved accepted alerts remain pending; operator selections are recorded without overwriting contradictory source identity.
- Preserve event/provider status separately from investigation results and action outcomes.

Specification: [Incident contracts](../design/contracts.md#incident-and-exploration-extension), [SRE plan](../design/sre_integration_plan.md).

### T14 — Investigate incidents with a controller-owned checklist

Implement bounded exploration of current/historical deployment, owner/on-call, runtime dependencies, customer observations and runbook context. Models may order reads; the controller owns required checks and STOP eligibility.

- Premature STOP causes a required read while budget remains; budget exhaustion returns an explicitly partial brief.
- Timeout is `UNAVAILABLE`, authoritative absence is `MISSING`, and unattempted work is `NOT_CHECKED`.
- Distinguish authors/owners/current responders and observed/possible impact; incomplete action prerequisites block execution plans.

Specification: [SRE plan](../design/sre_integration_plan.md), [Phase 3](../design/phase_03_traversal_and_branch_decisions.md).

### T15 — Build the disposable payments sandbox and recovery probe

Create the local sandbox with immutable healthy/failing artifact versions, explicit instance identity, deployment/config/schema compatibility records and a measurable health probe.

- Every artifact/deployment identifier is real for this sandbox; synthetic customers, routes and alerts are labeled fixtures.
- A failing version and a compatible healthy target can be observed without affecting real services.
- Probe results include served artifact identity and the canonical 30-second, one-request-per-second recovery window; incomplete sampling is not recovery.

Specification: [Sandbox recipe](../design/sre_integration_plan.md#poc-sandbox-recipe).

### T16 — Execute one approved sandbox restoration durably

Implement only `RESTORE_SANDBOX_ARTIFACT`, with exact plan approval, durable execution claim, per-target serialization, retained receipts and outcome reconciliation.

- Validate exact target/current state, compatibility, access and expiry before the atomic claim; duplicates return existing operation state.
- Crashes before/after mutation and receipt failures leave explicit outcomes; unknown outcome retains the target reservation and is reconciled without blind retry.
- Report execution and measured recovery separately; matching artifact identity alone does not fabricate an execution receipt or close an incident.

Specification: [Action protocol](../design/contracts.md#poc-sandbox-execution-protocol), [SRE plan](../design/sre_integration_plan.md).

### T17 — Document the live-data demo and sandbox rehearsal procedure

Write the actual setup/rehearsal procedure, curate permitted source mappings and prepare the allowlisted demo Google Doc. Record the repository/Plane identity bindings and label synthetic runtime facts explicitly.

- Instructions cover prerequisites, source refresh, task/PR evidence, sandbox applicability, failure handling and reset ownership.
- The Google Doc is manually created or created through a separately authorized document workflow, and its real ID/version is recorded; missing access is reported.
- Keep expected answers and discovery ground truth out of the app's retrieval sources; document limitations without claiming passed checks.

Specification: [Phase 6](../design/phase_06_ui_evaluation_and_demo.md), [Source adapters](../design/source_adapters.md).

### T18 — Run acceptance checks and record the hackathon demonstration

Exercise the implemented workflows against real project evidence and isolated synthetic edge cases. Record actual outcomes, source modes, provider availability, timings and limitations.

- Live Plane and Google Docs smoke checks have actual receipts, or remain explicitly incomplete.
- Rehearse task context, branch coverage, ID-free discovery when eligible, incident investigation and approved sandbox recovery; absent features are reported as not implemented.
- Keep regression reports, demo procedure and evaluation counts reproducible; do not mark the task complete because tickets or fixtures were created.

Specification: [Phase 6](../design/phase_06_ui_evaluation_and_demo.md), [POC decisions](../design/README.md#poc-core-decisions).

## Explicit dependency manifest

Direction is **dependent task → prerequisite**. `CODE` means required implementation, not merely an earlier place in the schedule. `PROCESS` means a procedure/coordination prerequisite that remains visible but does not invent a Git delivery requirement. The table lists direct edges; the app traverses the full closure.

| Dependent | CODE prerequisites | PROCESS prerequisites |
| --- | --- | --- |
| T01 | None | None |
| T02 | None | None |
| T03 | T01, T02 | None |
| T04 | T03 | None |
| T05 | T01, T02 | None |
| T06 | T01, T02 | None |
| T07 | T01, T02 | None |
| T08 | T03, T05, T06, T07 | None |
| T09 | T04, T07, T08 | None |
| T10 | T04, T05, T07, T08 | None |
| T11 | T04, T08, T09, T14 | None |
| T12 | T09, T10, T11, T14, T16 | None |
| T13 | T02, T03 | None |
| T14 | T04, T08, T13 | None |
| T15 | T01, T02 | None |
| T16 | T14, T15 | None |
| T17 | None | None |
| T18 | T12, T16 | T17 |

An empty prerequisite list here is an explicit reviewed seed declaration, not absence inferred from a failed provider read. T05/T06 initially implement retrieval; T08 integrates shared access handling, avoiding a circular implementation dependency. T11 covers both task and incident answers; T12's full acceptance requires its incident/action integrations even if basic UI work starts earlier. Epics are grouping records, not code prerequisites. If implementation changes these boundaries, update the reviewed manifest with actor/time/reason.

## Files and receipts to produce

Create `demo/plane_seed_receipts.json`, `demo/project_relationships.json` and `demo/seed_report.md`. These are preparation artifacts; `project_relationships.json` is an operator manifest to adapt to the implemented import schema, not a claim that an importer already exists. Do not create application schema changes merely to seed Plane.

The receipts must record namespace, Plane instance/workspace/project identities, actual native epic/task IDs, actual display keys/URLs, seed markers, initial observed state/assignees, and creation/reuse/verification timestamps. Leave unknown fields `null` and describe the missing evidence. Use actual provider timestamps separately from local observation times. Store no secrets or raw private email lists; keep sensitive identity bindings in a local ignored configuration.

The relationship manifest must contain:

- A schema/version label, allowed project/repository scope, verified stable ref, and the native-ID mapping for every seed key.
- Explicit hierarchy and all dependencies above, with `kind`, `authority=CONFIRMED`, `link_method=MANIFEST`, and actual operator/creation provenance. These describe deliberately configured POC relationships; do not label them provider-discovered facts.
- Explicit repository bindings for all leaf tasks, and reviewed document links using actual available sources. Git Markdown and a Google Doc are distinct sources with distinct IDs/modes.
- Per-task declaration of dependency-list coverage. Record the table as complete only after every endpoint/edge is resolved and verified.
- Initially empty implementation/delivery/effect mappings. Add them only after work and review supply real evidence. A task marked done or a PR URL alone does not establish complete delivery.

The report must list created/reused/conflicting/failed items, actual links, unsupported fields, absent assignments, parent/type mapping limitations, and the next real work to start. Verify four logical epics and eighteen unique leaf tasks, eighteen parent memberships, no dangling references, no dependency cycles, and agreement between descriptions and the manifest. Rerunning must not create duplicates.

## Workflow when developers begin implementation

Use this section during a later implementation task. Do not execute it during initial seeding.

1. Choose the corresponding real Plane task. Assign the actual developer and move it to the actual in-progress state **before** their implementation commits. Read back activity history so the app can reconstruct the interval. Missing history remains missing; never rewrite commit dates or backdate tracker events to satisfy the demo.
2. Inspect dependency delivery and actual repository state before selecting a base. Use the verified stable ref when prerequisites are present; if intentionally stacking on a prerequisite feature, record that relationship and actual PR target. Never treat a tracker status as proof of Git coverage.
3. Normally name branches `codex/<actual-plane-key>-<short-slug>`, include the actual Plane key in meaningful commits and the PR title/body, and link the real task. Do not use a seed key as if it were a provider key. Follow any later repository instructions if they override naming.
4. Implement real changes and checks. Create a PR only when authorized as part of that work and there is a meaningful diff. State which acceptance criteria are met and which are pending. Do not create empty/fake PRs to populate the graph, manufacture reviews, or mark unrun tests passed.
5. Retain real repository ID, PR number/URL/base/head, exact implementation revision(s), observed reviews and timestamps. A draft/WIP PR may provide partial implementation evidence; it cannot be declared complete delivery until its mapped scope actually meets the criteria.
6. After a real merge, retain the actual integration revision and explicitly confirm its relationship to the implementation delivery group (especially for squash/rebase). Preserve source branches only according to the user's repository policy. Never merge/revert/delete branches merely to stage a demo without authorization.
7. Update the task state from actual progress. Provider events, task state, delivery verification and review readiness remain separate. Imported mappings carry actor/time/evidence; incomplete work stays partial.

Suggested PR body for normal, explicitly linked tasks:

```text
Plane task: <actual task URL and key>
Problem and resulting behavior: <concrete description>
Acceptance criteria completed: <actual items>
Validation: <commands/checks actually run and results>
Remaining work or limitations: <actual gaps, or none>
Depends on: <actual prerequisite task/PR links where relevant>
```

If one PR spans several tasks, map scope per task rather than declaring every task completely delivered by the entire PR. Separate PRs are preferable where the work is independently reviewable; the catalog is not a requirement to make eighteen PRs.

## Preserve one clean branch-discovery example

Reserve **T10** for an ID-free association demonstration if its actual implementation workflow permits it. This is an evidence experiment, not a change to normal task scope.

- Assign T10 and start its real in-progress interval before making relevant commits. Verify the assignee-to-author binding and activity coverage. Use meaningful branch/commit/PR descriptions of the work, but omit T10's seed key, actual Plane key/URL and explicit task-to-branch links from those Git/PR records. A neutral branch such as `codex/work-activity-matching` is a naming suggestion, not a pre-created ref.
- Do not add a confirmed T10 implementation mapping, development-panel link or task-backlink before the discovery demonstration. Existing explicit association makes discovery not applicable; it is not evidence of successful inference.
- Keep any evaluator's known-answer mapping outside the app's ingestion/model context. Exclude **this instruction file**, seed reports, evaluator notes and expected-answer tables from retrieval for this experiment; they reveal the intended association. Legitimate task descriptions and design specifications remain available.
- Run the demo while the task is genuinely in progress and relevant work lies inside the configured search window (currently 14 days). A completed/merged task may no longer be a suitable discovery example. Do not hold completed work in progress or falsify history; use another eligible real task or a clearly labeled fixture replay instead.
- A correct result is still an inferred candidate with evidence and uncertainty, never verified delivery. If time/identity/history/provider evidence is inadequate, show abstention. After evaluation, an operator can add an explicit mapping with provenance for ordinary use.

Keep T10 out of any staged **verified branch-base** story until its needed delivery is explicitly mapped; inferred associations cannot supply prerequisite coverage.

## Demo checkpoints using the project's real work

These are conditional rehearsal opportunities, not instructions to fabricate states. The full edge-case suite still uses isolated synthetic fixtures and temporary Git repositories.

| Checkpoint | Example question | Evidence needed / expected behavior |
| --- | --- | --- |
| Seeded backlog | What is left to build in the graph foundation? | Four real E01 leaf tasks; report their actual states, not a preselected progress ratio |
| Explicit implementation | What work and design documents relate to this task? | Real task, curated design links, actual PR/commits; show only observed reviews |
| Open prerequisite implementation | Which base should I use for the bounded graph query task (T04)? | Complete T01/T02 deliveries on stable; complete mapped T03 implementation on an available unmerged branch; T04 dependency scope complete; live verification decides eligibility |
| Prerequisite integrated | Ask the same T04 branch question again | Actual confirmed integration/coverage on stable; stable preferred only if all checks pass |
| Discovery | Which branch is likely implementing the work-activity task (T10)? | The real ID-free workflow above, without ground-truth leakage; a suggestion or honest abstention |
| Procedure | What must I do before the final demo acceptance task (T18)? | T17 procedure content plus its PROCESS relationship, alongside actual CODE prerequisites; reading instructions does not complete a task |
| Incident | Investigate this exact sandbox payments instance | T13–T16 actually implemented, explicit instance/deployment/ownership/runbook mappings and labeled synthetic runtime observations; repository work alone does not provide runtime facts |

For the open-prerequisite checkpoint, multiple covering candidates may require clarification, partial implementation cannot support a command, and a review warning requires a real review. If the live project has already moved past a checkpoint, label and use a captured fixture replay or skip it. Do not alter real project history to recreate it.

## Scope and completion boundaries

The initial result is a truthful, reusable backlog plus explicit mappings. It does not pass the app's live-adapter, inference, Git verification or action-execution gates. Payments/TLS fixture scenarios in the design remain regression inputs; these self-referential Company Brain tasks supplement them. In particular, do not mark four of five tasks done simply to reproduce a fixture's progress example.

Production automation, broad connectors and other [deferred design questions](../design/open_questions_and_probable_solutions.md) are outside this seed. Keep the eighteen-task catalog stable unless the user changes the POC scope. Synthetic incident data belongs to the disposable sandbox, and actual restoration still requires the exact approval protocol defined by the application.
