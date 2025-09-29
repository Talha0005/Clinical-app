import sys
from pathlib import Path
import asyncio

# Ensure backend root on path
backend_root = Path(__file__).parents[2]
sys.path.insert(0, str(backend_root))

from services.direct_llm_service import direct_llm_service  # noqa: E402


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
