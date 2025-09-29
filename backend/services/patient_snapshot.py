"""
Utilities to build a compact patient snapshot string suitable for prompt
context. Uses the existing `MockPatientDB` for development.
"""

from typing import Optional

from db.mock_patient_db import MockPatientDB
from .db_sqlite import get_patient_snapshot_by_ni
from model.patient import Patient


def build_patient_snapshot(patient: Patient) -> str:
    has_history = bool(patient.medical_history)
    problems = ", ".join(patient.medical_history) if has_history else "None recorded"
    has_meds = bool(patient.current_medications)
    meds = ", ".join(patient.current_medications) if has_meds else "None recorded"
    age_text = f", age {patient.age}" if patient.age is not None else ""
    return (
        f"Patient: {patient.name}{age_text} "
        f"(NI: {patient.national_insurance})\n"
        f"Active problems: {problems}\n"
        f"Current medications: {meds}"
    )


def build_patient_snapshot_by_ni(national_insurance: str) -> Optional[str]:
    # Prefer SQLite if available
    snap = get_patient_snapshot_by_ni(national_insurance)
    if snap:
        return snap
    db = MockPatientDB()
    try:
        patients = db.load_patients()
    except Exception:
        return None
    for p in patients:
        if p.national_insurance == national_insurance:
            return build_patient_snapshot(p)
    return None


def get_any_patient_snapshot() -> Optional[str]:
    """Return snapshot for any patient in DB (useful for demos)."""
    db = MockPatientDB()
    try:
        patients = db.load_patients()
        if not patients:
            return None
        return build_patient_snapshot(patients[0])
    except Exception:
        return None


__all__ = [
    "build_patient_snapshot",
    "build_patient_snapshot_by_ni",
    "get_any_patient_snapshot",
]
