"""Tests for the pure helpers in voxnote.pipeline.

The full Pipeline class drives audio capture + asyncio loops + LLM and is
exercised end-to-end via manual smoke tests; here we lock down the pattern-
based TODO extractor since it has the most subtle behaviour.
"""
from __future__ import annotations

from voxnote.pipeline import _extract_todos


def test_summary_action_items_block_is_extracted() -> None:
    summary = (
        "Some summary text\n"
        "- bullet about a topic\n"
        "\n"
        "Action items\n"
        "- send the contract draft to Bob\n"
        "* schedule follow-up meeting Friday\n"
        "• confirm budget with finance\n"
    )
    todos = _extract_todos(transcript="", summary=summary)
    assert "send the contract draft to Bob" in todos
    assert "schedule follow-up meeting Friday" in todos
    assert "confirm budget with finance" in todos


def test_pattern_extracts_intent_phrases_in_english() -> None:
    transcript = "I will follow up with the vendor tomorrow. We will draft the proposal."
    todos = _extract_todos(transcript=transcript, summary="")
    assert any("follow up with the vendor" in t for t in todos)
    assert any("draft the proposal" in t for t in todos)


def test_pattern_extracts_chinese_intent_phrases() -> None:
    transcript = "我们需要确认下一步的预算分配。明天必须把方案发给客户。"
    todos = _extract_todos(transcript=transcript, summary="")
    assert any("确认下一步的预算分配" in t for t in todos)


def test_dedup_and_cap_at_twenty() -> None:
    transcript = " ".join(["I will run task " + str(i) for i in range(50)])
    todos = _extract_todos(transcript=transcript, summary="")
    assert len(todos) <= 20
    # Each entry is unique.
    assert len(set(todos)) == len(todos)


def test_empty_inputs_yield_no_todos() -> None:
    assert _extract_todos("", "") == []
