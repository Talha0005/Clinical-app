"""
Medical AI API Endpoints
Integrates structured medical data with professional prompts for AI responses
"""

from fastapi import APIRouter, Depends, HTTPException, Body, Query
from sqlalchemy.orm import Session
from models.database_models import get_db
from services.medical_ai_agent import create_medical_response
from llm.base_llm import BaseLLM
from llm.claude_llm import ClaudeLLM
from pydantic import BaseModel
from typing_extensions import Literal
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

class MedicalQueryRequest(BaseModel):
    query: str
    user_role: Literal["patient", "doctor"] = "patient"
    session_id: str = None  # Optional session tracking

class MedicalQueryResponse(BaseModel):
    timestamp: str
    role: str
    response_type: str
    content: str
    confidence: float
    source: str
    nhs_verified: bool
    additional_info: dict = {}

@router.post("/medical-query", response_model=dict)
async def process_medical_query(
    request: MedicalQueryRequest,
    db: Session = Depends(get_db)
):
    """
    Main endpoint for medical AI agent queries
    
    The AI agent responds differently based on user role:
    - Patient: Empathetic, step-by-step responses with medical disclaimers
    - Doctor: Detailed, structured medical information following the condition format
    """
    
    try:
        # Initialize LLM instance (using Claude as default)
        llm_instance = ClaudeLLM()
        
        # Process the medical query
        response = create_medical_response(
            user_query=request.query,
            user_role=request.user_role,
            db=db,
            llm_instance=llm_instance
        )
        
        # Log query for quality monitoring
        logger.info(f"Medical query processed - Role: {request.user_role}, Query: {request.query[:100]}...")
        
        return {
            "success": True,
            "data": response,
            "usage_stats": {
                "session_id": request.session_id,
                "processing_time_ms": 500  # Would be calculated in real implementation
            }
        }
        
    except Exception as e:
        logger.error(f"Error processing medical query: {e}")
        return {
            "success": False,
            "error": "This requires validation by a qualified medical professional.",
            "technical_issue": str(e),
            "recommendation": "Please consult with a healthcare provider for accurate medical advice."
        }

@router.get("/medical-knowledge/summary")
async def get_medical_knowledge_summary(
    db: Session = Depends(get_db)
):
    """Get summary of NHS-verified medical knowledge available to the AI agent"""
    
    from sqlalchemy import func
    
    # Count NHS-verified conditions
    conditions_count = db.query(func.count()).filter(
        MedicalConditions.verified_by_nhs == True,
        MedicalConditions.nhs_review_status == "approved"
    ).scalar()
    
    # Count NHS-approved professional prompts
    prompts_count = db.query(func.count()).filter(
        ProfessionalPrompts.nhs_quality_check == True,
        ProfessionalPrompts.professional_review_status == "approved"
    ).scalar()
    
    return {
        "nhs_verified_knowledge": {
            "medical_conditions": conditions_count,
            "professional_prompts": prompts_count,
            "total_training_examples": conditions_count + prompts_count
        },
        "ai_capabilities": {
            "role_based_responses": True,
            "structured_medical_format": True,
            "evidence_based_only": True,
            "nhs_validation_required": True
        },
        "behavior_rules": [
            "Always answer using NHS-verified structured data format",
            "Prioritize professional prompts as authoritative guidelines",
            "Patient responses: empathetic, step-by-step, simple language",
            "Doctor responses: detailed, structured, clinical format",
            "Uncertain information marked as requiring professional validation"
        ]
    }

@router.post("/medical-validation/check")
async def validate_medical_response(
    query: str = Body(..., description="Original medical query"),
    ai_response: str = Body(..., description="AI generated response"),
    reviewer_credentials: dict = Body(..., description="NHS reviewer credentials"),
    db: Session = Depends(get_db)
):
    """NHS healthcare professionals can validate AI responses"""
    
    from models.medical_condition import QualityAnalysis
    from datetime import datetime
    
    validation_record = QualityAnalysis(
        analysis_type="ai_response_validation",
        resource_id=0,  # AI response doesn't have specific resource ID
        reviewed_by_nhs_professional=reviewer_credentials.get("reviewer_name"),
        review_notes=f"Query: {query}\\nResponse: {ai_response}",
        approval_status="pending",
        analyzed_at=datetime.utcnow()
    )
    
    db.add(validation_record)
    db.commit()
    
    return {
        "validation_id": validation_record.id,
        "status": "recorded_for_nhs_review",
        "message": "Response validation logged for NHS quality assurance review"
    }

@router.get("/ai-agent/behavior-rules")
async def get_ai_behavior_rules():
    """Get the AI agent's behavior rules and guidelines"""
    
    return {
        "agent_identity": "Medical AI Agent trained on verified structured data and validated prompts from medical professionals",
        "knowledge_format": {
            "condition_name": "Medical condition identifier",
            "definition": "Clear medical definition",
            "classification": "Medical classification",
            "epidemiology": "Incidence and prevalence data",
            "aetiology": "Causal factors",
            "risk_factors": "Risk assessment",
            "signs": "Clinical signs",
            "symptoms": "Patient symptoms",
            "complications": "Potential complications",
            "tests": "Diagnostic tests and criteria",
            "differential_diagnoses": "Alternative diagnoses",
            "associated_conditions": "Comorbidities",
            "management": "Conservative, medical, surgical approaches with care pathways",
            "prevention": "Primary and secondary prevention"
        },
        "behavior_rules": {
            "1": "Always answer using structuree format",
            "2": "Prioritize doctor prompts as authoritative guidelines",
            "3": "Patient interaction: empathetic clinical persona with step-by-step questions",
            "4": "Medical professional interaction: structured, detailed medical format",
            "5": "Only use NHS-verified prompts and conditions as source of truth",
            "6": "Uncertainty response: 'This requires validation by a qualified medical professional.'"
        },
        "response_adaptation": {
            "patient_mode": {
                "tone": "empathetic and clear",
                "language": "simple, conversational",
                "approach": "step-by-step questioning",
                "overload_prevention": "gradual information release",
                "disclaimer": "require healthcare professional consultation"
            },
            "doctor_mode": {
                "tone": "structured and detailed",
                "language": "clinical terminology",
                "approach": "complete medical information",
                "format": "organized medical condition structure",
                "authority": "NHS-verified source citation"
            }
        }


@router.get("/structured-response/example")
async def get_structured_response_example():
    """Example of structured response format"""
    
    return {
        "example_patient_response": {
            "role": "patient",
            "condition": "Type 2 Diabetes",
            "response_parts": [
                {
                    "section": "introduction",
                    "content": "I'm here to help you understand Type 2 Diabetes. Let me explain this step by step."
                },
                {
                    "section": "condition_overview", 
                    "content": "Type 2 diabetes is a chronic condition that affects how your body processes blood sugar."
                },
                {
                    "section": "symptoms",
                    "content": "Common symptoms include increased thirst, frequent urination, and unexplained weight loss.",
                    "followup": "Do any of these symptoms sound familiar to you?"
                },
                {
                    "section": "medical_disclaimer",
                    "content": "This information is for educational purposes. Please consult with a qualified healthcare professional."
                }
            ],
            "source": "NHS_verified_condition",
            "confidence": 0.95
        },
        "example_doctor_response": {
            "role": "doctor",
            "condition": "Type 2 Diabetes",
            "structured_info": {
                "condition_name": "Type 2 Diabetes",
                "definition": "A chronic metabolic disorder characterized by insulin resistance and relative insulin deficiency",
                "epidemiology": {
                    "incidence": "10-15 per 1000 population annually",
                    "prevalence": "40-60 per 1000 population"
                },
                "management": {
                    "conservative": "Lifestyle modifications, diet, exercise",
                    "medical": "Metformin, sulfonylureas, DPP-4 inhibitors",
                    "surgical": "Bariatric surgery for obesity-related diabetes"
                }
            },
            "clinical_notes": {
                "nhs_verified": True,
                "evidence_sources": ["NICE Guidelines", "Diabetes UK"],
                "last_updated": "2024-01-15T10:30:00Z"
            }
        }
    }


# Import statements needed for the validation function
from models.medical_condition import MedicalCondition as MedicalConditions, ProfessionalPrompt as ProfessionalPrompts
