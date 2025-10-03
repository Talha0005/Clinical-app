"""Evaluation utilities for training/validation metrics.

Writes JSON lines to `backend/dat/eval_metrics.jsonl` and maintains a
compact rolling summary in `backend/dat/eval_summary.json`.

Supports single-label classification metrics: accuracy, recall, F1.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Iterable, List


_DAT_DIR = Path(__file__).parent.parent / "dat"
_DAT_DIR.mkdir(parents=True, exist_ok=True)
_HISTORY = _DAT_DIR / "eval_metrics.jsonl"
_SUMMARY = _DAT_DIR / "eval_summary.json"


@dataclass
class EvalMetrics:
    accuracy: float
    recall: float  # macro recall
    f1: float  # macro f1
    total: int


def _safe_div(x: float, y: float) -> float:
    return x / y if y else 0.0


def _unique_labels(y_true: Iterable[str], y_pred: Iterable[str]) -> List[str]:
    labels = set(y_true) | set(y_pred)
    return sorted([str(lbl) for lbl in labels])


def compute_metrics(y_true: List[str], y_pred: List[str]) -> EvalMetrics:
    """Compute accuracy, macro recall and macro F1 for single-label
    classification.
    """
    n = len(y_true)
    if n == 0 or n != len(y_pred):
        return EvalMetrics(accuracy=0.0, recall=0.0, f1=0.0, total=0)

    labels = _unique_labels(y_true, y_pred)
    correct = sum(1 for t, p in zip(y_true, y_pred) if t == p)
    accuracy = _safe_div(float(correct), float(n))

    # Per-class metrics
    recalls: List[float] = []
    f1s: List[float] = []
    for lab in labels:
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == lab and p == lab)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == lab and p != lab)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t != lab and p == lab)

        prec = _safe_div(tp, tp + fp)
        rec = _safe_div(tp, tp + fn)
        f1 = _safe_div(2 * prec * rec, prec + rec) if prec or rec else 0.0

        recalls.append(rec)
        f1s.append(f1)

    macro_recall = sum(recalls) / len(recalls) if recalls else 0.0
    macro_f1 = sum(f1s) / len(f1s) if f1s else 0.0
    return EvalMetrics(accuracy=accuracy, recall=macro_recall, f1=macro_f1, total=n)


def record_evaluation(
    *,
    y_true: List[str],
    y_pred: List[str],
    model_id: str,
    dataset_name: str = "adhoc",
    actor: str = "system",
) -> Dict[str, float]:
    """Compute metrics and persist a history event and summary."""
    metrics = compute_metrics(y_true, y_pred)
    event = {
        "ts": time.time(),
        "type": "evaluation",
        "model_id": model_id,
        "dataset": dataset_name,
        "actor": actor,
        "metrics": asdict(metrics),
    }
    with _HISTORY.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")

    # Update summary: keep last and best
    summary = {
        "last": {
            "model_id": model_id,
            "dataset": dataset_name,
            "metrics": asdict(metrics),
            "ts": event["ts"],
        }
    }
    try:
        if _SUMMARY.exists():
            with _SUMMARY.open("r", encoding="utf-8") as f:
                prev = json.load(f)
            best = prev.get("best")
        else:
            best = None
    except Exception:
        best = None

    def better(a: Dict[str, float], b: Dict[str, float]) -> bool:
        # Simple dominance: prioritize F1, then accuracy, then recall
        return a.get("f1", 0.0) > b.get("f1", 0.0) or (
            a.get("f1", 0.0) == b.get("f1", 0.0)
            and (
                a.get("accuracy", 0.0) > b.get("accuracy", 0.0)
                or (
                    a.get("accuracy", 0.0) == b.get("accuracy", 0.0)
                    and a.get("recall", 0.0) > b.get("recall", 0.0)
                )
            )
        )

    if not best or better(asdict(metrics), best.get("metrics", {})):
        summary["best"] = {
            "model_id": model_id,
            "dataset": dataset_name,
            "metrics": asdict(metrics),
            "ts": event["ts"],
        }
    else:
        summary["best"] = best

    with _SUMMARY.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    return asdict(metrics)


def get_evaluation_summary() -> Dict[str, object]:
    if not _SUMMARY.exists():
        return {"last": None, "best": None}
    try:
        with _SUMMARY.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"last": None, "best": None}


def get_evaluation_history(limit: int = 100) -> List[Dict[str, object]]:
    if not _HISTORY.exists():
        return []
    rows: List[Dict[str, object]] = []
    try:
        with _HISTORY.open("r", encoding="utf-8") as f:
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


__all__ = [
    "EvalMetrics",
    "compute_metrics",
    "record_evaluation",
    "get_evaluation_summary",
    "get_evaluation_history",
]
