from typing import Any, Optional
import json
from .base import Agent, AgentContext, AgentResult
from .prompts import HISTORY_TEMPLATE


class HistoryTakingAgent(Agent):
    name = "history"

    def run(
        self,
        ctx: AgentContext,
        user_text: str,
        *,
        llm: Optional[Any] = None,
    ) -> AgentResult:
        if llm is None:
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

        # Use LLM to extract structured history
        system = HISTORY_TEMPLATE
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": f"Extract medical history from: {user_text}"},
        ]

        try:
            response = llm(messages)
            # Try to parse JSON response
            data = json.loads(response)
        except (json.JSONDecodeError, Exception):
            # Fallback to scaffold if JSON parsing fails
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
            text="Medical history captured.",
            data={
                "agent": "history",
                "history": data,
                "extracted_symptoms": data.get("presenting_complaint", user_text),
            },
        )
