"""Unit tests for MockPatientDB class."""

import json
import pytest
from pathlib import Path

from db.mock_patient_db import MockPatientDB


@pytest.mark.unit
class TestMockPatientDB:
    """Test cases for MockPatientDB class."""

    def test_load_patients_success(self, mock_patient_db, sample_patient_data):
        """Test successful loading of patient data."""
        patients = mock_patient_db.load_patients()
        assert len(patients) == 2

        # Check first patient
        assert patients[0].name == "John Smith"
        assert patients[0].national_insurance == "AB123456C"
        assert patients[0].age == 45
        assert patients[0].medical_history == ["Hypertension", "Type 2 Diabetes"]
        assert patients[0].current_medications == ["Metformin", "Lisinopril"]

        # Check second patient
        assert patients[1].name == "Jane Doe"
        assert patients[1].national_insurance == "CD789012E"
        assert patients[1].age == 32
        assert patients[1].medical_history == ["Asthma"]
        assert patients[1].current_medications == ["Ventolin"]

    def test_load_patients_file_not_found(self, tmp_path):
        """Test handling of missing database file."""
        non_existent_file = tmp_path / "missing.json"
        db = MockPatientDB(db_path=non_existent_file)

        with pytest.raises(FileNotFoundError, match="Patient database not found"):
            db.load_patients()

    def test_load_patients_invalid_json(self, tmp_path):
        """Test handling of invalid JSON file."""
        invalid_json_file = tmp_path / "invalid.json"
        with open(invalid_json_file, "w") as f:
            f.write("invalid json content")

        db = MockPatientDB(db_path=invalid_json_file)

        with pytest.raises(ValueError, match="Error reading patient database"):
            db.load_patients()

    def test_find_patient_success(self, mock_patient_db):
        """Test successful patient lookup."""
        patient = mock_patient_db.find_patient("John Smith", "AB123456C")

        assert patient is not None
        assert patient.name == "John Smith"
        assert patient.national_insurance == "AB123456C"
        assert patient.age == 45

    def test_find_patient_case_insensitive_name(self, mock_patient_db):
        """Test case-insensitive name matching."""
        patient = mock_patient_db.find_patient("john smith", "AB123456C")

        assert patient is not None
        assert patient.name == "John Smith"

    def test_find_patient_not_found_wrong_name(self, mock_patient_db):
        """Test patient not found with wrong name."""
        patient = mock_patient_db.find_patient("Wrong Name", "AB123456C")
        assert patient is None

    def test_find_patient_not_found_wrong_ni(self, mock_patient_db):
        """Test patient not found with wrong National Insurance."""
        patient = mock_patient_db.find_patient("John Smith", "WRONG123")
        assert patient is None

    def test_get_patient_list(self, mock_patient_db):
        """Test getting patient list with names and NI numbers."""
        patient_list = mock_patient_db.get_patient_list()

        assert len(patient_list) == 2
        assert patient_list[0] == {
            "name": "John Smith",
            "national_insurance": "AB123456C",
        }
        assert patient_list[1] == {
            "name": "Jane Doe",
            "national_insurance": "CD789012E",
        }

    def test_default_db_path(self):
        """Test default database path construction."""
        db = MockPatientDB()
        expected_path = Path(__file__).parent.parent.parent / "dat" / "patient-db.json"
        assert db.db_path == expected_path

    def test_create_new_patient_success(self, mock_patient_db, tmp_path):
        """Test successful creation of new patient."""
        new_patient = {
            "name": "Test Patient",
            "national_insurance": "ZZ999999Z",
            "age": 30,
            "medical_history": [],
            "current_medications": [],
        }

        result = mock_patient_db.create_new_patient(new_patient)
        assert result is True

        # Verify patient was added
        found_patient = mock_patient_db.find_patient("Test Patient", "ZZ999999Z")
        assert found_patient is not None
        assert found_patient.name == "Test Patient"
        assert found_patient.age == 30

    def test_create_new_patient_duplicate_ni(self, mock_patient_db):
        """Test creation fails with duplicate National Insurance number."""
        new_patient = {
            "name": "Different Name",
            "national_insurance": "AB123456C",  # Already exists
            "age": 25,
        }

        with pytest.raises(
            ValueError, match="Patient with National Insurance .* already exists"
        ):
            mock_patient_db.create_new_patient(new_patient)

    def test_create_new_patient_missing_required_fields(self, mock_patient_db):
        """Test creation fails with missing required fields."""
        incomplete_patient = {
            "name": "Test Patient"
            # Missing national_insurance
        }

        with pytest.raises(ValueError, match="Missing required fields"):
            mock_patient_db.create_new_patient(incomplete_patient)

    def test_create_new_patient_invalid_ni_format(self, mock_patient_db):
        """Test creation fails with invalid National Insurance format."""
        invalid_patient = {
            "name": "Test Patient",
            "national_insurance": "INVALID123",  # Wrong format
            "age": 30,
        }

        with pytest.raises(ValueError, match="Invalid National Insurance format"):
            mock_patient_db.create_new_patient(invalid_patient)
