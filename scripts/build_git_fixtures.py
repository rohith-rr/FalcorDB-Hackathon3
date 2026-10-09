"""Minimal Git fixture builder (Phase 0, coding sequence step 6).

Creates a small real Git repository under `.local/state/git/` containing a
stable commit and an unmerged backend delivery, then resolves the symbolic
labels used in fixture JSON (e.g. `SYMBOLIC:backend_delivery_commit`) into
real full 40-char SHAs. Fixture manifests use symbolic labels; the builder
resolves them to real SHAs BEFORE validation or graph ingestion. Fake
valid-looking SHAs are never invented.

Deterministic: commits use fixed author/committer identity and dates so the
same build always produces the same SHAs.

Usage (through the project environment):
  backend\\.venv\\Scripts\\python.exe scripts\\build_git_fixtures.py
  backend\\.venv\\Scripts\\python.exe scripts\\build_git_fixtures.py --validate-only
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
GIT_ROOT = WORKSPACE_ROOT / ".local" / "state" / "git"
FIXTURES_ROOT = WORKSPACE_ROOT / "fixtures"
MANIFEST_PATH = WORKSPACE_ROOT / ".local" / "state" / "git" / "git_fixture_manifest.json"

# Deterministic clock for reproducible commit SHAs.
FIXED_DATE = "2026-10-09T12:00:00+00:00"


class GitFixtureError(RuntimeError):
    pass


def run_git(repo: Path, *args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if check and result.returncode != 0:
        raise GitFixtureError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def commit(
    repo: Path,
    message: str,
    *,
    parent: Optional[str] = None,
    index: Optional[Dict[str, str]] = None,
) -> str:
    """Create a real commit object deterministically.

    `index` maps paths to file contents; when omitted an empty commit is made
    only if a parent exists. Uses fixed identity/dates for reproducible SHAs.
    """
    env = {
        "GIT_AUTHOR_NAME": "Demo Fixture",
        "GIT_AUTHOR_EMAIL": "fixture@demo.invalid",
        "GIT_AUTHOR_DATE": FIXED_DATE,
        "GIT_COMMITTER_NAME": "Demo Fixture",
        "GIT_COMMITTER_EMAIL": "fixture@demo.invalid",
        "GIT_COMMITTER_DATE": FIXED_DATE,
        "HOME": str(repo.parent),  # avoid reading the user's global git config
    }
    if index is not None:
        for path, content in index.items():
            file_path = repo / path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
            run_git(repo, "add", path)
        result = subprocess.run(
            ["git", "-C", str(repo), "commit", "-m", message],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
            check=False,
        )
        if result.returncode != 0:
            raise GitFixtureError(f"commit failed: {result.stderr.strip()}")
    else:
        result = subprocess.run(
            ["git", "-C", str(repo), "commit", "--allow-empty", "-m", message],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
            check=False,
        )
        if result.returncode != 0:
            raise GitFixtureError(f"empty commit failed: {result.stderr.strip()}")
    sha = run_git(repo, "rev-parse", "HEAD")
    if not sha or len(sha) != 40:
        raise GitFixtureError(f"builder did not produce a full SHA: {sha!r}")
    return sha


def cat_file(repo: Path, sha: str) -> str:
    """Prove the object exists as a real commit object."""
    return run_git(repo, "cat-file", "-p", sha)


def object_type(repo: Path, sha: str) -> str:
    return run_git(repo, "cat-file", "-t", sha)


def build_payments_fixture() -> Dict[str, object]:
    """Build the payments-service fixture repository and manifest entries.

    History:
      main:    C0 (scaffold) <- C1 (unrelated stable work)
      feature/backend-service: C0 <- D1 (backend delivery, unmerged)

    The backend delivery is unmerged: stable does not contain it.
    """
    repo = GIT_ROOT / "payments-service"
    if repo.exists():

        def _clear_ro(func, path, _exc):
            import os
            import stat

            os.chmod(path, stat.S_IWRITE)
            func(path)

        import shutil

        shutil.rmtree(repo, onerror=_clear_ro)  # deterministic rebuild consumes prior state
    repo.mkdir(parents=True, exist_ok=True)
    run_git(repo, "init", "-b", "main")
    run_git(repo, "config", "user.name", "Demo Fixture")
    run_git(repo, "config", "user.email", "fixture@demo.invalid")

    c0 = commit(repo, "Initial payments service scaffold", index={
        "README.md": "payments-service synthetic fixture repo\n",
        "service/__init__.py": "",
    })
    c1 = commit(repo, "Add stable-only utility module", index={
        "service/util.py": "def stable_helper() -> str:\n    return 'stable'\n",
    })
    run_git(repo, "checkout", "-b", "feature/backend-service", "HEAD~1")
    d1 = commit(repo, "PAY-101 implement backend service core", index={
        "service/core.py": "def settle(intent_id: str) -> str:\n    return f'settled {intent_id}'\n",
    })
    d2 = commit(repo, "PAY-101 settlement module follow-up", index={
        "service/settlement.py": "def batch_settle(ids):\n    return [settle(i) for i in ids]\n",
    })
    run_git(repo, "checkout", "main")

    manifest: Dict[str, object] = {
        "tenant_id": "demo",
        "label": "SYNTHETIC FIXTURE - real commit objects built by scripts/build_git_fixtures.py",
        "generated_with": "git fixture builder (deterministic dates)",
        "repositories": {
            "demo:github:payments:repository:901": {
                "path": str(repo),
                "stable_ref": "refs/heads/main",
                "branches": {
                    "refs/heads/main": c1,
                    "refs/heads/feature/backend-service": d2,
                },
            }
        },
        "commits": {
            "scaffold_commit": {"sha": c0, "parent": None, "repository_id": "demo:github:payments:repository:901"},
            "stable_only_commit": {"sha": c1, "parent": c0, "repository_id": "demo:github:payments:repository:901"},
            "main_head": {"sha": c1, "parent": c0, "repository_id": "demo:github:payments:repository:901"},
            "backend_delivery_commit": {"sha": d1, "parent": c0, "repository_id": "demo:github:payments:repository:901"},
            "backend_delivery_head": {"sha": d2, "parent": d1, "repository_id": "demo:github:payments:repository:901"},
        },
    }

    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(
        json.dumps(manifest, indent=1, sort_keys=True), encoding="utf-8"
    )
    return manifest


def resolve_symbol(value: str, manifest: Dict[str, object]) -> str:
    """Resolve a SYMBOLIC:<label> to a real full SHA from the builder manifest."""
    if not isinstance(value, str) or not value.startswith("SYMBOLIC:"):
        return value
    label = value.split(":", 1)[1]
    commits = manifest.get("commits", {})
    entry = commits.get(label)  # type: ignore[union-attr]
    if not entry:
        raise GitFixtureError(f"unknown symbolic revision label {label!r}")
    sha = entry["sha"]  # type: ignore[index]
    if not (isinstance(sha, str) and len(sha) == 40):
        raise GitFixtureError(f"builder produced non-SHA for {label!r}: {sha!r}")
    return sha


def collect_symbolic_references(fixtures_root: Path) -> List[str]:
    symbols: List[str] = []
    for path in fixtures_root.rglob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))

        def walk(node: object) -> None:
            if isinstance(node, dict):
                for v in node.values():
                    walk(v)
            elif isinstance(node, list):
                for v in node:
                    walk(v)
            elif isinstance(node, str) and node.startswith("SYMBOLIC:"):
                symbols.append(node)

        walk(data)
    return sorted(set(symbols))


def validate_manifest(manifest: Dict[str, object]) -> None:
    repo_paths: Dict[str, str] = {
        rid: entry["path"]
        for rid, entry in manifest["repositories"].items()  # type: ignore[union-attr]
    }
    for label, entry in manifest["commits"].items():  # type: ignore[union-attr]
        sha = entry["sha"]  # type: ignore[index]
        if not (isinstance(sha, str) and len(sha) == 40 and all(c in "0123456789abcdef" for c in sha)):
            raise GitFixtureError(f"{label!r}: {sha!r} is not a real full SHA")
        repo = Path(repo_paths[entry["repository_id"]])  # type: ignore[index]
        if object_type(repo, sha) != "commit":
            raise GitFixtureError(f"{label!r}: object {sha} is not a commit object")
        body = cat_file(repo, sha)
        if not body:
            raise GitFixtureError(f"{label!r}: empty commit object body")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build/validate the Git fixtures")
    parser.add_argument("--validate-only", action="store_true",
                        help="only validate the existing manifest against real objects")
    args = parser.parse_args()

    if args.validate_only and MANIFEST_PATH.is_file():
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    else:
        manifest = build_payments_fixture()

    symbols = collect_symbolic_references(FIXTURES_ROOT)
    unresolved = []
    for symbol in symbols:
        label = symbol.split(":", 1)[1]
        if label not in manifest.get("commits", {}):  # type: ignore[operator]
            unresolved.append(symbol)
    if unresolved:
        raise GitFixtureError(f"fixture references without builder entries: {unresolved}")

    validate_manifest(manifest)
    print(json.dumps({
        "status": "ok",
        "manifest": str(MANIFEST_PATH),
        "resolved_symbols": symbols,
        "commits": {k: v["sha"] for k, v in manifest["commits"].items()},  # type: ignore[union-attr]
    }, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
