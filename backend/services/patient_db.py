"""
Lightweight patient database service using SQLite (stdlib sqlite3).

Features:
- Initialize schema for patients, conditions, medications
- Create/update (upsert) patients with nested conditions/medications
- Search by demographics, condition, medication
- Simple import helpers that other scripts can call (e.g., Synthea FHIR JSON)

Database file location: backend/db/patients.sqlite
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional


DB_PATH = Path(__file__).resolve().parent.parent / "db" / "patients.sqlite"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = _connect()
    cur = conn.cursor()
    cur.executescript(
        """
        PRAGMA foreign_keys = ON;

        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            external_id TEXT UNIQUE, -- e.g., FHIR Patient.id
            name TEXT,
            age INTEGER,
            gender TEXT,
            ni_number TEXT,
            demographics_json TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS conditions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            code TEXT,
            display TEXT,
            clinical_status TEXT,
            onset TEXT,
            raw_json TEXT,
            FOREIGN KEY(patient_id) REFERENCES patients(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS medications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            code TEXT,
            display TEXT,
            status TEXT,
            raw_json TEXT,
            FOREIGN KEY(patient_id) REFERENCES patients(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_patients_name ON patients(name);
        CREATE INDEX IF NOT EXISTS idx_conditions_display
            ON conditions(display);
        CREATE INDEX IF NOT EXISTS idx_medications_display
            ON medications(display);
        """
    )
    conn.commit()
    conn.close()


def upsert_patient(
    *,
    external_id: Optional[str],
    name: Optional[str],
    age: Optional[int],
    gender: Optional[str],
    ni_number: Optional[str] = None,
    demographics: Optional[Dict[str, Any]] = None,
    conditions_list: Optional[List[Dict[str, Any]]] = None,
    medications_list: Optional[List[Dict[str, Any]]] = None,
) -> int:
    """Insert or update a patient and nested records.

    Returns the patient row id.
    """
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO patients (
            external_id, name, age, gender, ni_number, demographics_json
        )
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(external_id) DO UPDATE SET
            name=excluded.name,
            age=excluded.age,
            gender=excluded.gender,
            ni_number=excluded.ni_number,
            demographics_json=excluded.demographics_json,
            updated_at=CURRENT_TIMESTAMP
        """,
        (
            external_id,
            name,
            age,
            gender,
            ni_number,
            json.dumps(demographics or {}),
        ),
    )
    if cur.lastrowid:
        patient_id = cur.lastrowid
    else:
        # Fetch existing id
        cur.execute(
            "SELECT id FROM patients WHERE external_id = ?",
            (external_id,),
        )
        row = cur.fetchone()
        patient_id = int(row["id"]) if row else None

    if patient_id is None:
        conn.commit()
        conn.close()
        raise RuntimeError("Failed to upsert patient")

    # Replace nested data for simplicity
    if conditions_list is not None:
        cur.execute(
            "DELETE FROM conditions WHERE patient_id = ?",
            (patient_id,),
        )
        cur.executemany(
            """
            INSERT INTO conditions (
                patient_id, code, display, clinical_status, onset, raw_json
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    patient_id,
                    c.get("code"),
                    c.get("display"),
                    c.get("clinical_status"),
                    c.get("onset"),
                    json.dumps(c),
                )
                for c in conditions_list
            ],
        )

    if medications_list is not None:
        cur.execute(
            "DELETE FROM medications WHERE patient_id = ?",
            (patient_id,),
        )
        cur.executemany(
            """
            INSERT INTO medications (
                patient_id, code, display, status, raw_json
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (
                    patient_id,
                    m.get("code"),
                    m.get("display"),
                    m.get("status"),
                    json.dumps(m),
                )
                for m in medications_list
            ],
        )

    conn.commit()
    conn.close()
    return patient_id


def get_patient(patient_id: int) -> Optional[Dict[str, Any]]:
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM patients WHERE id = ?", (patient_id,))
    p = cur.fetchone()
    if not p:
        conn.close()
        return None
    patient = dict(p)
    cur.execute("SELECT * FROM conditions WHERE patient_id = ?", (patient_id,))
    patient["conditions"] = [dict(r) for r in cur.fetchall()]
    cur.execute(
        "SELECT * FROM medications WHERE patient_id = ?",
        (patient_id,),
    )
    patient["medications"] = [dict(r) for r in cur.fetchall()]
    conn.close()
    return patient


def update_patient(patient_id: int, fields: Dict[str, Any]) -> bool:
    allowed = {"name", "age", "gender", "ni_number", "demographics_json"}
    keys = [k for k in fields.keys() if k in allowed]
    if not keys:
        return False
    sets = ", ".join([f"{k} = ?" for k in keys])
    values = [fields[k] for k in keys]
    values.append(patient_id)
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        (f"UPDATE patients SET {sets}, " "updated_at=CURRENT_TIMESTAMP WHERE id = ?"),
        values,
    )
    conn.commit()
    conn.close()
    return cur.rowcount > 0


def search_patients(
    *,
    name: Optional[str] = None,
    min_age: Optional[int] = None,
    max_age: Optional[int] = None,
    gender: Optional[str] = None,
    condition: Optional[str] = None,
    medication: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """Search by demographics plus condition/medication filters."""
    clauses = []
    params: List[Any] = []
    join_conditions = False
    join_meds = False

    if name:
        clauses.append("patients.name LIKE ?")
        params.append(f"%{name}%")
    if min_age is not None:
        clauses.append("patients.age >= ?")
        params.append(min_age)
    if max_age is not None:
        clauses.append("patients.age <= ?")
        params.append(max_age)
    if gender:
        clauses.append("patients.gender = ?")
        params.append(gender)
    if condition:
        join_conditions = True
        clauses.append("conditions.display LIKE ?")
        params.append(f"%{condition}%")
    if medication:
        join_meds = True
        clauses.append("medications.display LIKE ?")
        params.append(f"%{medication}%")

    where_sql = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    join_sql = ""
    if join_conditions:
        join_sql += " LEFT JOIN conditions ON conditions.patient_id = patients.id"
    if join_meds:
        join_sql += " LEFT JOIN medications ON medications.patient_id = patients.id"

    sql = f"""
        SELECT DISTINCT patients.*
        FROM patients
        {join_sql}
        {where_sql}
        ORDER BY patients.updated_at DESC
        LIMIT ? OFFSET ?
    """
    params.extend([limit, offset])
    conn = _connect()
    cur = conn.cursor()
    cur.execute(sql, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def stats() -> Dict[str, Any]:
    conn = _connect()
    cur = conn.cursor()
    out: Dict[str, Any] = {}
    cur.execute("SELECT COUNT(*) as c FROM patients")
    out["patients"] = cur.fetchone()["c"]
    cur.execute("SELECT COUNT(*) as c FROM conditions")
    out["conditions"] = cur.fetchone()["c"]
    cur.execute("SELECT COUNT(*) as c FROM medications")
    out["medications"] = cur.fetchone()["c"]
    conn.close()
    return out
