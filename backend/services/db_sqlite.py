"""
Lightweight SQLite storage for synthetic patients.

Tables (simplified for prototype):
- patients(id PK, ni UNIQUE, name, age)
- conditions(id PK, patient_id FK, text, UNIQUE(patient_id, text))
- medications(id PK, patient_id FK, text, UNIQUE(patient_id, text))
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable, Optional


DB_PATH = Path(__file__).resolve().parent.parent / "dat" / "patients.sqlite"


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: Optional[sqlite3.Connection] = None) -> None:
    own = False
    if conn is None:
        conn = get_connection()
        own = True
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS patients (
              id INTEGER PRIMARY KEY,
              ni TEXT UNIQUE NOT NULL,
              name TEXT NOT NULL,
              age INTEGER
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS conditions (
              id INTEGER PRIMARY KEY,
              patient_id INTEGER NOT NULL,
              text TEXT NOT NULL,
              UNIQUE(patient_id, text),
              FOREIGN KEY(patient_id) REFERENCES patients(id) ON DELETE CASCADE
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS medications (
              id INTEGER PRIMARY KEY,
              patient_id INTEGER NOT NULL,
              text TEXT NOT NULL,
              UNIQUE(patient_id, text),
              FOREIGN KEY(patient_id) REFERENCES patients(id) ON DELETE CASCADE
            )
            """
        )
        conn.commit()
    finally:
        if own:
            conn.close()


def upsert_patient(
    ni: str,
    name: str,
    age: Optional[int],
    *,
    conditions: Iterable[str] = (),
    medications: Iterable[str] = (),
    conn: Optional[sqlite3.Connection] = None,
) -> int:
    own = False
    if conn is None:
        conn = get_connection()
        own = True
    try:
        init_schema(conn)
        cur = conn.cursor()
        cur.execute(
            "INSERT OR IGNORE INTO patients(ni, name, age) VALUES(?, ?, ?)",
            (ni, name, age),
        )
        cur.execute(
            "UPDATE patients SET name = ?, age = ? WHERE ni = ?",
            (name, age, ni),
        )
        cur.execute("SELECT id FROM patients WHERE ni = ?", (ni,))
        row = cur.fetchone()
        patient_id = int(row[0])
        for txt in conditions or []:
            if not txt:
                continue
            cur.execute(
                "INSERT OR IGNORE INTO conditions(patient_id, text) VALUES(?, ?)",
                (patient_id, txt),
            )
        for txt in medications or []:
            if not txt:
                continue
            cur.execute(
                "INSERT OR IGNORE INTO medications(patient_id, text)" " VALUES(?, ?)",
                (patient_id, txt),
            )
        conn.commit()
        return patient_id
    finally:
        if own:
            conn.close()


def get_patient_snapshot_by_ni(ni: str) -> Optional[str]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, name, age FROM patients WHERE ni = ?", (ni,))
        row = cur.fetchone()
        if not row:
            return None
        pid, name, age = row
        cur.execute(
            "SELECT text FROM conditions WHERE patient_id = ? ORDER BY id",
            (pid,),
        )
        problems = [r[0] for r in cur.fetchall()]
        cur.execute(
            "SELECT text FROM medications WHERE patient_id = ? ORDER BY id",
            (pid,),
        )
        meds = [r[0] for r in cur.fetchall()]
        age_txt = f", age {age}" if age is not None else ""
        probs = ", ".join(problems) if problems else "None recorded"
        meds_txt = ", ".join(meds) if meds else "None recorded"
        return (
            f"Patient: {name}{age_txt} (NI: {ni})\n"
            f"Active problems: {probs}\n"
            f"Current medications: {meds_txt}"
        )
    finally:
        conn.close()
