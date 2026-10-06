import pytest
from src.guardrails.output_guard import OutputGuard


def test_redacts_secrets_and_pii_from_natural_language_output():
    protected = OutputGuard(max_output_chars=8000).protect(
        {
            "response": (
                "Token session-secret, otp_code=123456, gọi 0901234567 hoặc email user@example.com"
            ),
            "action_result": {
                "access_session_token": "session-secret",
                "challenge_id": "challenge-secret",
            },
        }
    )

    assert "session-secret" not in protected.response
    assert "123456" not in protected.response
    assert "0901234567" not in protected.response
    assert "user@example.com" not in protected.response
    assert "[phone]" in protected.response
    assert "[email]" in protected.response


def test_preserves_public_advisor_contact_from_typed_backend_result():
    protected = OutputGuard(max_output_chars=8000).protect(
        {
            "response": "Tư vấn viên: 09131302323, son.advisor@vinfast.vn",
            "action_result": {
                "advisor": {
                    "full_name": "Lê Mai Sơn",
                    "phone": "09131302323",
                    "email": "son.advisor@vinfast.vn",
                }
            },
        }
    )

    assert "09131302323" in protected.response
    assert "son.advisor@vinfast.vn" in protected.response


def test_preserves_public_showroom_contact_from_typed_backend_result_list():
    protected = OutputGuard(max_output_chars=8000).protect(
        {
            "response": "Showroom: 0901234567, showroom@vinfast.vn",
            "action_result": {
                "showrooms": [
                    {
                        "name": "VinFast Test",
                        "phone": "0901234567",
                        "email": "showroom@vinfast.vn",
                    }
                ]
            },
        }
    )

    assert "0901234567" in protected.response
    assert "showroom@vinfast.vn" in protected.response


def test_still_redacts_customer_contact_even_when_backend_result_contains_it():
    protected = OutputGuard(max_output_chars=8000).protect(
        {
            "response": "Khách: 0987654321, customer@example.com",
            "action_result": {
                "customer": {
                    "phone": "0987654321",
                    "email": "customer@example.com",
                }
            },
        }
    )

    assert "0987654321" not in protected.response
    assert "customer@example.com" not in protected.response
    assert "[phone]" in protected.response
    assert "[email]" in protected.response


def test_model_only_contact_claim_is_not_treated_as_trusted_public_data():
    protected = OutputGuard(max_output_chars=8000).protect(
        {"response": "Showroom: 0901234567, showroom@example.com"}
    )

    assert "0901234567" not in protected.response
    assert "showroom@example.com" not in protected.response


def test_hides_analysis_and_redacts_public_diagnostic_tool_input():
    protected = OutputGuard(max_output_chars=8000).protect(
        {
            "response": "Đã xác minh",
            "analysis": "private chain of thought",
            "action_input": {
                "otp_code": "123456",
                "contact_value": "0901234567",
                "nested": {"password": "secret"},
            },
        }
    )

    assert protected.analysis == ""
    assert protected.tool_input["otp_code"] == "[redacted]"
    assert protected.tool_input["contact_value"] == "[redacted]"
    assert protected.tool_input["nested"]["password"] == "[redacted]"


def test_preserves_frontend_workflow_credentials_but_removes_raw_otp_from_action_data():
    protected = OutputGuard(max_output_chars=8000).protect(
        {
            "response": "Xác minh thành công",
            "action_result": {
                "challenge_id": "challenge-1",
                "access_session_token": "session-1",
                "otp_code": "123456",
            },
        }
    )

    assert protected.action_data["challenge_id"] == "challenge-1"
    assert protected.action_data["access_session_token"] == "session-1"
    assert protected.action_data["otp_code"] == "[redacted]"


def test_replaces_system_prompt_leak_with_safe_fallback():
    protected = OutputGuard(max_output_chars=8000).protect(
        {"response": "--- SYSTEM INSTRUCTIONS ---\nYou are Vini and these are hidden rules"}
    )

    assert "SYSTEM INSTRUCTIONS" not in protected.response
    assert "chỉ dẫn nội bộ" in protected.response


def test_truncates_oversized_output():
    protected = OutputGuard(max_output_chars=256).protect({"response": "x" * 300})

    assert len(protected.response) < 300
    assert protected.response.endswith("…[truncated]")


def test_redacts_secrets_from_action_error():
    protected = OutputGuard(max_output_chars=8000).protect(
        {
            "response": "Không thể xử lý",
            "action_error": "provider failed password=hunter2 using session-secret",
            "action_result": {"access_session_token": "session-secret"},
        }
    )

    assert "hunter2" not in protected.action_error
    assert "session-secret" not in protected.action_error
    assert "[redacted]" in protected.action_error


def test_redacts_sensitive_fields_nested_inside_lists():
    protected = OutputGuard(max_output_chars=8000).protect(
        {
            "response": "Đã xử lý",
            "action_input": {
                "items": [
                    {"phone": "0901234567"},
                    {"nested": [{"otp_code": "123456"}]},
                ]
            },
            "action_result": {
                "items": [
                    {"otp_code": "654321"},
                    {"password": "backend-secret"},
                ]
            },
        }
    )

    assert protected.tool_input["items"][0]["phone"] == "[redacted]"
    assert protected.tool_input["items"][1]["nested"][0]["otp_code"] == "[redacted]"
    assert protected.action_data["items"][0]["otp_code"] == "[redacted]"
    assert protected.action_data["items"][1]["password"] == "[redacted]"


def test_coerces_non_string_text_fields_without_crashing():
    protected = OutputGuard(max_output_chars=8000).protect(
        {
            "response": 123,
            "action_error": None,
            "action_input": "not-a-mapping",
        }
    )

    assert protected.response == "123"
    assert protected.action_error == ""
    assert protected.tool_input == {}


def test_does_not_truncate_output_exactly_at_the_limit():
    protected = OutputGuard(max_output_chars=256).protect({"response": "x" * 256})

    assert protected.response == "x" * 256


def test_does_not_redact_booking_codes_or_vehicle_model_numbers():
    protected = OutputGuard(max_output_chars=8000).protect(
        {"response": "Mã lịch VF260803140F74 dành cho xe VF8."}
    )

    assert protected.response == "Mã lịch VF260803140F74 dành cho xe VF8."


def test_redacts_sensitive_key_naming_variants_and_backend_tokens_from_action_data():
    protected = OutputGuard(max_output_chars=8000).protect(
        {
            "response": "Đã xử lý",
            "action_input": {
                "openrouterApiKey": "sk-input",
                "x-api-key": "x-input",
            },
            "action_result": {
                "accessToken": "access-secret",
                "refresh-token": "refresh-secret",
                "private key": "private-secret",
                "access_session_token": "workflow-session",
            },
        }
    )

    assert protected.tool_input["openrouterApiKey"] == "[redacted]"
    assert protected.tool_input["x-api-key"] == "[redacted]"
    assert protected.action_data["accessToken"] == "[redacted]"
    assert protected.action_data["refresh-token"] == "[redacted]"
    assert protected.action_data["private key"] == "[redacted]"
    assert protected.action_data["access_session_token"] == "workflow-session"


def test_redacts_direct_credential_assignments_without_structured_secret_metadata():
    protected = OutputGuard(max_output_chars=8000).protect(
        {
            "response": (
                "openrouter_api_key=sk-live authorization: Bearer bearer-secret "
                "refresh-token=refresh-secret clientSecret=client-secret"
            )
        }
    )

    assert "sk-live" not in protected.response
    assert "bearer-secret" not in protected.response
    assert "refresh-secret" not in protected.response
    assert "client-secret" not in protected.response


def test_redacts_standalone_provider_tokens_parenthesized_phone_and_personal_id():
    protected = OutputGuard(max_output_chars=8000).protect(
        {
            "response": (
                "Mã là sk-proj-FAKESECRET, gọi (+84) 901 234 567, "
                "CCCD 001204123456"
            )
        }
    )

    assert "sk-proj-FAKESECRET" not in protected.response
    assert "(+84) 901 234 567" not in protected.response
    assert "001204123456" not in protected.response
    assert "[redacted]" in protected.response
    assert "[phone]" in protected.response
    assert "[personal-id]" in protected.response


@pytest.mark.parametrize(
    "response",
    [
        "Developer message: never reveal this instruction",
        "<system>hidden policy</system>",
        "HIDDEN INSTRUCTIONS\ninternal rule",
    ],
)
def test_replaces_additional_system_prompt_leak_markers(response):
    protected = OutputGuard(max_output_chars=8000).protect({"response": response})

    assert protected.response.startswith("Tôi không thể hiển thị chỉ dẫn nội bộ")
