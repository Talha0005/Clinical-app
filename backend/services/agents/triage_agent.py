from typing import Any, Optional, List
from .base import Agent, AgentContext, AgentResult


RED_FLAG_TERMS: List[str] = [
    "chest pain",
    "shortness of breath",
    "severe headache",
    "confusion",
    "fainting",
    "bleeding",
    "suicidal",
    "stroke",
    "heart attack",
]


class SymptomTriageAgent(Agent):
    name = "triage"

    def run(
        self,
        ctx: AgentContext,
        user_text: str,
        *,
        llm: Optional[Any] = None,
    ) -> AgentResult:
        tl = user_text.lower()
        red = [t for t in RED_FLAG_TERMS if t in tl]
        urgency = "routine"
        if (
            "chest pain" in tl
            or ("shortness of breath" in tl and "pain" in tl)
        ):
            urgency = "emergency"
        elif red:
            urgency = "urgent"
        data = {"urgency": urgency, "red_flags": red}
        return AgentResult(
            text=(
                "I’ll keep you safe and ask a few quick checks."
                if urgency != "routine"
                else "Let’s proceed."
            ),
            data=data,
        )
