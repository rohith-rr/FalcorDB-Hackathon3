## System Architecture & Database Schema

This architecture addresses the "Company Brain" track mandate by unifying fractured organizational knowledge—including code branches, ticketing systems, and process documents—into a single queryable graph. By establishing explicit entity relationships, the system guarantees clear provenance for answers and enforces an absolute reduction of hallucinations.

The core schema maps high-level product initiatives down to individual Git commits and the specific operational documents required to unblock them.

| Node Type | Description & Source Examples | Linked Via (Edges) | Target Node |
| --- | --- | --- | --- |
| **`Epic`** | High-level initiatives (e.g., *Q3 Security Update*). | `HAS_TASK` | `Task` |
| **`Task`** | Individual units of work (e.g., *Update Backend Service*). | `IMPLEMENTED_IN`<br>

<br>`DEPENDS_ON` | `Branch`<br>

<br>`Task` |
| **`DesignDoc`** | Architectural RFCs or UI specs. | `SPECIFIES` | `Task` |
| **`ProcessDoc`** | Operational workflows (e.g., *How to obtain a VM TLS Certificate*). | `GOVERNS_PROCESS` | `Task` |
| **`Branch`** | Code repository branches (e.g., `feature/tls-update`). | `HAS_PR` | `PullRequest` |
| **`PullRequest`** | Code review state and merge status. | `TARGETS` | `Branch` (e.g., `main`) |

## System-1 Traversal Engine (Jev / Laya)

Traditional autonomous agents rely on generative (System-2) LLMs to interpret database state, which often results in severe latency and logical hallucinations. This architecture completely replaces generative traversal with a System-1 decision-making model (Laya / Jev).

Rather than generating text, Laya operates as a deterministic, high-speed router. It issues Cypher queries to FalkorDB, retrieves the structural context, and applies strictly typed state evaluations to decide the next graph hop.

* **Semantic Routing (`choice`):** When querying FalkorDB for documents linked to a task, the system passes the returned document titles to Laya. Laya evaluates the state against a fixed array of choices and outputs the exact node ID to traverse next (e.g., distinguishing between an infrastructure design document and an operational TLS runbook).
* **State Verification (`noul`):** When evaluating code readiness, Laya ingests a `PullRequest` node's metadata (e.g., `status: OPEN`, `reviews: CHANGES_REQUESTED`) and answers a boolean probability question (e.g., *"Is this branch safely merged into main?"*). If the `noul` probability is near 0.0, the agent autonomously routes the user to the unmerged source branch instead of the main branch.
* **Priority Ranking (`score`):** When multiple `Task` nodes are returned as blockers, Laya scores their operational urgency based on their connected `ProcessDoc` nodes, allowing the system to surface the most critical blocker first.

## Core Execution Workflows

**Workflow 1: Procedural Blocker Resolution (The TLS Certificate)**
When an engineer asks, *"How do I complete the TLS update for Task-404?"*, the system bypasses standard vector search and executes a structural workflow:

1. **Node Identification:** Laya (`choice`) identifies the specific `Task` node for "Task-404".
2. **Edge Traversal:** FalkorDB executes a Cypher query seeking any `ProcessDoc` connected via a `GOVERNS_PROCESS` edge.
3. **State Synthesis:** The graph returns the specific document: *Standard Operating Procedure: Obtaining VM TLS Certificates*.
4. **Delivery:** The engineer receives a holistic view detailing that Task-404 is unblocked, providing the exact Wiki link to the TLS process, and showing that the parent `Epic` is 80% complete based on sibling task states.

**Workflow 2: Dependent Branch Routing**
When an engineer asks, *"Which branch should I use to build the Public API for Epic-Payments?"*

1. **Dependency Mapping:** FalkorDB traverses `Epic -> Task (Public API) -> DEPENDS_ON -> Task (Backend Service) -> IMPLEMENTED_IN -> Branch`.
2. **Merge Evaluation:** Laya (`noul`) evaluates the `PullRequest` node connected to the backend branch.
3. **Actionable Output:** Recognizing the PR is not merged into `main`, the engine deterministically advises the engineer to check out the unmerged `feature/backend-service` branch, completely avoiding the "5-hop query problem" that causes vector databases to fail on relational queries.



## Hackathon Implementation & Strategy

To guarantee a stable, production-ready prototype during the 48-hour sprint, the engineering team must strategically avoid computational bottlenecks.

* **Bypassing the Extraction Bottleneck:** The team will avoid running expensive Named Entity Recognition (NER) models over raw PDFs. Instead, the system will leverage structured data from GitHub and Jira APIs (JSON/CSVs) to map the `Task`, `Branch`, and `PullRequest` nodes deterministically.


* **Demonstrating Visual Tangibility:** During the presentation, the pitch will heavily feature the FalkorDB Browser Web UI. By visually rendering the sprawling network of code, tasks, and design documents, and pointing to the exact path the System-1 model took to deduce a Git command, the project will empirically prove the explainability and traceable reasoning required to win the "Company Brain" track.
