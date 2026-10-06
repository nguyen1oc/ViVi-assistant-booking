from src.guardrails.conversation import ConversationTokenManager


def test_conversation_token_round_trip_and_tamper_rejection():
    manager = ConversationTokenManager("s" * 32, ttl_seconds=60, now=lambda: 1_000)
    identity = manager.issue()

    assert manager.verify(identity.public_token) == identity
    tampered = identity.public_token[:-1] + ("A" if identity.public_token[-1] != "A" else "B")
    assert manager.verify(tampered) is None
    assert manager.verify("client-selected-thread") is None


def test_conversation_token_expires():
    current = [1_000.0]
    manager = ConversationTokenManager("s" * 32, ttl_seconds=60, now=lambda: current[0])
    identity = manager.issue()

    current[0] = 1_061.0

    assert manager.verify(identity.public_token) is None
