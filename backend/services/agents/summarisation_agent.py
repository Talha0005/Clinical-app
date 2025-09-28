from typing import Any, Optional, Dict
import json
from .base import Agent, AgentContext, AgentResult
from .prompts import SUMMARISATION_TEMPLATE


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
        if llm is None:
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
        
        # Use LLM for comprehensive summarisation
        system = SUMMARISATION_TEMPLATE
        context = f"""
        User Input: {user_text}
        History: {json.dumps(history or {}, indent=2)}
        Triage: {json.dumps(triage or {}, indent=2)}
        """
        
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": f"Create summary for: {context}"},
        ]
        
        try:
            response = llm(messages)
            data = json.loads(response)
        except (json.JSONDecodeError, Exception):
            # Fallback to basic summary
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
            data = {
                "patient_summary": patient_summary,
                "clinician_note": clinician_note,
                "red_flags": red_flags,
                "history": history or {},
            }
        
        return AgentResult(
            text=data.get("patient_summary", "Summary completed."),
            data={
                "agent": "summarisation",
                "patient_summary": data.get("patient_summary", ""),
                "clinician_note": data.get("clinician_note", {}),
                "red_flags": data.get("red_flags", []),
                "history": history or {},
                "urgency": data.get("clinician_note", {}).get("urgency", "routine")
            }
        )
