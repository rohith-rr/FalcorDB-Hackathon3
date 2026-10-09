# Company Brain (FalkorDB Hackathon)

A Company Brain prototype that connects epics, tasks, repositories, branches,
commits, PRs, reviews, documents and Codex conversations in FalkorDB and turns
engineer questions into typed, evidence-backed answers.

**Status:** Phase 0 (foundation, contracts, scenarios) and Phase 1 (graph
schema, durable import/recovery, query templates) are implemented. Question
answering/decisions arrive in Phase 3+ (see `docs/design/README.md`).

## Quick start (Windows PowerShell)

All commands run through the project environment, which keeps every
runtime, cache, temp dir and state path inside the workspace
(`docs/design/workspace_setup.md`).

```powershell
# 1. Enter the project environment (creates the workspace dirs, sets env vars)
.\scripts\Enter-ProjectEnvironment.ps1

# 2. Storage preflight (verifies paths and the Docker host disk before downloads)
.\scripts\Test-ProjectStorage.ps1

# 3. Start FalkorDB (pinned image, AOF + appendfsync always, 127.0.0.1 ports)
docker compose up -d

# 4. Sync the Python environment (managed Python + backend/.venv + uv.lock)
Set-Location backend
..\\.local\\tools\\uv\\uv.exe sync --extra dev

# 5. Build the Git fixtures (real commit objects; resolves SYMBOLIC labels)
..\\backend\\.venv\\Scripts\\python.exe ..\\scripts\\build_git_fixtures.py

# 6. Seed the graph through the durable publication protocol
..\\backend\\.venv\\Scripts\\python.exe ..\\scripts\\seed_graph.py

# 7. Run the API
..\\backend\\.venv\\Scripts\\python.exe -m uvicorn app.main:app --port 8000
```

- API: `GET /health`, `GET /ready` (per-projection), `POST /query` (typed
  Phase 0 placeholder), `GET /admin/import-state`.
- FalkorDB Browser (graph inspection): http://127.0.0.1:3000

## Tests

```powershell
Set-Location backend
..\\.venv\\Scripts\\python.exe -m pytest tests\\test_contracts.py tests\\test_fixtures.py tests\\test_git_fixture_builder.py tests\\test_read_sets.py tests\\test_schema.py -q
..\\.venv\\Scripts\\python.exe -m pytest tests\\integration -m integration -q   # requires FalkorDB up
```

Integration tests cover: idempotent reimport, stale-head retirement, tenant
scoping, read-only query API enforcing no writes, dirty-state read blocking
(`GRAPH_RECOVERY_REQUIRED`), recovery from retained bundles, missing/invalid
bundle handling, and graph/DIRTY-state survival across a container restart
(AOF `appendfsync always` durability).

## Layout

| Path | Purpose |
| --- | --- |
| `backend/app/contracts/` | Canonical Pydantic contracts (requests, evidence, decisions, conversations, SRE) |
| `backend/app/graph/` | FalkorDB client (separate ro_query/query), schema validation, durable import protocol, read sets, `.cypher` templates |
| `backend/app/storage/` | Versioned document content, conversation captures, retained records (.local/state, outside graph projection deletion) |
| `fixtures/` | Synthetic Payments/TLS/scenario/conversation fixtures (labeled, effect/revision links are symbolic) |
| `scripts/` | Environment entry, storage preflight, Git fixture builder, graph seed/recovery |
| `compose.yaml` | Pinned FalkorDB v4.20.7, local-only ports, workspace bind mount |
| `.env.example` | Startup configuration; external secrets stay empty until after Phase 2 |
| `reports/workspace_setup.md` | Generated storage preflight report |

## Workspace storage policy

All runtimes (`.local/tools/python`), the venv (`backend/.venv`), package
caches, temp files, Git fixture repos, retained records, recovery bundles,
document content and the database bind mount live inside
`E:\FalcorDB Hackathon`. Docker Desktop's engine disk must be E:-resident
(current location recorded in `reports/workspace_setup.md`; the policy target
is `E:\FalcorDB Hackathon\.local\docker`).

## Pinned versions (tested)

| Component | Version |
| --- | --- |
| Python | 3.12.15 (uv-managed, project-local) |
| uv | 0.12.24 |
| FalkorDB image | `falkordb/falkordb:v4.20.7` (Redis 8.10.2) |
| falkordb-py | 1.7.1 |
| FastAPI / Pydantic | 0.115.14 / 2.11.7 |

Fixtures are synthetic and clearly labeled. No external provider tokens,
OAuth or logins are required through Phase 2 implementation.
