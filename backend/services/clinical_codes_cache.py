"""
Clinical Codes Cache for DigiClinic MVP
Hard-coded clinical codes for common symptoms and conditions for testing and MVP functionality.
Includes SNOMED CT, ICD-10, and other relevant medical codes.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import json
import re


class CodeSystem(Enum):
    """Clinical coding systems."""
    SNOMED_CT = "SNOMED_CT"
    ICD_10 = "ICD_10"  
    ICD_11 = "ICD_11"
    LOINC = "LOINC"
    CPT = "CPT"
    HCPCS = "HCPCS"


@dataclass
class ClinicalCode:
    """Represents a clinical code with metadata."""
    code: str
    display: str
    system: CodeSystem
    description: Optional[str] = None
    category: Optional[str] = None
    severity: Optional[str] = None  # mild, moderate, severe
    body_system: Optional[str] = None
    synonyms: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "display": self.display,
            "system": self.system.value,
            "description": self.description,
            "category": self.category,
            "severity": self.severity,
            "body_system": self.body_system,
            "synonyms": self.synonyms
        }


@dataclass
class SymptomMapping:
    """Maps natural language symptoms to clinical codes."""
    keywords: List[str]
    primary_codes: List[ClinicalCode]
    related_codes: List[ClinicalCode] = field(default_factory=list)
    differential_diagnosis: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "keywords": self.keywords,
            "primary_codes": [code.to_dict() for code in self.primary_codes],
            "related_codes": [code.to_dict() for code in self.related_codes],
            "differential_diagnosis": self.differential_diagnosis
        }


class ClinicalCodesCache:
    """Hard-coded clinical codes cache for MVP functionality."""
    
    def __init__(self):
        self.codes_db = self._initialize_codes()
        self.symptom_mappings = self._initialize_symptom_mappings()
    
    def _initialize_codes(self) -> Dict[str, ClinicalCode]:
        """Initialize the clinical codes database."""
        codes = {}
        
        # COUGH RELATED CODES
        codes["49727002"] = ClinicalCode(
            code="49727002",
            display="Cough",
            system=CodeSystem.SNOMED_CT,
            description="Sudden, forceful expulsion of air from the lungs",
            category="symptom",
            body_system="respiratory",
            synonyms=["coughing", "tussis", "hack"]
        )
        
        codes["R05"] = ClinicalCode(
            code="R05",
            display="Cough",
            system=CodeSystem.ICD_10,
            description="Cough - ICD-10 classification",
            category="symptom",
            body_system="respiratory"
        )
        
        codes["MD02"] = ClinicalCode(
            code="MD02",
            display="Cough",
            system=CodeSystem.ICD_11,
            description="Cough - ICD-11 classification",
            category="symptom",
            body_system="respiratory"
        )
        
        # DRY COUGH
        codes["40401006"] = ClinicalCode(
            code="40401006",
            display="Dry cough",
            system=CodeSystem.SNOMED_CT,
            description="Cough without expectoration",
            category="symptom",
            body_system="respiratory",
            synonyms=["non-productive cough", "hacking cough"]
        )
        
        # PRODUCTIVE COUGH
        codes["28743005"] = ClinicalCode(
            code="28743005",
            display="Productive cough",
            system=CodeSystem.SNOMED_CT,
            description="Cough with expectoration of sputum",
            category="symptom",
            body_system="respiratory",
            synonyms=["wet cough", "chesty cough", "phlegmy cough"]
        )
        
        # CHEST PAIN CODES
        codes["29857009"] = ClinicalCode(
            code="29857009",
            display="Chest pain",
            system=CodeSystem.SNOMED_CT,
            description="Pain in the chest region",
            category="symptom",
            body_system="cardiovascular",
            synonyms=["thoracic pain", "chest discomfort"]
        )
        
        codes["R07.9"] = ClinicalCode(
            code="R07.9",
            display="Chest pain, unspecified",
            system=CodeSystem.ICD_10,
            description="Chest pain without further specification",
            category="symptom",
            body_system="cardiovascular"
        )
        
        codes["R07.1"] = ClinicalCode(
            code="R07.1",
            display="Chest pain on breathing",
            system=CodeSystem.ICD_10,
            description="Pleuritic chest pain",
            category="symptom",
            body_system="respiratory"
        )
        
        # PLEURITIC CHEST PAIN
        codes["5918000"] = ClinicalCode(
            code="5918000",
            display="Pleuritic pain",
            system=CodeSystem.SNOMED_CT,
            description="Sharp chest pain worsened by breathing",
            category="symptom",
            body_system="respiratory",
            synonyms=["pleuritic chest pain", "sharp chest pain"]
        )
        
        # FEVER CODES
        codes["386661006"] = ClinicalCode(
            code="386661006",
            display="Fever",
            system=CodeSystem.SNOMED_CT,
            description="Elevated body temperature",
            category="symptom",
            body_system="general",
            synonyms=["pyrexia", "hyperthermia", "raised temperature"]
        )
        
        codes["R50.9"] = ClinicalCode(
            code="R50.9",
            display="Fever, unspecified",
            system=CodeSystem.ICD_10,
            description="Fever without further specification",
            category="symptom",
            body_system="general"
        )
        
        # DYSPNEA (SHORTNESS OF BREATH)
        codes["267036007"] = ClinicalCode(
            code="267036007",
            display="Dyspnea",
            system=CodeSystem.SNOMED_CT,
            description="Difficulty or discomfort in breathing",
            category="symptom",
            body_system="respiratory",
            synonyms=["shortness of breath", "breathlessness", "SOB"]
        )
        
        codes["R06.00"] = ClinicalCode(
            code="R06.00",
            display="Dyspnea, unspecified",
            system=CodeSystem.ICD_10,
            description="Shortness of breath without specification",
            category="symptom",
            body_system="respiratory"
        )
        
        # FATIGUE
        codes["84229001"] = ClinicalCode(
            code="84229001",
            display="Fatigue",
            system=CodeSystem.SNOMED_CT,
            description="Feeling of tiredness or exhaustion",
            category="symptom",
            body_system="general",
            synonyms=["tiredness", "exhaustion", "weakness"]
        )
        
        codes["R53"] = ClinicalCode(
            code="R53",
            display="Malaise and fatigue",
            system=CodeSystem.ICD_10,
            description="General feeling of discomfort and tiredness",
            category="symptom",
            body_system="general"
        )
        
        # HEADACHE CODES
        codes["25064002"] = ClinicalCode(
            code="25064002",
            display="Headache",
            system=CodeSystem.SNOMED_CT,
            description="Pain in the head or upper neck",
            category="symptom",
            body_system="neurological",
            synonyms=["cephalgia", "head pain"]
        )
        
        codes["R51"] = ClinicalCode(
            code="R51",
            display="Headache",
            system=CodeSystem.ICD_10,
            description="Headache - ICD-10 classification",
            category="symptom",
            body_system="neurological"
        )
        
        # SORE THROAT
        codes["405737000"] = ClinicalCode(
            code="405737000",
            display="Sore throat",
            system=CodeSystem.SNOMED_CT,
            description="Pain or discomfort in the throat",
            category="symptom",
            body_system="respiratory",
            synonyms=["throat pain", "pharyngalgia"]
        )
        
        codes["R07.0"] = ClinicalCode(
            code="R07.0",
            display="Pain in throat",
            system=CodeSystem.ICD_10,
            description="Throat pain - ICD-10 classification",
            category="symptom",
            body_system="respiratory"
        )
        
        # NAUSEA
        codes["422587007"] = ClinicalCode(
            code="422587007",
            display="Nausea",
            system=CodeSystem.SNOMED_CT,
            description="Feeling of sickness with urge to vomit",
            category="symptom",
            body_system="gastrointestinal",
            synonyms=["queasiness", "sick feeling"]
        )
        
        codes["R11.0"] = ClinicalCode(
            code="R11.0",
            display="Nausea",
            system=CodeSystem.ICD_10,
            description="Nausea - ICD-10 classification",
            category="symptom",
            body_system="gastrointestinal"
        )
        
        # VOMITING
        codes["422400008"] = ClinicalCode(
            code="422400008",
            display="Vomiting",
            system=CodeSystem.SNOMED_CT,
            description="Forceful expulsion of stomach contents",
            category="symptom",
            body_system="gastrointestinal",
            synonyms=["emesis", "throwing up"]
        )
        
        codes["R11.10"] = ClinicalCode(
            code="R11.10",
            display="Vomiting, unspecified",
            system=CodeSystem.ICD_10,
            description="Vomiting without further specification",
            category="symptom",
            body_system="gastrointestinal"
        )
        
        # ABDOMINAL PAIN
        codes["21522001"] = ClinicalCode(
            code="21522001",
            display="Abdominal pain",
            system=CodeSystem.SNOMED_CT,
            description="Pain in the abdomen",
            category="symptom",
            body_system="gastrointestinal",
            synonyms=["stomach pain", "belly pain", "tummy ache"]
        )
        
        codes["R10.9"] = ClinicalCode(
            code="R10.9",
            display="Unspecified abdominal pain",
            system=CodeSystem.ICD_10,
            description="Abdominal pain without specification",
            category="symptom",
            body_system="gastrointestinal"
        )
        
        # DIARRHEA
        codes["62315008"] = ClinicalCode(
            code="62315008",
            display="Diarrhea",
            system=CodeSystem.SNOMED_CT,
            description="Frequent loose or liquid bowel movements",
            category="symptom",
            body_system="gastrointestinal",
            synonyms=["loose stools", "watery stools"]
        )
        
        codes["K59.1"] = ClinicalCode(
            code="K59.1",
            display="Diarrhea, unspecified",
            system=CodeSystem.ICD_10,
            description="Diarrhea without further specification",
            category="symptom",
            body_system="gastrointestinal"
        )
        
        # COMMON CONDITIONS
        # UPPER RESPIRATORY TRACT INFECTION
        codes["54150009"] = ClinicalCode(
            code="54150009",
            display="Upper respiratory tract infection",
            system=CodeSystem.SNOMED_CT,
            description="Infection of the upper respiratory system",
            category="condition",
            body_system="respiratory",
            synonyms=["URTI", "common cold"]
        )
        
        codes["J06.9"] = ClinicalCode(
            code="J06.9",
            display="Acute upper respiratory infection, unspecified",
            system=CodeSystem.ICD_10,
            description="Acute URTI without specification",
            category="condition",
            body_system="respiratory"
        )
        
        # PNEUMONIA
        codes["233604007"] = ClinicalCode(
            code="233604007",
            display="Pneumonia",
            system=CodeSystem.SNOMED_CT,
            description="Infection and inflammation of lung tissue",
            category="condition",
            body_system="respiratory",
            synonyms=["lung infection"]
        )
        
        codes["J18.9"] = ClinicalCode(
            code="J18.9",
            display="Pneumonia, unspecified organism",
            system=CodeSystem.ICD_10,
            description="Pneumonia without specified causative organism",
            category="condition",
            body_system="respiratory"
        )
        
        # BRONCHITIS
        codes["32398004"] = ClinicalCode(
            code="32398004",
            display="Bronchitis",
            system=CodeSystem.SNOMED_CT,
            description="Inflammation of the bronchi",
            category="condition",
            body_system="respiratory",
            synonyms=["chest infection"]
        )
        
        codes["J40"] = ClinicalCode(
            code="J40",
            display="Bronchitis, not specified as acute or chronic",
            system=CodeSystem.ICD_10,
            description="Bronchitis without acute/chronic specification",
            category="condition",
            body_system="respiratory"
        )
        
        return codes
    
    def _initialize_symptom_mappings(self) -> Dict[str, SymptomMapping]:
        """Initialize symptom to code mappings."""
        mappings = {}
        
        # COUGH MAPPINGS
        mappings["cough"] = SymptomMapping(
            keywords=["cough", "coughing", "hack", "hacking", "tussis"],
            primary_codes=[
                self.codes_db["49727002"],  # SNOMED Cough
                self.codes_db["R05"],       # ICD-10 Cough
            ],
            related_codes=[
                self.codes_db["40401006"],  # Dry cough
                self.codes_db["28743005"],  # Productive cough
            ],
            differential_diagnosis=[
                "Upper respiratory tract infection",
                "Bronchitis", 
                "Pneumonia",
                "Asthma",
                "COPD"
            ]
        )
        
        mappings["dry_cough"] = SymptomMapping(
            keywords=["dry cough", "non-productive cough", "hacking cough"],
            primary_codes=[
                self.codes_db["40401006"],  # Dry cough
                self.codes_db["R05"],       # ICD-10 Cough
            ],
            differential_diagnosis=[
                "Viral upper respiratory infection",
                "Early pneumonia",
                "Asthma"
            ]
        )
        
        mappings["productive_cough"] = SymptomMapping(
            keywords=["productive cough", "wet cough", "chesty cough", "phlegmy cough", "cough with phlegm"],
            primary_codes=[
                self.codes_db["28743005"],  # Productive cough
                self.codes_db["R05"],       # ICD-10 Cough
            ],
            differential_diagnosis=[
                "Bronchitis",
                "Pneumonia", 
                "COPD exacerbation"
            ]
        )
        
        # CHEST PAIN MAPPINGS
        mappings["chest_pain"] = SymptomMapping(
            keywords=["chest pain", "thoracic pain", "chest discomfort", "chest ache"],
            primary_codes=[
                self.codes_db["29857009"],  # SNOMED Chest pain
                self.codes_db["R07.9"],     # ICD-10 Chest pain
            ],
            related_codes=[
                self.codes_db["5918000"],   # Pleuritic pain
                self.codes_db["R07.1"],     # Chest pain on breathing
            ],
            differential_diagnosis=[
                "Musculoskeletal chest pain",
                "Pleuritis",
                "Pneumonia",
                "Myocardial infarction",
                "Pulmonary embolism"
            ]
        )
        
        mappings["pleuritic_chest_pain"] = SymptomMapping(
            keywords=["pleuritic chest pain", "sharp chest pain", "chest pain on breathing"],
            primary_codes=[
                self.codes_db["5918000"],   # Pleuritic pain
                self.codes_db["R07.1"],     # Chest pain on breathing
            ],
            differential_diagnosis=[
                "Pleuritis",
                "Pneumonia",
                "Pulmonary embolism"
            ]
        )
        
        # FEVER MAPPINGS
        mappings["fever"] = SymptomMapping(
            keywords=["fever", "pyrexia", "hyperthermia", "raised temperature", "high temperature"],
            primary_codes=[
                self.codes_db["386661006"], # SNOMED Fever
                self.codes_db["R50.9"],     # ICD-10 Fever
            ],
            differential_diagnosis=[
                "Viral infection",
                "Bacterial infection",
                "Upper respiratory tract infection",
                "Pneumonia"
            ]
        )
        
        # SHORTNESS OF BREATH MAPPINGS
        mappings["dyspnea"] = SymptomMapping(
            keywords=["dyspnea", "shortness of breath", "breathlessness", "SOB", "difficulty breathing"],
            primary_codes=[
                self.codes_db["267036007"], # SNOMED Dyspnea
                self.codes_db["R06.00"],    # ICD-10 Dyspnea
            ],
            differential_diagnosis=[
                "Pneumonia",
                "Asthma exacerbation",
                "COPD exacerbation",
                "Heart failure",
                "Pulmonary embolism"
            ]
        )
        
        # GENERAL SYMPTOMS
        mappings["fatigue"] = SymptomMapping(
            keywords=["fatigue", "tiredness", "exhaustion", "weakness", "tired"],
            primary_codes=[
                self.codes_db["84229001"],  # SNOMED Fatigue
                self.codes_db["R53"],       # ICD-10 Malaise and fatigue
            ],
            differential_diagnosis=[
                "Viral infection",
                "Anemia",
                "Depression",
                "Sleep disorders"
            ]
        )
        
        mappings["headache"] = SymptomMapping(
            keywords=["headache", "head pain", "cephalgia"],
            primary_codes=[
                self.codes_db["25064002"],  # SNOMED Headache
                self.codes_db["R51"],       # ICD-10 Headache
            ],
            differential_diagnosis=[
                "Tension headache",
                "Migraine",
                "Sinus infection",
                "Viral illness"
            ]
        )
        
        mappings["sore_throat"] = SymptomMapping(
            keywords=["sore throat", "throat pain", "pharyngalgia"],
            primary_codes=[
                self.codes_db["405737000"], # SNOMED Sore throat
                self.codes_db["R07.0"],     # ICD-10 Pain in throat
            ],
            differential_diagnosis=[
                "Viral pharyngitis",
                "Bacterial pharyngitis",
                "Upper respiratory tract infection"
            ]
        )
        
        # GASTROINTESTINAL SYMPTOMS
        mappings["nausea"] = SymptomMapping(
            keywords=["nausea", "queasiness", "sick feeling", "feeling sick"],
            primary_codes=[
                self.codes_db["422587007"], # SNOMED Nausea
                self.codes_db["R11.0"],     # ICD-10 Nausea
            ],
            differential_diagnosis=[
                "Gastroenteritis",
                "Food poisoning",
                "Migraine",
                "Pregnancy"
            ]
        )
        
        mappings["vomiting"] = SymptomMapping(
            keywords=["vomiting", "emesis", "throwing up", "being sick"],
            primary_codes=[
                self.codes_db["422400008"], # SNOMED Vomiting
                self.codes_db["R11.10"],    # ICD-10 Vomiting
            ],
            differential_diagnosis=[
                "Gastroenteritis",
                "Food poisoning",
                "Migraine",
                "Appendicitis"
            ]
        )
        
        mappings["abdominal_pain"] = SymptomMapping(
            keywords=["abdominal pain", "stomach pain", "belly pain", "tummy ache"],
            primary_codes=[
                self.codes_db["21522001"],  # SNOMED Abdominal pain
                self.codes_db["R10.9"],     # ICD-10 Abdominal pain
            ],
            differential_diagnosis=[
                "Gastroenteritis",
                "Appendicitis",
                "Peptic ulcer",
                "Gallstones"
            ]
        )
        
        mappings["diarrhea"] = SymptomMapping(
            keywords=["diarrhea", "loose stools", "watery stools", "runny tummy"],
            primary_codes=[
                self.codes_db["62315008"],  # SNOMED Diarrhea
                self.codes_db["K59.1"],     # ICD-10 Diarrhea
            ],
            differential_diagnosis=[
                "Gastroenteritis",
                "Food poisoning", 
                "Inflammatory bowel disease",
                "Antibiotic-associated diarrhea"
            ]
        )

        # DISEASE/CONDITION MAPPINGS (to support direct disease mentions)
        mappings["pneumonia"] = SymptomMapping(
            keywords=["pneumonia", "lung infection"],
            primary_codes=[
                self.codes_db["233604007"],  # SNOMED Pneumonia
                self.codes_db["J18.9"],      # ICD-10 Pneumonia
            ],
            differential_diagnosis=[
                "Bronchitis",
                "Upper respiratory tract infection",
                "Pulmonary embolism"
            ]
        )

        mappings["urti"] = SymptomMapping(
            keywords=[
                "urti",
                "upper respiratory tract infection",
                "common cold",
            ],
            primary_codes=[
                self.codes_db["54150009"],  # SNOMED URTI
                self.codes_db["J06.9"],     # ICD-10 URTI
            ],
            differential_diagnosis=[
                "Viral pharyngitis",
                "Acute bronchitis",
                "Influenza"
            ]
        )

        mappings["bronchitis"] = SymptomMapping(
            keywords=["bronchitis", "chest infection"],
            primary_codes=[
                self.codes_db["32398004"],  # SNOMED Bronchitis
                self.codes_db["J40"],       # ICD-10 Bronchitis
            ],
            differential_diagnosis=[
                "Pneumonia",
                "Asthma exacerbation",
                "COPD exacerbation"
            ]
        )
        
        return mappings
    
    def find_codes_for_symptom(self, symptom_text: str) -> Optional[SymptomMapping]:
        """Find clinical codes for a given symptom description.
        
        This matcher is tolerant to spacing, punctuation and common
        variations like "chestpain" vs "chest pain" or "shortnessofbreath".
        """
        def norm_space(s: str) -> str:
            # Keep letters and numbers, convert others to single spaces
            return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()

        def norm_compact(s: str) -> str:
            # Remove all spaces after normalization
            return re.sub(r"\s+", "", norm_space(s))

        s_raw = (symptom_text or "").lower().strip()
        s_norm = norm_space(s_raw)
        s_compact = norm_compact(s_raw)

        # Direct mapping lookup with normalization and compact matching
        for _key, mapping in self.symptom_mappings.items():
            for keyword in mapping.keywords:
                kw_raw = (keyword or "").lower().strip()
                if not kw_raw:
                    continue
                kw_norm = norm_space(kw_raw)
                kw_compact = norm_compact(kw_raw)
                if (
                    kw_raw in s_raw
                    or kw_norm in s_norm
                    or kw_compact in s_compact
                ):
                    return mapping

        # Fuzzy matching for common variations
        if any(w in s_norm for w in ["cough", "coughing"]):
            if any(w in s_norm for w in ["dry", "non productive", "hacking"]):
                return self.symptom_mappings.get("dry_cough")
            elif any(w in s_norm for w in ["wet", "productive", "phlegm", "mucus"]):
                return self.symptom_mappings.get("productive_cough")
            else:
                return self.symptom_mappings.get("cough")

        # Handle chest pain including concatenated forms ("chestpain") and pleuritic variants
        if ("chest pain" in s_norm) or ("chestpain" in s_compact) or ("chest ache" in s_norm):
            if any(w in s_norm for w in ["sharp", "breathing", "pleuritic"]):
                return self.symptom_mappings.get("pleuritic_chest_pain")
            else:
                return self.symptom_mappings.get("chest_pain")

        # Shortness of breath variations ("shortnessofbreath", "sob")
        if (
            "shortness of breath" in s_norm
            or "shortnessofbreath" in s_compact
            or "sob" in s_norm.split()  # exact token
            or "breathlessness" in s_norm
            or "difficulty breathing" in s_norm
        ):
            return self.symptom_mappings.get("dyspnea")

        # Condition name detection (direct disease mentions)
        # If no explicit mapping matched, scan known condition codes
        # to build a minimal mapping on the fly.
        for code in self.codes_db.values():
            if code.category == "condition":
                disp = (code.display or "")
                disp_norm = norm_space(disp)
                disp_compact = norm_compact(disp)
                if disp and (disp.lower() in s_raw or disp_norm in s_norm or disp_compact in s_compact):
                    return SymptomMapping(
                        keywords=[disp_norm or disp.lower()],
                        primary_codes=[code],
                        related_codes=[],
                        differential_diagnosis=[],
                    )
                # synonyms match
                for syn in code.synonyms:
                    syn_norm = norm_space(syn)
                    syn_compact = norm_compact(syn)
                    if syn and (syn.lower() in s_raw or syn_norm in s_norm or syn_compact in s_compact):
                        return SymptomMapping(
                            keywords=[syn_norm or syn.lower()],
                            primary_codes=[code],
                            related_codes=[],
                            differential_diagnosis=[],
                        )

        # Add more fuzzy matching as needed
        return None
    
    def generate_medical_report(self, symptoms: List[str], patient_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate a medical report with clinical codes for given symptoms."""
        report = {
            "patient_info": patient_info or {},
            "timestamp": "2025-09-26T16:57:18Z",
            "symptoms_analyzed": [],
            "clinical_codes": [],
            "differential_diagnoses": set(),
            "recommendations": [],
            "report_summary": ""
        }
        
        for symptom in symptoms:
            mapping = self.find_codes_for_symptom(symptom)
            if mapping:
                symptom_data = {
                    "symptom": symptom,
                    "codes_found": [code.to_dict() for code in mapping.primary_codes],
                    "related_codes": [code.to_dict() for code in mapping.related_codes],
                    "differential_diagnosis": mapping.differential_diagnosis
                }
                report["symptoms_analyzed"].append(symptom_data)
                
                # Add codes to clinical codes list
                report["clinical_codes"].extend([code.to_dict() for code in mapping.primary_codes])
                
                # Add to differential diagnoses
                report["differential_diagnoses"].update(mapping.differential_diagnosis)
        
        # Convert set back to list
        report["differential_diagnoses"] = list(report["differential_diagnoses"])
        
        # Generate recommendations
        if report["symptoms_analyzed"]:
            report["recommendations"] = [
                "Clinical examination recommended",
                "Consider vital signs assessment",
                "Monitor symptom progression",
                "Seek medical attention if symptoms worsen"
            ]
            
            # Add specific recommendations based on symptoms
            symptom_texts = [s.lower() for s in symptoms]
            if any("fever" in s for s in symptom_texts):
                report["recommendations"].append("Monitor temperature regularly")
            if any("chest pain" in s for s in symptom_texts):
                report["recommendations"].append("Consider ECG if cardiac symptoms present")
            if any("cough" in s for s in symptom_texts):
                report["recommendations"].append("Consider chest X-ray if persistent")
        
        # Generate summary
        if report["symptoms_analyzed"]:
            primary_codes = len(report["clinical_codes"])
            dd_count = len(report["differential_diagnoses"])
            report["report_summary"] = (
                f"Analyzed {len(symptoms)} symptoms with {primary_codes} clinical codes identified. "
                f"{dd_count} differential diagnoses considered. Further clinical assessment recommended."
            )
        else:
            report["report_summary"] = "No clinical codes found for provided symptoms."
        
        return report


# Global instance for easy access
clinical_codes_cache = ClinicalCodesCache()


def get_clinical_codes_for_symptoms(symptoms: List[str]) -> Dict[str, Any]:
    """Convenience function to get clinical codes for symptoms."""
    return clinical_codes_cache.generate_medical_report(symptoms)


def search_codes_by_keyword(keyword: str) -> List[ClinicalCode]:
    """Search for codes by keyword."""
    results = []
    keyword_lower = keyword.lower()
    
    for code in clinical_codes_cache.codes_db.values():
        if (keyword_lower in code.display.lower() or 
            keyword_lower in (code.description or "").lower() or
            any(keyword_lower in synonym.lower() for synonym in code.synonyms)):
            results.append(code)
    
    return results


# Example usage for testing
if __name__ == "__main__":
    # Test the system
    test_symptoms = [
        "cough", 
        "chest pain", 
        "fever",
        "shortness of breath"
    ]
    
    patient_data = {
        "symptom": "cough",
        "duration": "5 days", 
        "associated_symptom": "chest pain"
    }
    
    report = get_clinical_codes_for_symptoms(test_symptoms)
    print("Medical Report:")
    print(json.dumps(report, indent=2))
    
    print("\n" + "="*50)
    print("Search Results for 'cough':")
    cough_codes = search_codes_by_keyword("cough")
    for code in cough_codes:
        print(f"- {code.code} ({code.system.value}): {code.display}")