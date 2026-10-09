"""Company Brain API (Phase 0 surface).

- `GET /health`: liveness, no secrets, always available.
- `GET /ready`: database connectivity plus per-projection readiness. Database
  failure or dirty/uninitialized required projections fails aggregate
  readiness; optional provider entries are listed separately and never block
  startup. No external credentials are required through Phase 2.
- `POST /query`: typed placeholder. Phase 0 does not implement question
  answering; requests resolve as `UNSUPPORTED` with no decision/answer.
- `GET /admin/import-state`: operator projection state inspection.

Synchronous FalkorDB calls run in the threadpool (never on the event loop).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from app.config import Settings, get_settings
from app.contracts.import_state import ImportStateCode, ProjectionID
from app.contracts.query import QueryRequest, QueryResponse, Resolution
from app.graph.client import GraphClient, GraphConnectionError
from app.graph.import_state import GraphRecoveryRequiredError, read_import_state

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("company-brain")

app = FastAPI(
    title="Company Brain API",
    version="0.1.0",
    description="Phase 0 foundation surface: liveness, readiness and typed contracts.",
)

_CLIENT: Optional[GraphClient] = None


def get_graph_client() -> GraphClient:
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = GraphClient().connect()
    return _CLIENT


@app.get("/health")
def health() -> Dict[str, Any]:
    """Liveness without secrets."""
    settings = get_settings()
    return {
        "status": "live",
        "app": settings.app_name,
        "time": datetime.now(timezone.utc).isoformat(),
        "source_mode": settings.source_mode,
    }


@app.get("/ready")
def ready() -> JSONResponse:
    """Aggregate readiness with per-projection detail.

    Required projections: STRUCTURAL and INCIDENT (configured). UNINITIALIZED
    is expected before the first seed; it fails aggregate readiness without
    being an application error.
    """
    settings = get_settings()
    required = [p.strip().upper() for p in settings.ready_required_projections.split(",") if p.strip()]
    projections: List[Dict[str, Any]] = []
    database_ok = True
    db_error: Optional[str] = None
    try:
        client = get_graph_client()
        client.ping()
    except GraphConnectionError as exc:
        database_ok = False
        db_error = str(exc)
        client = None

    if database_ok and client is not None:
        for projection in ("STRUCTURAL", "INCIDENT"):
            try:
                state = read_import_state(client, projection)
                is_required = projection in required
                projections.append({
                    "projection_id": projection,
                    "state": state["state"],
                    "generation": state["generation"],
                    "active_snapshot_id": state["active_snapshot_id"],
                    "required": is_required,
                    "ready": state["state"] == ImportStateCode.READY.value,
                })
            except Exception as exc:  # unreadable control state
                database_ok = False
                db_error = str(exc)
                projections.append({
                    "projection_id": projection,
                    "state": "UNREADABLE",
                    "required": projection in required,
                    "ready": False,
                    "error": "control state unreadable",
                })

    optional_providers = {
        "plane": bool(settings.plane_api_key),
        "google_docs": bool(settings.google_docs_client_id and settings.google_docs_client_secret),
        "github": bool(settings.github_token),
        "answer_llm": bool(settings.answer_llm_api_key),
        "decision_model": bool(settings.decision_model_api_key),
    }

    ready_value = database_ok and all(p.get("ready") for p in projections if p.get("required"))
    body = {
        "status": "ready" if ready_value else "not_ready",
        "database": {"connected": database_ok, "error": db_error},
        "projections": projections,
        "optional_providers": {
            name: {"configured": configured, "required": False, "blocks_startup": False}
            for name, configured in optional_providers.items()
        },
    }
    return JSONResponse(status_code=200 if ready_value else 503, content=body)


@app.post("/query")
def query(request: Request, payload: QueryRequest) -> QueryResponse:
    """Typed query placeholder. Phase 0 implements resolution contracts only.

    No graph-backed decision or answer is produced in Phase 0; a typed
    UNSUPPORTED response keeps the surface honest without crashing.
    """
    settings = get_settings()
    return QueryResponse(
        request_id=f"req-{datetime.now(timezone.utc).timestamp():.0f}",
        resolution=Resolution.UNSUPPORTED,
        limitations=[
            "Phase 0 does not implement question answering",
            "graph traversal and decisions arrive in Phase 3",
        ],
        timings={"phase": "0"},
    )


@app.get("/admin/import-state")
def import_state() -> Dict[str, Any]:
    """Operator projection-state inspection (no secrets)."""
    try:
        client = get_graph_client()
        client.ping()
    except GraphConnectionError as exc:
        raise HTTPException(status_code=503, detail=f"database unavailable: {exc}")
    states = {}
    for projection in ("STRUCTURAL", "INCIDENT"):
        states[projection] = read_import_state(client, projection)
    return {"tenant_id": get_settings().tenant_id, "projections": states}


@app.exception_handler(GraphRecoveryRequiredError)
async def recovery_required_handler(request: Request, exc: GraphRecoveryRequiredError):
    return JSONResponse(
        status_code=503,
        content={
            "request_id": "n/a",
            "code": "GRAPH_RECOVERY_REQUIRED",
            "message": str(exc),
        },
    )
