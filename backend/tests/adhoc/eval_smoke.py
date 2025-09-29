"""Minimal evaluation smoke test.

Generates a couple of synthetic prompts representing chronic and acute cases
and records latency/tokens via the dev metrics logger.
"""

import asyncio
from services.direct_llm_service import direct_llm_service


async def main():
    cases = [
        (
            "chronic",
            "I have type 2 diabetes and hypertension. How should I manage my medications?",
        ),
        ("acute", "I have sudden chest pain and shortness of breath."),
    ]
    for label, msg in cases:
        res = await direct_llm_service.generate_response(
            messages=[{"role": "user", "content": msg}],
            model_preference="anthropic",
            conversation_id=f"eval-{label}",
        )
        print(label, res.get("model_used"), len((res.get("content") or "")))


if __name__ == "__main__":
    asyncio.run(main())
