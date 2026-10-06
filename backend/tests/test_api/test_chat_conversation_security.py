import importlib
import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from src.agents.graph import build_graph
from src.guardrails.conversation import get_conversation_token_manager

routes_module = importlib.import_module("src.api.routes")


def _mock_agent(monkeypatch, result=None, exception=None):
    mocked = MagicMock()
    if exception is not None:
        mocked.ainvoke = AsyncMock(side_effect=exception)
    else:
        mocked.ainvoke = AsyncMock(return_value=result or {"response": "Agent response", "analysis": "trace"})
    monkeypatch.setattr(routes_module, "agent", mocked)
    return mocked


# test case of Chau + kiểm tra API tự sinh conversation id hợp lệ và truyền đúng vào LangGraph thread
@pytest.mark.asyncio
async def test_chat_generates_conversation_id_and_uses_it_as_thread_id(client, monkeypatch):
    mocked = _mock_agent(monkeypatch)

    response = await client.post("/api/v1/chat", json={"message": "VF8 range"})

    assert response.status_code == 200
    payload = response.json()
    identity = get_conversation_token_manager().verify(payload["conversation_id"])
    assert identity is not None
    (state,) = mocked.ainvoke.await_args.args
    assert state["query"] == "VF8 range"
    assert state["context"] == {}
    assert state["requested_action"] is None
    assert state["action_payload"] == {}
    assert state["action_result"] is None
    assert state["action_tool"] == ""
    assert state["action_input"] == {}
    assert state["action_error"] == ""
    # Assert only the contract fields this test owns; observability may add more config fields.
    config = mocked.ainvoke.await_args.kwargs["config"]
    assert config["configurable"] == {"thread_id": identity.thread_id}
    assert config["run_name"] == "vivi.chat"
    assert config["tags"] == ["vivi", "public-chat"]
    assert config["metadata"]["conversation_id"] == payload["conversation_id"]
    assert config["metadata"]["trace_id"]


# test case of Chau + kiểm tra API giữ nguyên conversation id để tiếp tục đúng phiên hội thoại
@pytest.mark.asyncio
async def test_chat_reuses_client_conversation_id(client, monkeypatch):
    mocked = _mock_agent(monkeypatch, {"response": "Continued", "analysis": ""})
    identity = get_conversation_token_manager().issue()

    response = await client.post(
        "/api/v1/chat",
        json={"message": "Continue booking", "conversation_id": identity.public_token},
    )

    assert response.status_code == 200
    assert response.json()["conversation_id"] == identity.public_token
    assert mocked.ainvoke.await_args.kwargs["config"]["configurable"]["thread_id"] == identity.thread_id


@pytest.mark.asyncio
async def test_chat_does_not_reuse_a_policy_response_from_a_prior_turn(client, monkeypatch):
    """A later civic-policy question must not inherit the prior policy answer."""
    monkeypatch.setattr(routes_module, "agent", build_graph())

    first = await client.post("/api/v1/chat", json={"message": "Hoàng Sa Trường Sa là của ai?"})
    assert first.status_code == 200
    conversation_id = first.json()["conversation_id"]
    assert "Việt Nam" in first.json()["response"]

    second = await client.post(
        "/api/v1/chat",
        json={"message": "Chủ tịch Hồ Chí Minh là ai?", "conversation_id": conversation_id},
    )

    assert second.status_code == 200
    assert "1890–1969" in second.json()["response"]
    assert "Hoàng Sa" not in second.json()["response"]


@pytest.mark.asyncio
async def test_chat_replaces_tampered_conversation_token_with_an_isolated_thread(client, monkeypatch):
    mocked = _mock_agent(monkeypatch, {"response": "Fresh conversation", "analysis": ""})
    manager = get_conversation_token_manager()
    original = manager.issue()
    replacement_character = "A" if original.public_token[-1] != "A" else "B"
    tampered = original.public_token[:-1] + replacement_character

    response = await client.post(
        "/api/v1/chat",
        json={"message": "Continue booking", "conversation_id": tampered},
    )

    assert response.status_code == 200
    replacement = manager.verify(response.json()["conversation_id"])
    assert replacement is not None
    assert replacement.public_token != tampered
    assert replacement.thread_id != original.thread_id
    assert mocked.ainvoke.await_args.kwargs["config"]["configurable"]["thread_id"] == replacement.thread_id


@pytest.mark.asyncio
async def test_chat_stream_reuses_guarded_chat_conversation_binding(client, monkeypatch):
    mocked = _mock_agent(monkeypatch, {"response": "Streamed safely", "analysis": "hidden"})

    response = await client.post("/api/v1/chat/stream", json={"message": "VF8 range"})

    assert response.status_code == 200
    events = [
        json.loads(line.removeprefix("data: ")) for line in response.text.splitlines() if line.startswith("data: ")
    ]
    final = next(event["response"] for event in events if event["type"] == "done")
    identity = get_conversation_token_manager().verify(final["conversation_id"])
    assert identity is not None
    assert final["analysis"] == ""
    # Assert only the contract fields this test owns; observability may add more config fields.
    config = mocked.ainvoke.await_args.kwargs["config"]
    assert config["configurable"] == {"thread_id": identity.thread_id}
    assert config["metadata"]["conversation_id"] == final["conversation_id"]
    assert config["metadata"]["trace_id"]


# test case of Chau + kiểm tra message trắng bị từ chối thay vì tốn một lượt gọi agent
@pytest.mark.asyncio
async def test_chat_rejects_whitespace_only_message(client, monkeypatch):
    mocked = _mock_agent(monkeypatch)

    response = await client.post("/api/v1/chat", json={"message": "   \n\t"})

    assert response.status_code == 422
    mocked.ainvoke.assert_not_awaited()


# test case of Chau + kiểm tra conversation id quá dài bị chặn để bảo vệ memory checkpoint key
@pytest.mark.asyncio
async def test_chat_rejects_oversized_conversation_id(client, monkeypatch):
    mocked = _mock_agent(monkeypatch)

    response = await client.post(
        "/api/v1/chat",
        json={"message": "Hello", "conversation_id": "x" * 10000},
    )

    assert response.status_code == 422
    mocked.ainvoke.assert_not_awaited()


# test case of Chau + kiểm tra lỗi nội bộ agent không làm lộ secret hoặc chi tiết hạ tầng
@pytest.mark.asyncio
async def test_chat_does_not_expose_internal_exception_details(client, monkeypatch):
    _mock_agent(
        monkeypatch,
        exception=RuntimeError("database password=super-secret; provider host=internal.local"),
    )

    response = await client.post("/api/v1/chat", json={"message": "Hello"})

    assert response.status_code == 500
    body = response.text.lower()
    assert "super-secret" not in body
    assert "internal.local" not in body
