from typing import Optional, Callable
from .base import AgentContext, AgentResult
from .avatar_agent import AvatarAgent
from .history_agent import HistoryTakingAgent
from .triage_agent import SymptomTriageAgent
from .summarisation_agent import SummarisationAgent


LLMFunc = Callable[[list], str]  # messages -> text


class Orchestrator:
    """
    Minimal orchestrator for MVP chain:
    Avatar → History Taking → Symptom Triage → Summarisation
    """

    def __init__(self) -> None:
        self.avatar = AvatarAgent()
        self.history = HistoryTakingAgent()
        self.triage = SymptomTriageAgent()
        self.summarise = SummarisationAgent()

    def handle_turn(
        self,
        user_text: str,
        *,
        ctx: Optional[AgentContext] = None,
        llm: Optional[LLMFunc] = None,
        progress_callback: Optional[Callable[[str, str], None]] = None,
    ) -> AgentResult:
        ctx = ctx or AgentContext()

        # 1) Avatar phrasing (conversational layer)
        if progress_callback:
            progress_callback("avatar", "active")
        avatar_res = self.avatar.run(ctx, user_text, llm=llm)
        if progress_callback:
            progress_callback("avatar", "completed")

        # 2) History collection (structured)
        if progress_callback:
            progress_callback("history", "active")
        history_res = self.history.run(ctx, user_text, llm=llm)
        if progress_callback:
            progress_callback("history", "completed")

        # 3) Triage (safety-first)
        if progress_callback:
            progress_callback("triage", "active")
        triage_res = self.triage.run(ctx, user_text, llm=llm)
        if progress_callback:
            progress_callback("triage", "completed")

        # 4) Summarisation (patient + clinician outputs)
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

        # Compose final result: use Avatar text (empathetic) with summary meta
        final = AgentResult(
            text=avatar_res.text,
            data={
                "history": history_res.data,
                "triage": triage_res.data,
                "summary": summary_res.data,
            },
            avatar=avatar_res.avatar or "dr_hervix",
        )
        return final
