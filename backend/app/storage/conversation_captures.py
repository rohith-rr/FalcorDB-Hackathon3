"""Retained conversation capture storage.

Sanitized immutable captures and import cursors live under
`.local/state/conversations/` and `.local/state/retained/` — outside graph
projection deletion. Graph nodes reference capture IDs/hashes only.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config import get_settings


# Shared across instances; save_cursor() re-enters it through load_cursors().
_CURSOR_LOCK = threading.RLock()


class CaptureIdentityConflict(ValueError):
    """Conflicting content for an already retained capture ID.

    Retained captures are immutable and are referenced by graph nodes and
    historical evidence; they are never overwritten with different bytes.
    """


class ConversationCaptureStore:
    def __init__(self, root: Path, retained_root: Path) -> None:
        self.root = root
        self.retained_root = retained_root
        self.root.mkdir(parents=True, exist_ok=True)
        self.retained_root.mkdir(parents=True, exist_ok=True)

    def _source_dir(self, source_key: str, epoch: int) -> Path:
        return self.root / source_key.replace(":", "_") / str(epoch)

    def write_capture(
        self,
        capture_id: str,
        source_key: str,
        epoch: int,
        messages: List[Dict[str, Any]],
        parser_version: str,
        redaction_version: str,
        coverage: str,
        limitations: List[str],
    ) -> Dict[str, Any]:
        """Persist one immutable sanitized capture; returns its reference.

        Like document renditions, re-writing identical bytes is an idempotent
        re-preparation; different bytes under the same capture ID are
        rejected so an aborted import cannot alter retained evidence.
        """
        source_dir = self._source_dir(source_key, epoch)
        source_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "capture_id": capture_id,
            "source_key": source_key,
            "source_epoch": epoch,
            "parser_version": parser_version,
            "redaction_version": redaction_version,
            "coverage": coverage,
            "limitations": limitations,
            "messages": messages,
        }
        serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        content_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        path = source_dir / f"{capture_id}.json"
        if path.is_file():
            existing = path.read_text(encoding="utf-8")
            if existing != serialized:
                raise CaptureIdentityConflict(
                    f"capture {capture_id!r} already exists with different content; "
                    "retained captures are immutable and are not overwritten."
                )
        else:
            # Write + fsync a temporary file first, then atomically commit the
            # final pathname: an interrupted preparation leaves no partial
            # capture file that a later immutable re-write would misread as a
            # conflicting capture.
            tmp = path.with_name(f"{path.name}.{uuid.uuid4().hex}.tmp")
            try:
                with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
                    fh.write(serialized)
                    fh.flush()
                    os.fsync(fh.fileno())
                os.replace(tmp, path)
            finally:
                if tmp.is_file():
                    try:
                        tmp.unlink()
                    except OSError:  # pragma: no cover - cleanup best effort
                        pass
        return {
            "capture_id": capture_id,
            "content_reference": str(path),
            "content_hash": content_hash,
            "parser_version": parser_version,
            "redaction_version": redaction_version,
            "coverage": coverage,
            "limitations": limitations,
        }

    def load_capture(self, source_key: str, epoch: int, capture_id: str) -> Optional[Dict[str, Any]]:
        path = self._source_dir(source_key, epoch) / f"{capture_id}.json"
        if not path.is_file():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    # --- retained cursors -----------------------------------------------------
    @property
    def _cursors_path(self) -> Path:
        return self.retained_root / "conversation_cursors.json"

    def save_cursor(self, cursor: Dict[str, Any]) -> None:
        # Serialize the entire read-modify-replace so concurrent stores also
        # preserve updates to other cursor keys.
        with _CURSOR_LOCK:
            cursors = self.load_cursors()
            key = f"{cursor['source_key']}:{cursor['source_epoch']}"
            cursors[key] = cursor
            # Transactional replace: a crash mid-write must not destroy the last
            # acknowledged cursor or leave invalid JSON behind.
            tmp = self._cursors_path.with_name(
                f"{self._cursors_path.name}.{uuid.uuid4().hex}.tmp"
            )
            try:
                with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
                    fh.write(json.dumps(cursors, sort_keys=True, indent=1))
                    fh.flush()
                    os.fsync(fh.fileno())
                os.replace(tmp, self._cursors_path)
            finally:
                if tmp.is_file():
                    try:
                        tmp.unlink()
                    except OSError:  # pragma: no cover - cleanup best effort
                        pass

    def load_cursors(self) -> Dict[str, Dict[str, Any]]:
        # Windows readers must close their handles before atomic replacement.
        with _CURSOR_LOCK:
            if not self._cursors_path.is_file():
                return {}
            return json.loads(self._cursors_path.read_text(encoding="utf-8"))

    def load_cursor(self, source_key: str, epoch: int) -> Optional[Dict[str, Any]]:
        return self.load_cursors().get(f"{source_key}:{epoch}")
