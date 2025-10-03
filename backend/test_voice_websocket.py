#!/usr/bin/env python3
"""
Test script for Voice WebSocket functionality
"""

import asyncio
import websockets
import json
import base64
import numpy as np
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from auth import create_access_token
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def create_test_audio(duration_seconds=2, sample_rate=16000, frequency=440):
    """Create a test sine wave audio for testing"""
    t = np.linspace(0, duration_seconds, int(sample_rate * duration_seconds), False)
    # Generate sine wave
    audio_data = np.sin(frequency * 2 * np.pi * t)
    # Convert to 16-bit PCM
    audio_16bit = (audio_data * 32767).astype(np.int16)
    return audio_16bit.tobytes()


async def test_voice_websocket():
    """Test the voice WebSocket connection"""

    # Create a test token
    token = create_access_token(data={"sub": "test_user"})
    print(f"🔑 Created test token: {token[:50]}...")

    # WebSocket URL
    session_id = f"test_{int(asyncio.get_event_loop().time())}"
    ws_url = f"ws://localhost:8000/api/voice/stream/{session_id}"

    print(f"🎤 Connecting to: {ws_url}")

    try:
        async with websockets.connect(ws_url) as websocket:
            print("✅ WebSocket connected successfully!")

            # Wait for welcome message
            welcome_msg = await websocket.recv()
            welcome_data = json.loads(welcome_msg)
            print(f"📨 Welcome: {welcome_data}")

            # Send authentication
            auth_message = {"type": "auth", "token": token}
            await websocket.send(json.dumps(auth_message))
            print("🔐 Sent authentication")

            # Wait for auth response
            auth_response = await websocket.recv()
            auth_data = json.loads(auth_response)
            print(f"🔓 Auth response: {auth_data}")

            if auth_data.get("status") == "authenticated":
                print("✅ Authentication successful!")

                # Create test audio data
                print("🎵 Creating test audio...")
                test_audio = create_test_audio(duration_seconds=1)

                # Split audio into chunks and send
                chunk_size = 1024  # 1KB chunks
                chunks = [
                    test_audio[i : i + chunk_size]
                    for i in range(0, len(test_audio), chunk_size)
                ]

                print(f"📤 Sending {len(chunks)} audio chunks...")
                for i, chunk in enumerate(chunks):
                    # Encode chunk as base64
                    chunk_b64 = base64.b64encode(chunk).decode("utf-8")

                    audio_message = {"type": "audio", "data": chunk_b64}
                    await websocket.send(json.dumps(audio_message))
                    print(f"📤 Sent chunk {i+1}/{len(chunks)}")

                    # Wait a bit between chunks
                    await asyncio.sleep(0.1)

                # Listen for responses for a bit
                print("🎧 Listening for transcription responses...")
                timeout_count = 0
                max_timeouts = 10

                while timeout_count < max_timeouts:
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                        response_data = json.loads(response)
                        print(f"📨 Response: {response_data}")

                        if response_data.get("type") == "final_transcript":
                            print("✅ Received final transcript!")
                            break

                    except asyncio.TimeoutError:
                        timeout_count += 1
                        print(f"⏰ Timeout {timeout_count}/{max_timeouts}")

                # Send close message
                close_message = {"type": "close"}
                await websocket.send(json.dumps(close_message))
                print("🏁 Sent close message")

            else:
                print(f"❌ Authentication failed: {auth_data}")

    except Exception as e:
        print(f"❌ WebSocket test failed: {e}")
        import traceback

        traceback.print_exc()


async def test_voice_health():
    """Test the voice service health endpoint"""
    import aiohttp

    print("🏥 Testing voice health endpoint...")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "http://localhost:8000/api/health/voice"
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Voice health: {json.dumps(data, indent=2)}")
                else:
                    print(f"❌ Voice health check failed: {response.status}")
                    text = await response.text()
                    print(f"Response: {text}")

    except Exception as e:
        print(f"❌ Health check failed: {e}")


async def main():
    """Main test function"""
    print("🧪 Starting Voice WebSocket Tests")
    print("=" * 50)

    # Test health endpoint first
    await test_voice_health()
    print()

    # Test WebSocket connection
    await test_voice_websocket()

    print("\n✅ Voice WebSocket tests completed!")


if __name__ == "__main__":
    asyncio.run(main())
