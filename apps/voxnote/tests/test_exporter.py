"""Tests for voxnote.exporter — md / srt formats (docx is optional)."""
from __future__ import annotations

from pathlib import Path

import pytest

from voxnote.exporter import export
from voxnote.storage import Segment, Storage, Summary


@pytest.fixture()
def loaded_storage(tmp_path: Path) -> tuple[Storage, str]:
    s = Storage(tmp_path / "vn.db")
    sess = s.create_session(title="Demo / Session", asr_name="echo", llm_name="echo")
    s.add_segment(Segment(session_id=sess.id, start_ms=0, end_ms=2_000,
                          text="hello world", speaker="Alice"))
    s.add_segment(Segment(session_id=sess.id, start_ms=2_000, end_ms=5_500,
                          text="follow up next week"))
    s.upsert_summary(Summary(session_id=sess.id, kind="final", generated_at=1.0,
                              summary_md="- summary line 1\n- summary line 2",
                              todos=["follow up next week"]))
    s.end_session(sess.id)
    yield s, sess.id
    s.close()


def test_export_md_contains_summary_and_segments(loaded_storage, tmp_path: Path) -> None:
    storage, sid = loaded_storage
    out = export(storage, sid, fmt="md", out_dir=tmp_path / "out")
    assert out.exists() and out.suffix == ".md"
    text = out.read_text(encoding="utf-8")
    assert "# Demo / Session" in text  # H1 keeps original title
    # And the on-disk filename has slashes replaced.
    assert out.name == "Demo _ Session.md"
    assert "## Summary" in text
    assert "summary line 1" in text
    assert "## Action items" in text
    assert "- [ ] follow up next week" in text
    assert "hello world" in text
    assert "**Alice**" in text


def test_export_srt_format(loaded_storage, tmp_path: Path) -> None:
    storage, sid = loaded_storage
    out = export(storage, sid, fmt="srt", out_dir=tmp_path / "out")
    assert out.exists() and out.suffix == ".srt"
    text = out.read_text(encoding="utf-8")
    # First cue must be index 1 + properly formatted timestamps.
    lines = text.splitlines()
    assert lines[0] == "1"
    assert "00:00:00,000 --> 00:00:02,000" in text
    assert "00:00:02,000 --> 00:00:05,500" in text
    assert "hello world" in text


def test_export_unknown_format_raises(loaded_storage, tmp_path: Path) -> None:
    storage, sid = loaded_storage
    with pytest.raises(ValueError):
        export(storage, sid, fmt="pdf", out_dir=tmp_path / "out")


def test_export_unknown_session_raises(loaded_storage, tmp_path: Path) -> None:
    storage, _ = loaded_storage
    with pytest.raises(ValueError):
        export(storage, "no-such-id", fmt="md", out_dir=tmp_path / "out")
