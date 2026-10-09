"""FalkorDB client wrapper with separated read/write surfaces.

Reads (application domain queries) go through the database's read-only query
API (`ro_query`); writes are only reachable from ingestion/operator paths via
`query()`. Synchronous client calls must run outside the FastAPI event loop
(use `run_in_threadpool`).

Pinned stack: falkordb-py 1.7.1 against falkordb/falkordb:v4.20.7 (Redis
8.10.2). See reports/workspace_setup.md for the compatibility record.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Dict, List, Optional

from app.config import Settings

logger = logging.getLogger(__name__)


class GraphConnectionError(RuntimeError):
    pass


class GraphReadError(RuntimeError):
    pass


class GraphWriteError(RuntimeError):
    pass


class GraphClient:
    """Single application client. One writer/worker for the POC."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        if settings is not None:
            self._settings: Settings = settings
        else:
            self._settings = None  # type: ignore[assignment]
        self._client: Any = None
        self._graphs: Dict[str, Any] = {}
        self._lock = threading.Lock()

    # --- Lifecycle -----------------------------------------------------------
    @property
    def settings(self) -> Settings:
        if self._settings is None:
            from app.config import get_settings

            self._settings = get_settings()
        return self._settings

    def connect(self) -> "GraphClient":
        try:
            from falkordb import FalkorDB

            settings = self.settings
            kwargs: Dict[str, Any] = {
                "host": settings.falkordb_host,
                "port": settings.falkordb_port,
            }
            if settings.falkordb_password:
                kwargs["password"] = settings.falkordb_password
            if settings.falkordb_username:
                kwargs["username"] = settings.falkordb_username
            self._client = FalkorDB(**kwargs)
        except Exception as exc:  # connection refused / auth failure
            raise GraphConnectionError(f"cannot connect to FalkorDB: {exc}") from exc
        return self

    def ping(self) -> bool:
        if self._client is None:
            self.connect()
        try:
            self._client.connection.ping()
            return True
        except Exception as exc:
            raise GraphConnectionError(f"FalkorDB ping failed: {exc}") from exc

    def close(self) -> None:
        try:
            if self._client is not None:
                self._client.close()
        except Exception:  # pragma: no cover - close best effort
            pass
        self._client = None
        self._graphs = {}

    # --- Graph handle --------------------------------------------------------
    def select_graph(self, graph_name: Optional[str] = None) -> Any:
        """Resolve a graph handle. The name comes from server configuration,
        never from user/model input."""
        if self._client is None:
            self.connect()
        from app.config import get_settings

        name = graph_name or get_settings().falkordb_graph_name
        with self._lock:
            if name not in self._graphs:
                self._graphs[name] = self._client.select_graph(name)
        return self._graphs[name]

    # --- Reads (read-only query API) ------------------------------------------
    def ro_query(
        self,
        template: str,
        params: Optional[Dict[str, Any]] = None,
        timeout_ms: Optional[int] = None,
        graph_name: Optional[str] = None,
    ) -> List[List[Any]]:
        graph = self.select_graph(graph_name)
        try:
            result = graph.ro_query(
                template,
                params or {},
                timeout=timeout_ms,
            )
            return list(result.result_set)
        except Exception as exc:
            # A freshly created database has no graph key yet: reads are
            # semantically empty (ImportState is treated as UNINITIALIZED).
            if "empty key" in str(exc).lower():
                return []
            raise GraphReadError(f"read-only query failed: {exc}") from exc

    # --- Writes (ingestion/operator paths only) -------------------------------
    def query(
        self,
        template: str,
        params: Optional[Dict[str, Any]] = None,
        graph_name: Optional[str] = None,
    ) -> List[List[Any]]:
        """Write path. Never call from domain-read request flows; the loader
        and operator scripts own this surface."""
        graph = self.select_graph(graph_name)
        try:
            result = graph.query(template, params or {})
            return list(result.result_set)
        except Exception as exc:
            raise GraphWriteError(f"write query failed: {exc}") from exc

    # --- Introspection ---------------------------------------------------------
    def procedure_list_indexes(self, graph_name: Optional[str] = None) -> List[List[Any]]:
        try:
            graph = self.select_graph(graph_name)
            result = graph.procedure("db", "indexes")
            return list(result.result_set)
        except Exception as exc:
            raise GraphReadError(f"db.indexes failed: {exc}") from exc


def connect_default(settings: Optional[Settings] = None) -> GraphClient:
    return GraphClient(settings).connect()
