"""
Clinical Codes API for DigiClinic
Provides endpoints for clinical coding and medical report generation
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field

# Import the clinical codes cache
try:
    from services.clinical_codes_cache import (
        clinical_codes_cache,
        get_clinical_codes_for_symptoms,
        search_codes_by_keyword,
        ClinicalCode
    )
except ImportError:
    # Handle import errors gracefully
    clinical_codes_cache = None
    get_clinical_codes_for_symptoms = None
    search_codes_by_keyword = None

# Import auth for protected endpoints
try:
    from auth import verify_token
except ImportError:
    # Fallback for development
    def verify_token(token: str = None):
        return "demo_user"

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/clinical", tags=["clinical-codes"])


# Pydantic models for API requests/responses
class SymptomRequest(BaseModel):
    """Request model for symptom analysis."""
    symptoms: List[str] = Field(..., description="List of symptoms to analyze")
    patient_info: Optional[Dict[str, Any]] = Field(default=None, description="Optional patient information")
    duration: Optional[str] = Field(default=None, description="Duration of symptoms")
    associated_symptoms: Optional[List[str]] = Field(default=None, description="Associated symptoms")
    
    class Config:
        schema_extra = {
            "example": {
                "symptoms": ["cough", "chest pain"],
                "patient_info": {
                    "age": 35,
                    "gender": "male"
                },
                "duration": "5 days",
                "associated_symptoms": ["fever"]
            }
        }


class ClinicalCodeResponse(BaseModel):
    """Response model for clinical codes."""
    code: str
    display: str
    system: str
    description: Optional[str] = None
    category: Optional[str] = None
    body_system: Optional[str] = None
    synonyms: List[str] = []


class MedicalReportResponse(BaseModel):
    """Response model for medical reports."""
    success: bool
    patient_info: Dict[str, Any]
    symptoms_analyzed: List[Dict[str, Any]]
    clinical_codes: List[Dict[str, Any]]
    differential_diagnoses: List[str]
    recommendations: List[str]
    report_summary: str
    timestamp: str


class CodeSearchResponse(BaseModel):
    """Response model for code search."""
    success: bool
    query: str
    codes_found: List[ClinicalCodeResponse]
    total_results: int


class QuickCodeRequest(BaseModel):
    """Request model for quick symptom coding"""
    symptom: str = Field(..., description="Single symptom to get codes for")


@router.post("/analyze-symptoms", response_model=MedicalReportResponse)
async def analyze_symptoms(
    request: SymptomRequest,
    current_user: str = Depends(verify_token)
):
    """
    Analyze symptoms and generate medical report with clinical codes.
    
    This endpoint takes a list of symptoms and returns:
    - Relevant clinical codes (SNOMED CT, ICD-10, etc.)
    - Differential diagnoses
    - Clinical recommendations
    - Structured medical report
    """
    
    if not clinical_codes_cache:
        raise HTTPException(
            status_code=503,
            detail="Clinical codes service not available"
        )
    
    try:
        logger.info(f"Analyzing symptoms for user {current_user}: {request.symptoms}")
        
        # Combine all symptoms for analysis
        all_symptoms = request.symptoms.copy()
        if request.associated_symptoms:
            all_symptoms.extend(request.associated_symptoms)
        
        # Generate the medical report
        report = get_clinical_codes_for_symptoms(all_symptoms)
        
        # Add additional context from request
        if request.duration:
            report["patient_info"]["symptom_duration"] = request.duration
        
        if request.patient_info:
            report["patient_info"].update(request.patient_info)
        
        # Update timestamp
        report["timestamp"] = datetime.utcnow().isoformat() + "Z"
        
        logger.info(f"Generated medical report with {len(report['clinical_codes'])} codes")
        
        return MedicalReportResponse(
            success=True,
            **report
        )
        
    except Exception as e:
        logger.error(f"Error analyzing symptoms: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze symptoms: {str(e)}"
        )


@router.get("/search-codes", response_model=CodeSearchResponse)
async def search_clinical_codes(
    q: str = Query(..., description="Search query for clinical codes"),
    limit: Optional[int] = Query(default=20, description="Maximum number of results"),
    current_user: str = Depends(verify_token)
):
    """
    Search for clinical codes by keyword.
    
    Searches across:
    - Code displays
    - Descriptions  
    - Synonyms
    - Both SNOMED CT and ICD-10 codes
    """
    
    if not search_codes_by_keyword:
        raise HTTPException(
            status_code=503,
            detail="Clinical codes search service not available"
        )
    
    try:
        logger.info(f"Searching clinical codes for user {current_user}: '{q}'")
        
        # Search for codes
        codes = search_codes_by_keyword(q)
        
        # Limit results
        if limit and len(codes) > limit:
            codes = codes[:limit]
        
        # Convert to response format
        code_responses = []
        for code in codes:
            code_responses.append(ClinicalCodeResponse(
                code=code.code,
                display=code.display,
                system=code.system.value,
                description=code.description,
                category=code.category,
                body_system=code.body_system,
                synonyms=code.synonyms
            ))
        
        logger.info(f"Found {len(code_responses)} codes for query '{q}'")
        
        return CodeSearchResponse(
            success=True,
            query=q,
            codes_found=code_responses,
            total_results=len(code_responses)
        )
        
    except Exception as e:
        logger.error(f"Error searching codes: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to search codes: {str(e)}"
        )


@router.get("/symptoms/common")
async def get_common_symptoms(
    current_user: str = Depends(verify_token)
):
    """
    Get list of common symptoms that can be coded.
    
    Returns a list of symptoms that have clinical codes available
    for quick testing and reference.
    """
    
    if not clinical_codes_cache:
        raise HTTPException(
            status_code=503,
            detail="Clinical codes service not available"
        )
    
    try:
        # Get available symptom mappings
        available_symptoms = []
        
        for key, mapping in clinical_codes_cache.symptom_mappings.items():
            symptom_info = {
                "key": key,
                "keywords": mapping.keywords,
                "primary_codes_count": len(mapping.primary_codes),
                "related_codes_count": len(mapping.related_codes),
                "differential_diagnoses_count": len(mapping.differential_diagnosis),
                "body_systems": list(set(code.body_system for code in mapping.primary_codes if code.body_system))
            }
            available_symptoms.append(symptom_info)
        
        return {
            "success": True,
            "common_symptoms": available_symptoms,
            "total_available": len(available_symptoms),
            "supported_code_systems": ["SNOMED_CT", "ICD_10", "ICD_11"],
            "example_usage": {
                "symptoms": ["cough", "chest pain", "fever"],
                "endpoint": "/api/clinical/analyze-symptoms"
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting common symptoms: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get common symptoms: {str(e)}"
        )


@router.post("/quick-code")
async def quick_symptom_code(
    request: QuickCodeRequest,
    current_user: str = Depends(verify_token)
):
    """
    Quick endpoint to get clinical codes for a single symptom.
    
    Useful for rapid testing and development.
    """
    
    if not clinical_codes_cache:
        raise HTTPException(
            status_code=503,
            detail="Clinical codes service not available"
        )
    
    try:
        logger.info(f"Quick coding for user {current_user}: '{request.symptom}'")
        
        # Find codes for the symptom
        mapping = clinical_codes_cache.find_codes_for_symptom(request.symptom)
        
        if not mapping:
            return {
                "success": False,
                "symptom": request.symptom,
                "message": "No clinical codes found for this symptom",
                "suggestion": "Try searching with the /search-codes endpoint"
            }
        
        return {
            "success": True,
            "symptom": request.symptom,
            "primary_codes": [code.to_dict() for code in mapping.primary_codes],
            "related_codes": [code.to_dict() for code in mapping.related_codes],
            "differential_diagnoses": mapping.differential_diagnosis,
            "keywords_matched": mapping.keywords
        }
        
    except Exception as e:
        logger.error(f"Error in quick symptom coding: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to code symptom: {str(e)}"
        )


@router.get("/health")
async def clinical_codes_health():
    """Health check for clinical codes service."""
    
    try:
        if not clinical_codes_cache:
            return {
                "success": False,
                "status": "unhealthy",
                "error": "Clinical codes cache not available"
            }
        
        # Basic functionality test
        test_codes = search_codes_by_keyword("cough") if search_codes_by_keyword else []
        
        return {
            "success": True,
            "status": "healthy",
            "clinical_codes_available": len(clinical_codes_cache.codes_db),
            "symptom_mappings_available": len(clinical_codes_cache.symptom_mappings),
            "test_search_results": len(test_codes),
            "supported_systems": ["SNOMED_CT", "ICD_10", "ICD_11"],
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except Exception as e:
        logger.error(f"Clinical codes health check failed: {str(e)}")
        return {
            "success": False,
            "status": "unhealthy", 
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }


# Example usage endpoint for testing
@router.post("/example-report")
async def generate_example_report(current_user: str = Depends(verify_token)):
    """
    Generate an example medical report for demonstration.
    
    Shows how the clinical coding system works with common symptoms.
    """
    
    example_symptoms = ["cough", "chest pain", "fever", "shortness of breath"]
    example_patient = {
        "age": 35,
        "gender": "male",
        "duration": "5 days"
    }
    
    request = SymptomRequest(
        symptoms=example_symptoms,
        patient_info=example_patient,
        duration="5 days",
        associated_symptoms=["fatigue"]
    )
    
    return await analyze_symptoms(request, current_user)