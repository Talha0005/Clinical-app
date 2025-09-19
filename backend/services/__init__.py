"""
Services module for DigiClinic
"""

import os
from dotenv import load_dotenv
from .chat_service import DigiClinicChatService

# Load environment variables (for local development only)
# Don't load .env in production environments like Railway
if not os.getenv('RAILWAY_ENVIRONMENT_NAME'):
    load_dotenv()
else:
    print("🚂 Railway environment detected - skipping dotenv")
    # In Railway, try refreshing the environment
    import importlib
    importlib.reload(os)

# Register Claude LLM provider
from llm.base_llm import LLMFactory
from llm.claude_llm import ClaudeLLM

LLMFactory.register_provider("claude", ClaudeLLM)

# Create chat service instance
# Check for multiple possible environment variable names
# Lazy initialization function for chat service (like get_user_password)
def get_claude_api_key() -> str:
    """Get Claude API key from environment variables at runtime."""
    print("🔍 get_claude_api_key() called - checking environment variables...")
    
    # Check ANTHROPIC_KEY
    key_value = os.getenv('ANTHROPIC_KEY')
    print(f"Checking ANTHROPIC_KEY: {'✅ FOUND' if key_value else '❌ NOT FOUND'}")
    if key_value and key_value.strip():
        print(f"✅ Found Claude API key from: ANTHROPIC_KEY")
        return key_value.strip()
    
    print("⚠️  No Claude API key found at runtime")
    return None

def get_chat_service():
    """Get chat service with lazy initialization (like password verification)."""
    print("🔧 get_chat_service() called - initializing chat service...")
    api_key = get_claude_api_key()
    
    if api_key:
        try:
            print(f"🔧 Creating DigiClinicChatService with LLM router...")
            service = DigiClinicChatService(llm_provider="router")
            print(f"✅ LLM Router initialized with API key: {api_key[:8]}...")
            print(f"🔧 Service router type: {service.llm_router.__class__.__name__ if service.llm_router else 'None'}")
            return service
        except Exception as e:
            print(f"❌ Failed to initialize LLM router: {e}")
            import traceback
            traceback.print_exc()
            print("⚠️  Falling back to legacy LLM")
            return DigiClinicChatService(llm_provider="claude", api_key=api_key)
    else:
        print("⚠️  Using mock LLM - no API key available")
        return DigiClinicChatService(llm_provider="mock")

# Initialize to None - will be created when first accessed
chat_service = None

__all__ = [
    "DigiClinicChatService",
    "get_chat_service",
    "get_claude_api_key"
]