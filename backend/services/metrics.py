"""Lightweight metrics logger for development.

Writes JSON lines to `backend/dat/metrics.jsonl` so we can inspect token
usage, latency and model selection over time without external services.
"""

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional


_DAT_DIR = Path(__file__).parent.parent / "dat"
_DAT_DIR.mkdir(parents=True, exist_ok=True)
_LOG_FILE = _DAT_DIR / "metrics.jsonl"


def _write_line(payload: Dict[str, Any]) -> None:
    payload["ts"] = time.time()
    with _LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def log_llm_interaction(
    *,
    conversation_id: str,
    model_used: str,
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
    latency_ms: float,
    truncated: bool = False,
    notes: Optional[str] = None,
) -> None:
    _write_line(
        {
            "type": "llm_interaction",
            "conversation_id": conversation_id,
            "model_used": model_used,
            "prompt_tokens": int(prompt_tokens or 0),
            "completion_tokens": int(completion_tokens or 0),
            "total_tokens": int(total_tokens or 0),
            "latency_ms": float(latency_ms or 0.0),
            "truncated": bool(truncated),
            "notes": notes or "",
        }
    )


def log_event(event_type: str, data: Dict[str, Any]) -> None:
    payload = {"type": event_type}
    payload.update(data)
    _write_line(payload)


__all__ = ["log_llm_interaction", "log_event"]
