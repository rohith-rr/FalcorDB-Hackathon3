"""Shared pytest configuration: paths, fixture loading, DB availability."""

from __future__ import annotations

import json
import socket
import sys
from pathlib import Path
from uuid import uuid4

WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = WORKSPACE_ROOT / "backend"

for candidate in (str(WORKSPACE_ROOT), str(BACKEND_ROOT)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

FIXTURES_ROOT = WORKSPACE_ROOT / "fixtures"


def load_fixture(*relative: str):
    return json.loads(FIXTURES_ROOT.joinpath(*relative).read_text(encoding="utf-8"))


def falkordb_available() -> bool:
    """Cheap reachability probe for the pinned local database."""
    try:
        with socket.create_connection(("127.0.0.1", 6379), timeout=1.5):
            return True
    except OSError:
        return False


# Re-exported for tests via fixtures below.
import pytest  # noqa: E402


@pytest.fixture(scope="session")
def workspace_root() -> Path:
    return WORKSPACE_ROOT


@pytest.fixture(scope="session")
def fixtures_root() -> Path:
    return FIXTURES_ROOT


@pytest.fixture(scope="session")
def git_manifest():
    from scripts.build_git_fixtures import build_payments_fixture

    return build_payments_fixture()


@pytest.fixture(scope="session")
def db_available() -> bool:
    return falkordb_available()


requires_db = pytest.mark.skipif(
    not falkordb_available(), reason="FalkorDB not reachable on 127.0.0.1:6379 (docker compose up)"
)


@pytest.fixture(scope="session", autouse=True)
def _isolated_graph_and_bundles(tmp_path_factory):
    """Give each test session its own graph and retained recovery bundles.

    Durable import controls reference bundles_root, so both settings must be
    isolated together to preserve application recovery state. Unique graph
    names prevent sessions from inheriting DIRTY projections whose bundles
    belong to another temporary directory.
    """
    from app.config import get_settings

    settings = get_settings()
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(
            settings, "falkordb_graph_name",
            f"{settings.falkordb_graph_name}_test_{uuid4().hex}",
        )
        patch.setattr(settings, "bundles_root", tmp_path_factory.mktemp("test-bundles"))
        yield settings
