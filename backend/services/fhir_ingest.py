"""
FHIR ingest utilities for importing Synthea-generated bundles into the app's
mock patient database (`backend/dat/patient-db.json`).

The ingest focuses on a compact subset needed by the prototype:
- Patient → name, age (derived from birthDate), synthetic National Insurance
- Condition → medical_history (problem list)
- MedicationRequest → current_medications

Usage (programmatic):
    from services.fhir_ingest import ingest_directory_to_mock_db
    ingest_directory_to_mock_db(input_dir=Path("data/synthea/2025-09-29"))

Notes:
- Synthea uses US-centric identifiers; we mint a deterministic synthetic
  National Insurance number based on the Synthea Patient.id so the
  existing `Patient` model constraints are satisfied.
- This module avoids adding new third-party deps; it parses JSON directly.
"""

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from model.patient import Patient
from db.mock_patient_db import MockPatientDB
from .db_sqlite import get_connection, init_schema, upsert_patient


def _safe_read_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _derive_age(birth_date: Optional[str]) -> Optional[int]:
    if not birth_date:
        return None
    try:
        # Synthea uses YYYY-MM-DD
        dob = datetime.strptime(birth_date[:10], "%Y-%m-%d").date()
        today = datetime.utcnow().date()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        return max(0, min(120, age))
    except Exception:
        return None


def _mint_synthetic_ni_from_id(patient_id: str) -> str:
    """
    Create a UK-like National Insurance number that passes the existing
    regex (XX123456X). Not real; derived deterministically from Patient.id.
    """
    # Extract alphanumerics and take a hashy slice for digits
    base = re.sub(r"[^A-Za-z0-9]", "", patient_id or "SYNTHEA")
    letters = (base[:2].upper() + "AB")[:2]
    digits = ("".join(str((ord(c) % 10)) for c in base) + "000000")[:6]
    suffix = base[-1:].upper() or "Z"
    if not letters.isalpha():
        letters = "AA"
    if not suffix.isalpha():
        suffix = "Z"
    return f"{letters}{digits}{suffix}"


@dataclass
class _PatientAccumulator:
    name: str = ""
    national_insurance: str = ""
    age: Optional[int] = None
    medical_history: List[str] = field(default_factory=list)
    current_medications: List[str] = field(default_factory=list)


def _accumulate_from_bundle(bundle: Dict[str, Any]) -> List[Patient]:
    if not bundle or bundle.get("resourceType") != "Bundle":
        return []

    # Map patient id -> accumulator
    acc: Dict[str, _PatientAccumulator] = {}

    entries = bundle.get("entry", [])
    for item in entries:
        resource = item.get("resource", {})
        rtype = resource.get("resourceType")

        if rtype == "Patient":
            pid = resource.get("id") or resource.get("identifier", [{}])[0].get(
                "value", "synthea"
            )
            name_parts = resource.get("name", [{}])[0]
            full_name = (
                " ".join(
                    filter(
                        None,
                        [
                            (name_parts.get("given") or [None])[0],
                            name_parts.get("family"),
                        ],
                    )
                ).strip()
                or "Synthea Patient"
            )
            birth_date = resource.get("birthDate")
            acc[pid] = _PatientAccumulator(
                name=full_name,
                national_insurance=_mint_synthetic_ni_from_id(pid),
                age=_derive_age(birth_date),
            )

        elif rtype == "Condition":
            patient_ref = (resource.get("subject", {}) or {}).get("reference", "")
            # Expecting format "Patient/{id}"
            pid = patient_ref.split("/")[-1] if "/" in patient_ref else patient_ref
            if not pid:
                continue
            if pid not in acc:
                acc[pid] = _PatientAccumulator(
                    name="Synthea Patient",
                    national_insurance=_mint_synthetic_ni_from_id(pid),
                )
            text = (resource.get("code", {}) or {}).get("text") or (
                resource.get("code", {}) or {}
            ).get("coding", [{}])[0].get("display")
            if text and text not in acc[pid].medical_history:
                acc[pid].medical_history.append(text)

        elif rtype == "MedicationRequest":
            patient_ref = (resource.get("subject", {}) or {}).get("reference", "")
            pid = patient_ref.split("/")[-1] if "/" in patient_ref else patient_ref
            if not pid:
                continue
            if pid not in acc:
                acc[pid] = _PatientAccumulator(
                    name="Synthea Patient",
                    national_insurance=_mint_synthetic_ni_from_id(pid),
                )
            med = (resource.get("medicationCodeableConcept", {}) or {}).get("text") or (
                resource.get("medicationCodeableConcept", {}) or {}
            ).get("coding", [{}])[0].get("display")
            if med and med not in acc[pid].current_medications:
                acc[pid].current_medications.append(med)

    patients: List[Patient] = []
    for _pid, data in acc.items():
        try:
            patients.append(
                Patient(
                    name=data.name or "Synthea Patient",
                    national_insurance=data.national_insurance,
                    age=data.age,
                    medical_history=data.medical_history,
                    current_medications=data.current_medications,
                )
            )
        except Exception:
            # Skip invalid entries silently for robustness in dev
            continue

    return patients


def ingest_directory_to_mock_db(
    input_dir: Path, output_db: Optional[Path] = None
) -> int:
    """
    Read all JSON files under `input_dir` (recursively), collect FHIR data and
    merge patients into the mock DB. Supports:
    - FHIR Bundles (Synthea transaction bundles)
    - Individual FHIR resources (Patient, Condition, MedicationRequest)
    Returns number of patients written.
    """
    input_dir = Path(input_dir)
    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")

    bundles: List[Dict[str, Any]] = []
    loose_resources: List[Dict[str, Any]] = []
    for path in input_dir.rglob("*.json"):
        data = _safe_read_json(path)
        if not data or not isinstance(data, dict):
            continue
        rtype = data.get("resourceType")
        if rtype == "Bundle":
            bundles.append(data)
        elif rtype in {"Patient", "Condition", "MedicationRequest"}:
            loose_resources.append(data)

    # Accumulate patients from all resources
    merged: Dict[str, Patient] = {}
    if bundles:
        for bundle in bundles:
            pts = _accumulate_from_bundle(bundle)
            for p in pts:
                merged[p.national_insurance] = p
    if loose_resources:
        # Reuse the same accumulator logic over a synthetic entry list
        acc: Dict[str, _PatientAccumulator] = {}
        for resource in loose_resources:
            rtype = resource.get("resourceType")
            if rtype == "Patient":
                pid = resource.get("id") or (resource.get("identifier", [{}])[0]).get(
                    "value", "synthea"
                )
                name_parts = (resource.get("name") or [{}])[0]
                full_name = (
                    " ".join(
                        filter(
                            None,
                            [
                                (name_parts.get("given") or [None])[0],
                                name_parts.get("family"),
                            ],
                        )
                    ).strip()
                    or "Synthea Patient"
                )
                acc[pid] = _PatientAccumulator(
                    name=full_name,
                    national_insurance=_mint_synthetic_ni_from_id(pid),
                    age=_derive_age(resource.get("birthDate")),
                )
            elif rtype == "Condition":
                patient_ref = (resource.get("subject", {}) or {}).get("reference", "")
                pid = patient_ref.split("/")[-1] if "/" in patient_ref else patient_ref
                if not pid:
                    continue
                if pid not in acc:
                    acc[pid] = _PatientAccumulator(
                        name="Synthea Patient",
                        national_insurance=_mint_synthetic_ni_from_id(pid),
                    )
                text = (resource.get("code", {}) or {}).get("text") or (
                    resource.get("code", {}) or {}
                ).get("coding", [{}])[0].get("display")
                if text and text not in acc[pid].medical_history:
                    acc[pid].medical_history.append(text)
            elif rtype == "MedicationRequest":
                patient_ref = (resource.get("subject", {}) or {}).get("reference", "")
                pid = patient_ref.split("/")[-1] if "/" in patient_ref else patient_ref
                if not pid:
                    continue
                if pid not in acc:
                    acc[pid] = _PatientAccumulator(
                        name="Synthea Patient",
                        national_insurance=_mint_synthetic_ni_from_id(pid),
                    )
                med = (resource.get("medicationCodeableConcept", {}) or {}).get(
                    "text"
                ) or (resource.get("medicationCodeableConcept", {}) or {}).get(
                    "coding", [{}]
                )[
                    0
                ].get(
                    "display"
                )
                if med and med not in acc[pid].current_medications:
                    acc[pid].current_medications.append(med)

        for _pid, data in acc.items():
            try:
                merged[data.national_insurance] = Patient(
                    name=data.name or "Synthea Patient",
                    national_insurance=data.national_insurance,
                    age=data.age,
                    medical_history=data.medical_history,
                    current_medications=data.current_medications,
                )
            except Exception:
                continue

    # Load existing DB and merge
    db = MockPatientDB(db_path=output_db) if output_db else MockPatientDB()
    try:
        existing = {p.national_insurance: p for p in db.load_patients()}
    except Exception:
        existing = {}

    existing.update(merged)
    all_patients = list(existing.values())

    # Persist to SQLite for scalable access
    conn = get_connection()
    try:
        init_schema(conn)
        for p in all_patients:
            upsert_patient(
                ni=p.national_insurance,
                name=p.name,
                age=p.age,
                conditions=p.medical_history,
                medications=p.current_medications,
                conn=conn,
            )
    finally:
        conn.close()

    # Write back JSON for backward compatibility
    # Convert to dicts in a stable order for reproducibility
    patient_dicts = [
        p.to_dict() for p in sorted(all_patients, key=lambda x: x.national_insurance)
    ]
    db_path = db.db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with db_path.open("w", encoding="utf-8") as f:
        json.dump(patient_dicts, f, indent=2)

    return len(patient_dicts)


__all__ = [
    "ingest_directory_to_mock_db",
]
