"""
Unit tests for NHS Terminology Server integration.

Tests the enhanced NHS Terminology Server integration including:
- OAuth 2.0 authentication
- SNOMED CT, ICD-10, and dm+d terminology lookups
- Code validation and translation
- FHIR bundle enhancement
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from services.nhs_terminology import (
    NHSTerminologyService,
    TerminologySystem,
    TerminologyConcept,
    ClinicalCodingService,
    DrugInformation,
    ConceptMapping
)
from services.fhir_bundle_enhancer import FHIRBundleEnhancer, ProvenanceInfo
from services.agents.coding_agent import CodingAgent


class TestNHSTerminologyService:
    """Test NHS Terminology Service functionality."""
    
    @pytest.fixture
    def terminology_service(self):
        """Create a mock terminology service for testing."""
        service = NHSTerminologyService(
            base_url="https://ontology.nhs.uk/production1/fhir",
            auth_url="https://ontology.nhs.uk/authorisation/auth/realms/nhs-digital-terminology/protocol/openid-connect/token",
            client_id="test_client_id",
            client_secret="test_client_secret"
        )
        return service
    
    @pytest.mark.asyncio
    async def test_oauth_token_retrieval(self, terminology_service):
        """Test OAuth 2.0 token retrieval."""
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {
                "access_token": "test_token",
                "expires_in": 3600
            }
            mock_post.return_value = mock_response
            
            token = await terminology_service._get_access_token()
            
            assert token == "test_token"
            assert terminology_service.access_token == "test_token"
            assert terminology_service.token_expires is not None
    
    @pytest.mark.asyncio
    async def test_concept_lookup(self, terminology_service):
        """Test concept lookup functionality."""
        with patch.object(terminology_service, '_make_request') as mock_request:
            mock_request.return_value = {
                "resourceType": "Parameters",
                "parameter": [
                    {"name": "name", "valueString": "29857009"},
                    {"name": "display", "valueString": "Chest pain"},
                    {"name": "definition", "valueString": "Pain in the chest"}
                ]
            }
            
            concept = await terminology_service.lookup_concept(
                TerminologySystem.SNOMED_CT,
                "29857009"
            )
            
            assert concept is not None
            assert concept.code == "29857009"
            assert concept.display == "Chest pain"
            assert concept.system == "http://snomed.info/sct"
    
    @pytest.mark.asyncio
    async def test_code_validation(self, terminology_service):
        """Test code validation functionality."""
        with patch.object(terminology_service, '_make_request') as mock_request:
            mock_request.return_value = {
                "resourceType": "Parameters",
                "parameter": [
                    {"name": "result", "valueBoolean": True}
                ]
            }
            
            is_valid = await terminology_service.validate_code(
                TerminologySystem.SNOMED_CT,
                "29857009",
                "Chest pain"
            )
            
            assert is_valid is True
    
    @pytest.mark.asyncio
    async def test_concept_search(self, terminology_service):
        """Test concept search functionality."""
        with patch.object(terminology_service, '_make_request') as mock_request:
            mock_request.return_value = {
                "resourceType": "ValueSet",
                "expansion": {
                    "contains": [
                        {
                            "code": "29857009",
                            "display": "Chest pain",
                            "system": "http://snomed.info/sct"
                        },
                        {
                            "code": "29857010",
                            "display": "Chest pain, unspecified",
                            "system": "http://snomed.info/sct"
                        }
                    ]
                }
            }
            
            concepts = await terminology_service.search_concepts(
                TerminologySystem.SNOMED_CT,
                "chest pain",
                limit=10
            )
            
            assert len(concepts) == 2
            assert concepts[0].code == "29857009"
            assert concepts[0].display == "Chest pain"
    
    @pytest.mark.asyncio
    async def test_code_translation(self, terminology_service):
        """Test code translation between terminology systems."""
        with patch.object(terminology_service, '_make_request') as mock_request:
            mock_request.return_value = {
                "resourceType": "Parameters",
                "parameter": [
                    {
                        "name": "match",
                        "part": [
                            {
                                "name": "concept",
                                "valueCoding": {
                                    "code": "R07.9",
                                    "display": "Chest pain, unspecified"
                                }
                            },
                            {
                                "name": "equivalence",
                                "valueCode": "equivalent"
                            }
                        ]
                    }
                ]
            }
            
            mappings = await terminology_service.translate_code(
                TerminologySystem.SNOMED_CT,
                "29857009",
                TerminologySystem.ICD_10
            )
            
            assert len(mappings) == 1
            assert mappings[0].source_code == "29857009"
            assert mappings[0].target_code == "R07.9"
            assert mappings[0].equivalence == "equivalent"
    
    @pytest.mark.asyncio
    async def test_drug_information_lookup(self, terminology_service):
        """Test drug information lookup from dm+d."""
        with patch.object(terminology_service, 'lookup_concept') as mock_lookup:
            mock_concept = TerminologyConcept(
                code="123456789",
                system="https://dmd.nhs.uk",
                display="Metformin 500mg tablets",
                properties={
                    "VTM": "123456",
                    "VMP": "789012",
                    "strength": "500mg",
                    "form": "tablet"
                },
                designations=[
                    {"use": "preferred", "value": "Metformin"}
                ]
            )
            mock_lookup.return_value = mock_concept
            
            drug_info = await terminology_service.get_drug_information("123456789")
            
            assert drug_info is not None
            assert drug_info.name == "Metformin 500mg tablets"
            assert drug_info.vtm_id == "123456"
            assert drug_info.strength == "500mg"
            assert drug_info.generic_name == "Metformin"
    
    @pytest.mark.asyncio
    async def test_health_check(self, terminology_service):
        """Test health check functionality."""
        with patch.object(terminology_service, '_make_request') as mock_request:
            mock_request.return_value = {
                "software": {
                    "name": "NHS Terminology Server",
                    "version": "1.0.0"
                },
                "fhirVersion": "4.0.1"
            }
            
            health = await terminology_service.health_check()
            
            assert health["status"] == "healthy"
            assert health["server_name"] == "NHS Terminology Server"
            assert health["fhir_version"] == "4.0.1"


class TestClinicalCodingService:
    """Test Clinical Coding Service functionality."""
    
    @pytest.fixture
    def coding_service(self):
        """Create a mock coding service for testing."""
        mock_terminology = Mock()
        coding_service = ClinicalCodingService(mock_terminology)
        return coding_service
    
    @pytest.mark.asyncio
    async def test_diagnosis_coding(self, coding_service):
        """Test diagnosis coding functionality."""
        # Mock the terminology service
        mock_concepts = [
            TerminologyConcept(
                code="29857009",
                display="Chest pain",
                system="http://snomed.info/sct"
            ),
            TerminologyConcept(
                code="29857010",
                display="Chest pain, unspecified",
                system="http://snomed.info/sct"
            )
        ]
        
        coding_service.terminology.search_concepts = AsyncMock(return_value=mock_concepts)
        
        coded_diagnoses = await coding_service.code_diagnosis("chest pain")
        
        assert len(coded_diagnoses) == 2
        assert coded_diagnoses[0]["snomed_code"] == "29857009"
        assert coded_diagnoses[0]["snomed_display"] == "Chest pain"
        assert coded_diagnoses[0]["relevance_score"] > 0
    
    @pytest.mark.asyncio
    async def test_medication_coding(self, coding_service):
        """Test medication coding functionality."""
        # Mock the terminology service
        mock_concepts = [
            TerminologyConcept(
                code="123456789",
                display="Metformin 500mg tablets",
                system="https://dmd.nhs.uk"
            )
        ]
        
        mock_drug_info = DrugInformation(
            name="Metformin 500mg tablets",
            vtm_id="123456",
            strength="500mg",
            form="tablet",
            generic_name="Metformin"
        )
        
        coding_service.terminology.search_concepts = AsyncMock(return_value=mock_concepts)
        coding_service.terminology.get_drug_information = AsyncMock(return_value=mock_drug_info)
        
        drug_infos = await coding_service.code_medication("metformin")
        
        assert len(drug_infos) == 1
        assert drug_infos[0].name == "Metformin 500mg tablets"
        assert drug_infos[0].strength == "500mg"
    
    def test_text_relevance_calculation(self, coding_service):
        """Test text relevance calculation."""
        # Exact match
        score = coding_service._calculate_text_relevance("chest pain", "chest pain")
        assert score == 1.0
        
        # Substring match
        score = coding_service._calculate_text_relevance("chest", "chest pain")
        assert score == 0.8
        
        # Word overlap
        score = coding_service._calculate_text_relevance("chest pain", "pain in chest")
        assert score > 0.6
        
        # No match
        score = coding_service._calculate_text_relevance("headache", "chest pain")
        assert score == 0.0


class TestFHIRBundleEnhancer:
    """Test FHIR Bundle Enhancer functionality."""
    
    @pytest.fixture
    def bundle_enhancer(self):
        """Create a mock bundle enhancer for testing."""
        mock_terminology = Mock()
        enhancer = FHIRBundleEnhancer(mock_terminology)
        return enhancer
    
    @pytest.fixture
    def sample_bundle(self):
        """Create a sample FHIR bundle for testing."""
        return {
            "resourceType": "Bundle",
            "type": "collection",
            "entry": [
                {
                    "resource": {
                        "resourceType": "Condition",
                        "id": "condition-001",
                        "code": {
                            "text": "Chest pain",
                            "coding": [
                                {
                                    "system": "http://snomed.info/sct",
                                    "code": "29857009",
                                    "display": "Chest pain"
                                }
                            ]
                        }
                    }
                },
                {
                    "resource": {
                        "resourceType": "MedicationRequest",
                        "id": "medication-001",
                        "medicationCodeableConcept": {
                            "text": "Metformin",
                            "coding": [
                                {
                                    "system": "https://dmd.nhs.uk",
                                    "code": "123456789",
                                    "display": "Metformin 500mg tablets"
                                }
                            ]
                        }
                    }
                }
            ]
        }
    
    @pytest.mark.asyncio
    async def test_bundle_enhancement(self, bundle_enhancer, sample_bundle):
        """Test FHIR bundle enhancement."""
        # Mock the coding service
        mock_coding_service = Mock()
        mock_coding_service.code_diagnosis = AsyncMock(return_value=[
            {"snomed_code": "29857009", "snomed_display": "Chest pain", "relevance_score": 1.0}
        ])
        mock_coding_service.code_medication = AsyncMock(return_value=[
            DrugInformation(name="Metformin 500mg tablets", vtm_id="123456")
        ])
        
        bundle_enhancer.coding_service = mock_coding_service
        
        enhanced_bundle = await bundle_enhancer.enhance_bundle(sample_bundle)
        
        assert enhanced_bundle["resourceType"] == "Bundle"
        assert len(enhanced_bundle["entry"]) == 2
        
        # Check that provenance was added
        condition = enhanced_bundle["entry"][0]["resource"]
        assert "extension" in condition
    
    def test_provenance_info_creation(self):
        """Test provenance information creation."""
        provenance = ProvenanceInfo(
            terminology_server="NHS Terminology Server",
            environment="production1",
            source_system="DigiClinic"
        )
        
        provenance_dict = provenance.to_dict()
        
        assert provenance_dict["terminology_server"] == "NHS Terminology Server"
        assert provenance_dict["environment"] == "production1"
        assert provenance_dict["source_system"] == "DigiClinic"
        assert "timestamp" in provenance_dict
    
    def test_text_extraction(self, bundle_enhancer, sample_bundle):
        """Test text extraction from FHIR resources."""
        condition = sample_bundle["entry"][0]["resource"]
        medication = sample_bundle["entry"][1]["resource"]
        
        condition_text = bundle_enhancer._extract_condition_text(condition)
        medication_text = bundle_enhancer._extract_medication_text(medication)
        
        assert condition_text == "Chest pain"
        assert medication_text == "Metformin"


class TestCodingAgent:
    """Test Enhanced Coding Agent functionality."""
    
    @pytest.fixture
    def coding_agent(self):
        """Create a coding agent for testing."""
        return CodingAgent()
    
    def test_basic_coding_result(self, coding_agent):
        """Test basic heuristic coding."""
        result = coding_agent._get_basic_coding_result("I have chest pain")
        
        assert result.text == "Basic clinical codes suggested."
        assert "29857009" in result.data["snomed_ct"]
        assert "R07.9" in result.data["icd10"]
        assert "provenance" in result.data
    
    def test_term_extraction(self, coding_agent):
        """Test term extraction for coding."""
        summary = {
            "patient_summary": "Patient reports chest pain",
            "clinician_note": {
                "summary": "Chest pain with shortness of breath"
            }
        }
        
        terms = coding_agent._extract_terms_for_coding("I have chest pain", summary)
        
        assert len(terms) == 3
        assert "I have chest pain" in terms
        assert "Patient reports chest pain" in terms
        assert "Chest pain with shortness of breath" in terms
    
    def test_clinical_term_detection(self, coding_agent):
        """Test clinical term detection."""
        assert coding_agent._is_clinical_term("chest pain") is True
        assert coding_agent._is_clinical_term("hypertension") is True
        assert coding_agent._is_clinical_term("diabetes") is True
        assert coding_agent._is_clinical_term("hello world") is False
    
    def test_medication_term_detection(self, coding_agent):
        """Test medication term detection."""
        assert coding_agent._is_medication_term("metformin tablet") is True
        assert coding_agent._is_medication_term("500mg dose") is True
        assert coding_agent._is_medication_term("prescription") is True
        assert coding_agent._is_medication_term("chest pain") is False


class TestIntegration:
    """Integration tests for the complete NHS Terminology workflow."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_coding_workflow(self):
        """Test the complete coding workflow from text to FHIR codes."""
        # This would test the complete workflow:
        # 1. User input text
        # 2. Coding agent processes text
        # 3. NHS Terminology Server lookup
        # 4. FHIR bundle enhancement
        # 5. Provenance tracking
        
        # Mock the complete workflow
        with patch('services.nhs_terminology.NHSTerminologyService') as mock_service:
            # Setup mocks
            mock_service.return_value.__aenter__ = AsyncMock()
            mock_service.return_value.__aexit__ = AsyncMock()
            
            # Test the workflow
            coding_agent = CodingAgent()
            result = coding_agent.run(
                ctx=Mock(),
                user_text="I have chest pain and take metformin",
                summary={"patient_summary": "Chest pain with diabetes"}
            )
            
            assert result.text is not None
            assert "data" in result.data
            assert "provenance" in result.data


if __name__ == "__main__":
    pytest.main([__file__])
