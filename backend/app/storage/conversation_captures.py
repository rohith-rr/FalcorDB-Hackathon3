"""Retained conversation capture storage.

Sanitized immutable captures and import cursors live under
`.local/state/conversations/` and `.local/state/retained/` — outside graph
projection deletion. Graph nodes reference capture IDs/hashes only.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config import get_settings


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
        """Persist one immutable sanitized capture; returns its reference."""
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
        path.write_text(serialized, encoding="utf-8")
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
        cursors = self.load_cursors()
        key = f"{cursor['source_key']}:{cursor['source_epoch']}"
        cursors[key] = cursor
        self._cursors_path.write_text(
            json.dumps(cursors, sort_keys=True, indent=1), encoding="utf-8"
        )

    def load_cursors(self) -> Dict[str, Dict[str, Any]]:
        if not self._cursors_path.is_file():
            return {}
        return json.loads(self._cursors_path.read_text(encoding="utf-8"))

    def load_cursor(self, source_key: str, epoch: int) -> Optional[Dict[str, Any]]:
        return self.load_cursors().get(f"{source_key}:{epoch}")
