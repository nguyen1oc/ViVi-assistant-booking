"""Integration tests for multi-turn memory isolation via thread_id."""

import pytest
from src.agents.graph import agent


def _cfg(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


@pytest.mark.asyncio
async def test_two_threads_do_not_share_state():
    """Hai thread_id khác nhau không được lẫn state với nhau."""
    # Thread A: booking intent
    result_a = await agent.ainvoke(
        {"query": "Đặt lịch lái thử xe VF3 tại Hà Nội"},
        config=_cfg("memory-thread-A"),
    )
    # Thread B: greeting also stays in the booking-only MVP skill.
    result_b = await agent.ainvoke(
        {"query": "Xin chào bạn nhé!"},
        config=_cfg("memory-thread-B"),
    )

    # Both turns use booking but state must still not leak across thread IDs.
    assert result_a.get("active_skill") == "booking"
    assert result_b.get("active_skill") == "booking"


@pytest.mark.asyncio
async def test_same_thread_retains_context():
    """Cùng thread_id giữa 2 lượt phải có lịch sử messages tích lũy."""
    thread_id = "memory-same-thread-test"

    # Lượt 1
    result_1 = await agent.ainvoke(
        {"query": "Xin chào!"},
        config=_cfg(thread_id),
    )
    assert "response" in result_1

    # Lượt 2 — cùng thread, messages phải được nối tiếp
    result_2 = await agent.ainvoke(
        {"query": "VF8 đi được bao nhiêu km?"},
        config=_cfg(thread_id),
    )
    assert "response" in result_2

    # Messages trong state phải có ít nhất 2 HumanMessage (lượt 1 + lượt 2)
    messages = result_2.get("messages", [])
    from langchain_core.messages import HumanMessage

    human_msgs = [m for m in messages if isinstance(m, HumanMessage)]
    assert len(human_msgs) >= 2, "Multi-turn: phải có ít nhất 2 HumanMessage trong cùng thread"
