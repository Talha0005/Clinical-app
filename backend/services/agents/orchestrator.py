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
    ) -> AgentResult:
        ctx = ctx or AgentContext()

        # 1) Avatar phrasing (conversational layer)
        avatar_res = self.avatar.run(ctx, user_text, llm=llm)

        # 2) History collection (structured)
        history_res = self.history.run(ctx, user_text, llm=None)

        # 3) Triage (safety-first)
        triage_res = self.triage.run(ctx, user_text, llm=None)

        # 4) Summarisation (patient + clinician outputs)
        summary_res = self.summarise.run(
            ctx,
            user_text,
            llm=None,
            triage=triage_res.data,
            history=history_res.data,
        )

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
