"""Operator projection recovery helper.

Usage: python scripts/recover_projection.py [STRUCTURAL|INCIDENT]

If the durable pending retained bundle is missing/invalid, falls back to the
documented operator path: rebuild the full validated bundle from fixtures and
recover_with_bundle() (retained-bundle hash preserved).
"""
import json
import sys
from pathlib import Path

_workspace = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_workspace / "backend"))
sys.path.insert(0, str(_workspace))

from app.config import get_settings
from app.graph.client import connect_default
from app.graph.import_state import (
    BundleStore,
    RecoveryRequired,
    PublicationGateProtocol,
    read_import_state,
)

projection = sys.argv[1] if len(sys.argv) > 1 else "STRUCTURAL"
client = connect_default(get_settings())
try:
    state = read_import_state(client, projection)
    print("before:", state)
    protocol = PublicationGateProtocol(client, BundleStore())
    try:
        report = protocol.recover(projection)
    except RecoveryRequired as exc:
        print(f"retained-bundle recovery unavailable ({exc}); rebuilding a full validated bundle")
        # A recovery bundle must capture exactly the projection being
        # recovered: fixture rebuilding is only available for STRUCTURAL.
        # For any other projection, provide a validated full bundle instead.
        if projection != "STRUCTURAL":
            print(f"no fixture-built bundle exists for {projection!r}; "
                  "operator must supply a validated full bundle for it")
            raise SystemExit(1)
        from scripts.seed_graph import merge_structural_bundles

        full = merge_structural_bundles()
        report = protocol.recover_with_bundle(projection, full)
    print("report:", json.dumps(report, default=str))
    print("after:", read_import_state(client, projection))
finally:
    client.close()
