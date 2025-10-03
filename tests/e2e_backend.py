"""
End-to-end backend smoke test for DigiClinic.

Covers:
- Auth login + verify
- Chat send (non-stream)
- Model: current, available, optional switch
- Model chat (non-stream)
- Medical intelligence: comprehensive assessment
- Vision: get formats + analyze with a tiny generated PNG
- Voice: health check

Environment:
- DIGICLINIC_BASE_URL (default http://127.0.0.1:8000)
- DIGICLINIC_USER (default doctor)
- DIGICLINIC_PASS (default doctor)
"""

from __future__ import annotations

import base64
import json
import os
import tempfile
from dataclasses import dataclass
from typing import Optional

import requests


BASE_URL = os.environ.get("DIGICLINIC_BASE_URL", "http://127.0.0.1:8000")


@dataclass
class Auth:
    token: str
    username: str


def req_json(r: requests.Response) -> dict:
    r.raise_for_status()
    return r.json()


def login(username: str, password: str) -> Auth:
    data = req_json(
        requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": username, "password": password},
            timeout=20,
        )
    )
    return Auth(
        token=data["access_token"],
        username=data.get("username", username),
    )


def verify(auth: Auth) -> dict:
    return req_json(
        requests.get(
            f"{BASE_URL}/api/auth/verify",
            headers={"Authorization": f"Bearer {auth.token}"},
            timeout=10,
        )
    )


def chat_send(
    auth: Auth, message: str, conversation_id: Optional[str] = None
) -> dict:
    payload: dict = {"message": message}
    if conversation_id:
        payload["conversation_id"] = conversation_id
    return req_json(
        requests.post(
            f"{BASE_URL}/api/chat/send",
            headers={
                "Authorization": f"Bearer {auth.token}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=30,
        )
    )


def models_current(auth: Auth) -> dict:
    return req_json(
        requests.get(
            f"{BASE_URL}/api/models/current",
            headers={"Authorization": f"Bearer {auth.token}"},
            timeout=10,
        )
    )


def models_available(auth: Auth) -> dict:
    return req_json(
        requests.get(
            f"{BASE_URL}/api/models/available",
            headers={"Authorization": f"Bearer {auth.token}"},
            timeout=10,
        )
    )


def models_switch(auth: Auth, model_id: str, conversation_id: str) -> dict:
    return req_json(
        requests.post(
            f"{BASE_URL}/api/models/switch",
            headers={
                "Authorization": f"Bearer {auth.token}",
                "Content-Type": "application/json",
            },
            json={
                "model_id": model_id,
                "conversation_id": conversation_id,
                "reason": "smoke test",
            },
            timeout=20,
        )
    )


def models_chat(
    auth: Auth,
    message: str,
    conversation_id: str,
    model_id: Optional[str] = None,
) -> dict:
    payload: dict = {
        "message": message,
        "conversation_id": conversation_id,
    }
    if model_id:
        payload["model_id"] = model_id
    return req_json(
        requests.post(
            f"{BASE_URL}/api/models/chat",
            headers={
                "Authorization": f"Bearer {auth.token}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=30,
        )
    )


def medical_assessment(auth: Auth) -> dict:
    payload = {
        "patient_message": "I have a sore throat and mild fever for 2 days.",
        "patient_id": None,
        "session_id": "smoke-session",
        "context": {"notes": "E2E test"},
    }
    return req_json(
        requests.post(
            f"{BASE_URL}/api/medical/clinical/comprehensive-assessment",
            headers={
                "Authorization": f"Bearer {auth.token}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=60,
        )
    )


def medical_vision_formats(auth: Auth) -> dict:
    return req_json(
        requests.get(
            f"{BASE_URL}/api/medical/vision/formats",
            headers={"Authorization": f"Bearer {auth.token}"},
            timeout=10,
        )
    )


def _tiny_png_bytes() -> bytes:
    # Minimal valid 1x1 PNG (red pixel); pre-encoded to avoid Pillow dependency
    return base64.b64decode(
        b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAA"
        b"AAC0lEQVR42mP8/x8AAuMB9p0p/6kAAAAASUVORK5CYII="
    )


def medical_vision_analyze(auth: Auth) -> dict:
    img_bytes = _tiny_png_bytes()
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp.write(img_bytes)
        tmp_path = tmp.name

    try:
        with open(tmp_path, "rb") as f:
            files = {"file": ("tiny.png", f, "image/png")}
            data = {"analysis_level": "clinical"}
            r = requests.post(
                f"{BASE_URL}/api/medical/vision/analyze",
                headers={"Authorization": f"Bearer {auth.token}"},
                files=files,
                data=data,
                timeout=60,
            )
        return req_json(r)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def voice_health() -> dict:
    # No auth required for health
    return req_json(requests.get(f"{BASE_URL}/api/voice/health", timeout=10))


def main() -> int:
    user = os.environ.get("DIGICLINIC_USER", "doctor")
    pwd = os.environ.get("DIGICLINIC_PASS", "doctor")

    print(f"Base URL: {BASE_URL}")
    print("1) Login...")
    auth = login(user, pwd)
    print("   -> OK")

    print("2) Verify...")
    ver = verify(auth)
    print("   ->", ver)

    print("3) Chat send (non-stream)...")
    chat1 = chat_send(auth, "Hello from the E2E test.")
    print("   ->", json.dumps(chat1, indent=2)[:300], "...")
    conv_id = chat1.get("conversation_id")

    print("4) Models current...")
    cur = models_current(auth)
    print("   ->", cur)

    print("5) Models available...")
    avail = models_available(auth)
    print("   -> total:", avail.get("total"))

    picked_model = None
    if avail.get("models"):
        picked_model = avail["models"][0]["id"]
        print("   picking:", picked_model)
        if conv_id:
            print("6) Switch model...")
            sw = models_switch(auth, picked_model, conv_id)
            print("   ->", sw.get("success"), sw.get("current_model"))

            print("7) Model chat (non-stream)...")
            mchat = models_chat(
                auth, "Say hello politely.", conv_id, picked_model
            )
            print("   ->", json.dumps(mchat, indent=2)[:300], "...")

    print("8) Medical assessment...")
    assess = medical_assessment(auth)
    print("   -> success:", assess.get("success"))

    print("9) Vision formats...")
    formats = medical_vision_formats(auth)
    print("   ->", formats.get("supported_formats"))

    print("10) Vision analyze tiny PNG...")
    try:
        analysis = medical_vision_analyze(auth)
        print("   -> keys:", list(analysis.keys())[:5])
    except Exception as e:
        print("   -> Vision analyze failed:", e)

    print("11) Voice health...")
    vhealth = voice_health()
    print("   ->", vhealth.get("success"))

    print("E2E smoke test completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
