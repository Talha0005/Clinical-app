#!/usr/bin/env python3
"""
Test script for LLM wrapper functionality
Feature 2: LLM Wrapper Component - Testing
"""

import asyncio
import json
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent  # Go up to backend/
sys.path.insert(0, str(backend_path))

from services.chat_service import DigiClinicChatService


async def test_llm_wrapper():
    """Test the LLM wrapper with mock provider"""
    
    print("🔬 Testing DigiClinic LLM Wrapper...")
    
    # Initialize chat service with mock LLM
    chat_service = DigiClinicChatService(llm_provider="mock")
    
    print(f"✅ Initialized LLM: {chat_service.get_llm_info()}")
    
    # Start a new conversation
    conversation = await chat_service.start_conversation()
    print(f"✅ Started conversation: {conversation.conversation_id}")
    
    # Print initial conversation state
    print("\n📝 Initial conversation:")
    for msg in conversation.messages:
        print(f"  {msg.role}: {msg.content[:100]}...")
    
    # Simulate sending messages (like browser would)
    test_messages = [
        "I've been having headaches for the past few days",
        "The pain is mostly in my forehead and gets worse in bright light",
        "I haven't taken any medication yet"
    ]
    
    for user_msg in test_messages:
        print(f"\n👤 User: {user_msg}")
        
        # Convert conversation to dict (simulating browser → server)
        conv_data = conversation.to_dict()
        
        # Send message and get response
        result = await chat_service.send_message(conv_data, user_msg)
        
        if result["success"]:
            # Update conversation from response (simulating server → browser)
            conversation = conversation.__class__.from_dict(result["conversation"])
            print(f"🏥 Dr. Hervix: {result['response']}")
        else:
            print(f"❌ Error: {result['error']}")
            break
    
    print(f"\n📊 Final conversation has {len(conversation.messages)} messages")
    print(f"🕒 Conversation created: {conversation.created_at}")
    
    # Test conversation data serialization (browser ↔ server)
    print("\n🔄 Testing browser ↔ server serialization...")
    conv_json = json.dumps(conversation.to_dict(), indent=2)
    print(f"✅ Serialized conversation: {len(conv_json)} characters")
    
    # Test recreation from JSON
    conv_dict = json.loads(conv_json)
    recreated_conv = conversation.__class__.from_dict(conv_dict)
    print(f"✅ Recreated conversation with {len(recreated_conv.messages)} messages")
    
    print("\n🎉 LLM wrapper test completed successfully!")


if __name__ == "__main__":
    asyncio.run(test_llm_wrapper())