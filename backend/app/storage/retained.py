"""Retained transactional storage outside graph rebuild deletion.

Holds source receipts, source-access registry records, association audit
records, action plans/receipts and durable event-log positions as JSON
transactions under `.local/state/retained/`.
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config import get_settings

_LOCK = threading.Lock()


class RetainedStore:
    """Append/transaction JSON store with durable flush; local POC store."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _collection_path(self, collection: str) -> Path:
        return self.root / f"{collection}.json"

    def load(self, collection: str) -> List[Dict[str, Any]]:
        path = self._collection_path(collection)
        if not path.is_file():
            return []
        return json.loads(path.read_text(encoding="utf-8"))

    def save(self, collection: str, records: List[Dict[str, Any]]) -> None:
        path = self._collection_path(collection)
        payload = json.dumps(records, sort_keys=True, indent=1, ensure_ascii=False)
        with _LOCK:
            with open(path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(payload)
                fh.flush()
                os.fsync(fh.fileno())

    def append(self, collection: str, record: Dict[str, Any], key_field: str = "id") -> Dict[str, Any]:
        records = self.load(collection)
        existing = next((r for r in records if r.get(key_field) == record.get(key_field)), None)
        if existing is not None:
            existing.update(record)
        else:
            records.append(record)
        self.save(collection, records)
        return record


def default_retained_store() -> RetainedStore:
    return RetainedStore(get_settings().retained_root)
