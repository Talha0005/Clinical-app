from typing import Any, Optional, Dict
from .base import Agent, AgentContext, AgentResult


class SummarisationAgent(Agent):
    name = "summarisation"

    def run(
        self,
        ctx: AgentContext,
        user_text: str,
        *,
        llm: Optional[Any] = None,
        triage: Optional[Dict] = None,
        history: Optional[Dict] = None,
    ) -> AgentResult:
        # Minimal deterministic summary for MVP without LLM
        urgency = (triage or {}).get("urgency", "routine")
        red_flags = (triage or {}).get("red_flags", [])
        patient_summary = (
            "I understand your concerns. We'll summarise "
            "and keep safety in mind."
        )
        clinician_note = {
            "summary": user_text[:200],
            "urgency": urgency,
            "recommendation": (
                "Escalate to clinician"
                if urgency != "routine"
                else "Routine care"
            ),
            "codes": {"snomed_ct": "", "icd10": ""},
        }
        # Optionally add simple demo codes if chest pain detected
        tl = user_text.lower()
        if "chest pain" in tl:
            clinician_note["codes"]["snomed_ct"] = "29857009"  # chest pain
            clinician_note["codes"]["icd10"] = "R07.9"

        data = {
            "patient_summary": patient_summary,
            "clinician_note": clinician_note,
            "red_flags": red_flags,
            "history": history or {},
        }
        return AgentResult(text=patient_summary, data=data)
