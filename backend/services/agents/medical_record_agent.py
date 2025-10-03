from __future__ import annotations
from typing import Any, Optional, Dict
from .base import Agent, AgentContext, AgentResult
# Template available in prompts; heuristics here do not directly use it.


class MedicalRecordAgent(Agent):
    name = "medical_record"

    def run(
        self,
        ctx: AgentContext,
        user_text: str,
        *,
        llm: Optional[Any] = None,
        history: Optional[Dict] = None,
        triage: Optional[Dict] = None,
        reasoning: Optional[Dict] = None,
        summary: Optional[Dict] = None,
    ) -> AgentResult:
        # Minimal structured JSON assembly for MVP + FHIR Bundle
        ehr_json = {
            "patient": {"reference": "Patient/demo"},
            "encounter": {"type": "virtual", "region": ctx.region},
            "history": history or {},
            "triage": triage or {},
            "reasoning": reasoning or {},
            "summary": summary or {},
        }

        # Create a minimal FHIR Bundle (not fully compliant but structured)
        fhir_bundle = {
            "resourceType": "Bundle",
            "type": "collection",
            "entry": [
                {
                    "resource": {
                        "resourceType": "Patient",
                        "id": "demo",
                    }
                },
                {
                    "resource": {
                        "resourceType": "Encounter",
                        "status": "finished",
                        "class": {"code": "VR", "display": "Virtual"},
                    }
                },
                {
                    "resource": {
                        "resourceType": "Composition",
                        "status": "final",
                        "type": {"text": "Clinical Note (SOAP/SBAR)"},
                        "subject": {"reference": "Patient/demo"},
                        "section": [
                            {
                                "title": "Subjective",
                                "text": {
                                    "status": "generated",
                                    "div": (summary or {}).get(
                                        "patient_friendly"
                                    ),
                                },
                            },
                            {
                                "title": "Objective",
                                "text": {
                                    "status": "generated",
                                    "div": (triage or {}).get("findings"),
                                },
                            },
                            {
                                "title": "Assessment",
                                "text": {
                                    "status": "generated",
                                    "div": (reasoning or {}).get(
                                        "differentials"
                                    ),
                                },
                            },
                            {
                                "title": "Plan",
                                "text": {
                                    "status": "generated",
                                    "div": (summary or {}).get("next_steps"),
                                },
                            },
                        ],
                    }
                },
            ],
        }

        record = {"ehr": ehr_json, "fhir": fhir_bundle}
        return AgentResult(text="Structured record prepared.", data=record)
