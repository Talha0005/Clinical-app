#!/usr/bin/env python3
"""
Test script for agent service
"""

import asyncio
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from services.agents import Orchestrator, AgentContext
from services.direct_llm_service import direct_llm_service


async def test_agent():
    print("Testing agent service...")

    # Create LLM wrapper
    def llm_wrapper(messages):
        try:
            print(f"LLM wrapper called with {len(messages)} messages")
            # Run in a separate thread to avoid event loop conflicts
            import threading

            result = [None]
            exception = [None]

            def run_llm():
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        response = loop.run_until_complete(
                            direct_llm_service.generate_response(
                                messages=messages, model_preference="anthropic"
                            )
                        )
                        result[0] = response
                    finally:
                        loop.close()
                except Exception as e:
                    exception[0] = e

            thread = threading.Thread(target=run_llm)
            thread.start()
            thread.join()

            if exception[0]:
                raise exception[0]

            response = result[0]
            content = response.get("content", "Fallback response")
            print(f"LLM response: {content[:100]}...")
            return content
        except Exception as e:
            print(f"LLM wrapper failed: {e}")
            return "Fallback response"

    # Test orchestrator
    try:
        orch = Orchestrator()
        agent_out = orch.handle_turn(
            "Hello, I have a headache",
            ctx=AgentContext(user_id="test_user"),
            llm=llm_wrapper,
        )

        print(
            f'Agent response: {agent_out.text[:100] if agent_out.text else "None"}...'
        )
        return True
    except Exception as e:
        print(f"Agent test failed: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_agent())
    if success:
        print("✅ Agent test passed")
    else:
        print("❌ Agent test failed")
