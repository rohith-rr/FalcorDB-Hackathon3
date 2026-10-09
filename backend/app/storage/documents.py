"""Immutable versioned document content storage.

Document bytes and section anchors live in local content storage
(`.local/state/content/`); graph nodes store references, versions and hashes.
Every selected excerpt carries its document version. Versioned content
referenced by previous evidence is never overwritten.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class DocumentStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _doc_dir(self, document_id: str, version: str) -> Path:
        # document identity is stable across versions; versions never overwrite.
        safe_id = document_id.replace(":", "_")
        return self.root / safe_id / version

    def register(
        self,
        document_id: str,
        version: str,
        title: str,
        document_type: str,  # DesignDoc | ProcessDoc
        doc_status: str,     # CURRENT | SUPERSEDED | DRAFT
        sections: List[Dict[str, Any]],
        source_url: Optional[str] = None,
        source_record_ref: str = "",
        observed_at: str = "",
    ) -> Dict[str, Any]:
        """Persist one immutable document rendition.

        Sections carry `anchor` (version-bound), `tab_id` (nullable for
        Markdown) and `text`. Returns the graph reference fields
        (content_hash + content_path).
        """
        if document_type not in ("DesignDoc", "ProcessDoc"):
            raise ValueError(f"unknown document type {document_type!r}")
        if doc_status not in ("CURRENT", "SUPERSEDED", "DRAFT"):
            raise ValueError(f"unknown document status {doc_status!r}")
        for section in sections:
            if not section.get("anchor"):
                raise ValueError("document sections require version-bound anchors")
        doc_dir = self._doc_dir(document_id, version)
        doc_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "document_id": document_id,
            "version": version,
            "title": title,
            "document_type": document_type,
            "doc_status": doc_status,
            "source_url": source_url,
            "source_record_ref": source_record_ref,
            "observed_at": observed_at,
            "sections": sections,
        }
        serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False, indent=1)
        digest = content_hash(serialized)
        payload["content_hash"] = digest
        path = doc_dir / "content.json"
        path.write_text(serialized, encoding="utf-8")
        payload["content_path"] = str(path)
        return payload

    def load(self, document_id: str, version: str) -> Optional[Dict[str, Any]]:
        path = self._doc_dir(document_id, version) / "content.json"
        if not path.is_file():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def section(
        self, document_id: str, version: str, anchor: str, tab_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        doc = self.load(document_id, version)
        if doc is None:
            return None
        for section in doc["sections"]:
            if section["anchor"] == anchor and section.get("tab_id") == tab_id:
                return section
        return None
