# Workspace storage and deferred credentials

Status: implementation policy, requested by the user on 2026-10-10. Setup scripts and runtime checks below are Phase 0 deliverables; this document does not claim that storage has already been relocated or dependencies downloaded.

## Storage requirement

Keep all new project downloads, language runtimes, installed dependencies, caches, container images/layers, build cache, writable container data, application state and temporary build files within `E:\FalcorDB Hackathon`. Configure and verify storage before the first dependency installation, image pull or container build. An unknown location or a location on C: fails the setup gate; do not continue the affected download using its default location.

Existing Windows components and already installed host tools may remain on C:. Windows, Docker Desktop and WSL can also retain small settings, registry entries and OS-managed files there. The requirement controls project artifacts and large Docker/WSL disks; it does not promise zero operating-system writes to C:. Use project-local runtimes for new installations and record any unavoidable system component separately before installing it.

## Directory layout

Paths below are relative to the workspace root. Generated directories are ignored by Git; dependency manifests, locks, scripts and sanitized fixture expectations remain committed.

| Artifact | Required location |
| --- | --- |
| Downloaded installers, archives and optional wheel bundles | `.local/downloads/` |
| Project uv executable and managed Python runtimes | `.local/tools/uv/`, `.local/tools/python/` |
| Python environment and installed backend packages | `backend/.venv/` |
| Python package caches and uv tool environments/binaries | `.local/cache/pip/`, `.local/cache/uv/`, `.local/tools/uv-tools/`, `.local/tools/bin/` |
| Node runtime and any npm global tools, when their phase needs them | `.local/tools/node/`, `.local/tools/npm/` |
| Frontend dependencies and build output | `frontend/node_modules/`, `frontend/dist/` |
| npm cache, optional browser binaries and optional model cache | `.local/cache/npm/`, `.local/cache/playwright/`, `.local/cache/models/` |
| Docker Desktop engine disk containing images, layers, build cache and managed volumes | `.local/docker/` |
| WSL swap disk, if the WSL backend uses swap | `.local/docker/wsl-swap.vhdx` |
| FalkorDB host bind-mount data, if supported by the tested image/filesystem | `.local/state/falkordb/` |
| Retained transactional records, recovery bundles and immutable content | `.local/state/retained/`, `.local/state/bundles/`, `.local/state/content/` |
| Local Git fixture repositories/mirrors and sanitized conversation captures | `.local/state/git/`, `.local/state/conversations/` |
| Runtime logs, test scratch data and temporary downloads/build files | `.local/logs/`, `.local/tmp/` |
| Project tool configuration and later credentials | `.local/config/`, `.local/secrets/`, root `.env` |

Do not download optional models, GraphRAG components, browser automation binaries or frontend dependencies during Phases 0-2 unless their implemented checks actually need them. Any later download uses this same storage policy.

## Windows and Docker preparation

Docker stores images in its engine disk, independently of the Compose file's directory. Setting a bind mount, `DOCKER_CONFIG`, or running `docker pull` from E: does not relocate that disk. Docker documents the WSL backend's default data location on C: and its relocation through Settings > Resources > Advanced. Before pulling images, use the installed version's supported disk relocation to place the disk under `.local/docker/`, restart Docker and verify the actual host disk path. Record the backend/version and any existing shared workloads affected by the relocation. Use supported migration rather than manually moving an active VHD or unregistering a distribution. [Docker WSL storage](https://docs.docker.com/desktop/features/wsl/).

For a new Docker Desktop installation, retain the installer under `.local/downloads/` and use the supported installation/data-root options for the selected version. The documented options include `--installation-dir`, `--wsl-default-data-root` and `--hyper-v-default-data-root`; resolve their destinations under `.local/tools/docker-desktop/` and `.local/docker/`. An existing Desktop installation need not be reinstalled to relocate its engine data. [Windows installation options](https://docs.docker.com/desktop/setup/install/windows-install/).

If WSL swap is enabled, configure its `swapFile` under `.local/docker/` or explicitly disable swap after assessing available memory. `.wslconfig` is an OS-level file in the user's profile and affects all WSL distributions; preserve unrelated settings and record any required restart. Do not provision another Linux distribution for this project unless necessary; any required distribution disk must also be located under `.local/docker/`. [WSL settings](https://learn.microsoft.com/en-us/windows/wsl/wsl-config).

Prefer explicit workspace bind mounts for application state. Inspect the pinned FalkorDB image's actual data directory and test fsync/restart behavior. If the Windows bind mount fails the required durability or compatibility checks, use an explicitly named project volume inside the verified E:-resident Docker disk and record that mapping. Retained records, bundles and content must remain outside graph projection deletion in either layout. Container writable layers and volumes are acceptable only when their backing engine disk has passed the location check.

Use bounded container log rotation and record image/build/volume sizes. A Linux `DockerRootDir` such as `/var/lib/docker` is not evidence of the Windows host drive; retain the host VHD location as well as container mount inspection. Public images/packages should be downloaded without provider sign-in. If an anonymous-download limit prevents a required download, record the limitation and retain the credential deferral rather than initiating a login.

## Project environment and preflight

Implement `scripts/Enter-ProjectEnvironment.ps1` and `scripts/Test-ProjectStorage.ps1` in Phase 0. The environment script derives the workspace root from its own location, creates only workspace directories, and applies settings to the current process and its children. Do not change `HOME`, `USERPROFILE`, `APPDATA`, `LOCALAPPDATA` or `CODEX_HOME`, or modify machine/user-wide package settings. Launch all project install, seed, test and server commands through this environment.

| Setting | Project value |
| --- | --- |
| `TEMP`, `TMP`, `TMPDIR` | `.local/tmp/` |
| `PIP_CACHE_DIR` | `.local/cache/pip/` |
| `UV_CACHE_DIR` | `.local/cache/uv/` |
| `UV_PYTHON_INSTALL_DIR` | `.local/tools/python/` |
| `UV_PYTHON_BIN_DIR`, `UV_TOOL_BIN_DIR` | `.local/tools/bin/` |
| `UV_TOOL_DIR` | `.local/tools/uv-tools/` |
| `UV_PROJECT_ENVIRONMENT` | `backend/.venv/` |
| `PYTHONNOUSERSITE` | `1`; install into the project environment |
| `npm_config_cache`, `npm_config_prefix` | `.local/cache/npm/`, `.local/tools/npm/` |
| `npm_config_userconfig` | `.local/config/npmrc` |
| `DOCKER_CONFIG` | `.local/config/docker/`; this controls CLI configuration only |
| `PLAYWRIGHT_BROWSERS_PATH`, when used | `.local/cache/playwright/` |
| `HF_HOME`, when used | `.local/cache/models/` |

Use absolute resolved values in the scripts and verify against the pinned tools' effective configuration. Install uv from a pinned archive directly into its project directory rather than using a default user-profile installer. Prefer a managed project Python runtime and invoke the backend environment's executable explicitly. Invoke a project-local Node/npm when frontend work starts; do not use global package installations. Official references: [uv environment settings](https://docs.astral.sh/uv/reference/environment/), [pip caching](https://pip.pypa.io/en/stable/topics/caching/), [npm configuration](https://docs.npmjs.com/cli/v11/using-npm/config/).

The storage preflight must resolve destinations, including reparse-point targets, and verify that they stay under the workspace. Before bulk downloads, retain effective runtime/cache/temp paths, the Docker host disk location and available C:/E: space in a sanitized setup report. Inaccessible Docker settings or an unverified engine location leave the Docker storage gate pending; environment variables alone cannot pass it. After initial installation/pull and restart, repeat path checks and retain directory/image sizes and drive-space observations. Investigate unexplained material C: growth before further downloads; do not delete unrelated caches or existing Docker data.

## Credentials after Phase 2 implementation

Phases 0, 1 and 2 must be implementable and locally verifiable without external tokens, OAuth consent, account sign-in, cloud provisioning or live provider calls. Build complete Plane, Google Docs and GitHub adapter code, including authentication/refresh interfaces, pagination, retries and access-error behavior, using synthetic/sanitized saved responses and mocked HTTP transports. Use synthetic fixtures, local Git repositories, existing permitted exports and allowlisted local conversation imports for graph validation. Missing provider secrets must not block startup, readiness for local projections or the Phase 2 implementation gate. No interactive authentication or implicit token refresh occurs in fixture/import mode.

Leave provider secret values empty in `.env.example`; no dummy token should be sent to a provider. Test credential failures and OAuth refresh through mocks. Locally generated database/application secrets are allowed for the local runtime and require no external account. Keep required runtime authentication/access boundaries in the code. Any real-transcript check still requires explicit source selection and local file access, independently of provider credentials.

| Milestone | Required evidence |
| --- | --- |
| Phase 0 implementation | Verified workspace storage, pinned local runtime, contracts and synthetic scenarios; provider secrets unset |
| Phase 1 implementation | Actual local FalkorDB queries, seed/reimport, durable recovery and restart checks |
| Phase 2 implementation | Complete adapters with offline contract checks, repeatable local imports, provenance/access/recovery checks and a recorded deferred live checklist |
| After Phase 2 implementation: provider onboarding and live validation | Configure selected accounts, API tokens and Google OAuth; run real Plane/Google Docs/GitHub reads and retain source-backed smoke evidence |
| Full demo acceptance | Live-source checks plus the later branch/incident, model, answer and demo gates |

At the Phase 2 implementation gate, record implementation results separately from `LIVE_VALIDATION_DEFERRED` in the completion report; this report label is not a new source-mode or graph-state enum. Credential deferral is planned sequencing and does not block Phase 3 implementation. Keep data modes `FIXTURE`, `IMPORT` and `LIVE` accurate. Live compatibility remains unverified until actual calls pass, and full demo acceptance still requires those calls.

After Phase 2 implementation, follow a separate onboarding checklist: confirm allowed Plane workspace/project and API key; enable Google Docs/Drive APIs and configure OAuth consent/client/read scopes for allowlisted documents; configure GitHub repository read access; save secrets server-side; then run each adapter's real read/refresh/citation checks. Optional FalkorDB Cloud and model-provider account setup also wait until after Phase 2 implementation and are configured only when their later features need them. Use `.local/secrets/` or root `.env` for local secret material and avoid logging it.

## Completion record

Record tested versions, resolved storage paths, Docker disk/mount mapping, durability settings, restart output, disk-space observations, offline adapter results and deferred live checks. This policy revises setup and gate timing only; it does not remove live-source requirements from the final demonstration.
