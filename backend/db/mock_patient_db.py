"""Mock patient database implementation."""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional

try:
    from model.patient import Patient
except ImportError:
    from ..model.patient import Patient


class MockPatientDB:
    """Mock patient database class."""

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize the database with optional custom path."""
        if db_path is None:
            self.db_path = Path(__file__).parent.parent / "dat" / "patient-db.json"
        else:
            self.db_path = db_path

    def load_patients(self) -> List[Patient]:
        """Load all patients from the database."""
        try:
            with open(self.db_path, "r") as f:
                data = json.load(f)
                return [Patient.from_dict(patient_data) for patient_data in data]
        except FileNotFoundError:
            raise FileNotFoundError("Patient database not found")
        except json.JSONDecodeError:
            raise ValueError("Error reading patient database")

    def find_patient(
        self, patient_name: str, national_insurance: str
    ) -> Optional[Patient]:
        """Find a patient by name and national insurance number."""
        patients = self.load_patients()

        for patient in patients:
            if (
                patient.name.lower() == patient_name.lower()
                and patient.national_insurance == national_insurance
            ):
                return patient

        return None

    def get_patient_list(self) -> List[Dict[str, str]]:
        """Get a list of all patients with names and National Insurance numbers."""
        patients = self.load_patients()

        return [
            {"name": patient.name, "national_insurance": patient.national_insurance}
            for patient in patients
        ]

    def create_new_patient(self, patient_data: Dict[str, Any]) -> bool:
        """Create a new patient in the database."""
        # Create Patient object (this handles validation)
        new_patient = Patient.from_dict(patient_data)

        # Check for duplicate National Insurance number
        existing_patients = self.load_patients()
        for patient in existing_patients:
            if patient.national_insurance == new_patient.national_insurance:
                raise ValueError(
                    f"Patient with National Insurance {new_patient.national_insurance} already exists"
                )

        # Add new patient to list and convert to dict for JSON storage
        existing_patients.append(new_patient)
        patients_as_dicts = [patient.to_dict() for patient in existing_patients]

        # Save back to file
        try:
            with open(self.db_path, "w") as f:
                json.dump(patients_as_dicts, f, indent=2)
            return True
        except Exception as e:
            raise ValueError(f"Error saving patient to database: {e}")

    def add_patient(self, patient: Patient) -> bool:
        """Add a Patient object directly to the database."""
        return self.create_new_patient(patient.to_dict())
