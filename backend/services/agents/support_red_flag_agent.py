from __future__ import annotations
from typing import Dict, Any
# Template available in prompts; rules used inline here.


RED_FLAGS = [
    "chest pain",
    "shortness of breath",
    "severe headache",
    "confusion",
    "fainting",
    "bleeding",
    "suicidal",
    "stroke",
]


def detect_red_flags(text: str) -> Dict[str, Any]:
    tl = text.lower()
    hits = [rf for rf in RED_FLAGS if rf in tl]
    urgency = "routine"
    if "chest pain" in tl or ("shortness of breath" in tl and "pain" in tl):
        urgency = "emergency"
    elif hits:
        urgency = "urgent"
    return {"urgency": urgency, "red_flags": hits}
