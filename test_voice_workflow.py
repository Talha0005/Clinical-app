#!/usr/bin/env python3
"""
Test script for Voice WebSocket to Claude LLM workflow
Tests the complete pipeline: Voice → Transcription → Claude Response
"""

import asyncio
import websockets
import json
import requests
import sys
from datetime import datetime

# Test configuration
BACKEND_URL = "http://127.0.0.1:8000"
WS_URL = "ws://127.0.0.1:8000"
TEST_USERNAME = "doctor"
TEST_PASSWORD = "doctor"

async def test_voice_websocket_with_claude():
    """Test the complete voice workflow with Claude response"""
    
    print("🧪 Testing DigiClinic Voice WebSocket to Claude LLM Workflow")
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 60)
    
    # Step 1: Login and get token
    print("1️⃣ Authenticating user...")
    try:
        login_response = requests.post(f"{BACKEND_URL}/api/auth/login", json={
            "username": TEST_USERNAME,
            "password": TEST_PASSWORD
        })
        
        if login_response.status_code != 200:
            print(f"❌ Login failed: {login_response.status_code}")
            print(f"   Response: {login_response.text}")
            return False
        
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            print("✅ Authentication successful")
        else:
            print(f"❌ Login still failed: {login_response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Authentication error: {e}")
        return False
    
    # Step 2: Test WebSocket connection and message flow
    print("\n2️⃣ Testing WebSocket connection...")
    session_id = "test_session_123"
    ws_url = f"{WS_URL}/api/voice/stream/{session_id}?token={token}"
    
    try:
        async with websockets.connect(ws_url) as websocket:
            print("✅ WebSocket connection established")
            
            # Step 3: Authenticate with the WebSocket
            print("\n3️⃣ Authenticating with WebSocket...")
            auth_message = {
                "type": "auth",
                "token": token
            }
            await websocket.send(json.dumps(auth_message))
            print("📤 Sent authentication")
            
            # Wait for auth response
            auth_response = await websocket.recv()
            auth_data = json.loads(auth_response)
            print(f"📥 Auth response: {auth_data.get('status', 'unknown')}")
            
            # Step 4: Simulate audio data (we'll send a minimal base64 audio chunk)
            print("\n4️⃣ Simulating audio data...")
            
            # Create minimal audio data (silence) - 16-bit PCM, 16kHz, mono
            import base64
            # 1024 samples of silence (2048 bytes for 16-bit)
            silence_audio = b'\x00' * 2048
            audio_b64 = base64.b64encode(silence_audio).decode('utf-8')
            
            audio_message = {
                "type": "audio",
                "data": audio_b64
            }
            await websocket.send(json.dumps(audio_message))
            print("📤 Sent audio data")
            
            # Send close message to finish the stream
            close_message = {
                "type": "close"
            }
            await websocket.send(json.dumps(close_message))
            print("📤 Sent close message")
            
            # Step 5: Listen for responses
            print("\n5️⃣ Listening for server responses...")
            response_count = 0
            llm_response_received = False
            
            try:
                # Wait for responses with timeout (30 seconds)
                timeout_seconds = 30
                start_time = asyncio.get_event_loop().time()
                
                while response_count < 10:  # Limit to prevent infinite loop
                    current_time = asyncio.get_event_loop().time()
                    if current_time - start_time > timeout_seconds:
                        raise asyncio.TimeoutError("Response timeout exceeded")
                    
                        try:
                            message = await websocket.recv()
                            response = json.loads(message)
                            response_count += 1
                            
                            msg_type = response.get("type", "unknown")
                            print(f"📥 Received message #{response_count}: type='{msg_type}'")
                            
                            if msg_type == "transcript":
                                print(f"   📝 Transcript: {response.get('text', '')}")
                                print(f"   🔄 Is final: {response.get('is_final', False)}")
                            
                            elif msg_type == "llm_response":
                                print(f"   🤖 Claude Response: {response.get('response', '')}")
                                llm_response_received = True
                                break  # Success!
                                
                            elif msg_type == "error":
                                print(f"   ❌ Error: {response.get('message', '')}")
                                
                            else:
                                print(f"   ℹ️  Other: {json.dumps(response, indent=2)}")
                                
                        except websockets.exceptions.ConnectionClosed:
                            print("🔌 WebSocket connection closed")
                            break
                        except json.JSONDecodeError as e:
                            print(f"📋 JSON decode error: {e}")
                            
            except asyncio.TimeoutError:
                print("⏰ Timeout waiting for responses")
            
            # Step 6: Results summary
            print("\n6️⃣ Test Results Summary:")
            print("-" * 40)
            print(f"✅ WebSocket connection: SUCCESS")
            print(f"✅ Message sending: SUCCESS")
            print(f"📨 Total responses received: {response_count}")
            
            if llm_response_received:
                print("🎉 Claude LLM Response: ✅ SUCCESS")
                print("\n🏆 COMPLETE WORKFLOW TEST: PASSED")
                return True
            else:
                print("❌ Claude LLM Response: FAILED")
                print("\n⚠️  COMPLETE WORKFLOW TEST: PARTIAL SUCCESS")
                print("   - WebSocket communication works")
                print("   - LLM integration needs verification")
                return False
                
    except Exception as e:
        print(f"❌ WebSocket test failed: {e}")
        return False


if __name__ == "__main__":
    print("🧪 DigiClinic Voice WebSocket Test Suite")
    print("=" * 60)
    
    try:
        result = asyncio.run(test_voice_websocket_with_claude())
        
        if result:
            print("\n🎉 All tests passed! Voice → Claude workflow is functional.")
            sys.exit(0)
        else:
            print("\n⚠️  Some tests failed. Check the logs above.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)