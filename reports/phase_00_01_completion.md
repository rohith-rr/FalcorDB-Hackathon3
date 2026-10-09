# Phase 0 + Phase 1 completion record

Date: 2026-10-10. Machine: Windows 10/11, Docker Desktop 4.28 (WSL2 backend).

## Phase 0: foundation

| Gate | Result | Evidence |
| --- | --- | --- |
| Startup instructions work; workload-local Python runtime | PASS | uv 0.12.24 under `.local/tools/uv`; CPython 3.12.15 under `.local/tools/python`; env at `backend/.venv` via `uv sync` (`uv.lock` committed); all invoked through `scripts/Enter-ProjectEnvironment.ps1` |
| Storage preflight before downloads, rechecked after install/restart | PASS | `scripts/Test-ProjectStorage.ps1 -Report` exit 0; report at `reports/workspace_setup.md`; every env path resolves under the workspace (E:) |
| Contracts reject invalid enums, unscoped IDs, malformed fields | PASS | 35 unit tests; `tests/test_contracts.py` (rejected: enum values, `PAY-103`-style unscoped IDs, malformed evidence hashes, option-injection commands, command gating on non-RECOMMENDED) |
| Import states/errors, multi-assignee tasks, revision effects have explicit contracts | PASS | `app/contracts/import_state.py` (ImportState/ImportReport/EventBatchPolicy/EventBatchRecord/SourceAccessRecord), `app/contracts/decision.py::RevisionEffect` (REVERT has no resolves; REAPPLICATION requires them) |
| Scenarios/manifests: no duplicate IDs or dangling refs | PASS | `tests/test_fixtures.py`; scenario IDs unique; review-manifest supersession references resolve and are acyclic |
| Minimal Git fixture builder produces real commits and resolves symbolic labels | PASS | `scripts/build_git_fixtures.py`; deterministic SHAs (fixed identity/dates); `git cat-file -t` verifies every manifest SHA is a real commit object |
| `.env.example` with empty external secrets; startup works without credentials | PASS | fixture mode requires no provider tokens; `/ready` lists optional providers separately |
| Config/contracts preflight for conversations (Phase 0 extension) | PASS | `app/contracts/conversations.py` gates: EXACT mentions need target IDs, semantic candidates stay CANDIDATE, ACCEPTED/SUPERSEDED require review manifest + reviewer, SUPERSEDED requires replacement |
| SRE extension foundation contracts | PASS | `app/contracts/sre.py` (AlertInput/Receipt, IncidentState, InvestigationCheck with UNAVAILABLE distinct from MISSING/NOT_CHECKED, ImpactAssessment POSSIBLE vs OBSERVED) |

### Tested versions

uv 0.12.24, Python 3.12.15, falkordb-py 1.7.1, FastAPI 0.115.14, Pydantic 2.11.7, FalkorDB image `falkordb/falkordb:v4.20.7` (Redis server 8.10.2), Docker Desktop 4.28.0.139021, Compose v2.24.6.

### Storage observations / deviations

- All project dependencies, caches, temps, state and the database bind mount are E:-resident inside the workspace (see `reports/workspace_setup.md`).
- Docker Desktop's WSL2 engine disk was relocated by the user through Docker Desktop's supported GUI migration; it is now at `E:\Docker wsl\DockerDesktopWSL\data` — E:-resident but **outside the workspace folder** (the policy target `E:\FalcorDB Hackathon\.local\docker` was not chosen). Recorded as a deviation, not a gate failure (nothing project-related resides on C:; C: free space unchanged by project artifact installs).
- WSL swap was disabled (`swapMiB: 0`) under the policy's assessed-memory option (15.7 GB RAM). Docker `settings.json` backed up to `.local/config/docker-settings.backup.json`.
- Image persistence directory in the pinned image: `/var/lib/falkordb/data`, bind-mounted to workspace `.local/state/falkordb` (AOF directory created there; verified through container inspection).

## Phase 1: graph and fixtures

| Gate | Result | Evidence |
| --- | --- | --- |
| Schema/query compatibility verified against the pinned release | PASS | `tests/test_schema.py` + integration tests ran against `falkordb/falkordb:v4.20.7`; FalkorDB-specific findings recorded (no `HAVING` support; `SET r = $props` supported; empty-key reads treated as UNINITIALIZED) |
| Same fixture loaded twice leaves node/edge counts and active relationships unchanged | PASS | `test_reimport_is_idempotent` |
| Updating a head retires its old active edge | PASS | `test_updating_a_head_retires_its_old_active_edge` (exactly one active HEAD_AT after update) |
| Exact lookup, dependency, document and review queries return expected IDs/evidence | PASS | `test_exact_lookup_and_dependency_frontier`, `test_document_retrieval_retains_version` (runbook version 3 + hash), `test_review_retrieval_retains_reviewed_sha` (CHANGES_REQUESTED + reviewed SHA) |
| Tenant-filter tests return no foreign nodes | PASS | `test_tenant_filter_returns_no_foreign_nodes` |
| Read templates reject attempted mutations through the read-only interface | PASS | `test_read_only_interface_rejects_mutations` (`ro_query(CREATE ...)` → error) |
| Interrupted import across restart leaves dirty state; reads blocked | PASS | `test_restart_survives_dirty_state_and_recovers`: injected failure at `after_edges` → `docker compose restart falkordb` (AOF durability) → DIRTY survives restart → `GRAPH_RECOVERY_REQUIRED` on reads → gated full recovery restores exact records |
| Missing/invalid bundles | PASS | `test_failed_recovery_stays_blocked`; recovery requires the operator to supply a new validated full bundle (`recover_with_bundle`) |
| Durable write configuration | PASS | Compose passes `--appendonly yes --appendfsync always` (verified via `redis-cli CONFIG GET`); acknowledged writes are fsynced before reply |
| Graph survives container restart | PASS | `test_graph_survives_container_restart` (record counts identical across restart) |
| Retained bundles under workspace storage, outside projection deletion | PASS | `.local/state/bundles/<projection>/<bundle_id>.json` with sha256 hash; ImportState persisted in-graph as control records excluded from domain traversal |

## Deferred / next-phase notes

- INCIDENT projection remains UNINITIALIZED until the SRE incident phases; `/ready` reports it separately without failing local readiness (configurable via `READY_REQUIRED_PROJECTIONS`).
- Indices: current pin supports `CREATE INDEX FOR`; index creation is wired (`PublicationGateProtocol.create_indexes`) but not asserted in tests.
- Live Git verification, incident batching cadence and MCP adapters follow in Phases 2-4 per the implementation index.
- Final demo acceptance still requires the live Plane/Google Docs/GitHub gates after Phase 2 implementation (recorded separately from this record).
