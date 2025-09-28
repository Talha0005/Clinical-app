from typing import Any, Optional
from .base import Agent, AgentContext, AgentResult


class HistoryTakingAgent(Agent):
    name = "history"

    def run(
        self,
        ctx: AgentContext,
        user_text: str,
        *,
        llm: Optional[Any] = None,
    ) -> AgentResult:
        # Lightweight scaffold: extract minimal items without LLM
        txt = user_text.lower()
        data = {
            "presenting_complaint": user_text,
            "history_of_presenting_complaint": "",
            "red_flags": [],
            "pmh": "",
            "drugs": "",
            "allergies": "",
            "family_history": "",
            "social_history": "",
            "ros": [],
        }
        if "day" in txt or "week" in txt:
            data["history_of_presenting_complaint"] = "Duration mentioned."
        return AgentResult(
            text="I'll capture a few history points.",
            data={"history": data},
        )
