"""
FHIR Bundle Enhancer for DigiClinic.

This module enhances FHIR bundles with:
- NHS Terminology Server codes (SNOMED CT, ICD-10, dm+d)
- Provenance tracking
- Clinical coding validation
- Enhanced metadata
"""

import json
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field

from .nhs_terminology import NHSTerminologyService, TerminologySystem, ClinicalCodingService

logger = logging.getLogger(__name__)


@dataclass
class ProvenanceInfo:
    """Provenance information for FHIR resources."""
    
    terminology_server: str = "NHS Terminology Server"
    environment: str = "production1"
    timestamp: datetime = field(default_factory=datetime.utcnow)
    version: Optional[str] = None
    source_system: str = "DigiClinic"
    coding_method: str = "automated"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "terminology_server": self.terminology_server,
            "environment": self.environment,
            "timestamp": self.timestamp.isoformat(),
            "version": self.version,
            "source_system": self.source_system,
            "coding_method": self.coding_method
        }


@dataclass
class CodingEnhancement:
    """Enhanced coding information for a FHIR resource."""
    
    original_coding: Dict[str, Any]
    enhanced_coding: Dict[str, Any]
    provenance: ProvenanceInfo
    validation_status: str = "validated"
    confidence_score: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "original_coding": self.original_coding,
            "enhanced_coding": self.enhanced_coding,
            "provenance": self.provenance.to_dict(),
            "validation_status": self.validation_status,
            "confidence_score": self.confidence_score
        }


class FHIRBundleEnhancer:
    """Enhances FHIR bundles with NHS terminology codes and provenance."""
    
    def __init__(self, terminology_service: Optional[NHSTerminologyService] = None):
        """
        Initialize FHIR bundle enhancer.
        
        Args:
            terminology_service: NHS Terminology Service instance
        """
        self.terminology_service = terminology_service
        self.coding_service = None
        
        if self.terminology_service:
            self.coding_service = ClinicalCodingService(self.terminology_service)
    
    async def enhance_bundle(
        self, 
        bundle: Dict[str, Any],
        enhance_conditions: bool = True,
        enhance_medications: bool = True,
        enhance_procedures: bool = True,
        enhance_observations: bool = True
    ) -> Dict[str, Any]:
        """
        Enhance a FHIR bundle with NHS terminology codes.
        
        Args:
            bundle: FHIR bundle to enhance
            enhance_conditions: Whether to enhance Condition resources
            enhance_medications: Whether to enhance MedicationRequest resources
            enhance_procedures: Whether to enhance Procedure resources
            enhance_observations: Whether to enhance Observation resources
            
        Returns:
            Enhanced FHIR bundle
        """
        if not self.coding_service:
            logger.warning("No terminology service available, returning original bundle")
            return bundle
        
        enhanced_bundle = bundle.copy()
        enhanced_entries = []
        
        for entry in bundle.get("entry", []):
            resource = entry.get("resource", {})
            resource_type = resource.get("resourceType")
            
            enhanced_resource = resource
            
            try:
                if resource_type == "Condition" and enhance_conditions:
                    enhanced_resource = await self._enhance_condition(resource)
                elif resource_type == "MedicationRequest" and enhance_medications:
                    enhanced_resource = await self._enhance_medication_request(resource)
                elif resource_type == "Procedure" and enhance_procedures:
                    enhanced_resource = await self._enhance_procedure(resource)
                elif resource_type == "Observation" and enhance_observations:
                    enhanced_resource = await self._enhance_observation(resource)
                
                # Add provenance extension
                enhanced_resource = self._add_provenance_extension(enhanced_resource)
                
            except Exception as e:
                logger.error(f"Error enhancing {resource_type} resource: {e}")
                # Keep original resource if enhancement fails
                enhanced_resource = resource
            
            enhanced_entry = entry.copy()
            enhanced_entry["resource"] = enhanced_resource
            enhanced_entries.append(enhanced_entry)
        
        enhanced_bundle["entry"] = enhanced_entries
        
        # Add bundle-level metadata
        enhanced_bundle = self._add_bundle_metadata(enhanced_bundle)
        
        return enhanced_bundle
    
    async def _enhance_condition(self, condition: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance a Condition resource with SNOMED CT codes."""
        enhanced_condition = condition.copy()
        
        # Get the condition text
        condition_text = self._extract_condition_text(condition)
        if not condition_text:
            return enhanced_condition
        
        try:
            # Get SNOMED CT codes
            snomed_codes = await self.coding_service.code_diagnosis(condition_text)
            
            if snomed_codes:
                # Use the top match
                top_code = snomed_codes[0]
                
                # Enhance the coding
                enhanced_coding = {
                    "system": "http://snomed.info/sct",
                    "code": top_code["snomed_code"],
                    "display": top_code["snomed_display"]
                }
                
                # Update the condition code
                if "code" in enhanced_condition:
                    enhanced_condition["code"]["coding"] = [enhanced_coding]
                else:
                    enhanced_condition["code"] = {"coding": [enhanced_coding]}
                
                # Add extension with additional codes
                if len(snomed_codes) > 1:
                    additional_codes = []
                    for code in snomed_codes[1:4]:  # Top 3 additional codes
                        additional_codes.append({
                            "system": "http://snomed.info/sct",
                            "code": code["snomed_code"],
                            "display": code["snomed_display"]
                        })
                    
                    if "extension" not in enhanced_condition:
                        enhanced_condition["extension"] = []
                    
                    enhanced_condition["extension"].append({
                        "url": "http://hl7.org/fhir/StructureDefinition/condition-additional-coding",
                        "valueCoding": additional_codes
                    })
        
        except Exception as e:
            logger.error(f"Error enhancing condition {condition_text}: {e}")
        
        return enhanced_condition
    
    async def _enhance_medication_request(self, medication: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance a MedicationRequest resource with dm+d codes."""
        enhanced_medication = medication.copy()
        
        # Get the medication text
        medication_text = self._extract_medication_text(medication)
        if not medication_text:
            return enhanced_medication
        
        try:
            # Get dm+d codes
            drug_infos = await self.coding_service.code_medication(medication_text)
            
            if drug_infos:
                # Use the top match
                top_drug = drug_infos[0]
                
                # Enhance the medication coding
                enhanced_coding = {
                    "system": "https://dmd.nhs.uk",
                    "code": top_drug.vmp_id or top_drug.amp_id,
                    "display": top_drug.name
                }
                
                # Update the medication code
                if "medicationCodeableConcept" in enhanced_medication:
                    enhanced_medication["medicationCodeableConcept"]["coding"] = [enhanced_coding]
                elif "medicationReference" in enhanced_medication:
                    # Convert reference to codeable concept
                    enhanced_medication["medicationCodeableConcept"] = {"coding": [enhanced_coding]}
                    del enhanced_medication["medicationReference"]
        
        except Exception as e:
            logger.error(f"Error enhancing medication {medication_text}: {e}")
        
        return enhanced_medication
    
    async def _enhance_procedure(self, procedure: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance a Procedure resource with SNOMED CT codes."""
        enhanced_procedure = procedure.copy()
        
        # Get the procedure text
        procedure_text = self._extract_procedure_text(procedure)
        if not procedure_text:
            return enhanced_procedure
        
        try:
            # Get SNOMED CT codes for procedures
            snomed_codes = await self.coding_service.code_diagnosis(procedure_text)
            
            if snomed_codes:
                # Use the top match
                top_code = snomed_codes[0]
                
                # Enhance the coding
                enhanced_coding = {
                    "system": "http://snomed.info/sct",
                    "code": top_code["snomed_code"],
                    "display": top_code["snomed_display"]
                }
                
                # Update the procedure code
                if "code" in enhanced_procedure:
                    enhanced_procedure["code"]["coding"] = [enhanced_coding]
                else:
                    enhanced_procedure["code"] = {"coding": [enhanced_coding]}
        
        except Exception as e:
            logger.error(f"Error enhancing procedure {procedure_text}: {e}")
        
        return enhanced_procedure
    
    async def _enhance_observation(self, observation: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance an Observation resource with LOINC codes."""
        enhanced_observation = observation.copy()
        
        # Get the observation text
        observation_text = self._extract_observation_text(observation)
        if not observation_text:
            return enhanced_observation
        
        try:
            # For observations, we might want to use LOINC codes
            # For now, we'll use SNOMED CT for consistency
            snomed_codes = await self.coding_service.code_diagnosis(observation_text)
            
            if snomed_codes:
                # Use the top match
                top_code = snomed_codes[0]
                
                # Enhance the coding
                enhanced_coding = {
                    "system": "http://snomed.info/sct",
                    "code": top_code["snomed_code"],
                    "display": top_code["snomed_display"]
                }
                
                # Update the observation code
                if "code" in enhanced_observation:
                    enhanced_observation["code"]["coding"] = [enhanced_coding]
                else:
                    enhanced_observation["code"] = {"coding": [enhanced_coding]}
        
        except Exception as e:
            logger.error(f"Error enhancing observation {observation_text}: {e}")
        
        return enhanced_observation
    
    def _extract_condition_text(self, condition: Dict[str, Any]) -> Optional[str]:
        """Extract text from a Condition resource."""
        # Try to get text from various fields
        if "code" in condition and "text" in condition["code"]:
            return condition["code"]["text"]
        
        if "code" in condition and "coding" in condition["code"]:
            codings = condition["code"]["coding"]
            if codings and "display" in codings[0]:
                return codings[0]["display"]
        
        return None
    
    def _extract_medication_text(self, medication: Dict[str, Any]) -> Optional[str]:
        """Extract text from a MedicationRequest resource."""
        # Try to get text from various fields
        if "medicationCodeableConcept" in medication:
            concept = medication["medicationCodeableConcept"]
            if "text" in concept:
                return concept["text"]
            if "coding" in concept and concept["coding"]:
                return concept["coding"][0].get("display")
        
        return None
    
    def _extract_procedure_text(self, procedure: Dict[str, Any]) -> Optional[str]:
        """Extract text from a Procedure resource."""
        # Try to get text from various fields
        if "code" in procedure and "text" in procedure["code"]:
            return procedure["code"]["text"]
        
        if "code" in procedure and "coding" in procedure["code"]:
            codings = procedure["code"]["coding"]
            if codings and "display" in codings[0]:
                return codings[0]["display"]
        
        return None
    
    def _extract_observation_text(self, observation: Dict[str, Any]) -> Optional[str]:
        """Extract text from an Observation resource."""
        # Try to get text from various fields
        if "code" in observation and "text" in observation["code"]:
            return observation["code"]["text"]
        
        if "code" in observation and "coding" in observation["code"]:
            codings = observation["code"]["coding"]
            if codings and "display" in codings[0]:
                return codings[0]["display"]
        
        return None
    
    def _add_provenance_extension(self, resource: Dict[str, Any]) -> Dict[str, Any]:
        """Add provenance extension to a resource."""
        enhanced_resource = resource.copy()
        
        if "extension" not in enhanced_resource:
            enhanced_resource["extension"] = []
        
        provenance = ProvenanceInfo()
        enhanced_resource["extension"].append({
            "url": "http://hl7.org/fhir/StructureDefinition/provenance",
            "valueString": json.dumps(provenance.to_dict())
        })
        
        return enhanced_resource
    
    def _add_bundle_metadata(self, bundle: Dict[str, Any]) -> Dict[str, Any]:
        """Add metadata to the bundle."""
        enhanced_bundle = bundle.copy()
        
        # Add enhancement metadata
        if "meta" not in enhanced_bundle:
            enhanced_bundle["meta"] = {}
        
        enhanced_bundle["meta"]["extension"] = [
            {
                "url": "http://hl7.org/fhir/StructureDefinition/bundle-enhancement",
                "valueString": json.dumps({
                    "enhanced_by": "DigiClinic FHIR Bundle Enhancer",
                    "enhancement_timestamp": datetime.utcnow().isoformat(),
                    "terminology_server": "NHS Terminology Server",
                    "enhancement_version": "1.0"
                })
            }
        ]
        
        return enhanced_bundle
    
    async def validate_bundle_codes(self, bundle: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate all codes in a FHIR bundle.
        
        Args:
            bundle: FHIR bundle to validate
            
        Returns:
            Validation results
        """
        if not self.terminology_service:
            return {"status": "skipped", "reason": "No terminology service available"}
        
        validation_results = {
            "status": "completed",
            "timestamp": datetime.utcnow().isoformat(),
            "validations": []
        }
        
        for entry in bundle.get("entry", []):
            resource = entry.get("resource", {})
            resource_type = resource.get("resourceType")
            
            if resource_type in ["Condition", "MedicationRequest", "Procedure", "Observation"]:
                validation = await self._validate_resource_codes(resource)
                validation_results["validations"].append(validation)
        
        return validation_results
    
    async def _validate_resource_codes(self, resource: Dict[str, Any]) -> Dict[str, Any]:
        """Validate codes in a single resource."""
        validation = {
            "resource_type": resource.get("resourceType"),
            "resource_id": resource.get("id"),
            "codes": []
        }
        
        # Extract and validate codes
        codes = self._extract_codes_from_resource(resource)
        
        for code_info in codes:
            try:
                is_valid = await self.terminology_service.validate_code(
                    code_info["system"], 
                    code_info["code"],
                    code_info.get("display")
                )
                
                validation["codes"].append({
                    "system": code_info["system"],
                    "code": code_info["code"],
                    "display": code_info.get("display"),
                    "valid": is_valid
                })
                
            except Exception as e:
                validation["codes"].append({
                    "system": code_info["system"],
                    "code": code_info["code"],
                    "display": code_info.get("display"),
                    "valid": False,
                    "error": str(e)
                })
        
        return validation
    
    def _extract_codes_from_resource(self, resource: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract codes from a FHIR resource."""
        codes = []
        
        # Look for codes in various locations
        if "code" in resource and "coding" in resource["code"]:
            for coding in resource["code"]["coding"]:
                codes.append({
                    "system": coding.get("system"),
                    "code": coding.get("code"),
                    "display": coding.get("display")
                })
        
        if "medicationCodeableConcept" in resource and "coding" in resource["medicationCodeableConcept"]:
            for coding in resource["medicationCodeableConcept"]["coding"]:
                codes.append({
                    "system": coding.get("system"),
                    "code": coding.get("code"),
                    "display": coding.get("display")
                })
        
        return codes


# Convenience functions
async def enhance_fhir_bundle_file(
    bundle_file: Path,
    output_file: Optional[Path] = None,
    terminology_service: Optional[NHSTerminologyService] = None
) -> Path:
    """
    Enhance a FHIR bundle file with NHS terminology codes.
    
    Args:
        bundle_file: Path to the FHIR bundle file
        output_file: Path for the enhanced bundle (optional)
        terminology_service: NHS Terminology Service instance
        
    Returns:
        Path to the enhanced bundle file
    """
    if output_file is None:
        output_file = bundle_file.parent / f"enhanced_{bundle_file.name}"
    
    # Load the bundle
    with open(bundle_file, 'r', encoding='utf-8') as f:
        bundle = json.load(f)
    
    # Enhance the bundle
    enhancer = FHIRBundleEnhancer(terminology_service)
    enhanced_bundle = await enhancer.enhance_bundle(bundle)
    
    # Save the enhanced bundle
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(enhanced_bundle, f, indent=2, ensure_ascii=False)
    
    return output_file


async def validate_fhir_bundle_file(
    bundle_file: Path,
    terminology_service: Optional[NHSTerminologyService] = None
) -> Dict[str, Any]:
    """
    Validate codes in a FHIR bundle file.
    
    Args:
        bundle_file: Path to the FHIR bundle file
        terminology_service: NHS Terminology Service instance
        
    Returns:
        Validation results
    """
    # Load the bundle
    with open(bundle_file, 'r', encoding='utf-8') as f:
        bundle = json.load(f)
    
    # Validate the bundle
    enhancer = FHIRBundleEnhancer(terminology_service)
    validation_results = await enhancer.validate_bundle_codes(bundle)
    
    return validation_results
