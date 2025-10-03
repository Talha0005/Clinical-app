"""Audit logging utilities for compliance-sensitive actions.

Writes JSON lines to `backend/dat/audit.jsonl` with a minimal schema:
{ ts, actor, type, target, details }
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional


_DAT_DIR = Path(__file__).parent.parent / "dat"
_DAT_DIR.mkdir(parents=True, exist_ok=True)
_AUDIT_FILE = _DAT_DIR / "audit.jsonl"


def log_audit(
    *,
    actor: str,
    event_type: str,
    target: str,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    payload = {
        "ts": time.time(),
        "actor": actor or "unknown",
        "type": event_type,
        "target": target,
        "details": details or {},
    }
    with _AUDIT_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def read_audit(limit: int = 200) -> list[dict[str, Any]]:
    if not _AUDIT_FILE.exists():
        return []
    rows: list[dict[str, Any]] = []
    try:
        with _AUDIT_FILE.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    rows.append(json.loads(line))
                except Exception:
                    continue
        return rows[-limit:]
    except Exception:
        return []


__all__ = ["log_audit", "read_audit"]
