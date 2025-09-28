"""Agentic orchestration scaffolding for MVP.

Safe-by-default: importing these modules does not change runtime behavior.
Wire into your endpoints only when ready (e.g., behind AGENTS_ENABLED).
"""

from .base import AgentContext, AgentResult, Agent  # noqa: F401
from .orchestrator import Orchestrator  # noqa: F401
from .avatar_agent import AvatarAgent  # noqa: F401
from .history_agent import HistoryTakingAgent  # noqa: F401
from .triage_agent import SymptomTriageAgent  # noqa: F401
from .summarisation_agent import SummarisationAgent  # noqa: F401
