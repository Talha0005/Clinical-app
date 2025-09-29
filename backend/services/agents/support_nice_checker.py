from __future__ import annotations
from typing import Dict, Any, List
# Template available in prompts; rules used inline here.


TOPIC_HINTS = {
    "chest pain": ["Chest pain - assessment", "ACS"],
    "headache": ["Headaches in over 12s"],
    "cough": ["Cough (acute)", "COPD exacerbations"],
}


def suggest_nice_topics(text: str) -> Dict[str, Any]:
    tl = text.lower()
    topics: List[str] = []
    for key, vals in TOPIC_HINTS.items():
        if key in tl:
            topics.extend(vals)
    return {"topics": sorted(set(topics))}
