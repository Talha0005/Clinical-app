"""Shared test fixtures and configuration."""

import json
import sys
import tempfile
from pathlib import Path
from typing import Dict, Any

import pytest

# Add backend directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.mock_patient_db import MockPatientDB


@pytest.fixture
def sample_patient_data():
    """Sample patient data for testing."""
    return [
        {
            "name": "John Smith",
            "national_insurance": "AB123456C",
            "age": 45,
            "medical_history": ["Hypertension", "Type 2 Diabetes"],
            "current_medications": ["Metformin", "Lisinopril"]
        },
        {
            "name": "Jane Doe", 
            "national_insurance": "CD789012E",
            "age": 32,
            "medical_history": ["Asthma"],
            "current_medications": ["Ventolin"]
        }
    ]


@pytest.fixture
def mock_patient_db_file(sample_patient_data, tmp_path):
    """Create a temporary patient database file."""
    db_file = tmp_path / "test_patient_db.json"
    with open(db_file, "w") as f:
        json.dump(sample_patient_data, f)
    return db_file


@pytest.fixture
def mock_patient_db(mock_patient_db_file):
    """Create a MockPatientDB instance with test data."""
    return MockPatientDB(db_path=mock_patient_db_file)