from __future__ import annotations
from typing import Any, Optional, Dict
from .base import Agent, AgentContext, AgentResult
from .prompts import HITL_TEMPLATE


class HITLAgent(Agent):
    name = "hitl"

    def run(
        self,
        ctx: AgentContext,
        user_text: str,
        *,
        llm: Optional[Any] = None,
        triage: Optional[Dict] = None,
        risk: Optional[Dict] = None,
    ) -> AgentResult:
        route = False
        reason = ""
        if (triage or {}).get("urgency") in {"urgent", "emergency"}:
            route = True
            reason = "clinical_urgency"
        if (risk or {}).get("risk_level") in {"moderate", "high"}:
            route = True
            reason = reason or "sentiment_risk"

        handover = {
            "summary": user_text[:200],
            "urgency": (triage or {}).get("urgency", "unknown"),
            "risk": (risk or {}).get("risk_level", "low"),
        }
        data = {
            "route_to_human": bool(route),
            "needs_review": bool(route),  # alias for convenience
            "reason": reason,
            "handover": handover,
        }
        text = (
            "Routing to a human clinician for review."
            if route
            else "No human review required now."
        )
        return AgentResult(text=text, data=data)
