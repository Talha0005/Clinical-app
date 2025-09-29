from __future__ import annotations
from typing import Any, Optional, Dict, List
from .base import Agent, AgentContext, AgentResult
# Template available in prompts; heuristics here do not directly use it.


class CodingAgent(Agent):
    name = "coding"

    def run(
        self,
        ctx: AgentContext,
        user_text: str,
        *,
        llm: Optional[Any] = None,
        summary: Optional[Dict] = None,
    ) -> AgentResult:
        # Simple heuristic mapping for MVP
        text_l = user_text.lower()
        snomed: List[str] = []
        icd10: List[str] = []
        if "chest pain" in text_l:
            snomed.append("29857009")  # Chest pain
            icd10.append("R07.9")
        if "headache" in text_l:
            snomed.append("25064002")  # Headache
            icd10.append("R51")

        data = {"snomed_ct": snomed, "icd10": icd10}
        return AgentResult(text="Preliminary codes suggested.", data=data)
