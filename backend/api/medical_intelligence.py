"""API endpoints for Phase 2 Medical Intelligence services."""

import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import tempfile
import os

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from auth import verify_token
from utils.error_handler import raise_medical_service_error, raise_validation_error, raise_file_processing_error
from utils.file_validator import FileValidator
from services.clinical_agents import (
    ClinicalAgentOrchestrator, HistoryTakingAgent, SymptomTriageAgent, 
    DifferentialDiagnosisAgent, ClinicalHistory, TriageAssessment
)
from services.nhs_terminology import (
    NHSTerminologyService, ClinicalCodingService, TerminologySystem,
    TerminologyConcept, ConceptMapping, DrugInformation
)
from services.vision_processing import (
    MedicalVisionService, ImageType, AnalysisLevel, ImageAnalysis
)
from services.medical_knowledge import (
    MedicalKnowledgeBase, EvidenceBasedResponseGenerator,
    ClinicalEvidence, ClinicalRecommendation
)
from services.medical_observability import (
    init_medical_observability, medical_observability, EventType
)
from services.llm_router import DigiClinicLLMRouter
from medical.nice_cks import NiceCksDataSource
from model.patient import Patient


logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/api/medical", tags=["Medical Intelligence"])


# Pydantic models for request/response validation
class HistoryTakingRequest(BaseModel):
    patient_message: str = Field(..., description="Patient's description of their problem")
    patient_id: Optional[str] = Field(None, description="Patient identifier")
    session_id: Optional[str] = Field(None, description="Session identifier")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional conversation context")


class SymptomTriageRequest(BaseModel):
    chief_complaint: str = Field(..., description="Main reason for consultation")
    history_present_illness: str = Field(..., description="Current illness details")
    associated_symptoms: List[str] = Field(default=[], description="Associated symptoms")
    symptom_onset: Optional[str] = Field(None, description="When symptoms started")
    symptom_duration: Optional[str] = Field(None, description="Duration of symptoms")
    symptom_severity: Optional[str] = Field(None, description="Severity (1-10 scale)")
    patient_id: Optional[str] = Field(None, description="Patient identifier")


class ComprehensiveAssessmentRequest(BaseModel):
    patient_message: str = Field(..., description="Patient's description")
    patient_id: Optional[str] = Field(None, description="Patient identifier")
    session_id: Optional[str] = Field(None, description="Session identifier")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")


class TerminologyLookupRequest(BaseModel):
    system: str = Field(..., description="Terminology system (snomed_ct, icd_10, dm_d)")
    code: str = Field(..., description="Concept code to look up")
    properties: Optional[List[str]] = Field(None, description="Additional properties to retrieve")


class TerminologySearchRequest(BaseModel):
    system: str = Field(..., description="Terminology system")
    filter_text: str = Field(..., description="Search text")
    limit: int = Field(20, description="Maximum number of results", ge=1, le=100)


class CodeTranslationRequest(BaseModel):
    source_system: str = Field(..., description="Source terminology system")
    source_code: str = Field(..., description="Code to translate")
    target_system: str = Field(..., description="Target terminology system")


class ClinicalCodingRequest(BaseModel):
    diagnosis_text: str = Field(..., description="Natural language diagnosis description")


class DrugInteractionRequest(BaseModel):
    medications: List[str] = Field(..., description="Current medications")
    new_medication: str = Field(..., description="New medication to assess")


class EvidenceSearchRequest(BaseModel):
    query: str = Field(..., description="Search query")
    condition: Optional[str] = Field(None, description="Specific medical condition")
    limit: int = Field(10, description="Maximum number of results", ge=1, le=50)


class EvidenceBasedResponseRequest(BaseModel):
    query: str = Field(..., description="Medical query")
    clinical_context: Optional[Dict[str, Any]] = Field(None, description="Clinical context")
    patient_factors: Optional[Dict[str, Any]] = Field(None, description="Patient factors")


# Dependency injection for services
async def get_llm_router() -> DigiClinicLLMRouter:
    """Get LLM router instance."""
    # This would typically be dependency injected from app state
    return DigiClinicLLMRouter()


async def get_nhs_terminology() -> NHSTerminologyService:
    """Get NHS terminology service instance."""
    return NHSTerminologyService()


async def get_nice_data_source() -> NiceCksDataSource:
    """Get NICE data source instance."""
    return NiceCksDataSource()


async def get_clinical_orchestrator(
    llm_router: DigiClinicLLMRouter = Depends(get_llm_router),
    nice_data: NiceCksDataSource = Depends(get_nice_data_source)
) -> ClinicalAgentOrchestrator:
    """Get clinical agent orchestrator."""
    return ClinicalAgentOrchestrator(llm_router, nice_data)


async def get_medical_vision_service(
    llm_router: DigiClinicLLMRouter = Depends(get_llm_router),
    nhs_terminology: NHSTerminologyService = Depends(get_nhs_terminology)
) -> MedicalVisionService:
    """Get medical vision service."""
    return MedicalVisionService(llm_router, nhs_terminology)


async def get_evidence_generator(
    llm_router: DigiClinicLLMRouter = Depends(get_llm_router),
    nice_data: NiceCksDataSource = Depends(get_nice_data_source),
    nhs_terminology: NHSTerminologyService = Depends(get_nhs_terminology)
) -> EvidenceBasedResponseGenerator:
    """Get evidence-based response generator."""
    knowledge_base = MedicalKnowledgeBase(nice_data, nhs_terminology)
    return EvidenceBasedResponseGenerator(llm_router, knowledge_base, nhs_terminology)


# Clinical Agents Endpoints
@router.post("/clinical/history-taking")
async def take_clinical_history(
    request: HistoryTakingRequest,
    token_data: dict = Depends(verify_token),
    orchestrator: ClinicalAgentOrchestrator = Depends(get_clinical_orchestrator)
):
    """Take structured clinical history from patient input."""
    try:
        # Get patient information if patient_id provided
        patient = None
        if request.patient_id:
            # In production, load from database
            patient = Patient(
                name="Patient",
                national_insurance=request.patient_id,
                age=None,
                medical_history=[],
                current_medications=[]
            )
        
        # Get follow-up questions
        questions = await orchestrator.get_follow_up_questions(
            patient_message=request.patient_message,
            patient=patient,
            context=request.context
        )
        
        return {
            "success": True,
            "follow_up_questions": questions,
            "session_id": request.session_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise_medical_service_error(e, "Clinical History Taking")


@router.post("/clinical/comprehensive-assessment")
async def comprehensive_clinical_assessment(
    request: ComprehensiveAssessmentRequest,
    token_data: dict = Depends(verify_token),
    orchestrator: ClinicalAgentOrchestrator = Depends(get_clinical_orchestrator)
):
    """Perform comprehensive clinical assessment using all agents."""
    try:
        # Get patient information if patient_id provided
        patient = None
        if request.patient_id:
            # In production, load from database
            patient = Patient(
                name="Patient",
                national_insurance=request.patient_id,
                age=None,
                medical_history=[],
                current_medications=[]
            )
        
        # Perform comprehensive assessment
        assessment = await orchestrator.comprehensive_assessment(
            patient_message=request.patient_message,
            patient=patient,
            context=request.context
        )
        
        return {
            "success": True,
            "assessment": assessment,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise_medical_service_error(e, "Comprehensive Clinical Assessment")


# NHS Terminology Endpoints
@router.post("/terminology/lookup")
async def lookup_terminology_concept(
    request: TerminologyLookupRequest,
    token_data: dict = Depends(verify_token),
    nhs_terminology: NHSTerminologyService = Depends(get_nhs_terminology)
):
    """Look up a concept by code in a terminology system."""
    try:
        # Map string to enum
        system_map = {
            "snomed_ct": TerminologySystem.SNOMED_CT,
            "icd_10": TerminologySystem.ICD_10,
            "dm_d": TerminologySystem.DM_D,
            "read_v2": TerminologySystem.READ_V2,
            "read_ctv3": TerminologySystem.READ_CTV3
        }
        
        system = system_map.get(request.system)
        if not system:
            raise HTTPException(status_code=400, detail=f"Unsupported terminology system: {request.system}")
        
        async with nhs_terminology:
            concept = await nhs_terminology.lookup_concept(
                system=system,
                code=request.code,
                properties=request.properties
            )
        
        if concept:
            return {
                "success": True,
                "concept": concept.to_dict(),
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            return {
                "success": False,
                "message": "Concept not found",
                "timestamp": datetime.utcnow().isoformat()
            }
        
    except Exception as e:
        logger.error(f"Terminology lookup failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/terminology/search")
async def search_terminology_concepts(
    request: TerminologySearchRequest,
    token_data: dict = Depends(verify_token),
    nhs_terminology: NHSTerminologyService = Depends(get_nhs_terminology)
):
    """Search for concepts in a terminology system."""
    try:
        system_map = {
            "snomed_ct": TerminologySystem.SNOMED_CT,
            "icd_10": TerminologySystem.ICD_10,
            "dm_d": TerminologySystem.DM_D
        }
        
        system = system_map.get(request.system)
        if not system:
            raise HTTPException(status_code=400, detail=f"Unsupported terminology system: {request.system}")
        
        async with nhs_terminology:
            concepts = await nhs_terminology.search_concepts(
                system=system,
                filter_text=request.filter_text,
                limit=request.limit
            )
        
        return {
            "success": True,
            "concepts": [concept.to_dict() for concept in concepts],
            "count": len(concepts),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Terminology search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/terminology/translate")
async def translate_code(
    request: CodeTranslationRequest,
    token_data: dict = Depends(verify_token),
    nhs_terminology: NHSTerminologyService = Depends(get_nhs_terminology)
):
    """Translate a code from one terminology system to another."""
    try:
        system_map = {
            "snomed_ct": TerminologySystem.SNOMED_CT,
            "icd_10": TerminologySystem.ICD_10,
            "dm_d": TerminologySystem.DM_D
        }
        
        source_system = system_map.get(request.source_system)
        target_system = system_map.get(request.target_system)
        
        if not source_system or not target_system:
            raise HTTPException(status_code=400, detail="Unsupported terminology system")
        
        async with nhs_terminology:
            mappings = await nhs_terminology.translate_code(
                source_system=source_system,
                source_code=request.source_code,
                target_system=target_system
            )
        
        return {
            "success": True,
            "mappings": [mapping.to_dict() for mapping in mappings],
            "count": len(mappings),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Code translation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clinical/code-diagnosis")
async def code_clinical_diagnosis(
    request: ClinicalCodingRequest,
    token_data: dict = Depends(verify_token),
    nhs_terminology: NHSTerminologyService = Depends(get_nhs_terminology)
):
    """Suggest SNOMED CT codes for a diagnosis description."""
    try:
        clinical_coding = ClinicalCodingService(nhs_terminology)
        
        async with nhs_terminology:
            coded_diagnoses = await clinical_coding.code_diagnosis(request.diagnosis_text)
        
        return {
            "success": True,
            "diagnosis_text": request.diagnosis_text,
            "coded_diagnoses": coded_diagnoses,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Clinical coding failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/terminology/drug/{dmd_code}")
async def get_drug_information(
    dmd_code: str,
    token_data: dict = Depends(verify_token),
    nhs_terminology: NHSTerminologyService = Depends(get_nhs_terminology)
):
    """Get drug information from dm+d."""
    try:
        async with nhs_terminology:
            drug_info = await nhs_terminology.get_drug_information(dmd_code)
        
        if drug_info:
            return {
                "success": True,
                "drug_information": drug_info.to_dict(),
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            return {
                "success": False,
                "message": "Drug information not found",
                "timestamp": datetime.utcnow().isoformat()
            }
        
    except Exception as e:
        logger.error(f"Drug information lookup failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Medical Vision Processing Endpoints
@router.post("/vision/analyze")
async def analyze_medical_image(
    file: UploadFile = File(..., description="Medical image file"),
    analysis_level: str = Form("clinical", description="Analysis level: basic, clinical, diagnostic, detailed"),
    patient_id: Optional[str] = Form(None, description="Patient identifier"),
    token_data: dict = Depends(verify_token),
    vision_service: MedicalVisionService = Depends(get_medical_vision_service)
):
    """Analyze medical image using AI vision processing."""
    try:
        # Validate analysis level
        level_map = {
            "basic": AnalysisLevel.BASIC,
            "clinical": AnalysisLevel.CLINICAL,
            "diagnostic": AnalysisLevel.DIAGNOSTIC,
            "detailed": AnalysisLevel.DETAILED
        }
        
        analysis_level_enum = level_map.get(analysis_level)
        if not analysis_level_enum:
            raise HTTPException(status_code=400, detail="Invalid analysis level")
        
        # Comprehensive medical image file validation
        FileValidator.validate_medical_image_file(file)
        
        # Read image data after validation
        image_data = await file.read()
        
        # Prepare patient context
        patient_context = {}
        if patient_id:
            patient_context["patient_id"] = patient_id
            # In production, load additional patient context from database
        
        # Process image
        result = await vision_service.process_medical_image(
            image_data=image_data,
            filename=file.filename or "image.jpg",
            analysis_level=analysis_level_enum,
            patient_id=patient_id,
            patient_context=patient_context
        )
        
        return result
        
    except Exception as e:
        raise_file_processing_error(e, "medical image")


@router.get("/vision/analysis/{image_id}")
async def get_image_analysis(
    image_id: str,
    token_data: dict = Depends(verify_token),
    vision_service: MedicalVisionService = Depends(get_medical_vision_service)
):
    """Retrieve stored image analysis results."""
    try:
        analysis = vision_service.get_analysis(image_id)
        
        if analysis:
            return {
                "success": True,
                "analysis": analysis,
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            raise HTTPException(status_code=404, detail="Analysis not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve image analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vision/formats")
async def get_supported_image_formats(
    token_data: dict = Depends(verify_token),
    vision_service: MedicalVisionService = Depends(get_medical_vision_service)
):
    """Get list of supported image formats."""
    try:
        formats = vision_service.list_supported_formats()
        
        return {
            "success": True,
            "supported_formats": formats,
            "max_file_size_mb": 10,
            "max_dimension": 2048,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get supported formats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Medical Knowledge Base Endpoints
@router.post("/knowledge/search-evidence")
async def search_clinical_evidence(
    request: EvidenceSearchRequest,
    token_data: dict = Depends(verify_token),
    evidence_generator: EvidenceBasedResponseGenerator = Depends(get_evidence_generator)
):
    """Search for clinical evidence related to a query."""
    try:
        evidence_list = await evidence_generator.knowledge_base.search_evidence(
            query=request.query,
            condition=request.condition,
            limit=request.limit
        )
        
        return {
            "success": True,
            "query": request.query,
            "evidence": [evidence.to_dict() for evidence in evidence_list],
            "count": len(evidence_list),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Evidence search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/knowledge/drug-interactions")
async def assess_drug_interactions(
    request: DrugInteractionRequest,
    token_data: dict = Depends(verify_token),
    evidence_generator: EvidenceBasedResponseGenerator = Depends(get_evidence_generator)
):
    """Assess potential drug interactions."""
    try:
        interaction_assessment = await evidence_generator.knowledge_base.assess_drug_interactions(
            medications=request.medications,
            new_medication=request.new_medication
        )
        
        return {
            "success": True,
            "interaction_assessment": interaction_assessment,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Drug interaction assessment failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/knowledge/evidence-based-response")
async def generate_evidence_based_response(
    request: EvidenceBasedResponseRequest,
    token_data: dict = Depends(verify_token),
    evidence_generator: EvidenceBasedResponseGenerator = Depends(get_evidence_generator)
):
    """Generate evidence-based medical response."""
    try:
        response = await evidence_generator.generate_evidence_based_response(
            query=request.query,
            clinical_context=request.clinical_context,
            patient_factors=request.patient_factors
        )
        
        return {
            "success": True,
            "evidence_based_response": response,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Evidence-based response generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Health Check Endpoints
@router.get("/health/nhs-terminology")
async def check_nhs_terminology_health(
    token_data: dict = Depends(verify_token),
    nhs_terminology: NHSTerminologyService = Depends(get_nhs_terminology)
):
    """Check NHS terminology service health."""
    try:
        async with nhs_terminology:
            health_status = await nhs_terminology.health_check()
        
        return health_status
        
    except Exception as e:
        logger.error(f"NHS terminology health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@router.get("/health/vision-processing")
async def check_vision_processing_health(
    token_data: dict = Depends(verify_token),
    vision_service: MedicalVisionService = Depends(get_medical_vision_service)
):
    """Check vision processing service health."""
    try:
        health_status = await vision_service.health_check()
        return health_status
        
    except Exception as e:
        logger.error(f"Vision processing health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@router.get("/health/observability")
async def check_observability_health(token_data: dict = Depends(verify_token)):
    """Check medical observability health."""
    try:
        if medical_observability and medical_observability.enabled:
            return {
                "status": "healthy",
                "enabled": True,
                "environment": medical_observability.environment,
                "events_stored": len(medical_observability.events_store),
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            return {
                "status": "healthy",
                "enabled": False,
                "message": "Observability disabled (no credentials provided)",
                "timestamp": datetime.utcnow().isoformat()
            }
        
    except Exception as e:
        logger.error(f"Observability health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


# Compliance Reporting Endpoints
@router.get("/compliance/report")
async def get_compliance_report(
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    event_types: Optional[str] = Query(None, description="Comma-separated event types"),
    token_data: dict = Depends(verify_token)
):
    """Generate compliance report for medical events."""
    try:
        if not medical_observability or not medical_observability.enabled:
            raise HTTPException(status_code=503, detail="Observability service not available")
        
        # Parse parameters
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None
        
        event_type_list = None
        if event_types:
            event_type_list = [EventType(et.strip()) for et in event_types.split(",")]
        
        # Generate report
        report = medical_observability.get_compliance_report(
            start_date=start_dt,
            end_date=end_dt,
            event_types=event_type_list
        )
        
        return {
            "success": True,
            "compliance_report": report,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid parameter: {str(e)}")
    except Exception as e:
        logger.error(f"Compliance report generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# System Status Endpoint
@router.get("/system/status")
async def get_system_status(token_data: dict = Depends(verify_token)):
    """Get overall system status for Phase 2 services."""
    try:
        # This would check all services in parallel in production
        status = {
            "phase_2_services": {
                "clinical_agents": "operational",
                "nhs_terminology": "operational", 
                "vision_processing": "operational",
                "medical_knowledge": "operational",
                "observability": "operational" if medical_observability and medical_observability.enabled else "disabled"
            },
            "service_versions": {
                "clinical_agents": "2.0.0",
                "nhs_terminology": "1.0.0",
                "vision_processing": "1.0.0", 
                "medical_knowledge": "1.0.0",
                "observability": "1.0.0"
            },
            "timestamp": datetime.utcnow().isoformat(),
            "phase": "Phase 2 - Enhanced Medical Intelligence"
        }
        
        return status
        
    except Exception as e:
        logger.error(f"System status check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))