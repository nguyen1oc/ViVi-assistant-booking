import os
import sys

# Ensure backend src is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient
from src.main import app


def test_chat():
    client = TestClient(app)
    payload = {
        "message": "tôi muốn lái thử vf 3",
        "conversation_id": "test-session-456",
        "context": {}
    }

    print("Sending POST request to /api/v1/chat...")
    response = client.post("/api/v1/chat", json=payload)

    print("\n--- Response ---")
    print(f"Status: {response.status_code}")
    print(f"Body: {response.json()}")
    print("----------------")

if __name__ == '__main__':
    test_chat()
