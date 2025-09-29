import os
import json
from typing import Dict

import requests


BASE_URL = os.environ.get("DIGICLINIC_BASE_URL", "http://127.0.0.1:8000")


def login(username: str, password: str) -> str:
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"username": username, "password": password},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def check_health(token: str) -> Dict:
    r = requests.get(
        f"{BASE_URL}/api/models/agent/health",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    r.raise_for_status()
    return r.json()


def stream_once(token: str, message: str) -> None:
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {
        "message": message,
        "conversation_id": "default",
        "model_id": None,
    }
    with requests.post(
        f"{BASE_URL}/api/models/chat/stream",
        json=payload,
        headers=headers,
        stream=True,
    ) as r:
        r.raise_for_status()
        print("--- STREAM BEGIN ---")
        for line in r.iter_lines():
            if not line:
                continue
            if not line.startswith(b"data:"):
                continue
            try:
                obj = json.loads(line.split(b":", 1)[1].strip())
            except Exception:
                print(line.decode("utf-8", errors="ignore"))
                continue
            print(obj)
        print("--- STREAM END ---")


def main() -> int:
    user = os.environ.get("DIGICLINIC_USER", "doctor")
    pwd = os.environ.get("DIGICLINIC_PASS", "doctor")

    print(f"Target: {BASE_URL}")
    token = login(user, pwd)
    print("Login OK")

    health = check_health(token)
    print("Agent health:", health)
    if not (
        health.get("agents_enabled") and health.get("mode") == "extended"
    ):
        print(
            "WARNING: Agents not in extended mode; progress will be limited."
        )

    print("Streaming a test message...\n")
    stream_once(
        token,
        "I have chest pain and also have diabetes. What should I do?",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
