"""Seed the FalkorDB graph from the synthetic fixtures (Phase 1).

Runs the durable per-projection publication protocol through the operator
path: retained full bundle -> DIRTY fence -> nodes/edges -> validation ->
READY publication with durable acknowledgment. Initial seeding follows the
same protocol; no active snapshot is readable until publication succeeds.

Usage (through the project environment):
  backend\\.venv\\Scripts\\python.exe scripts\\seed_graph.py
  backend\\.venv\\Scripts\\python.exe scripts\\seed_graph.py --reset
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.config import get_settings  # noqa: E402
from app.fixtures.build import (  # noqa: E402
    build_conversation_bundle,
    build_structural_bundle,
    load_git_manifest,
)
from app.graph.client import connect_default  # noqa: E402
from app.graph.import_state import (  # noqa: E402
    BundleConflictError,
    BundleStore,
    PublicationGateProtocol,
    read_import_state,
)
from app.graph.schema import validate_bundle  # noqa: E402


def merge_structural_bundles() -> dict:
    """Payments/TLS tasks/code/docs + conversation extension = one STRUCTURAL
    bundle (a second full-bundle publication would tombstone the first)."""
    main = build_structural_bundle()
    conv = build_conversation_bundle()
    # Versioned fixture snapshot: the corrected SUPERSEDES direction and CLI
    # message normalization change the retained bundle's bytes, and retained
    # bundles are immutable (a changed bundle must be allocated a new
    # bundle/snapshot ID, phase_01: BundleConflictError). The corrected
    # builder therefore claims the next unclaimed fixture version instead of
    # reusing an already-retained ID, so workspaces seeded before the
    # correction keep every predecessor's recovery bytes intact for a
    # still-DIRTY projection (seed_graph.py --reset clears only the graph,
    # never retained bundles; test runs are isolated to their own temporary
    # bundle directory, so only operator publications claim IDs here).
    snapshot_id = "snap-structural-004-cli-messages"
    for bundle in (main, conv):
        for record in bundle["nodes"] + bundle["edges"]:
            record["snapshot_id"] = snapshot_id
    merged = {
        "projection_id": "STRUCTURAL",
        "bundle_id": f"bundle-structural-{snapshot_id}",
        "snapshot_id": snapshot_id,
        "tenant_id": main["tenant_id"],
        "label": "SYNTHETIC FIXTURE structural bundle (payments+tls+conversations)",
        "source_scopes": main["source_scopes"] + conv["source_scopes"],
        "coverage": {**main["coverage"], **conv["coverage"]},
        "nodes": main["nodes"] + conv["nodes"],
        "edges": main["edges"] + conv["edges"],
    }
    validate_bundle(merged)
    return merged


def reset(client) -> None:
    """Operator reset: clears domain records and control state."""
    client.query("MATCH (n) DETACH DELETE n", {})
    print("reset: graph cleared")


def counts(client) -> dict:
    rows = client.ro_query(
        "MATCH (n) WHERE n.projection_owner IS NOT NULL "
        "RETURN labels(n)[0] AS label, count(*) AS cnt",
        {},
    )
    by_label = {str(row[0]): int(row[1]) for row in rows}
    edge_rows = client.ro_query(
        "MATCH ()-[r]->() RETURN type(r) AS t, count(*) AS cnt", {}
    )
    by_edge = {str(row[0]): int(row[1]) for row in edge_rows}
    return {"nodes": by_label, "edges": by_edge}


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed the Company Brain graph")
    parser.add_argument("--reset", action="store_true", help="clear the graph before seeding")
    parser.add_argument("--inspect", action="store_true", help="print graph topology counts only")
    args = parser.parse_args()

    settings = get_settings()
    manifest = load_git_manifest()
    print(f"git fixture manifest: commits="
          f"{ {k: v['sha'][:10] for k, v in manifest['commits'].items()} }")  # type: ignore[union-attr]

    client = connect_default(settings)
    try:
        if args.reset:
            reset(client)

        bundle = merge_structural_bundles()
        protocol = PublicationGateProtocol(client, BundleStore(settings.bundles_root))
        try:
            report = protocol.publish(bundle)
        except BundleConflictError as exc:
            print(f"bundle preparation conflict: {exc}")
            print("operator options:")
            print("  - allocate a new snapshot/bundle ID for the changed bundle, or")
            print(f"  - operator-clear stale retained bundles under {settings.bundles_root}")
            return 1
        print(json.dumps(report, indent=1, default=str))

        state = read_import_state(client, "STRUCTURAL")
        print(f"STRUCTURAL state: {state['state']} generation={state['generation']} "
              f"snapshot={state['active_snapshot_id']}")

        topology = counts(client)
        print(json.dumps(topology, indent=1))
        return 0
    finally:
        client.close()


if __name__ == "__main__":
    sys.exit(main())
