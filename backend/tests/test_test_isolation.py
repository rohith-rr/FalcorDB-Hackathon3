"""Test sessions keep graph control state and retained bundles together."""

from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from app.config import get_settings
from app.graph.client import GraphClient
from app.graph.import_state import BundleStore
from tests import conftest


@pytest.mark.parametrize("abort_session", [False, True])
def test_session_isolates_graph_and_bundles_and_restores_settings(
    tmp_path, tmp_path_factory, monkeypatch, abort_session,
):
    application_graph = "application_graph"
    application_bundles = tmp_path / "application-bundles"
    application_bundles.mkdir()
    retained_bundle = application_bundles / "retained.json"
    retained_bundle.write_text('{"bundle_id": "application-bundle"}', encoding="utf-8")
    original_bytes = retained_bundle.read_bytes()
    settings = get_settings()
    monkeypatch.setattr(settings, "falkordb_graph_name", application_graph)
    monkeypatch.setattr(settings, "bundles_root", application_bundles)
    isolated_session = contextmanager(conftest._isolated_graph_and_bundles.__wrapped__)
    session_graphs = set()
    session_bundle_roots = set()

    for _ in range(2):
        try:
            with isolated_session(tmp_path_factory) as isolated:
                assert isolated is settings
                assert isolated.falkordb_graph_name != application_graph
                assert isolated.falkordb_graph_name not in session_graphs
                session_graphs.add(isolated.falkordb_graph_name)
                assert isolated.bundles_root != application_bundles
                assert isolated.bundles_root not in session_bundle_roots
                session_bundle_roots.add(isolated.bundles_root)
                assert isolated.bundles_root.is_dir()

                # Exercise the defaults used by graph reads and publications.
                client = GraphClient()
                client._client = SimpleNamespace(select_graph=lambda name: name)
                assert client.select_graph() == isolated.falkordb_graph_name
                assert BundleStore().root == isolated.bundles_root
                if abort_session:
                    raise RuntimeError("interrupted test session")
        except RuntimeError as exc:
            assert abort_session
            assert str(exc) == "interrupted test session"

        assert settings.falkordb_graph_name == application_graph
        assert settings.bundles_root == application_bundles
        assert retained_bundle.read_bytes() == original_bytes
