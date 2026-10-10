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


class ContentIdentityConflict(ValueError):
    """Conflicting bytes for an already-registered immutable identity.

    Versioned content referenced by previous evidence is never overwritten
    (docs/design/phase_01_graph_and_fixtures.md: immutable document bytes).
    """


#: Observation metadata travels with a rendition but never contributes to the
#: immutable rendition identity: a later observed_at or a CURRENT->SUPERSEDED
#: status transition advances observation state without requiring a new source
#: content version, so these fields stay outside the rendition comparison and
#: previously retained content is never rewritten to absorb them.
_OBSERVATION_FIELDS = ("doc_status", "observed_at")


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

        Registration happens during import preparation, so re-registering
        identical bytes is idempotent, but DIFFERENT bytes for an existing
        (document_id, version) identity are rejected: even an aborted import
        must not change content referenced by a still-READY graph or by
        historical evidence. Observation metadata (doc_status, observed_at) is
        NOT part of that identity: advancing it (a later observation, a
        CURRENT->SUPERSEDED transition) re-registers unchanged versioned
        content idempotently and never rewrites previously retained bytes.
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
        # The immutable rendition identity covers only versioned content;
        # observation metadata is excluded from both the comparison and the
        # content hash, so it can advance without a new source version.
        rendition = {
            key: value
            for key, value in payload.items()
            if key not in _OBSERVATION_FIELDS
        }
        serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False, indent=1)
        digest = content_hash(
            json.dumps(rendition, sort_keys=True, ensure_ascii=False, indent=1)
        )
        payload["content_hash"] = digest
        path = doc_dir / "content.json"
        if path.is_file():
            existing = json.loads(path.read_text(encoding="utf-8"))
            existing_rendition = {
                key: value
                for key, value in existing.items()
                if key not in _OBSERVATION_FIELDS and key != "content_hash"
            }
            if existing_rendition != rendition:
                raise ContentIdentityConflict(
                    f"document {document_id!r} version {version!r} is already registered "
                    "with different content; versioned renditions are immutable and are "
                    "not overwritten. Allocate a new version for the changed content."
                )
            # Previously retained content stays exactly as first registered;
            # the returned payload carries the current observation metadata.
            payload["content_path"] = str(path)
            return payload
        # Write + fsync a temporary file first, then atomically commit the
        # final pathname: an interrupted preparation leaves no partial content
        # file that a later immutable re-registration would misread as a
        # conflicting rendition.
        import os
        import uuid

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
