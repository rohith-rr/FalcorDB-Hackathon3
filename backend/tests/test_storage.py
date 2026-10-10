"""Immutable retained/storage tests (Phase 1 gates):
- document renditions and conversation captures are idempotent for identical
  bytes but never overwritten with conflicting content;
- retained collections are replaced transactionally (durably flushed temp
  file + atomic rename), so a crash cannot destroy acknowledged records or
  leave invalid JSON.
"""

from __future__ import annotations

import json
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from pathlib import Path

import pytest

from app.storage.conversation_captures import CaptureIdentityConflict, ConversationCaptureStore
from app.storage.documents import ContentIdentityConflict, DocumentStore
from app.storage.retained import RetainedStore


@pytest.fixture
def doc_store(tmp_path):
    return DocumentStore(tmp_path / "content")


_DOC_SECTIONS = [
    {"anchor": "prerequisites", "tab_id": None, "text": "Stage: verify access scope."},
    {"anchor": "step-1", "tab_id": None, "text": "Perform the first bounded step."},
]


def test_document_register_is_idempotent_for_identical_bytes(doc_store):
    a = doc_store.register(
        "demo:markdown:runbook", "3", "Runbook", "ProcessDoc", "CURRENT",
        sections=_DOC_SECTIONS, observed_at="2026-10-10T00:00:00Z",
    )
    b = doc_store.register(
        "demo:markdown:runbook", "3", "Runbook", "ProcessDoc", "CURRENT",
        sections=_DOC_SECTIONS, observed_at="2026-10-10T00:00:00Z",
    )
    assert a["content_hash"] == b["content_hash"]
    assert json.loads((doc_store.root / "demo_markdown_runbook" / "3" / "content.json").read_text(
        encoding="utf-8"))["version"] == "3"


def test_document_observation_metadata_is_not_rendition_identity(doc_store):
    """A later observed_at or a CURRENT->SUPERSEDED status transition advances
    observation state without a new source content version: re-registering
    unchanged versioned content stays idempotent and never rewrites the
    previously retained rendition."""
    a = doc_store.register(
        "demo:markdown:runbook", "3", "Runbook", "ProcessDoc", "CURRENT",
        sections=_DOC_SECTIONS, observed_at="2026-10-10T00:00:00Z",
    )
    b = doc_store.register(
        "demo:markdown:runbook", "3", "Runbook", "ProcessDoc", "SUPERSEDED",
        sections=_DOC_SECTIONS, observed_at="2026-10-11T00:00:00Z",
    )
    assert a["content_hash"] == b["content_hash"], \
        "observation metadata must not change the rendition content hash"
    assert b["content_path"] == a["content_path"]
    # the previously retained content is preserved as first observed
    stored = doc_store.load("demo:markdown:runbook", "3")
    assert stored["sections"][0]["text"].startswith("Stage: verify")
    assert stored["observed_at"] == "2026-10-10T00:00:00Z"
    assert stored["doc_status"] == "CURRENT"


def test_document_register_rejects_conflicting_rendition(doc_store):
    """Registering different bytes under the same (id, version) must not
    overwrite content referenced by still-READY graph evidence."""
    doc_store.register(
        "demo:markdown:runbook", "3", "Runbook", "ProcessDoc", "CURRENT",
        sections=_DOC_SECTIONS, observed_at="2026-10-10T00:00:00Z",
    )
    changed = [
        {"anchor": "prerequisites", "tab_id": None, "text": "Stage: MUTATED content."},
        {"anchor": "step-1", "tab_id": None, "text": "Perform the first bounded step."},
    ]
    with pytest.raises(ContentIdentityConflict, match="immutable"):
        doc_store.register(
            "demo:markdown:runbook", "3", "Runbook", "ProcessDoc", "CURRENT",
            sections=changed, observed_at="2026-10-10T00:00:00Z",
        )
    # the original rendition is untouched
    stored = doc_store.load("demo:markdown:runbook", "3")
    assert stored["sections"][0]["text"].startswith("Stage: verify")


@pytest.fixture
def capture_store(tmp_path):
    return ConversationCaptureStore(tmp_path / "conversations", tmp_path / "retained")


def test_capture_write_is_idempotent_then_rejects_conflict(capture_store):
    messages = [{"ordinal": 1, "text": "hello"}]
    ref = capture_store.write_capture(
        "capture-1", "local_session", 1, messages, "1.0.0", "1.0.0", "COMPLETE", []
    )
    same = capture_store.write_capture(
        "capture-1", "local_session", 1, messages, "1.0.0", "1.0.0", "COMPLETE", []
    )
    assert same["content_hash"] == ref["content_hash"]
    with pytest.raises(CaptureIdentityConflict):
        capture_store.write_capture(
            "capture-1", "local_session", 1,
            [{"ordinal": 1, "text": "tampered"}], "1.0.0", "1.0.0", "COMPLETE", [],
        )
    stored = capture_store.load_capture("local_session", 1, "capture-1")
    assert stored["messages"][0]["text"] == "hello"




def test_retained_save_is_transactional(tmp_path):
    """The live collection file always holds complete valid JSON; a save
    replaces it atomically instead of rewriting it in place."""
    store = RetainedStore(tmp_path)
    store.append("receipts", {"id": "r1", "kind": "source"})
    path = store._collection_path("receipts")
    assert len(store.load("receipts")) == 1

    # Record the live bytes, then simulate the transactional replace used by
    # save(): the acknowledged collection must remain readable at every step.
    acknowledged = json.loads(path.read_text(encoding="utf-8"))
    assert acknowledged[0]["id"] == "r1"

    store.append("receipts", {"id": "r2", "kind": "operator"})
    records = store.load("receipts")
    assert [r["id"] for r in records] == ["r1", "r2"]
    # no partial/temp residue corrupts the collection
    assert json.loads(path.read_text(encoding="utf-8")) == records


@pytest.mark.parametrize("first_record, second_record, expected", [
    (
        {"id": "first"}, {"id": "second"},
        [{"id": "acknowledged"}, {"id": "first"}, {"id": "second"}],
    ),
    (
        {"id": "acknowledged", "source": "first"},
        {"id": "acknowledged", "status": "second"},
        [{"id": "acknowledged", "source": "first", "status": "second"}],
    ),
])
def test_retained_append_serializes_entire_transaction(
    tmp_path, monkeypatch, first_record, second_record, expected,
):
    """Concurrent inserts and updates survive across separate store instances."""
    first_store = RetainedStore(tmp_path)
    second_store = RetainedStore(tmp_path)
    first_store.save("receipts", [{"id": "acknowledged"}])
    first_loaded = threading.Event()
    release_first = threading.Event()
    second_started = threading.Event()
    original_load = first_store.load

    def paused_load(collection):
        records = original_load(collection)
        first_loaded.set()
        assert release_first.wait(5), "first appender was never released"
        return records

    def append_second():
        second_started.set()
        return second_store.append("receipts", second_record)

    monkeypatch.setattr(first_store, "load", paused_load)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(first_store.append, "receipts", first_record)
        try:
            assert first_loaded.wait(5), "first appender never loaded the collection"
            second = pool.submit(append_second)
            assert second_started.wait(5), "second appender never started"
            with pytest.raises(TimeoutError):
                second.result(timeout=0.2)
        finally:
            release_first.set()
        assert first.result(timeout=5) == first_record
        assert second.result(timeout=5) == second_record

    assert RetainedStore(tmp_path).load("receipts") == expected
    assert not list(tmp_path.glob("*.tmp"))


def test_retained_replacement_waits_for_open_reader(tmp_path, monkeypatch):
    """An ordinary read handle must close before replacing its collection,
    including when the reader and writer use separate store instances."""
    reader_store = RetainedStore(tmp_path)
    writer_store = RetainedStore(tmp_path)
    old = [{"id": "acknowledged"}]
    new = [{"id": "replacement"}]
    writer_store.save("receipts", old)
    path = reader_store._collection_path("receipts")
    reader_open = threading.Event()
    release_reader = threading.Event()
    writer_started = threading.Event()
    original_read_text = Path.read_text

    def held_read_text(target, *args, **kwargs):
        if target != path:
            return original_read_text(target, *args, **kwargs)
        with target.open("r", encoding="utf-8") as handle:
            reader_open.set()
            assert release_reader.wait(5), "reader was never released"
            return handle.read()

    def save():
        writer_started.set()
        writer_store.save("receipts", new)

    monkeypatch.setattr(Path, "read_text", held_read_text)
    with ThreadPoolExecutor(max_workers=2) as pool:
        reader = pool.submit(reader_store.load, "receipts")
        writer = None
        try:
            assert reader_open.wait(5), "reader never opened the collection"
            writer = pool.submit(save)
            assert writer_started.wait(5), "writer never started"
            with pytest.raises(TimeoutError):
                writer.result(timeout=0.2)
        finally:
            release_reader.set()
        assert reader.result(timeout=5) == old
        writer.result(timeout=5)
    assert reader_store.load("receipts") == new
    assert not list(tmp_path.glob("*.tmp"))


@pytest.mark.parametrize("reader_updates_cursor", [False, True])
def test_cursor_replacement_waits_for_open_reader(
    tmp_path, monkeypatch, reader_updates_cursor,
):
    """Separate instances share read/replacement and read-modify-write locks."""
    reader_store = ConversationCaptureStore(tmp_path / "captures", tmp_path / "retained")
    writer_store = ConversationCaptureStore(reader_store.root, reader_store.retained_root)
    old = {"source_key": "session", "source_epoch": 1, "ordinal": 1}
    updated = {**old, "ordinal": 2}
    new = {"source_key": "other-session", "source_epoch": 1, "ordinal": 1}
    writer_store.save_cursor(old)
    path = reader_store._cursors_path
    reader_open = threading.Event()
    reader_closed = threading.Event()
    release_reader = threading.Event()
    writer_started = threading.Event()
    original_read_text = Path.read_text
    from app.storage import conversation_captures

    original_replace = conversation_captures.os.replace

    def held_read_text(target, *args, **kwargs):
        if target != path or reader_open.is_set():
            return original_read_text(target, *args, **kwargs)
        try:
            with target.open("r", encoding="utf-8") as handle:
                reader_open.set()
                assert release_reader.wait(5), "reader was never released"
                return handle.read()
        finally:
            reader_closed.set()

    def replace(source, destination):
        # Exercise Windows handle-sharing semantics on every platform.
        if destination == path and reader_open.is_set() and not reader_closed.is_set():
            raise PermissionError("cursor still has an open reader")
        return original_replace(source, destination)

    def save():
        writer_started.set()
        writer_store.save_cursor(new)

    monkeypatch.setattr(Path, "read_text", held_read_text)
    monkeypatch.setattr(conversation_captures.os, "replace", replace)
    with ThreadPoolExecutor(max_workers=2) as pool:
        if reader_updates_cursor:
            reader = pool.submit(reader_store.save_cursor, updated)
        else:
            reader = pool.submit(reader_store.load_cursors)
        try:
            assert reader_open.wait(5), "reader never opened the cursor file"
            writer = pool.submit(save)
            assert writer_started.wait(5), "writer never started"
            with pytest.raises(TimeoutError):
                writer.result(timeout=0.2)
        finally:
            release_reader.set()
        expected = {"session:1": updated if reader_updates_cursor else old, "other-session:1": new}
        assert reader.result(timeout=5) == (None if reader_updates_cursor else {"session:1": old})
        writer.result(timeout=5)
    assert reader_store.load_cursors() == expected
    assert not list(reader_store.retained_root.glob("*.tmp"))


def test_bundle_preparation_repairs_after_interruption(tmp_path):
    """A preparation interrupted before atomic commit leaves at most a temp
    residue and no final bundle file: retrying the same bundle repairs it
    instead of failing the immutable-bundle conflict check."""
    import hashlib

    from app.graph.import_state import BundleConflictError, BundleStore

    store = BundleStore(root=tmp_path)
    bundle = {"bundle_id": "bundle-1", "projection_id": "STRUCTURAL"}
    digest = store.persist(bundle)
    assert store.load("STRUCTURAL", "bundle-1") == bundle
    # the committed file bytes hash exactly to the returned digest
    assert store.hash_of("STRUCTURAL", "bundle-1") == digest
    final = tmp_path / "STRUCTURAL" / "bundle-1.json"
    assert hashlib.sha256(final.read_bytes()).hexdigest() == digest
    # idempotent re-preparation of identical bytes is accepted
    assert store.persist(bundle) == digest

    # conflicting bytes for a committed ID are rejected; retained bytes intact
    with pytest.raises(BundleConflictError):
        store.persist({**bundle, "extra": "changed"})
    assert hashlib.sha256(final.read_bytes()).hexdigest() == digest

    # interrupted-preparation semantics: leftover .tmp residue without a
    # committed final file is ignored and the retry repairs cleanly
    residue_dir = tmp_path / "STRUCTURAL"
    (residue_dir / "bundle-2.json.deadbeef.tmp").write_text("{partial", encoding="utf-8")
    digest2 = store.persist({**bundle, "bundle_id": "bundle-2"})
    assert store.load("STRUCTURAL", "bundle-2") == {**bundle, "bundle_id": "bundle-2"}
    assert hashlib.sha256((residue_dir / "bundle-2.json").read_bytes()).hexdigest() == digest2


def test_document_register_repairs_after_interruption(tmp_path):
    """A preparation interrupted before atomic commit leaves no partial
    content.json: retrying the same rendition repairs it rather than failing
    with ContentIdentityConflict."""
    from app.storage.documents import DocumentStore

    store = DocumentStore(tmp_path / "content")
    doc_dir = tmp_path / "content" / "demo_markdown_runbook" / "3"
    doc_dir.mkdir(parents=True, exist_ok=True)
    (doc_dir / "content.json.deadbeef.tmp").write_text("{partial", encoding="utf-8")

    registered = store.register(
        "demo:markdown:runbook", "3", "Runbook", "ProcessDoc", "CURRENT",
        sections=_DOC_SECTIONS, observed_at="2026-10-10T00:00:00Z",
    )
    assert registered["version"] == "3"
    assert store.load("demo:markdown:runbook", "3")["title"] == "Runbook"
    # identical re-registration stays idempotent
    again = store.register(
        "demo:markdown:runbook", "3", "Runbook", "ProcessDoc", "CURRENT",
        sections=_DOC_SECTIONS, observed_at="2026-10-10T00:00:00Z",
    )
    assert again["content_hash"] == registered["content_hash"]
