"""
Medical AI API Endpoints
Integrates structured medical data with professional prompts for AI responses
Uses MySQL database for NHS-verified medical knowledge
"""

from fastapi import APIRouter, Depends, HTTPException, Body, Query
from sqlalchemy.orm import Session
from config.database import SessionLocal
from services.medical_ai_agent import create_medical_response
from llm.base_llm import BaseLLM
from llm.claude_llm import ClaudeLLM
from pydantic import BaseModel
from typing_extensions import Literal
from typing import Optional
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# Dependency to get MySQL database session
def get_mysql_db():
    """Get MySQL database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class MedicalQueryRequest(BaseModel):
    query: str
    user_role: Literal["Patient", "Doctor"] = "Patient"  # EXACT CLIENT SPECIFICATION: Patient (User Mode) or Doctor (Admin Mode)
    session_id: Optional[str] = None

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
    db: Session = Depends(get_mysql_db)
):
    """
    Main endpoint for medical AI agent queries - EXACT CLIENT SPECIFICATION
    
    Doctor (Admin Mode): Complete 14-category structured overview
    Patient (User Mode): Conversational, empathetic step-by-step responses
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
                "processing_time_ms": 500,  # Would be calculated in real implementation
                "database_used": "MySQL"
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
    db: Session = Depends(get_mysql_db)
):
    """Get summary of NHS-verified medical knowledge available to the AI agent"""
    
    from sqlalchemy import func
    from models.medical_condition import MedicalCondition, ProfessionalPrompt
    
    # Count NHS-verified conditions
    conditions_count = db.query(func.count()).filter(
        MedicalCondition.verified_by_nhs == True,
        MedicalCondition.nhs_review_status == "approved"
    ).scalar()
    
    # Count NHS-approved professional prompts
    prompts_count = db.query(func.count()).filter(
        ProfessionalPrompt.nhs_quality_check == True,
        ProfessionalPrompt.professional_review_status == "approved"
    ).scalar()
    
    return {
        "success": True,
        "database_type": "MySQL",
        "nhs_verified_knowledge": {
            "medical_conditions": conditions_count,
            "professional_prompts": prompts_count,
            "total_training_examples": conditions_count + prompts_count
        },
        "ai_capabilities": {
            "role_based_responses": True,
            "structured_medical_format": True,
            "evidence_based_only": True,
            "nhs_validation_required": True,
            "mysql_database_integration": True
        },
        "behavior_rules": [
            "Doctor (Admin Mode): Complete 14-category structured overview only",
            "Patient (User Mode): Conversational, empathetic, step-by-step responses",
            "Doctor prompts prioritized as authoritative guidelines",
            "Only NHS-verified data and professional prompts as source of truth",
            "Uncertain responses: 'This requires validation by a qualified medical professional'",
            "Patient responses do not overwhelm with full medical structure unless requested"
        ]
    }

@router.post("/medical-validation/check")
async def validate_medical_response(
    query: str = Body(..., description="Original medical query"),
    ai_response: str = Body(..., description="AI generated response"),
    reviewer_credentials: dict = Body(..., description="NHS reviewer credentials"),
    db: Session = Depends(get_mysql_db)
):
    """NHS healthcare professionals can validate AI responses"""
    
    from models.medical_condition import QualityAnalysis
    from datetime import datetime
    
    try:
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
            "success": True,
            "validation_id": validation_record.id,
            "status": "recorded_for_nhs_review",
            "message": "Response validation logged for NHS quality assurance review",
            "database": "MySQL"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Validation logging failed: {str(e)}")

@router.get("/ai-agent/behavior-rules")
async def get_ai_behavior_rules():
    """Get the AI agent's behavior rules and guidelines"""
    
    return {
        "success": True,
        "agent_identity": "Medical AI Agent trained on verified structured data and validated prompts from medical professionals",
        "database_backend": "MySQL",
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
            "1": "Always answer using NHS-verified structured data format from MySQL database",
            "2": "Prioritize doctor prompts as authoritative guidelines",
            "3": "Patient interaction: empathetic clinical persona with step-by-step questions",
            "4": "Medical professional interaction: structured, detailed medical format",
            "5": "Only use NHS-verified prompts and conditions as source of truth",
            "6": "Uncertainty response: 'This requires validation by a qualified medical professional.'",
            "7": "Use MySQL database exclusively - no SQLite fallbacks"
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
    }

@router.get("/structured-response/example")
async def get_structured_response_example():
    """Example of structured response format"""
    
    return {
        "success": True,
        "database_backend": "MySQL",
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
            "source": "NHS_verified_condition_from_MySQL",
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
                "last_updated": "2024-01-15T10:30:00Z",
                "database_source": "MySQL"
            }
        }
    }

@router.get("/database-status")
async def get_database_status(db: Session = Depends(get_mysql_db)):
    """Check MySQL database connection and medical data status"""
    
    try:
        from models.medical_condition import MedicalCondition, ProfessionalPrompt
        from sqlalchemy import func
        
        # Test database connection
        db.execute("SELECT 1")
        
        # Get counts
        conditions_count = db.query(MedicalCondition).count()
        prompts_count = db.query(ProfessionalPrompt).count()
        verified_conditions = db.query(MedicalCondition).filter(
            MedicalCondition.verified_by_nhs == True
        ).count()
        verified_prompts = db.query(ProfessionalPrompt).filter(
            ProfessionalPrompt.nhs_quality_check == True
        ).count()
        
        return {
            "success": True,
            "database_type": "MySQL",
            "connection_status": "Connected",
            "medical_data_status": {
                "total_conditions": conditions_count,
                "nhs_verified_conditions": verified_conditions,
                "total_prompts": prompts_count,
                "nhs_verified_prompts": verified_prompts,
                "verification_rate": f"{(verified_conditions + verified_prompts) / (conditions_count + prompts_count) * 100:.1f}%" if (conditions_count + prompts_count) > 0 else "0%"
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database status check failed: {str(e)}")