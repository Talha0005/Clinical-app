from __future__ import annotations
from typing import Dict, Any, List
# Template available in prompts; rules used inline here.


SYSTEM_MAP = {
    "chest": "cardiovascular/respiratory",
    "headache": "neurology",
    "cough": "respiratory",
    "stomach": "gastrointestinal",
}


def map_to_systems(text: str) -> Dict[str, Any]:
    tl = text.lower()
    systems: List[str] = []
    for key, system in SYSTEM_MAP.items():
        if key in tl:
            systems.append(system)
    return {"systems": sorted(set(systems))}
