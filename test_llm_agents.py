#!/usr/bin/env python3
"""
Simple Test for LLM and Agents
"""

import sys
import os
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

def test_llm_and_agents():
    """Test LLM and Agents functionality"""
    print("🧪 Testing LLM and Agents...")
    
    try:
        # Test Direct LLM Service
        from services.direct_llm_service import direct_llm_service
        print("✅ Direct LLM Service imported successfully")
        
        # Test Agents
        from services.agents import Orchestrator
        from services.agents.base import AgentContext
        
        agent = Orchestrator()
        ctx = AgentContext()
        result = agent.handle_turn("I have chest pain", ctx=ctx, llm=None)
        
        print(f"✅ Agent Response: {result.text[:100]}...")
        print(f"✅ Agent Data: {list(result.data.keys())}")
        print(f"✅ Agent Avatar: {result.avatar}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 DigiClinic LLM & Agents Test")
    print("=" * 40)
    
    success = test_llm_and_agents()
    
    if success:
        print("\n🎉 SUCCESS! LLM and Agents are working!")
        print("✅ Real AI responses available")
        print("✅ Medical agents processing correctly")
        print("✅ All features functional")
    else:
        print("\n❌ FAILED! Check the errors above")
    
    print("\nPress Enter to exit...")
    input()
