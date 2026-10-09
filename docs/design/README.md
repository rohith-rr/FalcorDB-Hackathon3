# Company Brain implementation map

Read the [master design](../../requirement_doc.md) first. This folder divides coding into independently reviewable phases. The repository currently contains design documents; paths listed as deliverables are proposed files to create during implementation.

## Shared specifications

- [Graph schema](graph_schema.md): identities, source properties, relationship direction and delivery evidence.
- [Application contracts](contracts.md): typed requests, branch decisions, evidence and API responses.
- [Source adapters](source_adapters.md): required live Plane/Google Docs reads, provider mappings, labeled export fallback and smoke gates.
- [Task-branch association](task_branch_association.md): assignment/in-progress windows, author/commit evidence and Clef inference when explicit task references are absent.
- [Decision model evaluation](decision_models.md): Jev/Clef/Laya evaluation, alternatives and selection policy.
- [POC core logic review](../reviews/poc_core_logic_review.md): assessment under the hackathon POC scope and the concrete decisions needed for the demo.
- [Open questions and probable solutions](open_questions_and_probable_solutions.md): deferred non-core gaps, proposed solutions and conditions for revisiting them.
- [SRE event handling](../../SRE%20event%20handling.md): incident-assistant requirements and grounded interpretation of the supplied PDF.
- [SRE graph extension](sre_graph_schema.md): runtime, deployment, ownership, on-call and customer evidence.
- [SRE integration plan](sre_integration_plan.md): model-guided exploration, shared-phase changes, MCP access and sandbox demonstration.
- [FalkorDB resources and hackathon plan](falkordb_resources_and_hackathon_plan.md): verified event guidance, client/MCP/GraphRAG SDK choices, focused demo and submission evidence.
- [Original draft](archive/original_requirement_doc.md): preserved source document; superseded by the master design.

## POC core decisions

The user approved these fixes for the hackathon POC on 2026-10-09. They are now design requirements in the owning specifications; application implementation and runtime checks remain future work. Curated manifests are sufficient POC inputs. Deferred production questions remain in [open questions and probable solutions](open_questions_and_probable_solutions.md).

| Review ID | Embedded decision | Authoritative specification / coding phase |
| --- | --- | --- |
| C-01 | Request-local suggestions, retained audit records, explicit later candidate projection | [Association lifecycle](task_branch_association.md#representation-and-use), [Phase 4](phase_04_decision_model_integration.md#clef-task-branch-discovery) |
| C-02 | Exact instance IDs / authorized picker; fresh scoped requests and pending unresolved alerts | [Scope contract](contracts.md#poc-incident-scope-selection), [SRE plan](sre_integration_plan.md#3-node-exploration-and-stop-conditions) |
| C-03 | Controller-owned required checks, guarded STOP and explicit unavailable/partial outcomes | [Investigation contracts](contracts.md#incident-and-exploration-extension), [SRE scheduler](sre_integration_plan.md#3-node-exploration-and-stop-conditions) |
| C-04 | Engine fact registry, constrained explanations and final validity checks | [Answer contracts](contracts.md#context-and-answer-response), [Phase 5](phase_05_context_and_llm_answers.md#fact-registry-and-final-publication) |
| C-05 | Durable access registry independent of graph import success | [Access contract](contracts.md#source-access-registry), [Source adapters](source_adapters.md#persistent-source-access-handling) |
| C-06 | One restore operation with durable approval/claim/receipt, reconciliation and measured recovery | [Action protocol](contracts.md#poc-sandbox-execution-protocol), [Sandbox recipe](sre_integration_plan.md#poc-sandbox-recipe) |
| C-07 | One writer, scenario-batch publication and shared direct/MCP read gates | [Phase 1](phase_01_graph_and_fixtures.md#snapshot-consistency) |

## Execution order

| Order | Design document | Depends on | Completion artifact |
| --- | --- | --- | --- |
| 0 | [Foundation](phase_00_foundation.md) | Shared specifications | Running API/database and deterministic scenarios |
| 1 | [Graph and fixtures](phase_01_graph_and_fixtures.md) | 0 | Durable interrupted-import recovery and scoped query results |
| 2 | [Ingestion and sync](phase_02_ingestion_and_sync.md) | 1 | Normalized snapshots, confirmed links and live Plane/Google Docs smoke evidence |
| 3 | [Traversal and branch decisions](phase_03_traversal_and_branch_decisions.md) | 2 | Correct typed recommendations and trace evidence |
| 4 | [Decision model integration](phase_04_decision_model_integration.md) | 3 | Measured routing choice or documented rules fallback |
| 5 | [Context and LLM answers](phase_05_context_and_llm_answers.md) | 3, 4 | A cited explanation from a real LLM API call |
| 6 | [UI, evaluation and demo](phase_06_ui_evaluation_and_demo.md) | 5 | Reproducible demo and scenario regression report |
| 7 | [Production and actions](phase_07_production_and_actions.md) | 6 | Operational release gates and controlled actions |

Use each completion gate before moving on. A failing semantic adapter can be disabled without preventing graph decisions or the answer LLM. Record provider unavailability as an unevaluated result, not a passing evaluation.

For the incident demo, follow the SRE integration plan's additions to these phases. Its original 36-hour estimate replaces the demo allocation rather than adding another 36-hour workload; both estimates are provisional under the revised recovery/live-adapter scope. The existing development scenarios remain part of the product requirements and regressions when implemented; completing all development and incident features in one sprint is not assumed. The shared live Plane/Google Docs gate applies to either demo path.

The recommended hackathon demonstration leads with incident investigation and approved sandbox recovery. The FalkorDB resource plan maps sponsor tools to that workflow and treats document SDK retrieval, native algorithm projections and Canvas as optional additions. Event dates and the user's reported organizer permission for early coding are recorded there; the 48-hour budget below remains an internal planning assumption.

## 48-hour sprint boundary

The original allocation was 36 engineering hours to Phases 0-6 and 12 for setup failures, integration and rehearsal. Treat every phase timebox as provisional and re-estimate after recovery/persistence and live-adapter compatibility checks. These are internal engineering estimates, not a delivery guarantee or calendar estimate for a single inexperienced developer.

If time runs short in the development-focused demo, cut extra connectors beyond Plane/Google Docs/GitHub, sophisticated visuals, optional checks ingestion and model fine-tuning. Preserve durable recovery, candidate-specific revision effects, the verified branch workflow, review warnings, TLS content, citations, traversal trace and a real retrieval-to-LLM explanation. Live Plane and Google Docs are required completion gates; export fallback is labeled as a partial deliverable. Keep fixtures clearly labeled. A rules-only demo does not establish the value of Jev, Clef or Laya. For the SRE-focused demo, use the alternative scope and cuts in the [SRE integration plan](sre_integration_plan.md).

## Questions settled by default

Python backend; React frontend; structured fixtures/exports first, then required live Plane/Google Docs/GitHub reads; Markdown and verified manifests remain supported; durable read blocking during import/recovery; candidate-specific revert/reapplication evidence; one process/demo tenant/repository; stable ref configured per repository; advisory production actions; model-guided incident exploration; approved action execution only in a disposable sandbox during the incident demo; no NER pipeline in the sprint. Revisit defaults only when implementation evidence requires it, and update the canonical contracts before changing consumers.

## Design revision gate

Before application implementation, review the import state machine, candidate-effect semantics and source-adapter contract together. Confirm phase scenarios/gates have no marker-only recovery, global delivery-reversion flag or optional-live Plane/Google Docs guidance. Keep the archived original draft unchanged. Documentation validation can verify links, examples and consistency; it cannot claim database recovery, Git scenarios or live providers have passed. Retain the [design revision record](design_revision_record.md) with this distinction.

## Definition of a phase completion

Commit its implementation, update its completion record, run its stated checks, and retain sample output. The record should identify actual versions, fixture/live mode, enabled providers, unresolved limits and the next phase. These documents define future checks; they do not claim that code or service checks have already passed.
