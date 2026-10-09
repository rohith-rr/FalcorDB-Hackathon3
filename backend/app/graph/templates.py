"""Approved Cypher query templates.

Templates live in `backend/app/graph/templates/*.cypher`. Every domain read
executes through the read-only query API with a declared bound and sentinel
(limit = budget + 1); truncation is an explicit incompleteness, never silent
evidence slicing. Template version matches the schema version.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Dict

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"

#: template id -> (filename, row budget, projections required READY)
TEMPLATE_INDEX: Dict[str, dict] = {
    "exact_task_lookup": {"budget": 2, "projections": ["STRUCTURAL"]},
    "dependency_frontier": {"budget": 200, "projections": ["STRUCTURAL"]},
    "epic_children": {"budget": 200, "projections": ["STRUCTURAL"]},
    "task_delivery_groups": {"budget": 50, "projections": ["STRUCTURAL"]},
    "revision_effects": {"budget": 50, "projections": ["STRUCTURAL"]},
    "implementation_links": {"budget": 50, "projections": ["STRUCTURAL"]},
    "work_periods": {"budget": 50, "projections": ["STRUCTURAL"]},
    "association_candidates": {"budget": 50, "projections": ["STRUCTURAL"]},
    "current_documents": {"budget": 50, "projections": ["STRUCTURAL"]},
    "task_reviews": {"budget": 50, "projections": ["STRUCTURAL"]},
    "candidate_heads": {"budget": 50, "projections": ["STRUCTURAL"]},
    "import_state_read": {"budget": 2, "projections": []},
}


class TemplateRegistry:
    def __init__(self, directory: Path = TEMPLATES_DIR) -> None:
        self.directory = directory
        self._cache: Dict[str, str] = {}

    def get(self, template_id: str) -> str:
        if template_id not in TEMPLATE_INDEX:
            raise KeyError(f"unknown template {template_id!r}")
        if template_id not in self._cache:
            path = self.directory / f"{template_id}.cypher"
            self._cache[template_id] = path.read_text(encoding="utf-8")
        return self._cache[template_id]

    def budget(self, template_id: str) -> int:
        return TEMPLATE_INDEX[template_id]["budget"]

    def projections(self, template_id: str) -> list:
        return TEMPLATE_INDEX[template_id]["projections"]


@lru_cache
def default_registry() -> TemplateRegistry:
    return TemplateRegistry()
