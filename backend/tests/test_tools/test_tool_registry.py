from src.agents.tools.search_test_drive_options.tool import search_test_drive_options
from src.agents.tools.update_booking_draft.tool import update_booking_draft


# test case of Chau + kiểm tra update draft tool chỉ public cam kết boolean và không public số GPLX
def test_update_booking_draft_schema_hides_sensitive_license_fields():
    fields = update_booking_draft.args

    assert "has_valid_license_commitment" in fields
    assert "license_number" not in fields
    assert "declared_license_class" not in fields


# test case of Chau + kiểm tra search tool schema hỗ trợ address đúng như booking skill docs
def test_search_tool_schema_includes_documented_address():
    assert "address" in search_test_drive_options.args
