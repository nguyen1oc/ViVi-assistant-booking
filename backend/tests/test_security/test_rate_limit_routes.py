from src.security.rate_limit import route_class_for_path


def test_all_public_booking_action_aliases_use_the_canonical_rate_limiter():
    assert route_class_for_path("/api/v1/chat") == "chat"
    assert route_class_for_path("/api/v1/demo/action") == "demo_action"
    assert route_class_for_path("/api/v1/test-drive/actions") == "demo_action"


def test_unrelated_routes_are_not_accidentally_classified():
    assert route_class_for_path("/health") is None


def test_public_invitation_lookup_is_rate_limited():
    # Mã lịch chỉ có 6 ký tự hex nên endpoint công khai này là chỗ dò mã lý tưởng.
    # Bỏ quên nó khỏi bộ đếm là mở cửa cho việc quét sạch tên khách và giờ hẹn.
    assert route_class_for_path("/api/v1/invitations/v1.abc.def") == "invitation"
    assert route_class_for_path("/api/v1/invitations/") == "invitation"


def test_invitation_rules_key_on_ip_because_recipients_have_no_session():
    from src.config import get_settings
    from src.security.client_identity import ClientIdentity
    from src.security.rate_limit import rules_for_route

    identity = ClientIdentity(session_id="s1", client_ip="203.0.113.9")
    rules = rules_for_route("invitation", identity, get_settings())

    assert [rule.window_seconds for rule in rules] == [60, 3_600]
    assert all("203.0.113.9" in rule.key for rule in rules)
    assert all("s1" not in rule.key for rule in rules)
