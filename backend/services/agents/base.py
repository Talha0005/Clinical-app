from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol


@dataclass
class AgentContext:
    """Shared per-turn context passed to all agents.

    Extend later with user profile, auth, locale, session state, etc.
    """

    user_id: str = "anonymous"
    locale: str = "en-GB"
    tone: str = "empathetic"
    region: str = "UK"
    session_vars: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResult:
    """Output from an agent.

    text: Natural language intended for the user
        (may be empty for non-conversational agents).
    data: Structured payload (JSON-like) for downstream agents or UI.
    next_actions: Suggestions for the orchestrator (optional).
    avatar: Optional avatar id for UI.
    """

    text: str
    data: Dict[str, Any] = field(default_factory=dict)
    next_actions: List[Dict[str, Any]] = field(default_factory=list)
    avatar: Optional[str] = None


class Agent(Protocol):
    name: str

    def run(
        self,
        ctx: AgentContext,
        user_text: str,
        *,
        llm: Optional[Any] = None,
    ) -> AgentResult: ...
