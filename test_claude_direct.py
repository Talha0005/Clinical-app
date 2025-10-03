#!/usr/bin/env python3
"""
Quick test to verify Claude integration works
This bypasses voice processing entirely
"""

import requests
import json

def test_claude_integration():
    """Test Claude integration directly via chat endpoint"""
    
    print("🧪 Testing Claude Integration")
    print("-" * 40)
    
    # Step 1: Login
    print("1️⃣ Logging in...")
    try:
        login_response = requests.post("http://127.0.0.1:8000/api/auth/login", json={
            "username": "doctor",
            "password": "doctor"
        })
        
        if login_response.status_code != 200:
            print(f"❌ Login failed: {login_response.status_code}")
            return False
        
        token = login_response.json().get("access_token")
        print("✅ Login successful")
        
    except Exception as e:
        print(f"❌ Login error: {e}")
        return False
    
    # Step 2: Test chat endpoint
    print("\n2️⃣ Testing Claude chat...")
    try:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        chat_data = {
            "message": "I have chest pain and cough for 3 days. What could it be?",
            "conversation_id": "test_conversation_123",
            "model_id": "anthropic/claude-3-5-sonnet-20240620"
        }
        
        response = requests.post(
            "http://127.0.0.1:8000/api/models/chat",
            headers=headers,
            json=chat_data
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Claude responded successfully!")
            print(f"📝 Response: {result.get('content', 'No content')[:100]}...")
            return True
        else:
            print(f"❌ Chat failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Chat error: {e}")
        return False

if __name__ == "__main__":
    if test_claude_integration():
        print("\n🎉 Claude integration is working!")
    else:
        print("\n❌ Claude integration failed!")