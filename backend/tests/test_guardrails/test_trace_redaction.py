import json
import logging

import pytest
from src.agents.trace import LOGGER_NAME, redact, trace_event


@pytest.mark.parametrize(
    "key",
    [
        "openrouterApiKey",
        "x-api-key",
        "client secret",
        "refreshToken",
        "challenge-id",
        "conversation_id",
        "token_hash",
    ],
)
def test_trace_redacts_sensitive_key_naming_variants(key):
    assert redact({key: "must-not-leak"})[key] == "[redacted]"


def test_trace_redacts_pii_and_direct_credential_assignments_inside_text():
    value = redact(
        "user@example.com 0901234567 openrouter_api_key=sk-live "
        "authorization: Bearer bearer-secret"
    )

    assert "user@example.com" not in value
    assert "0901234567" not in value
    assert "sk-live" not in value
    assert "bearer-secret" not in value
    assert "[email]" in value
    assert "[phone]" in value


def test_trace_redacts_standalone_token_parenthesized_phone_and_personal_id():
    value = redact("sk-proj-FAKESECRET (+84) 901 234 567 001204123456")

    assert "sk-proj-FAKESECRET" not in value
    assert "(+84) 901 234 567" not in value
    assert "001204123456" not in value


def test_trace_event_never_logs_nested_credentials(caplog):
    with caplog.at_level(logging.INFO, logger=LOGGER_NAME):
        trace_event(
            "security.test",
            message="password=hunter2",
            context={"openrouterApiKey": "sk-live", "phone": "0901234567"},
        )

    payload = json.loads(caplog.records[-1].message)
    assert payload["event"] == "security.test"
    assert payload["context"]["openrouterApiKey"] == "[redacted]"
    assert "hunter2" not in caplog.text
    assert "sk-live" not in caplog.text
    assert "0901234567" not in caplog.text
