"""Patient model class for DigiClinic."""

import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class Patient:
    """Patient model with validation."""
    
    name: str
    national_insurance: str
    age: Optional[int] = None
    medical_history: List[str] = field(default_factory=list)
    current_medications: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate patient data after initialization."""
        self.validate()
    
    def validate(self) -> None:
        """Validate patient data."""
        if not self.name or not self.name.strip():
            raise ValueError("Patient name is required")
        
        if not self.national_insurance:
            raise ValueError("National Insurance number is required")
        
        # Validate UK National Insurance format: XX123456X
        ni_pattern = r'^[A-Z]{2}[0-9]{6}[A-Z]$'
        if not re.match(ni_pattern, self.national_insurance):
            raise ValueError("Invalid National Insurance format (expected: XX123456X)")
        
        if self.age is not None and (self.age < 0 or self.age > 120):
            raise ValueError("Age must be between 0 and 120")
        
        # Clean up name
        self.name = self.name.strip()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert patient to dictionary."""
        return {
            "name": self.name,
            "national_insurance": self.national_insurance,
            "age": self.age,
            "medical_history": self.medical_history,
            "current_medications": self.current_medications
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Patient":
        """Create patient from dictionary."""
        # Validate required fields are present
        required_fields = ["name", "national_insurance"]
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")
        
        return cls(
            name=data["name"],
            national_insurance=data["national_insurance"],
            age=data.get("age"),
            medical_history=data.get("medical_history", []),
            current_medications=data.get("current_medications", [])
        )
    
    def add_medical_condition(self, condition: str) -> None:
        """Add a medical condition to patient history."""
        if condition and condition not in self.medical_history:
            self.medical_history.append(condition)
    
    def add_medication(self, medication: str) -> None:
        """Add a medication to patient's current medications."""
        if medication and medication not in self.current_medications:
            self.current_medications.append(medication)
    
    def remove_medication(self, medication: str) -> bool:
        """Remove a medication from patient's current medications."""
        try:
            self.current_medications.remove(medication)
            return True
        except ValueError:
            return False
    
    def __str__(self) -> str:
        """String representation of patient."""
        return f"Patient(name='{self.name}', ni='{self.national_insurance}', age={self.age})"
    
    def __eq__(self, other) -> bool:
        """Compare patients by National Insurance number."""
        if not isinstance(other, Patient):
            return False
        return self.national_insurance == other.national_insurance