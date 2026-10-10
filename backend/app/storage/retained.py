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

# Shared across instances; append() re-enters through load() and save().
_LOCK = threading.RLock()


class RetainedStore:
    """Append/transaction JSON store with durable flush; local POC store."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _collection_path(self, collection: str) -> Path:
        return self.root / f"{collection}.json"

    def load(self, collection: str) -> List[Dict[str, Any]]:
        path = self._collection_path(collection)
        # Windows read handles do not share deletion, so replacement must
        # wait until read_text() has closed the live collection's handle.
        with _LOCK:
            if not path.is_file():
                return []
            return json.loads(path.read_text(encoding="utf-8"))

    def save(self, collection: str, records: List[Dict[str, Any]]) -> None:
        """Replace one retained collection transactionally.

        A crash while rewriting an existing collection in place would destroy
        previously acknowledged records or leave invalid JSON behind (an
        fsync at the end cannot protect the preceding committed collection).
        Instead the new payload is durably flushed to a temporary file and
        then atomically replaces the live collection; readers always see
        either the previous acknowledged collection or the new complete one.
        """
        import uuid

        path = self._collection_path(collection)
        payload = json.dumps(records, sort_keys=True, indent=1, ensure_ascii=False)
        tmp = path.with_name(f"{path.name}.{uuid.uuid4().hex}.tmp")
        with _LOCK:
            try:
                with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
                    fh.write(payload)
                    fh.flush()
                    os.fsync(fh.fileno())
                # Atomic both on POSIX (rename) and Windows (MoveFileEx) — no
                # window where the collection is empty or truncated.
                os.replace(tmp, path)
            finally:
                if tmp.is_file():
                    try:
                        tmp.unlink()
                    except OSError:  # pragma: no cover - cleanup best effort
                        pass
            self._fsync_directory(path.parent)

    @staticmethod
    def _fsync_directory(directory: Path) -> None:
        """Best-effort directory-entry fsync so the replaced file name itself
        is durable. POSIX only; Windows does not permit opening directories."""
        try:
            fd = os.open(str(directory), os.O_RDONLY)
        except OSError:  # pragma: no cover - Windows / other
            return
        try:
            os.fsync(fd)
        except OSError:  # pragma: no cover - directory fsync unsupported
            pass
        finally:
            os.close(fd)

    def append(self, collection: str, record: Dict[str, Any], key_field: str = "id") -> Dict[str, Any]:
        # Serialize the complete read-modify-replace, including durable flush,
        # so concurrent appenders cannot overwrite each other's records.
        with _LOCK:
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
