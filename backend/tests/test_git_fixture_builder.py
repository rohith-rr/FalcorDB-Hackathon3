"""Git fixture builder tests: real commit objects, resolved symbolic labels,
deterministic rebuild."""

from __future__ import annotations

import pytest

from scripts.build_git_fixtures import (
    GitFixtureError,
    build_payments_fixture,
    object_type,
    resolve_symbol,
)


def test_builder_produces_real_commit_objects():
    manifest = build_payments_fixture()
    repo_root = None
    for _rid, entry in manifest["repositories"].items():
        repo_root = entry["path"]
    assert repo_root is not None
    for label, info in manifest["commits"].items():
        sha = info["sha"]
        assert len(sha) == 40 and all(c in "0123456789abcdef" for c in sha)
        assert object_type(__import__("pathlib").Path(repo_root), sha) == "commit"


def test_builder_is_deterministic():
    first = build_payments_fixture()
    second = build_payments_fixture()
    for label in first["commits"]:
        assert first["commits"][label]["sha"] == second["commits"][label]["sha"], (
            "deterministic dates must produce identical SHAs"
        )


def test_symbolic_labels_resolve_to_real_shas():
    manifest = build_payments_fixture()
    sha = resolve_symbol("SYMBOLIC:backend_delivery_commit", manifest)
    assert len(sha) == 40
    with pytest.raises(GitFixtureError):
        resolve_symbol("SYMBOLIC:unknown_label", manifest)


def test_backend_delivery_is_unmerged():
    manifest = build_payments_fixture()
    delivery = manifest["commits"]["backend_delivery_commit"]["sha"]
    stable_only = manifest["commits"]["stable_only_commit"]["sha"]
    assert delivery != stable_only
    feature_head = manifest["repositories"]["demo:github:payments:repository:901"]["branches"][
        "refs/heads/feature/backend-service"
    ]
    stable_head = manifest["repositories"]["demo:github:payments:repository:901"]["branches"]["refs/heads/main"]
    assert feature_head != stable_head
