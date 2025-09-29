from __future__ import annotations
from typing import Any, Optional, Dict, List
from .base import Agent, AgentContext, AgentResult
from .prompts import SENTIMENT_RISK_TEMPLATE


RISK_KEYWORDS = [
    "suicidal", "kill myself", "end my life", "self-harm", "abuse",
    "violence", "unsafe", "panic", "hopeless"
]


class SentimentRiskAgent(Agent):
    name = "sentiment_risk"

    def run(
        self,
        ctx: AgentContext,
        user_text: str,
        *,
        llm: Optional[Any] = None,
    ) -> AgentResult:
        tl = user_text.lower()
        signals: List[str] = [kw for kw in RISK_KEYWORDS if kw in tl]
        risk = "low"
        if any(k in tl for k in ["suicidal", "kill myself", "end my life"]):
            risk = "high"
        elif any(k in tl for k in ["panic", "unsafe", "abuse", "violence"]):
            risk = "moderate"

        actions: List[str] = []
        if risk == "high":
            actions = ["escalate", "offer_support", "slow_down"]
        elif risk == "moderate":
            actions = ["offer_support", "slow_down"]
        else:
            actions = ["continue"]

        data: Dict[str, Any] = {
            "risk_level": risk,
            "signals": signals,
            "actions": actions,
        }
        text = (
            "I'm here to support you. If you're in immediate danger, call 999."
            if risk != "low"
            else "I'll proceed at your pace."
        )
        return AgentResult(text=text, data=data)
