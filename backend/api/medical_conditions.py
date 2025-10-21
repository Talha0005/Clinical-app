"""
Medical Conditions API
Handles CRUD operations for medical conditions and professional prompts management
Uses MySQL database with NHS verification workflows
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from config.database import SessionLocal
from models.medical_condition import MedicalCondition, ProfessionalPrompt, QualityAnalysis
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime
import json

router = APIRouter(
    prefix="/api/medical-conditions",
    tags=["medical-conditions"]
)

# Dependency to get MySQL database session
def get_mysql_db():
    """Get MySQL database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Request/Response Models
class MedicalConditionRequest(BaseModel):
    condition_name: str
    definition: Optional[str] = None
    classification: Optional[str] = None
    incidence_rate: Optional[str] = None
    prevalence_rate: Optional[str] = None
    epidemiology_notes: Optional[str] = None
    aetiology: Optional[str] = None
    risk_factors: Optional[List[str]] = None
    signs: Optional[List[str]] = None
    symptoms: Optional[List[str]] = None
    quality_complications: Optional[str] = None
    diagnostic_tests: Optional[List[str]] = None
    diagnostic_criteria: Optional[str] = None
    differential_diagnoses: Optional[List[str]] = None
    associated_conditions: Optional[List[str]] = None
    conservative_management: Optional[str] = None
    medical_management: Optional[str] = None
    surgical_management: Optional[str] = None
    care_pathway: Optional[str] = None
    treatment_criteria: Optional[str] = None
    primary_prevention: Optional[str] = None
    secondary_prevention: Optional[str] = None

class ProfessionalPromptRequest(BaseModel):
    title: str
    prompt_text: str
    prompt_category: str
    clinical_context: Optional[str] = None
    clinical_indicators: Optional[Dict[str, Any]] = None
    evidence_level: Optional[str] = None
    specialty: Optional[str] = None
    created_by_professional: str
    professional_title: Optional[str] = None
    professional_credentials: Optional[str] = None
    usage_count: int = 0

# --- Medical Condition Endpoints ---

@router.post("/conditions/", response_model=Dict[str, Any], status_code=201)
async def create_medical_condition(
    condition_data: MedicalConditionRequest,
    db: Session = Depends(get_mysql_db)
):
    """Create a new medical condition with structured data"""
    
    try:
        # Convert to dict and create condition
        condition_dict = condition_data.dict()
        new_condition = MedicalCondition(**condition_dict)
        
        db.add(new_condition)
        db.commit()
        db.refresh(new_condition)
        
        return {
            "success": True,
            "message": "Medical condition created successfully",
            "condition": new_condition.to_dict(),
            "nhs_verification": "Pending NHS review"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to create medical condition: {str(e)}")

@router.get("/conditions/", response_model=Dict[str, Any])
async def get_all_medical_conditions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    verified_only: bool = Query(False),
    db: Session = Depends(get_mysql_db)
):
    """Get all medical conditions with optional NHS verification filter"""
    
    try:
        query = db.query(MedicalCondition)
        
        if verified_only:
            query = query.filter(
                MedicalCondition.verified_by_nhs == True,
                MedicalCondition.nhs_review_status == "approved"
            )
        
        conditions = query.offset(skip).limit(limit).all()
        
        return {
            "success": True,
            "conditions": [condition.to_dict() for condition in conditions],
            "total_count": db.query(MedicalCondition).count(),
            "verified_count": db.query(MedicalCondition).filter(
                MedicalCondition.verified_by_nhs == True
            ).count()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/conditions/{condition_id}", response_model=Dict[str, Any])
async def get_medical_condition(
    condition_id: int,
    db: Session = Depends(get_mysql_db)
):
    """Get a specific medical condition with full structured data"""
    
    condition = db.query(MedicalCondition).filter(MedicalCondition.id == condition_id).first()
    if not condition:
        raise HTTPException(status_code=404, detail="Medical condition not found")
    
    return {
        "success": True,
        "condition": condition.to_dict(),
        "nhs_status": "verified" if condition.verified_by_nhs else "pending_review"
    }

@router.put("/conditions/{condition_id}", response_model=Dict[str, Any])
async def update_medical_condition(
    condition_id: int,
    condition_data: MedicalConditionRequest,
    db: Session = Depends(get_mysql_db)
):
    """Update medical condition - requires NHS re-verification"""
    
    condition = db.query(MedicalCondition).filter(MedicalCondition.id == condition_id).first()
    if not condition:
        raise HTTPException(status_code=404, detail="Medical condition not found")
    
    try:
        # Update fields
        update_data = condition_data.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(condition, key, value)
        
        # Reset NHS verification status for updated condition
        condition.nhs_verified = False
        condition.nhs_review_status = "requires_review"
        condition.last_updated = datetime.utcnow()
        
        db.commit()
        db.refresh(condition)
        
        return {
            "success": True,
            "message": "Medical condition updated successfully",
            "condition": condition.to_dict(),
            "note": "NHS re-verification required due to updates"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to update medical condition: {str(e)}")

@router.delete("/conditions/{condition_id}")
async def delete_medical_condition(
    condition_id: int,
    db: Session = Depends(get_mysql_db)
):
    """Delete medical condition"""
    
    condition = db.query(MedicalCondition).filter(MedicalCondition.id == condition_id).first()
    if not condition:
        raise HTTPException(status_code=404, detail="Medical condition not found")
    
    db.delete(condition)
    db.commit()
    
    return {
        "success": True,
        "message": "Medical condition deleted successfully"
    }

# --- Professional Prompt Endpoints ---

@router.post("/prompts/", response_model=Dict[str, Any], status_code=201)
async def create_professional_prompt(
    prompt_data: ProfessionalPromptRequest,
    db: Session = Depends(get_mysql_db)
):
    """Create a new professional prompt for AI learning"""
    
    try:
        prompt_dict = prompt_data.dict()
        new_prompt = ProfessionalPrompt(**prompt_dict)
        
        db.add(new_prompt)
        db.commit()
        db.refresh(new_prompt)
        
        return {
            "success": True,
            "message": "Professional prompt created successfully",
            "prompt": new_prompt.to_dict(),
            "nhs_review": "Pending NHS quality assessment"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to create professional prompt: {str(e)}")

@router.get("/prompts/", response_model=Dict[str, Any])
async def get_all_professional_prompts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    category: Optional[str] = Query(None),
    specialty: Optional[str] = Query(None),
    nhs_verified_only: bool = Query(False),
    db: Session = Depends(get_mysql_db)
):
    """Get all professional prompts with filtering options"""
    
    try:
        query = db.query(ProfessionalPrompt)
        
        if category:
            query = query.filter(ProfessionalPrompt.prompt_category == category)
        
        if specialty:
            query = query.filter(ProfessionalPrompt.specialty == specialty)
        
        if nhs_verified_only:
            query = query.filter(
                ProfessionalPrompt.nhs_quality_check == True,
                ProfessionalPrompt.professional_review_status == "approved"
            )
        
        prompts = query.offset(skip).limit(limit).all()
        
        return {
            "success": True,
            "prompts": [prompt.to_dict() for prompt in prompts],
            "total_count": db.query(ProfessionalPrompt).count(),
            "nhs_verified_count": db.query(ProfessionalPrompt).filter(
                ProfessionalPrompt.nhs_quality_check == True
            ).count()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

# --- NHS Verification Endpoints ---

@router.post("/verify/condition/{condition_id}", response_model=Dict[str, Any])
async def nhs_verify_condition(
    condition_id: int,
    verification_data: Dict[str, Any] = Body(...),
    db: Session = Depends(get_mysql_db)
):
    """NHS verification endpoint for medical conditions"""
    
    condition = db.query(MedicalCondition).filter(MedicalCondition.id == condition_id).first()
    if not condition:
        raise HTTPException(status_code=404, detail="Medical condition not found")
    
    try:
        # Update NHS verification status
        nhs_verified = verification_data.get("verify", False)
        nhs_notes = verification_data.get("notes", "")
        reviewer_name = verification_data.get("reviewer", "NHS Reviewer")
        
        condition.verified_by_nhs = nhs_verified
        condition.nhs_review_status = "approved" if nhs_verified else "rejected"
        condition.nhs_review_notes = nhs_notes
        condition.nhs_review_date = datetime.utcnow()
        condition.reviewed_by_nhs_professional = reviewer_name
        
        # Create quality analysis record
        analysis = QualityAnalysis(
            analysis_type="medical_condition_review",
            resource_id=condition_id,
            reviewed_by_nhs_professional=reviewer_name,
            review_notes=nhs_notes,
            approval_status="approved" if nhs_verified else "rejected",
            analyzed_at=datetime.utcnow()
        )
        
        db.add(analysis)
        db.commit()
        
        return {
            "success": True,
            "message": "NHS verification completed",
            "condition_id": condition_id,
            "verified": nhs_verified,
            "status": condition.nhs_review_status
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"NHS verification failed: {str(e)}")

# --- Quality Analysis Endpoints ---

@router.get("/quality-analysis/", response_model=Dict[str, Any])
async def get_quality_analysis_reports(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    analysis_type: Optional[str] = Query(None),
    db: Session = Depends(get_mysql_db)
):
    """Get quality analysis reports for NHS review oversight"""
    
    try:
        query = db.query(QualityAnalysis)
        
        if analysis_type:
            query = query.filter(QualityAnalysis.analysis_type == analysis_type)
        
        reports = query.order_by(QualityAnalysis.analyzed_at.desc()).offset(skip).limit(limit).all()
        
        return {
            "success": True,
            "quality_reports": [report.to_dict() for report in reports],
            "pending_reviews": db.query(QualityAnalysis).filter(
                QualityAnalysis.approval_status == "pending"
            ).count()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch quality analysis: {str(e)}")

# --- Analytics Endpoints ---

@router.get("/analytics/summary", response_model=Dict[str, Any])
async def get_medical_data_analytics(db: Session = Depends(get_mysql_db)):
    """Get analytics summary for medical data management"""
    
    try:
        return {
            "success": True,
            "analytics": {
                "total_conditions": db.query(MedicalCondition).count(),
                "nhs_verified_conditions": db.query(MedicalCondition).filter(
                    MedicalCondition.verified_by_nhs == True
                ).count(),
                "pending_verification": db.query(MedicalCondition).filter(
                    MedicalCondition.nhs_verified == False
                ).count(),
                "total_prompts": db.query(ProfessionalPrompt).count(),
                "nhs_verified_prompts": db.query(ProfessionalPrompt).filter(
                    ProfessionalPrompt.nhs_quality_check == True
                ).count(),
                "quality_reports": db.query(QualityAnalysis).count(),
                "data_coverage": {
                    "conditions_with_management": db.query(MedicalCondition).filter(
                        MedicalCondition.medical_management.isnot(None)
                    ).count(),
                    "conditions_with_prevention": db.query(MedicalCondition).filter(
                        MedicalCondition.primary_prevention.isnot(None)
                    ).count(),
                    "prompts_with_clinical_context": db.query(ProfessionalPrompt).filter(
                        ProfessionalPrompt.clinical_context.isnot(None)
                    ).count()
                }
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analytics error: {str(e)}")