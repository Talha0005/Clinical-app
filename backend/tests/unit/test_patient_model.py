"""Unit tests for Patient model class."""

import pytest
from model.patient import Patient


@pytest.mark.unit
class TestPatient:
    """Test cases for Patient model class."""
    
    def test_patient_creation_success(self):
        """Test successful patient creation with valid data."""
        patient = Patient(
            name="John Smith",
            national_insurance="AB123456C",
            age=45,
            medical_history=["Hypertension"],
            current_medications=["Lisinopril"]
        )
        
        assert patient.name == "John Smith"
        assert patient.national_insurance == "AB123456C"
        assert patient.age == 45
        assert patient.medical_history == ["Hypertension"]
        assert patient.current_medications == ["Lisinopril"]
    
    def test_patient_creation_minimal_data(self):
        """Test patient creation with only required fields."""
        patient = Patient(name="Jane Doe", national_insurance="CD789012E")
        
        assert patient.name == "Jane Doe"
        assert patient.national_insurance == "CD789012E"
        assert patient.age is None
        assert patient.medical_history == []
        assert patient.current_medications == []
    
    def test_patient_invalid_name_empty(self):
        """Test patient creation fails with empty name."""
        with pytest.raises(ValueError, match="Patient name is required"):
            Patient(name="", national_insurance="AB123456C")
    
    def test_patient_invalid_name_whitespace(self):
        """Test patient creation fails with whitespace-only name."""
        with pytest.raises(ValueError, match="Patient name is required"):
            Patient(name="   ", national_insurance="AB123456C")
    
    def test_patient_invalid_ni_empty(self):
        """Test patient creation fails with empty National Insurance."""
        with pytest.raises(ValueError, match="National Insurance number is required"):
            Patient(name="John Smith", national_insurance="")
    
    def test_patient_invalid_ni_format(self):
        """Test patient creation fails with invalid NI format."""
        with pytest.raises(ValueError, match="Invalid National Insurance format"):
            Patient(name="John Smith", national_insurance="INVALID123")
    
    def test_patient_invalid_age_negative(self):
        """Test patient creation fails with negative age."""
        with pytest.raises(ValueError, match="Age must be between 0 and 150"):
            Patient(name="John Smith", national_insurance="AB123456C", age=-1)
    
    def test_patient_invalid_age_too_high(self):
        """Test patient creation fails with age over 150."""
        with pytest.raises(ValueError, match="Age must be between 0 and 150"):
            Patient(name="John Smith", national_insurance="AB123456C", age=151)
    
    def test_patient_name_whitespace_trimmed(self):
        """Test patient name whitespace is trimmed."""
        patient = Patient(name="  John Smith  ", national_insurance="AB123456C")
        assert patient.name == "John Smith"
    
    def test_patient_to_dict(self):
        """Test converting patient to dictionary."""
        patient = Patient(
            name="John Smith",
            national_insurance="AB123456C",
            age=45,
            medical_history=["Hypertension"],
            current_medications=["Lisinopril"]
        )
        
        expected = {
            "name": "John Smith",
            "national_insurance": "AB123456C",
            "age": 45,
            "medical_history": ["Hypertension"],
            "current_medications": ["Lisinopril"]
        }
        
        assert patient.to_dict() == expected
    
    def test_patient_from_dict(self):
        """Test creating patient from dictionary."""
        data = {
            "name": "Jane Doe",
            "national_insurance": "CD789012E",
            "age": 32,
            "medical_history": ["Asthma"],
            "current_medications": ["Ventolin"]
        }
        
        patient = Patient.from_dict(data)
        
        assert patient.name == "Jane Doe"
        assert patient.national_insurance == "CD789012E"
        assert patient.age == 32
        assert patient.medical_history == ["Asthma"]
        assert patient.current_medications == ["Ventolin"]
    
    def test_patient_from_dict_minimal(self):
        """Test creating patient from dictionary with minimal data."""
        data = {
            "name": "Jane Doe",
            "national_insurance": "CD789012E"
        }
        
        patient = Patient.from_dict(data)
        
        assert patient.name == "Jane Doe"
        assert patient.national_insurance == "CD789012E"
        assert patient.age is None
        assert patient.medical_history == []
        assert patient.current_medications == []
    
    def test_add_medical_condition(self):
        """Test adding medical condition to patient."""
        patient = Patient(name="John Smith", national_insurance="AB123456C")
        
        patient.add_medical_condition("Diabetes")
        assert "Diabetes" in patient.medical_history
        
        # Test no duplicates
        patient.add_medical_condition("Diabetes")
        assert patient.medical_history.count("Diabetes") == 1
    
    def test_add_medication(self):
        """Test adding medication to patient."""
        patient = Patient(name="John Smith", national_insurance="AB123456C")
        
        patient.add_medication("Metformin")
        assert "Metformin" in patient.current_medications
        
        # Test no duplicates
        patient.add_medication("Metformin")
        assert patient.current_medications.count("Metformin") == 1
    
    def test_remove_medication_success(self):
        """Test removing existing medication from patient."""
        patient = Patient(
            name="John Smith",
            national_insurance="AB123456C",
            current_medications=["Metformin", "Lisinopril"]
        )
        
        result = patient.remove_medication("Metformin")
        assert result is True
        assert "Metformin" not in patient.current_medications
        assert "Lisinopril" in patient.current_medications
    
    def test_remove_medication_not_found(self):
        """Test removing non-existent medication from patient."""
        patient = Patient(
            name="John Smith",
            national_insurance="AB123456C",
            current_medications=["Lisinopril"]
        )
        
        result = patient.remove_medication("Metformin")
        assert result is False
        assert patient.current_medications == ["Lisinopril"]
    
    def test_patient_string_representation(self):
        """Test patient string representation."""
        patient = Patient(name="John Smith", national_insurance="AB123456C", age=45)
        
        expected = "Patient(name='John Smith', ni='AB123456C', age=45)"
        assert str(patient) == expected
    
    def test_patient_equality(self):
        """Test patient equality comparison by National Insurance."""
        patient1 = Patient(name="John Smith", national_insurance="AB123456C")
        patient2 = Patient(name="Jane Doe", national_insurance="AB123456C")  # Same NI
        patient3 = Patient(name="John Smith", national_insurance="CD789012E")  # Different NI
        
        assert patient1 == patient2  # Same NI
        assert patient1 != patient3  # Different NI
        assert patient1 != "not a patient"  # Different type