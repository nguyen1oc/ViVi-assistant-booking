from types import SimpleNamespace
from unittest.mock import Mock

from langchain_core.messages import AIMessage
from src.services import llm


def test_build_llm_returns_none_when_no_provider_key(monkeypatch):
    monkeypatch.setattr(
        llm,
        "get_settings",
        lambda: SimpleNamespace(openrouter_api_key="", openai_api_key=""),
    )

    assert llm._build_llm("gpt-4o-mini", 0.7) is None


def test_main_gpt_5_6_uses_openai_responses_api(monkeypatch):
    settings = SimpleNamespace(
        openrouter_api_key="",
        openai_api_key="sk-test",
        model_name="gpt-5.6-luna",
        llm_temperature=0.7,
        llm_reasoning_effort="low",
    )
    chat_openai = Mock(return_value=object())
    monkeypatch.setattr(llm, "get_settings", lambda: settings)
    monkeypatch.setattr(llm, "ChatOpenAI", chat_openai)

    llm.get_llm()

    chat_openai.assert_called_once()
    kwargs = chat_openai.call_args.kwargs
    assert kwargs["model"] == "gpt-5.6-luna"
    assert kwargs["use_responses_api"] is True
    assert kwargs["reasoning_effort"] == "low"
    assert "temperature" not in kwargs


def test_classifier_keeps_chat_completions_configuration(monkeypatch):
    settings = SimpleNamespace(
        openrouter_api_key="",
        openai_api_key="sk-test",
        model_name="gpt-5.6-luna",
        classifier_model_name="gpt-4o-mini",
        llm_temperature=0.7,
        llm_reasoning_effort="low",
    )
    chat_openai = Mock(return_value=object())
    monkeypatch.setattr(llm, "get_settings", lambda: settings)
    monkeypatch.setattr(llm, "ChatOpenAI", chat_openai)

    llm.get_classifier_llm()

    kwargs = chat_openai.call_args.kwargs
    assert kwargs["model"] == "gpt-4o-mini"
    assert kwargs["temperature"] == 0.0
    assert "use_responses_api" not in kwargs
    assert "reasoning_effort" not in kwargs


def test_extract_response_text_reads_responses_api_content_blocks():
    response = AIMessage(
        content=[
            {
                "type": "text",
                "text": "Chào Quý khách",
                "annotations": [],
                "id": "msg_test",
                "phase": "final_answer",
            }
        ]
    )

    assert llm.extract_response_text(response) == "Chào Quý khách"


def test_extract_response_text_keeps_chat_completions_strings():
    assert llm.extract_response_text(AIMessage(content="  Xin chào  ")) == "Xin chào"
