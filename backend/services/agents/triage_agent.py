from typing import Any, Optional, List
import json
from .base import Agent, AgentContext, AgentResult
from .prompts import TRIAGE_TEMPLATE


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
        if llm is None:
            # Basic rule-based triage
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
                    "I'll keep you safe and ask a few quick checks."
                    if urgency != "routine"
                    else "Let's proceed."
                ),
                data=data,
            )
        
        # Use LLM for advanced triage
        system = TRIAGE_TEMPLATE
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": f"Assess urgency for: {user_text}"},
        ]
        
        try:
            response = llm(messages)
            data = json.loads(response)
        except (json.JSONDecodeError, Exception):
            # Fallback to rule-based triage
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
            data = {"urgency": urgency, "red_flags": red, "advice": "Please consult a healthcare professional"}
        
        return AgentResult(
            text=(
                "I'll keep you safe and ask a few quick checks."
                if data.get("urgency") != "routine"
                else "Let's proceed."
            ),
            data={
                "agent": "triage",
                "urgency": data.get("urgency", "routine"),
                "red_flags": data.get("red_flags", []),
                "advice": data.get("advice", "Please consult a healthcare professional")
            },
        )
