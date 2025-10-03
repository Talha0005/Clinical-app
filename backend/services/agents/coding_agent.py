from __future__ import annotations
from typing import Any, Optional, Dict, List
import asyncio
import logging
from datetime import datetime
from .base import Agent, AgentContext, AgentResult
from ..nhs_terminology import NHSTerminologyService, TerminologySystem, ClinicalCodingService

logger = logging.getLogger(__name__)


class CodingAgent(Agent):
    """Enhanced FHIR Coding Agent with NHS Terminology Server integration.
    
    Provides real-time terminology lookup, validation, and coding for:
    - SNOMED CT UK Edition (clinical terms, conditions, symptoms, procedures)
    - Dictionary of Medicines and Devices (dm+d) for medication coding
    - ICD-10 for diagnostic classification and reporting
    """

    name = "coding"

    def __init__(self):
        """Initialize the coding agent with NHS Terminology Service."""
        self.terminology_service = None
        self.coding_service = None
        self._initialized = False

    async def _initialize_services(self):
        """Initialize NHS terminology services if not already done."""
        if self._initialized:
            return

        try:
            # Initialize NHS Terminology Service with OAuth 2.0 credentials
            import os
            self.terminology_service = NHSTerminologyService(
                base_url="https://ontology.nhs.uk/production1/fhir",  # Sandbox/test environment
                auth_url="https://ontology.nhs.uk/authorisation/auth/realms/nhs-digital-terminology/protocol/openid-connect/token",
                client_id=os.getenv("NHS_TERMINOLOGY_CLIENT_ID"),  # From environment variables
                client_secret=os.getenv("NHS_TERMINOLOGY_CLIENT_SECRET"),  # From environment variables
            )
            
            # Initialize clinical coding service
            self.coding_service = ClinicalCodingService(self.terminology_service)
            self._initialized = True
            
        except Exception as e:
            logger.warning(f"Failed to initialize NHS Terminology Service: {e}")
            # Fall back to basic heuristic coding
            self._initialized = True

    def run(
        self,
        ctx: AgentContext,
        user_text: str,
        *,
        llm: Optional[Any] = None,
        summary: Optional[Dict] = None,
    ) -> AgentResult:
        """Run the coding agent with NHS terminology integration."""
        
        # Initialize services if needed
        if not self._initialized:
            try:
                # Run async initialization in sync context
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If we're already in an async context, create a new task
                    asyncio.create_task(self._initialize_services())
                else:
                    loop.run_until_complete(self._initialize_services())
            except Exception as e:
                logger.error(f"Failed to initialize coding services: {e}")

        # Try NHS terminology service first, fall back to heuristics
        if self.coding_service:
            try:
                # Run async coding operations
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Create task for async operations
                    task = asyncio.create_task(self._perform_advanced_coding(user_text, summary))
                    # For now, return basic result and let async operations complete in background
                    return self._get_basic_coding_result(user_text)
                else:
                    return loop.run_until_complete(self._perform_advanced_coding(user_text, summary))
            except Exception as e:
                logger.error(f"Advanced coding failed, falling back to basic: {e}")
        
        # Fall back to basic heuristic coding
        return self._get_basic_coding_result(user_text)

    async def _perform_advanced_coding(self, user_text: str, summary: Optional[Dict] = None) -> AgentResult:
        """Perform advanced coding using NHS Terminology Server."""
        try:
            async with self.terminology_service as terminology:
                # Extract key terms from user text and summary
                terms_to_code = self._extract_terms_for_coding(user_text, summary)
                
                coded_results = {
                    "snomed_ct": [],
                    "icd10": [],
                    "dmd": [],
                    "provenance": {
                        "terminology_server": "NHS Terminology Server",
                        "timestamp": datetime.utcnow().isoformat(),
                        "environment": "production1"  # Sandbox/test
                    }
                }

                # Code each term
                for term in terms_to_code:
                    # SNOMED CT coding for conditions/symptoms
                    if self._is_clinical_term(term):
                        snomed_codes = await self.coding_service.code_diagnosis(term)
                        coded_results["snomed_ct"].extend(snomed_codes)
                        
                        # Get ICD-10 mappings for top SNOMED codes
                        for snomed_code in snomed_codes[:3]:  # Top 3 matches
                            icd10_mappings = await self.coding_service.get_icd10_mapping(
                                snomed_code["snomed_code"]
                            )
                            for mapping in icd10_mappings:
                                coded_results["icd10"].append({
                                    "icd10_code": mapping.target_code,
                                    "icd10_display": mapping.target_display,
                                    "source_snomed": snomed_code["snomed_code"],
                                    "equivalence": mapping.equivalence
                                })

                    # dm+d coding for medications
                    elif self._is_medication_term(term):
                        drug_infos = await self.coding_service.code_medication(term)
                        for drug_info in drug_infos:
                            coded_results["dmd"].append(drug_info.to_dict())

                return AgentResult(
                    text="Clinical codes generated using NHS Terminology Server.",
                    data=coded_results
                )

        except Exception as e:
            logger.error(f"Advanced coding failed: {e}")
            return self._get_basic_coding_result(user_text)

    def _get_basic_coding_result(self, user_text: str) -> AgentResult:
        """Fallback basic heuristic coding."""
        text_l = user_text.lower()
        snomed: List[str] = []
        icd10: List[str] = []
        
        # Basic heuristic mappings
        if "chest pain" in text_l:
            snomed.append("29857009")  # Chest pain
            icd10.append("R07.9")
        if "headache" in text_l:
            snomed.append("25064002")  # Headache
            icd10.append("R51")
        if "hypertension" in text_l or "high blood pressure" in text_l:
            snomed.append("38341003")  # Hypertensive disorder
            icd10.append("I10")
        if "diabetes" in text_l:
            snomed.append("44054006")  # Diabetes mellitus
            icd10.append("E11")  # Type 2 diabetes
        if "fever" in text_l:
            snomed.append("386661006")  # Fever
            icd10.append("R50.9")
        if "cough" in text_l:
            snomed.append("49710002")  # Cough
            icd10.append("R05")

        data = {
            "snomed_ct": snomed, 
            "icd10": icd10,
            "provenance": {
                "method": "heuristic_fallback",
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        return AgentResult(text="Basic clinical codes suggested.", data=data)

    def _extract_terms_for_coding(self, user_text: str, summary: Optional[Dict] = None) -> List[str]:
        """Extract terms that need coding from user text and summary."""
        terms = []
        
        # Add user text
        terms.append(user_text)
        
        # Extract from summary if available
        if summary:
            if "patient_summary" in summary:
                terms.append(summary["patient_summary"])
            if "clinician_note" in summary:
                clinician_note = summary["clinician_note"]
                if isinstance(clinician_note, dict) and "summary" in clinician_note:
                    terms.append(clinician_note["summary"])
        
        return terms

    def _is_clinical_term(self, term: str) -> bool:
        """Check if term is likely a clinical condition/symptom."""
        clinical_keywords = [
            "pain", "ache", "disorder", "disease", "condition", "symptom",
            "syndrome", "infection", "inflammation", "hypertension", "diabetes",
            "fever", "cough", "headache", "nausea", "vomiting", "diarrhea"
        ]
        term_lower = term.lower()
        return any(keyword in term_lower for keyword in clinical_keywords)

    def _is_medication_term(self, term: str) -> bool:
        """Check if term is likely a medication."""
        medication_keywords = [
            "tablet", "capsule", "injection", "cream", "ointment", "drops",
            "metformin", "paracetamol", "ibuprofen", "aspirin", "insulin",
            "mg", "ml", "dose", "medication", "drug", "prescription"
        ]
        term_lower = term.lower()
        return any(keyword in term_lower for keyword in medication_keywords)
