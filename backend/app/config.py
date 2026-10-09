"""Application configuration for the Company Brain prototype.

Configuration is loaded from the workspace root `.env` (see `.env.example`).
Provider secrets stay server-only and empty in the example; local startup and
readiness for local projections must not require them (workspace_setup.md).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

WORKSPACE_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Canonical startup configuration.

    Values map to docs/design/contracts.md and workspace_setup.md. Every
    external provider secret defaults to empty: fixture/import mode must not
    send credentials or attempt authentication.
    """

    model_config = SettingsConfigDict(
        env_file=str(WORKSPACE_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Application identity -------------------------------------------------
    app_name: str = "company-brain"
    tenant_id: str = "demo"
    principal_id: str = "demo-operator"

    # --- FalkorDB -------------------------------------------------------------
    falkordb_host: str = "127.0.0.1"
    falkordb_port: int = 6379
    falkordb_username: Optional[str] = None
    falkordb_password: Optional[str] = None
    falkordb_graph_name: str = "company_brain_demo"
    falkordb_query_timeout_ms: int = 1000

    # Projections that /ready requires READY. INCIDENT is added when incident
    # ingestion lands (SRE phases); before that it is reported separately as
    # UNINITIALIZED without blocking local startup.
    ready_required_projections: str = "STRUCTURAL"  # comma-separated

    # --- Workspace state paths (must resolve inside the workspace) ------------
    state_root: Path = WORKSPACE_ROOT / ".local" / "state"
    bundles_root: Path = WORKSPACE_ROOT / ".local" / "state" / "bundles"
    content_root: Path = WORKSPACE_ROOT / ".local" / "state" / "content"
    retained_root: Path = WORKSPACE_ROOT / ".local" / "state" / "retained"
    git_root: Path = WORKSPACE_ROOT / ".local" / "state" / "git"
    conversations_root: Path = WORKSPACE_ROOT / ".local" / "state" / "conversations"

    # --- Fixtures -------------------------------------------------------------
    fixtures_root: Path = WORKSPACE_ROOT / "fixtures"
    source_mode: str = "FIXTURE"  # FIXTURE | IMPORT | LIVE

    # --- Clarification / batching policy ---------------------------------------
    clarification_ttl_seconds: int = 120
    event_batch_window_seconds: int = 30  # allowed 15-30
    event_batch_min_read_interval_seconds: int = 15
    event_batch_max_events: int = 100
    event_batch_max_pending_events: int = 1000

    # --- External provider settings (all empty by default) --------------------
    plane_api_key: Optional[str] = None
    plane_base_url: str = "https://api.plane.so"
    google_docs_client_id: Optional[str] = None
    google_docs_client_secret: Optional[str] = None
    github_token: Optional[str] = None
    answer_llm_api_key: Optional[str] = None
    decision_model_api_key: Optional[str] = None


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.bundles_root.mkdir(parents=True, exist_ok=True)
    settings.content_root.mkdir(parents=True, exist_ok=True)
    settings.retained_root.mkdir(parents=True, exist_ok=True)
    settings.git_root.mkdir(parents=True, exist_ok=True)
    settings.conversations_root.mkdir(parents=True, exist_ok=True)
    return settings
