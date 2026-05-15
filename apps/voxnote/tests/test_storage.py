"""Tests for voxnote.storage — covers schema bootstrap, CRUD, FTS5 search."""
from __future__ import annotations

from pathlib import Path

import pytest

from voxnote.storage import Segment, Storage, Summary


@pytest.fixture()
def storage(tmp_path: Path) -> Storage:
    s = Storage(tmp_path / "vn.db")
    yield s
    s.close()


def test_create_and_list_session(storage: Storage) -> None:
    sess = storage.create_session(title="Q1 Planning", asr_name="echo", llm_name="echo")
    assert sess.id and sess.title == "Q1 Planning"

    items = storage.list_sessions()
    assert len(items) == 1
    assert items[0].id == sess.id
    assert items[0].asr_name == "echo"


def test_rename_and_delete_session(storage: Storage) -> None:
    sess = storage.create_session(title="t1", asr_name="echo", llm_name="echo")
    storage.rename_session(sess.id, "renamed")
    assert storage.get_session(sess.id).title == "renamed"

    storage.delete_session(sess.id)
    assert storage.get_session(sess.id) is None
    assert storage.list_sessions() == []


def test_segments_and_fts_search(storage: Storage) -> None:
    sess = storage.create_session(title="t", asr_name="echo", llm_name="echo")
    storage.add_segment(Segment(session_id=sess.id, start_ms=0, end_ms=1000,
                                text="we will ship the alpha next Tuesday"))
    storage.add_segment(Segment(session_id=sess.id, start_ms=1000, end_ms=2000,
                                text="discussion about the database migration"))

    segs = storage.list_segments(sess.id)
    assert len(segs) == 2
    assert segs[0].start_ms < segs[1].start_ms

    hits = storage.search("database")
    assert len(hits) == 1
    assert "database" in hits[0]["text"].lower()
    assert "<b>" in hits[0]["snip"]

    assert storage.search("") == []


def test_summary_upsert_keeps_one_per_kind(storage: Storage) -> None:
    sess = storage.create_session(title="t", asr_name="echo", llm_name="echo")
    storage.upsert_summary(Summary(session_id=sess.id, kind="incremental",
                                    generated_at=1.0, summary_md="v1", todos=["a"]))
    storage.upsert_summary(Summary(session_id=sess.id, kind="incremental",
                                    generated_at=2.0, summary_md="v2", todos=["b"]))
    storage.upsert_summary(Summary(session_id=sess.id, kind="final",
                                    generated_at=3.0, summary_md="final", todos=[]))

    latest = storage.get_latest_summary(sess.id)
    assert latest is not None
    # final ranks above incremental.
    assert latest.kind == "final"
    assert latest.summary_md == "final"


def test_delete_cascades_segments(storage: Storage) -> None:
    sess = storage.create_session(title="t", asr_name="echo", llm_name="echo")
    storage.add_segment(Segment(session_id=sess.id, start_ms=0, end_ms=1, text="hello"))
    storage.delete_session(sess.id)
    assert storage.list_segments(sess.id) == []
    # FTS index should drop the row too.
    assert storage.search("hello") == []
