import asyncio
import base64
import json

import requests
import websockets

BASE_URL = "http://127.0.0.1:8000"
WS_URL = "ws://127.0.0.1:8000/api/voice/stream/ws_smoke"


async def main():
    # 1) Login to get JWT
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"username": "doctor", "password": "doctor"}, timeout=10)
    r.raise_for_status()
    token = r.json()["access_token"]
    print("Got token (truncated):", token[:24] + "...")

    # 2) Connect to WS
    async with websockets.connect(WS_URL) as ws:
        # expect welcome
        msg = await ws.recv()
        print("welcome:", msg)

        # 3) auth
        await ws.send(json.dumps({"type": "auth", "token": token}))
        msg = await ws.recv()
        print("auth_resp:", msg)

        # 4) send a tiny silent audio chunk (1600 samples @16kHz = 0.1s of silence)
        silent_pcm16 = (b"\x00\x00" * 1600)
        b64 = base64.b64encode(silent_pcm16).decode("utf-8")
        await ws.send(json.dumps({"type": "audio", "data": b64}))
        print("sent one audio chunk")

        # 5) listen briefly for status messages
        try:
            for _ in range(5):
                msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
                print("recv:", msg)
        except asyncio.TimeoutError:
            print("no more messages within timeout; closing")

        # 6) close
        await ws.send(json.dumps({"type": "close"}))
        print("sent close")


if __name__ == "__main__":
    asyncio.run(main())
