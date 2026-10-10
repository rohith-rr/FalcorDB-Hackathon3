# FalkorDB resources and hackathon plan

Research and proposed integration, 2026-10-09. No SDK, database, MCP server or model was installed or started for this review. This plan extends the [Company Brain](../../requirement_doc.md) and [SRE requirements](../../SRE%20event%20handling.md). Recommendations below are our design judgments, not a published judging rubric or a guarantee of winning.

Setup sequencing was revised by user request on 2026-10-10: apply [workspace setup](workspace_setup.md) to every new dependency/container/cache and complete Phase 2 implementation before external tokens, OAuth, logins or cloud provisioning. Earlier live-source requirements remain final demo gates, with live validation recorded separately after implementation.

## 1. Recommendation

Build the SRE incident workflow as the main demonstration of the Company Brain. Use FalkorDB to find the deployment active at the incident time, related changes, current responders, customer paths and applicable runbooks. Let Jev/Clef select useful next nodes from permitted choices, then give the collected evidence to one answer LLM.

Use the official Python client for ingestion and application queries; the official MCP server for constrained investigation reads; and Browser for inspecting actual returned paths. Add Canvas to the product only after the investigation works. Evaluate GraphRAG SDK for document retrieval as an optional extension, rather than replacing verified deployment records with document extraction.

The memorable result should be a recovery decision that changes when evidence changes: an earlier artifact can be proposed in one scenario, while a database compatibility change prevents that proposal in another. Show actual sandbox recovery in the first scenario and the supporting graph evidence in both.

## 2. Verified event guidance

The published pages list October 15-18, 2026, with submissions closing October 18 at 11:59 PM IST. The user reports direct organizer permission to start coding before the event; use that confirmation for this project and retain it with submission records. [Schedule](https://www.wemakedevs.org/hackathons/falkordb/schedule).

FalkorDB must be the primary graph database and essential to product behavior. Submission materials include public code, setup/data-model documentation, dependent queries or algorithms, a working video, deployment or complete local instructions, and named tracks. Disclose AI assistance and be able to explain and verify the work. The published timing rule differs from the organizer permission reported above. Recheck updated rules before submission. [Rules](https://www.wemakedevs.org/hackathons/falkordb/rules).

Prioritize Track 03, Company Brain, and enter Track 01 when the controlled action works. Track 01 highlights graph reasoning, queries/algorithms, MCP selection and evidence-based actions. Track 03 highlights linked company knowledge, ownership, sources and updates. Track 02 can be entered if incident history survives a restart and meaningfully improves a later investigation; a stored chat transcript alone would be a weak demonstration. The reviewed public pages do not supply numeric scoring weights. [Tracks](https://www.wemakedevs.org/hackathons/falkordb#tracks).

## 3. Resource choices

The organizer's [resource page](https://www.wemakedevs.org/hackathons/falkordb/resources) links setup, clients, GraphRAG SDK, Browser, algorithms, integrations, examples and support. Select components by the behavior they enable, not by how many sponsor tools can be listed.

| Resource | Specific use here | Priority and evidence |
| --- | --- | --- |
| [Python client](https://github.com/FalkorDB/falkordb-py) | Load normalized records; exact lookup; deployment and dependency queries; query diagnostics | Required. Record tested version and real query output. |
| [Docker/Compose](https://docs.falkordb.com/operations/docker) | Reproducible local database, persistence and Browser | Required local fallback, even if a hosted demo is used. |
| [FalkorDB Cloud](https://app.falkordb.cloud/) | Candidate hosted database for a live reviewer experience | Optional after Phase 2 implementation. Confirm available plan and connection details then; no free credits or capacity assumed. |
| [MCP server](https://github.com/FalkorDB/FalkorDB-MCPServer) | Execute selected, approved read queries through a standard tool connection | High value for Track 01. Show actual tool receipts and transport identity. |
| [Browser](https://docs.falkordb.com/browser/) | Inspect the same graph that produced the answer | Required developer/demo aid. Open a small relevant subgraph. |
| [Canvas](https://docs.falkordb.com/browser/canvas) | Embed the retrieved paths in the incident UI | Optional polish after core behavior. |
| [Algorithms](https://docs.falkordb.com/algorithms/) | Explore dependencies or explain a path where the algorithm's semantics fit | Optional; bounded Cypher queries already perform graph work. |
| [GraphRAG SDK](https://github.com/FalkorDB/GraphRAG-SDK) | Retrieve passages from runbooks and reviewed incident reports | Bounded evaluation; require identity/provenance compatibility first. |
| [Integration catalog](https://docs.falkordb.com/integration/) | Later larger imports or streaming connectors | Defer Kafka, bulk loading, extra ORMs and graph ML unless measured needs justify them. |

Use Python on the server, consistent with the existing design; the [official client catalog](https://docs.falkordb.com/getting-started/clients) also supports other languages. The browser application calls our API rather than connecting directly to the database.

## 4. Python client integration

Create the proposed `backend/app/graph/client.py` with separate `GraphReader` and ingestion writer interfaces. Resolve the graph name from server configuration, not user/model input. For the demo, use one authoritative graph such as `company_brain_demo`, with the existing tenant/source properties.

The current Python client's source exposes `query`, `ro_query`, parameter dictionaries, millisecond query timeouts, `explain`, `profile`, range indexes and constraint helpers. Use `ro_query` for investigations and `query` only through ingestion/operator paths. A read-only operation still needs access checks. Synchronous client calls must run outside the FastAPI event loop or through a separately verified asynchronous adapter. [Client implementation](https://raw.githubusercontent.com/FalkorDB/falkordb-py/master/falkordb/graph.py).

Illustrative integration shape, not executed or a complete authorization implementation:

```python
from falkordb import FalkorDB

db = FalkorDB(host=settings.host, port=settings.port,
              username=settings.username, password=settings.password)
graph = db.select_graph(settings.graph_name)
rows = graph.ro_query(
    approved_templates["incident_deployment"],
    params={"tenant": principal.tenant_id,
            "instance_id": authorized_instance_id,
            "at": incident_time},
    timeout=1000,
).result_set
```

Validate IDs, time window, source permissions and allowed template before the call. Convert rows into typed evidence with source references, snapshot, query ID and elapsed time. A timeout produces an incomplete result rather than an empty successful investigation.

Pin the client, server image, MCP package and optional SDK independently. Record a compatibility matrix with parameters, path decoding, procedure availability, constraints and read-only mutation rejection. An available method in current source is not proof that a chosen older server implements it.

## 5. Queries the product should depend on

Keep approved `.cypher` templates in the submission, paired with fixture inputs, expected IDs and returned evidence. The following are proposed query responsibilities; their exact syntax and performance need testing against the selected server.

| Template | Graph relationships and checks | Why an engineer needs it |
| --- | --- | --- |
| `incident_deployment` | `Deployment -> ServiceInstance`, `Deployment -> Artifact -> Commit`; deployment validity, environment, rollout fractions | Distinguish what was running from what happens to be on main now. |
| `change_context` | Commit/PR membership, individual reviews, `Task -> PullRequest`, incoming design documents; configuration/schema changes | Explain related work without declaring a cause. |
| `current_responder` | Assignment covering service and assigning employee; effective interval and override authority | Contact the actual current responder rather than the author. |
| `caller_exposure` | Incoming instance dependencies, scoped by environment/time; customer feature routing | Find possible effects through several caller paths. |
| `observed_customer_effects` | Customer-linked observations and measurement windows | Separate recorded failures from possible exposure. |
| `runbook_context` | Current applicable runbook, its version and relevant sections | Prepare recovery options from actual operating instructions. |
| `incident_history` | Prior events, plans, outcomes, reviewed reports and follow-up tasks | Reuse reviewed lessons while checking current conditions. |

Example for historical deployment retrieval. For this fixture, encode `at`, `valid_from` and `valid_to` as UTC epoch milliseconds; production adapters normalize their source timestamps. All displayed aliases below are projections of canonical properties.

```cypher
MATCH (i:ServiceInstance {id: $instance_id, tenant_id: $tenant})
MATCH (d:Deployment)-[r:DEPLOYED_TO]->(i)
MATCH (d)-[da:DEPLOYS_ARTIFACT]->(a:Artifact)
WHERE i.is_deleted = false AND d.is_deleted = false
  AND a.is_deleted = false
  AND d.tenant_id = $tenant AND a.tenant_id = $tenant
  AND r.tenant_id = $tenant AND da.tenant_id = $tenant
  AND r.is_deleted = false AND da.is_deleted = false
  AND r.authority = 'CONFIRMED' AND da.authority = 'CONFIRMED'
  AND r.valid_from <= $at
  AND (r.valid_to IS NULL OR $at < r.valid_to)
RETURN d.id AS deployment_id, a.id AS artifact_id,
       r.id AS deployment_edge_id, da.id AS artifact_edge_id,
       r.valid_from AS active_from, r.valid_to AS active_to,
       d.source_record_ref AS deployment_source,
       a.source_record_ref AS artifact_source
LIMIT 21
```

This template returns recorded active deployments, including more than one during a rollout. It does not prove artifact health or complete rollout coverage. The adapter separately retrieves served fractions, coverage, observation times and build revisions. If the response hits the 21-row sentinel for a 20-row budget, mark truncation instead of silently retaining only the first 20. Missing validity information is reported as a gap and investigated separately.

For customer exposure, begin with caller paths of zero to four dependency edges, including the failing instance itself. Validate every traversed node/edge's tenant, permission, active interval, deletion and confirmation state. Then join feature/customer mappings with their own validity and coverage. Mark results as possible until measurements support observed effects. Use a visited frontier and a shared row/time budget when fan-out exceeds the small demo cases; a result `LIMIT` alone is not a traversal-work budget.

Return node/edge identities for the evidence trace rather than only a prose summary. FalkorDB documents path functions including `nodes`, `relationships` and `length`, which can support those projections. [Path functions](https://docs.falkordb.com/cypher/functions).

## 6. Where native algorithms help

The [algorithm catalog](https://docs.falkordb.com/algorithms/) includes BFS, shortest paths, centrality and component analysis. For this project, the first two are the most practical experiments.

Use [BFS](https://docs.falkordb.com/algorithms/bfs) to explore a bounded runtime dependency network where direction and scope are verified. Its documented interface takes a starting node, maximum depth and relationship type; do not invent extra time/permission filters. Use [SPpaths](https://docs.falkordb.com/algorithms/sppath) for a representative explanation path where its direction, length and weight requirements are explicitly configured. One shortest path does not establish complete customer coverage.

Our choice: keep time-filtered Cypher/frontier retrieval as the initial impact implementation. If a native procedure cannot enforce the relevant edge validity and access scope, evaluate it on an operator-built, derived runtime projection containing only the authorized incident-time records. That projection is for calculation, not a second authority for deployments. Test equivalence with the canonical filtered queries before showing it.

PageRank or centrality could support later reviews of shared-service concentration; they do not identify a breaking commit or determine incident severity. Weakly connected components ignore direction and cannot substitute for caller impact. Do not add these merely to increase the feature list.

## 7. MCP with the decision model

The official server exposes `query_graph_readonly`, parameter support and schema inspection, alongside write/delete capabilities. It also documents `FALKORDB_DEFAULT_READONLY`. Use an application gateway that supplies approved query text and binds the allowed graph/parameters; permit only needed reads. Schema inspection is diagnostic sampling, not proof that every record satisfies our contracts. [MCP server](https://github.com/FalkorDB/FalkorDB-MCPServer).

The decision model chooses a permitted neighbor/evidence-operation ID. The controller maps that choice to a template, invokes MCP, validates the result and appends evidence. Do not ask Jev/Clef to invent Cypher or expose deployment execution as a graph tool. Record the actual MCP tool, request ID, server/package version, duration and result scope. Keep source ingestion and sandbox execution behind their own interfaces.

Preserve direct client access for ingestion and a labeled investigation fallback. In the demo, show when MCP was actually used. Compare the two transports with the same template/results so transport overhead is separate from model/navigation cost.

## 8. GraphRAG SDK: useful, with a compatibility gate

The SDK documents `retrieve()` for context-only retrieval and `completion(..., return_context=True)` for answer/context inspection. That allows a document retriever to feed our existing evidence bundle and answer LLM. [Getting started](https://docs.falkordb.com/graphrag/getting-started).

Its default retrieval combines semantic/text searches, entity discovery and graph expansion; optional text-to-Cypher adds another generative call. This is different from Jev/Clef choosing a next neighbor, and both approaches can be measured. Keep generated Cypher disabled in the initial document experiment. [Retrieval](https://docs.falkordb.com/graphrag/retrieval).

The documented storage uses document chunks, `MENTIONED_IN` provenance and generic `RELATES` edges; it is not automatically compatible with our typed operational edges. Deduplication/finalization can alter entity identities. Do not run the default pipeline against the authoritative operational graph without verifying those effects. [Storage](https://docs.falkordb.com/graphrag/storage).

Run a bounded compatibility experiment after the basic incident works:

1. Use three synthetic runbooks and two reviewed incident reports in an isolated scratch graph. Declare document versions and canonical service IDs explicitly.
2. Try context retrieval for a procedural question. Verify returned passages, document version, section/source reference and any extra LLM calls. Measure ingestion cost as well as retrieval cost.
3. Compare against current service-linked Markdown section retrieval. Adopt the SDK only if it improves passage coverage or implementation effort without losing provenance.
4. If adopted, either implement a compatible custom retrieval/ingestion strategy or keep the document index as a derived FalkorDB search projection. Both routes map results to canonical document/service IDs; only the authoritative graph determines deployment, on-call and action facts.

The SDK supports replaceable loading, extraction, resolution and retrieval strategies. A custom strategy is a real integration task, not a configuration claim. [Strategy reference](https://docs.falkordb.com/graphrag/strategies).

Until that gate passes, retain explicit Markdown links and section retrieval. Never treat a document mention as a verified runtime dependency, silently merge similarly named services, or replace the requested model-guided navigation with the SDK's default pipeline. Use synthetic documents during the hackathon; production retrieval must enforce access before source content reaches any model.

## 9. Browser, Canvas and persistence

Browser can execute queries and visualize returned graph records. Use it for topology inspection and a reviewer-facing view of the actual incident paths. [Browser](https://docs.falkordb.com/browser/).

For the product UI, evaluate `@falkordb/canvas`, the standalone Web Component used by Browser with a documented React/TypeScript example. Feed it authorized nodes/edges returned by our backend, using stable application IDs and an explicit display mapping. Highlight retrieved paths and let a node open its evidence/timestamp panel. Avoid exposing database credentials in the frontend. [Canvas](https://docs.falkordb.com/browser/canvas).

Start locally with a pinned Docker image, health checks, local-only access and persistent storage. Before any pull/build, verify Docker Desktop's host engine disk under `E:\FalcorDB Hackathon\.local\docker`; also keep runtime/package caches/temp and application state in the workspace. Verify the actual data directory in the selected image and prove persistence by restarting the container. The setup docs and MCP repository examples contain differing volume-path guidance; copying a sample volume mapping is insufficient. [Workspace policy](workspace_setup.md), [Docker guide](https://docs.falkordb.com/operations/docker), [MCP repository](https://github.com/FalkorDB/FalkorDB-MCPServer).

Apply [Phase 1 per-projection durability](phase_01_graph_and_fixtures.md#snapshot-consistency) and [graph publication](graph_publication.md) to direct/MCP/SDK reads and fallback. Record write durability and test interrupted owner-specific rebuilds across restart. Old markers cannot authorize dirty records. Declare template projections and complete read-set fingerprints; unrelated incident batches must not invalidate structural-only or equivalent answer inputs. Record fixed event cadence, delta time, backlog/freshness and blocked-read fraction with actual query receipts.

Index the properties used for exact lookup and add document text/vector indexes only if needed. Use execution plans and measurements on fixtures before making latency claims. Check supported Cypher syntax; do not assume Neo4j procedures or an unrestricted traversal protected by `LIMIT`. [Indexes](https://docs.falkordb.com/cypher/indexing), [limitations](https://docs.falkordb.com/cypher/known-limitations).

## 10. Focused demo and evidence

Proposed four-minute script, subject to the final submission's video limits:

| Time | Demonstration | What it establishes |
| --- | --- | --- |
| 0:00-0:25 | Replay payment errors in region A; ask who is responding and what may be affected | A concrete engineering problem. |
| 0:25-1:10 | Show model choices, MCP receipts and the retrieved deployment/PR/task/design and customer paths | FalkorDB materially supplies context for decisions. |
| 1:10-1:40 | Show cited brief, actual on-call override, observed Customer A failures and possible Customer B effects | Useful conclusions with honest limits. |
| 1:40-2:20 | Review a version-bound plan; approve restoration in the disposable service; show measured request recovery | A working action and observed outcome. |
| 2:20-2:55 | Replay with a conflicting schema change; show why restoration is withheld | Connected evidence changes behavior. |
| 2:55-3:25 | Restart the application; retrieve prior outcome and compare today's conditions | Persistent company knowledge has practical value. |
| 3:25-4:00 | Show evaluation results, setup path and optional Public API branch question | Measured behavior and a reusable Company Brain. |

Use recorded results, not prewritten answers. Add a controlled relation-change experiment: removing a dependency or changing an effective assignment changes exposure/contact results, while removing FalkorDB makes investigation unavailable. Do not implement a canned equivalent answer in the failure fallback. This demonstrates why the graph is required without pretending only graph databases could represent relationships.

Evaluate at least 20 incident cases with the three existing navigators: rules/direct graph, general-LLM selection and Jev/Clef selection. Keep cases, source snapshots, tools, required checks and final answer model consistent. Report grounded-brief correctness, missed evidence, wrong responders, invalid action proposals, p50/p95 time, calls/tokens and total cost per correct answer. Include all hidden SDK/provider calls if an SDK path is enabled. Compare a text-search baseline only if the team can hold source content and answer-model settings constant; make no universal vector-search failure claim.

User value is a responder finding useful next steps faster with fewer source lookups. A small supervised task comparison can measure that separately from inference savings. Mark fixtures and human timing sample sizes clearly.

## 11. Coding priorities and submission

Reuse the [existing phases](README.md), not a second full implementation schedule:

| Phase | Resource work | Completion evidence |
| --- | --- | --- |
| 0 | Verify workspace storage before downloads; pin Python client/server; persistent local runtime | Actual storage/compatibility/configuration record and restart proof; no external login. |
| 1 | Canonical graph, durable import/recovery, approved templates, ID indexes, Browser inspection | Repeatable seed, interrupted-import restart evidence and expected query results. |
| 2 | Complete Plane/Google Docs/GitHub adapters with mocked transports; local imports, event receipt and versioned facts | Offline adapter/local import, retry/deduplication and historical-state evidence; live checks recorded deferred. |
| After 2 implementation | Provider credential/OAuth onboarding and real read/refresh checks; optional hosted target when needed | Actual live adapter citations and compatibility results, recorded separately from implementation. |
| 3 | Bounded neighbor reads, incident-time impact queries, constrained MCP gateway | Real MCP read trace and multi-path coverage. |
| 4 | One accessible decision-model provider and fair navigator comparison | Measured selections, abstention and cost. |
| 5 | Evidence bundle and real answer LLM; optional SDK experiment | Valid source citations and reported omissions. |
| 6 | Recovery sandbox, focused UI/Canvas if feasible, demo and packaging | Actual restoration/blocked-plan variants and reproducible recording. |
| 7 | Additional live operational sources, production permissions/actions, larger pipelines | Separate operational release checks. |

If setup costs grow, cut GraphRAG SDK experimentation, native algorithm projections, Canvas polish and extra live connectors beyond the required Plane/Google Docs/GitHub scope in that order. Preserve durable recovery, real graph investigation, model-guided choices, evidence, one answer API call and approved sandbox action. Both [live adapter gates](source_adapters.md#acceptance-and-completion-record) remain required; export fallback is a partial deliverable. Optional Public API branching shares identities and can remain a short second example, not another complete product.

Prepare a root README, public repository, query/template inventory, seed/replay/reset instructions, environment example, tested versions, demo video, deployment/local path and named track claims. Explain participant contributions and AI assistance. Include evaluation results, labeled synthetic data, remaining limits and a small architecture diagram. Recheck submission requirements in the [official rules](https://www.wemakedevs.org/hackathons/falkordb/rules).

A blog post can explain the practical incident, schema choices, model comparison and one failed approach with measurements; the event lists a separate blog prize. Finish the working submission first. [Event overview](https://www.wemakedevs.org/hackathons/falkordb).

Use the linked Cypher/algorithm videos for the specific queries being built and the community examples for implementation patterns. Ask the resource page's Discord for compatibility questions when needed; this task has sent no messages or created external accounts. Before publishing, verify the actual project's behavior rather than presenting this plan as implemented work.
