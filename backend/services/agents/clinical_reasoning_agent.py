from __future__ import annotations
from typing import Any, Optional, Dict, List
from .base import Agent, AgentContext, AgentResult
from .prompts import CLINICAL_REASONING_TEMPLATE


class ClinicalReasoningAgent(Agent):
    """Builds differential diagnosis and suggests next steps.

    Rule-based MVP if no LLM is provided; otherwise can be wired to an LLM.
    """

    name = "clinical_reasoning"

    def run(
        self,
        ctx: AgentContext,
        user_text: str,
        *,
        llm: Optional[Any] = None,
        history: Optional[Dict] = None,
        triage: Optional[Dict] = None,
    ) -> AgentResult:
        if llm is None:
            # Minimal deterministic heuristic
            text_l = user_text.lower()
            differentials: List[str] = []
            if "chest pain" in text_l:
                differentials = [
                    "Musculoskeletal chest pain",
                    "Gastro-oesophageal reflux",
                    "Cardiac ischaemia (rule out)",
                ]
            elif "headache" in text_l:
                differentials = [
                    "Tension-type headache",
                    "Migraine",
                    "Medication overuse headache",
                ]
            elif "cough" in text_l:
                differentials = [
                    "Viral URTI",
                    "Asthma exacerbation",
                    "COPD exacerbation",
                ]
            else:
                differentials = ["Non-specific symptoms; needs more data"]

            advice = (
                "Consider basic observations; safety-net and review if "
                "worsening."
            )
            if (triage or {}).get("urgency") == "emergency":
                advice = "Immediate escalation to emergency services."

            data = {
                "differential": differentials,
                "next_steps": {
                    "questions": ["onset", "duration", "severity", "triggers"],
                    "observations": ["temperature", "pulse", "BP", "SpO2"],
                    "investigations": [],
                },
                "triage": triage or {},
                "history": history or {},
                "advice": advice,
            }
            return AgentResult(
                text="I'll consider a few possibilities.",
                data=data,
            )

        # LLM-enabled pathway (not used by default)
        messages = [
            {"role": "system", "content": CLINICAL_REASONING_TEMPLATE},
            {
                "role": "user",
                "content": (
                    f"Build differentials for: {user_text}\n"
                    f"History: {history}\nTriage: {triage}"
                ),
            },
        ]
        try:
            content = llm(messages)
            # Expecting natural language; keep in data for transparency
            return AgentResult(
                text="I've outlined possible causes and next steps.",
                data={
                    "llm_summary": content,
                    "history": history or {},
                    "triage": triage or {},
                },
            )
        except Exception:
            return AgentResult(
                text=(
                    "Unable to run advanced reasoning; "
                    "falling back to safety."
                ),
                data={"error": "llm_failed"},
            )
