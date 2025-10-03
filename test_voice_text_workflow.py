#!/usr/bin/env python3
"""
Test script for Voice-to-Claude workflow using the text-based test endpoint
This bypasses audio processing and directly tests the transcript-to-LLM flow
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

async def test_voice_text_workflow():
    """Test the voice-to-text-to-Claude workflow using the test endpoint"""
    
    print("🧪 Testing DigiClinic Voice-Text-Claude Workflow")
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
        
        token = login_response.json().get("access_token")
        print("✅ Authentication successful")
            
    except Exception as e:
        print(f"❌ Authentication error: {e}")
        return False
    
    # Step 2: Test WebSocket connection
    print("\n2️⃣ Testing WebSocket connection...")
    session_id = "test_session_text_123"
    ws_url = f"{WS_URL}/api/test/voice-text/{session_id}"
    
    try:
        async with websockets.connect(ws_url) as websocket:
            print("✅ WebSocket connection established")
            
            # Step 3: Authenticate with WebSocket
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
            
            # Step 4: Send test transcripts
            print("\n4️⃣ Sending test transcripts...")
            
            # Send partial transcript
            partial_message = {
                "type": "transcript",
                "text": "I have been experiencing chest pain",
                "is_final": False
            }
            await websocket.send(json.dumps(partial_message))
            print("📤 Sent partial transcript")
            
            # Send final transcript
            final_message = {
                "type": "transcript",
                "text": "I have been experiencing chest pain and cough for the past 3 days",
                "is_final": True
            }
            await websocket.send(json.dumps(final_message))
            print("📤 Sent final transcript")
            
            # Step 5: Listen for responses
            print("\n5️⃣ Listening for server responses...")
            response_count = 0
            llm_response_received = False
            transcript_received = False
            timeout_seconds = 45  # Give more time for LLM response
            start_time = asyncio.get_event_loop().time()
            
            try:
                while response_count < 15:  # Allow more responses
                    current_time = asyncio.get_event_loop().time()
                    if current_time - start_time > timeout_seconds:
                        raise asyncio.TimeoutError("Response timeout exceeded")
                    
                    try:
                        message = await websocket.recv()
                        response = json.loads(message)
                        response_count += 1
                        
                        msg_type = response.get("type", "unknown")
                        print(f"📥 Message #{response_count}: {msg_type}")
                        
                        if msg_type == "transcript":
                            text = response.get('text', '')
                            is_final = response.get('is_final', False)
                            print(f"   📝 Transcript: '{text}' (final: {is_final})")
                            transcript_received = True
                        
                        elif msg_type == "llm_response":
                            llm_text = response.get('response', '')
                            model = response.get('model', 'unknown')
                            print(f"   🤖 Claude Response ({model}):")
                            print(f"       {llm_text}")
                            llm_response_received = True
                            break  # Success!
                            
                        elif msg_type == "error":
                            error_msg = response.get('error', '')
                            print(f"   ❌ Error: {error_msg}")
                            
                        elif msg_type == "status":
                            status = response.get('status', '')
                            message_text = response.get('message', '')
                            print(f"   ℹ️  Status: {status} - {message_text}")
                            
                        else:
                            print(f"   🔍 Other: {json.dumps(response, indent=2)}")
                            
                    except websockets.exceptions.ConnectionClosed:
                        print("🔌 WebSocket connection closed")
                        break
                    except json.JSONDecodeError as e:
                        print(f"📋 JSON decode error: {e}")
                        
            except asyncio.TimeoutError:
                print("⏰ Timeout waiting for responses")
            
            # Send close message
            close_message = {"type": "close"}
            await websocket.send(json.dumps(close_message))
            
            # Step 6: Results summary
            print("\n6️⃣ Test Results Summary:")
            print("-" * 40)
            print("✅ WebSocket connection: SUCCESS")
            print("✅ Authentication: SUCCESS")
            print("✅ Message sending: SUCCESS")
            print(f"📨 Total responses received: {response_count}")
            print(f"📝 Transcript processing: {'✅ SUCCESS' if transcript_received else '❌ FAILED'}")
            
            if llm_response_received:
                print("🤖 Claude LLM Response: ✅ SUCCESS")
                print("\n🏆 COMPLETE WORKFLOW TEST: ✅ PASSED")
                print("   ✅ Text transcript processing works")
                print("   ✅ Claude integration works")
                print("   ✅ WebSocket response delivery works")
                return True
            else:
                print("❌ Claude LLM Response: FAILED")
                print("\n⚠️  COMPLETE WORKFLOW TEST: PARTIAL SUCCESS")
                print("   ✅ WebSocket communication works")
                print("   ❌ LLM integration needs verification")
                return False
                
    except Exception as e:
        print(f"❌ WebSocket test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("🧪 DigiClinic Voice-Text-Claude Test Suite")
    print("=" * 60)
    
    try:
        result = asyncio.run(test_voice_text_workflow())
        
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
        import traceback
        traceback.print_exc()
        sys.exit(1)