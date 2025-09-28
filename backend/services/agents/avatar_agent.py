from typing import Any, Optional
from .base import Agent, AgentContext, AgentResult
from .prompts import AVATAR_TEMPLATE


class AvatarAgent(Agent):
    name = "avatar"

    def run(
        self,
        ctx: AgentContext,
        user_text: str,
        *,
        llm: Optional[Any] = None,
    ) -> AgentResult:
        # Scaffold mode: return safe, empathetic text
        # if no LLM adapter is provided
        if llm is None:
            return AgentResult(
                text=(
                    "Thanks for sharing. I understand this may be concerning. "
                    "Could you tell me more about when this started "
                    "and how severe it is?"
                ),
                data={"note": "avatar_scaffold", "echo": user_text},
                avatar="dr_hervix",
            )

        system = AVATAR_TEMPLATE.format(
            tone=ctx.tone, region=ctx.region, locale=ctx.locale
        )
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user_text},
        ]
        reply = llm(messages)  # llm must return plain text
        return AgentResult(text=reply, data={}, avatar="dr_hervix")
