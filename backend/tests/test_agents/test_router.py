import pytest
from src.agents.graph import agent


def _cfg(thread_id: str) -> dict:
    """Helper tạo config với thread_id cho LangGraph MemorySaver."""
    return {"configurable": {"thread_id": thread_id}}


@pytest.mark.asyncio
# test case of Chau + kiểm tra câu hỏi chủ quyền được route sang sensitive policy
async def test_router_sovereignty_policy():
    """Kiểm tra câu hỏi chủ quyền Hoàng Sa Trường Sa được xử lý bởi sensitive_policy node."""
    query = "Hoàng Sa Trường Sa là của ai?"
    result = await agent.ainvoke({"query": query}, config=_cfg("test-sovereignty"))

    assert result.get("intent") == "sensitive"
    assert "Hoàng Sa" in result.get("response", "")
    assert "Trường Sa" in result.get("response", "")
    assert "Việt Nam" in result.get("response", "")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("query", "expected_text"),
    [
        ("Đảng Cộng sản Việt Nam được thành lập khi nào?", "3/2/1930"),
        ("Chủ tịch Hồ Chí Minh là ai?", "1890–1969"),
    ],
)
async def test_router_answers_benign_civic_history_questions(query, expected_text):
    result = await agent.ainvoke({"query": query}, config=_cfg(f"test-civic-{expected_text}"))

    assert result.get("intent") == "sensitive"
    assert expected_text in result.get("response", "")


@pytest.mark.asyncio
# test case of Chau + kiểm tra yêu cầu viết code ngoài phạm vi bị từ chối
async def test_router_out_of_scope_coding():
    """Kiểm tra yêu cầu viết code lập trình được chặn bởi sensitive_policy node."""
    query = "hãy viết cho tôi một đoạn code python để crawl web"
    result = await agent.ainvoke({"query": query}, config=_cfg("test-coding"))

    assert result.get("intent") == "sensitive"
    assert "Trợ lý ảo hỗ trợ lái thử xe VinFast" in result.get("response", "")
    assert "không hỗ trợ" in result.get("response", "")


@pytest.mark.asyncio
# test case of Chau + kiểm tra câu chào dùng booking skill trong MVP chỉ có booking
async def test_router_general_greeting():
    """A short greeting is classified by the LLM and stays in the booking skill."""
    query = "hi"
    result = await agent.ainvoke({"query": query}, config=_cfg("test-greeting"))

    assert result.get("intent") == "domain"
    assert result.get("active_skill") == "booking"
    assert (result.get("metadata") or {}).get("sub_intent") == "greeting"
    assert "response" in result
    assert len(result.get("response", "")) > 0


@pytest.mark.asyncio
async def test_router_assistant_identity_stays_in_domain():
    result = await agent.ainvoke(
        {"query": "bạn là ai"},
        config=_cfg("test-assistant-identity"),
    )

    assert result.get("intent") == "domain"
    assert result.get("active_skill") == "booking"
    assert (result.get("metadata") or {}).get("sub_intent") == "assistant_identity"
    assert "response" in result


@pytest.mark.asyncio
# test case of Chau + kiểm tra yêu cầu đặt lịch được route sang domain booking
async def test_router_domain_booking():
    """Kiểm tra yêu cầu đặt lịch/tư vấn xe được định tuyến sang booking skill."""
    query = "Đặt lịch lái thử xe VF3 tại Hà Nội"
    result = await agent.ainvoke({"query": query}, config=_cfg("test-booking"))

    assert result.get("intent") == "domain"
    assert result.get("active_skill") == "booking"
    assert "response" in result
    assert "Mocked LLM" in result.get("response", "")


@pytest.mark.asyncio
async def test_router_vehicle_question_uses_booking_skill():
    """Câu hỏi về xe vẫn dùng booking skill khi advise chưa được phát triển."""
    query = "VF8 đi được bao nhiêu km sau một lần sạc đầy?"
    result = await agent.ainvoke({"query": query}, config=_cfg("test-advisory"))

    assert result.get("intent") == "domain"
    assert result.get("active_skill") == "booking"
    assert "response" in result
    assert "Mocked LLM" in result.get("response", "")
