from __future__ import annotations
from typing import Optional, Callable
from .base import AgentContext, AgentResult
from .avatar_agent import AvatarAgent
from .history_agent import HistoryTakingAgent
from .triage_agent import SymptomTriageAgent
from .summarisation_agent import SummarisationAgent
from .clinical_reasoning_agent import ClinicalReasoningAgent
from .medical_record_agent import MedicalRecordAgent
from .coding_agent import CodingAgent
from .sentiment_risk_agent import SentimentRiskAgent
from .hitl_agent import HITLAgent
from .support_red_flag_agent import detect_red_flags
from .support_snomed_mapper import map_to_systems
from .support_nice_checker import suggest_nice_topics


LLMFunc = Callable[[list], str]  # messages -> text


class ExtendedOrchestrator:
    """Modular orchestrator including all core and support agents.

    Safe-by-default: pure-Python heuristics unless `llm` is passed in.
    Not wired into any endpoint by default.
    """

    def __init__(self) -> None:
        self.avatar = AvatarAgent()
        self.history = HistoryTakingAgent()
        self.triage = SymptomTriageAgent()
        self.reasoning = ClinicalReasoningAgent()
        self.summarise = SummarisationAgent()
        self.medrec = MedicalRecordAgent()
        self.coding = CodingAgent()
        self.risk = SentimentRiskAgent()
        self.hitl = HITLAgent()

    def handle_turn(
        self,
        user_text: str,
        *,
        ctx: Optional[AgentContext] = None,
        llm: Optional[LLMFunc] = None,
        progress_callback: Optional[Callable[[str, str], None]] = None,
    ) -> AgentResult:
        ctx = ctx or AgentContext()

        # Sentiment & risk detection (pre-pass)
        if progress_callback:
            progress_callback("sentiment_risk", "active")
        risk_res = self.risk.run(ctx, user_text, llm=llm)
        if progress_callback:
            progress_callback("sentiment_risk", "completed")

        # Avatar conversational layer
        if progress_callback:
            progress_callback("avatar", "active")
        avatar_res = self.avatar.run(ctx, user_text, llm=llm)
        if progress_callback:
            progress_callback("avatar", "completed")

        # History structured collection
        if progress_callback:
            progress_callback("history", "active")
        history_res = self.history.run(ctx, user_text, llm=llm)
        if progress_callback:
            progress_callback("history", "completed")

        # Triage (safety)
        if progress_callback:
            progress_callback("triage", "active")
        triage_res = self.triage.run(ctx, user_text, llm=llm)
        if progress_callback:
            progress_callback("triage", "completed")

        # Support subagents (rules-only)
        if progress_callback:
            progress_callback("support", "active")
        red = detect_red_flags(user_text)
        systems = map_to_systems(user_text)
        topics = suggest_nice_topics(user_text)
        if progress_callback:
            progress_callback("support", "completed")

        # Clinical reasoning
        if progress_callback:
            progress_callback("clinical_reasoning", "active")
        reasoning_res = self.reasoning.run(
            ctx,
            user_text,
            llm=llm,
            history=history_res.data,
            triage=triage_res.data,
        )
        if progress_callback:
            progress_callback("clinical_reasoning", "completed")

        # Summarisation
        if progress_callback:
            progress_callback("summarisation", "active")
        summary_res = self.summarise.run(
            ctx,
            user_text,
            llm=llm,
            triage=triage_res.data,
            history=history_res.data,
        )
        if progress_callback:
            progress_callback("summarisation", "completed")

        # Medical record assembly
        if progress_callback:
            progress_callback("medical_record", "active")
        medrec_res = self.medrec.run(
            ctx,
            user_text,
            llm=llm,
            history=history_res.data,
            triage=triage_res.data,
            reasoning=reasoning_res.data,
            summary=summary_res.data,
        )
        if progress_callback:
            progress_callback("medical_record", "completed")

        # Coding
        if progress_callback:
            progress_callback("coding", "active")
        coding_res = self.coding.run(
            ctx,
            user_text,
            llm=llm,
            summary=summary_res.data,
        )
        if progress_callback:
            progress_callback("coding", "completed")

        # Human-in-the-loop decision
        if progress_callback:
            progress_callback("hitl", "active")
        hitl_res = self.hitl.run(
            ctx,
            user_text,
            llm=llm,
            triage=triage_res.data,
            risk=risk_res.data,
        )
        if progress_callback:
            progress_callback("hitl", "completed")

        final = AgentResult(
            text=avatar_res.text,
            data={
                "risk": risk_res.data,
                "history": history_res.data,
                "triage": triage_res.data,
                "support": {
                    "red_flags": red,
                    "systems": systems,
                    "nice_topics": topics,
                },
                "reasoning": reasoning_res.data,
                "summary": summary_res.data,
                "medical_record": medrec_res.data,
                "coding": coding_res.data,
                "hitl": hitl_res.data,
            },
            avatar=avatar_res.avatar or "dr_hervix",
        )
        return final
