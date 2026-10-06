import pytest
from src.services.booking.common import (
    is_valid_customer_email,
    is_valid_customer_phone,
    person_patch_validation_error,
)


def test_customer_email_limits_each_side_of_at_sign():
    assert is_valid_customer_email(f"{'a' * 30}@{'b' * 16}.com") is True
    assert is_valid_customer_email(f"{'a' * 31}@example.com") is False
    assert is_valid_customer_email(f"user@{'b' * 17}.com") is False


@pytest.mark.parametrize("phone", ["0901234567", "090 123 4567", "+84901234567"])
def test_customer_phone_accepts_values_that_normalize_to_ten_digits(phone):
    assert is_valid_customer_phone(phone) is True


@pytest.mark.parametrize(
    ("patch", "message"),
    [
        ({"full_name": "A" * 31}, "Họ tên tối đa 30 ký tự."),
        ({"email": f"{'a' * 31}@example.com"}, "Email phải đúng định dạng, tối đa 30 ký tự trước @ và 20 ký tự sau @."),
        ({"phone": "09012345678"}, "Số điện thoại phải gồm đúng 10 chữ số và bắt đầu bằng 0."),
    ],
)
def test_person_patch_reports_customer_field_limit_errors(patch, message):
    assert person_patch_validation_error(patch) == message
