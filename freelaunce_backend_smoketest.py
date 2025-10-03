"""
Quick local smoke test for DigiClinic backend:
- Login (doctor/doctor dev fallback)
- Verify token
- Send a chat message
"""

import json
import os
from dataclasses import dataclass

import requests


BASE_URL = os.environ.get("DIGICLINIC_BASE_URL", "http://127.0.0.1:9999")


@dataclass
class Auth:
    token: str
    username: str


def login(username: str, password: str) -> Auth:
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"username": username, "password": password},
        timeout=15,
    )
    r.raise_for_status()
    data = r.json()
    return Auth(
        token=data["access_token"],
        username=data.get("username", username),
    )


def verify(auth: Auth) -> dict:
    r = requests.get(
        f"{BASE_URL}/api/auth/verify",
        headers={"Authorization": f"Bearer {auth.token}"},
        timeout=10,
    )
    r.raise_for_status()
    return r.json()


def chat_send(
    auth: Auth,
    message: str,
    conversation_id: str | None = None,
) -> dict:
    payload = {"message": message}
    if conversation_id:
        payload["conversation_id"] = conversation_id
    r = requests.post(
        f"{BASE_URL}/api/chat/send",
        headers={
            "Authorization": f"Bearer {auth.token}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def main() -> int:
    user = os.environ.get("DIGICLINIC_USER", "doctor")
    pwd = os.environ.get("DIGICLINIC_PASS", "doctor")

    print(f"Base URL: {BASE_URL}")
    print("1) Logging in...")
    auth = login(user, pwd)
    print("   -> OK")

    print("2) Verifying token...")
    v = verify(auth)
    print("   ->", v)

    print("3) Sending chat message...")
    resp = chat_send(
        auth,
        "Hello, can you summarize DigiClinic’s capabilities?",
    )
    print(json.dumps(resp, indent=2))
    print("   -> Chat OK")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except requests.HTTPError as e:
        print("HTTP error:", e)
        if e.response is not None:
            print("Body:", e.response.text)
        raise
    except Exception as e:
        print("Error:", e)
        raise
