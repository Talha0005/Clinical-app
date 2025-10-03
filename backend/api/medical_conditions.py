"""
Medical Conditions API
Handles CRUD operations for medical conditions and professional prompts management
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from models.database_models import get_db
from models.medical_condition import MedicalCondition, ProfessionalPrompt, QualityAnalysis
from services.auth import get_current_admin_user
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime
import json

router = APIRouter()

# Pydantic models for API requests/responses
class MedicalConditionCreate(BaseModel):
    condition_name: str
    definition: str
    classification: Optional[str] = None
    incidence_rate: Optional[float] = None
    prevalence_rate: Optional[float] = None
    epidemiology_notes: Optional[str] = None
    aetiology: Optional[str] = None
    risk_factors: Optional[List[str]] = None
    signs: Optional[List[str]] = None
    symptoms: Optional[List[str]] = None
    complications: Optional[str] = None
    diagnostic_tests: Optional[List[Dict[str, Any]]] = None
    diagnostic_criteria: Optional[str] = None
    differential_diagnoses: Optional[List[str]] = None
    associated_conditions: Optional[List[str]] = None
    conservative_management: Optional[Dict[str, Any]] = None
    medical_management: Optional[Dict[str, Any]] = None
    surgical_management: Optional[Dict[str, Any]] = None
    care_pathway: Optional[str] = None
    treatment_criteria: Optional[str] = None
    primary_prevention: Optional[str] = None
    secondary_prevention: Optional[str] = None
    source_references: Optional[List[str]] = None

class ProfessionalPromptCreate(BaseModel):
    title: str
    prompt_text: str
    prompt_category: str
    clinical_context: Optional[str] = None
    specialty: Optional[str] = None
    difficulty_level: str = "intermediate"
    evidence_level: Optional[str] = None
    clinical_indicators: Optional[Dict[str, Any]] = None
    professional_title: Optional[str] = None
    specialty_expertise: Optional[str] = None
    years_experience: Optional[int] = None
    tags: Optional[List[str]] = None

@router.get("/medical-conditions/", response_model=List[Dict[str, Any]])
async def get_all_conditions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = Query(None),
    specialty: Optional[str] = Query(None),
    verified_only: bool = Query(False),
    db: Session = Depends(get_db)
):
    """Get all medical conditions with filtering and pagination"""
    query = db.query(MedicalCondition)
    
    if search:
        query = query.filter(MedicalCondition.condition_name.ilike(f"%{search}%"))
    
    if verified_only:
        query = query.filter(MedicalCondition.verified_by_nhs == True)
    
    conditions = query.offset(skip).limit(limit).all()
    return [condition.to_dict() for condition in conditions]

@router.get("/medical-conditions/{condition_id}", response_model=Dict[str, Any])
async def get_condition_by_id(
    condition_id: int,
    db: Session = Depends(get_db)
):
    """Get specific medical condition by ID"""
    condition = db.query(MedicalCondition).filter(MedicalCondition.id == condition_id).first()
    if not condition:
        raise HTTPException(status_code=404, detail="Medical condition not found")
    return condition.to_dict()

@router.post("/medical-conditions/", response_model=Dict[str, Any])
async def create_medical_condition(
    condition_data: MedicalConditionCreate,
    current_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Create a new medical condition (Admin only)"""
    # Check if condition already exists
    existing = db.query(MedicalCondition).filter(
        MedicalCondition.condition_name == condition_data.condition_name
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Medical condition already exists")
    
    # Create new condition
    db_condition = MedicalCondition(
        condition_name=condition_data.condition_name,
        definition=condition_data.definition,
        classification=condition_data.classification,
        incidence_rate=condition_data.incidence_rate,
        prevalence_rate=condition_data.prevalence_rate,
        epidemiology_notes=condition_data.epidemiology_notes,
        aetiology=condition_data.aetiology,
        risk_factors=condition_data.risk_factors if condition_data.risk_factors else [],
        signs=condition_data.signs if condition_data.signs else [],
        symptoms=condition_data.symptoms if condition_data.symptoms else [],
        complications=condition_data.complications,
        diagnostic_tests=condition_data.diagnostic_tests if condition_data.diagnostic_tests else [],
        diagnostic_criteria=condition_data.diagnostic_criteria,
        differential_diagnoses=condition_data.differential_diagnoses if condition_data.differential_diagnoses else [],
        associated_conditions=condition_data.associated_conditions if condition_data.associated_conditions else [],
        conservative_management=condition_data.conservative_management,
        medical_management=condition_data.medical_management,
        surgical_management=condition_data.surgical_management,
        care_pathway=condition_data.care_pathway,
        treatment_criteria=condition_data.treatment_criteria,
        primary_prevention=condition_data.primary_prevention,
        secondary_prevention=condition_data.secondary_prevention,
        created_by=current_user.username,
        source_references=condition_data.source_references if condition_data.source_references else []
    )
    
    db.add(db_condition)
    db.commit()
    db.refresh(db_condition)
    
    return db_condition.to_dict()

@router.post("/professional-prompts/", response_model=Dict[str, Any])
async def create_professional_prompt(
    prompt_data: ProfessionalPromptCreate,
    clinical_credentials: Dict[str, Any] = Body(..., description="Professional credentials"),
    db: Session = Depends(get_db)
):
    """Medical professionals can submit prompts for model training"""
    
    # Create professional prompt
    db_prompt = ProfessionalPrompt(
        title=prompt_data.title,
        prompt_text=prompt_data.prompt_text,
        prompt_category=prompt_data.prompt_category,
        clinical_context=prompt_data.clinical_context,
        specialty=prompt_data.specialty,
        difficulty_level=prompt_data.difficulty_level,
        evidence_level=prompt_data.evidence_level,
        clinical_indicators=prompt_data.clinical_indicators,
        created_by_professional=clinical_credentials.get("professional_name"),
        professional_title=clinical_credentials.get("professional_title"),
        specialty_expertise=clinical_credentials.get("specialty_expertise"),
        years_experience=clinical_credentials.get("years_experience"),
        tags=prompt_data.tags if prompt_data.tags else []
    )
    
    db.add(db_prompt)
    db.commit()
    db.refresh(db_prompt)
    
    return db_prompt.to_dict()

@router.get("/professional-prompts/", response_model=List[Dict[str, Any]])
async def get_professional_prompts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    category: Optional[str] = Query(None),
    specialty: Optional[str] = Query(None),
    approved_only: bool = Query(False),
    db: Session = Depends(get_db)
):
    """Get professional prompts for training data"""
    query = db.query(ProfessionalPrompt)
    
    if category:
        query = query.filter(ProfessionalPrompt.prompt_category == category)
    
    if specialty:
        query = query.filter(ProfessionalPrompt.specialty == specialty)
    
    if approved_only:
        query = query.filter(
            ProfessionalPrompt.professional_review_status == "approved",
            ProfessionalPrompt.nhs_quality_check == True
        )
    
    prompts = query.offset(skip).limit(limit).all()
    return [prompt.to_dict() for prompt in prompts]

@router.post("/quality-analysis/")
async def perform_quality_analysis(
    resource_type: str,  # "condition" or "prompt"
    resource_id: int,
    reviewer_credentials: Dict[str, Any] = Body(..., description="NHS reviewer credentials"),
    quality_metrics: Dict[str, Any] = Body(..., description="Quality assessment metrics"),
    current_admin = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Perform NHS quality analysis on conditions or prompts"""
    
    # Create quality analysis record
    quality_analysis = QualityAnalysis(
        analysis_type=resource_type,
        resource_id=resource_id,
        clinical_accuracy_score=quality_metrics.get("clinical_accuracy_score"),
        evidence_strength=quality_metrics.get("evidence_strength"),
        comprehensiveness_score=quality_metrics.get("comprehensiveness_score"),
        reviewed_by_nhs_professional=reviewer_credentials.get("reviewer_name"),
        review_notes=quality_metrics.get("review_notes"),
        red_flags=quality_metrics.get("red_flags", []),
        improvement_suggestions=quality_metrics.get("improvement_suggestions", [])
    )
    
    # Update the source resource approval status
    if resource_type == "condition":
        condition = db.query(MedicalCondition).filter(MedicalCondition.id == resource_id).first()
        if condition:
            condition.nhs_review_status = quality_metrics.get("approval_status", "pending")
            condition.verified_by_nhs = quality_metrics.get("approval_status") == "approved"
    
    elif resource_type == "prompt":
        prompt = db.query(ProfessionalPrompt).filter(ProfessionalPrompt.id == resource_id).first()
        if prompt:
            prompt.nhs_quality_check = quality_metrics.get("approval_status") == "approved"
            prompt.professional_review_status = quality_metrics.get("approval_status", "pending")
    
    db.add(quality_analysis)
    db.commit()
    db.refresh(quality_analysis)
    
    return {
        "message": "Quality analysis completed",
        "analysis_id": quality_analysis.id,
        "approval_status": quality_metrics.get("approval_status")
    }

@router.get("/training-data/")
async def get_training_data(
    data_type: str = Query("all", description="Type of training data: all, conditions, prompts, both"),
    nhs_verified_only: bool = Query(True),
    db: Session = Depends(get_db)
):
    """Get cleaned training data for AI model training"""
    
    training_data = {}
    
    if data_type in ["all", "both", "conditions"]:
        # Get NHS-verified medical conditions
        conditions_query = db.query(MedicalCondition)
        if nhs_verified_only:
            conditions_query = conditions_query.filter(MedicalCondition.verified_by_nhs == True)
        
        conditions = conditions_query.all()
        training_data["conditions"] = [condition.to_dict() for condition in conditions]
    
    if data_type in ["all", "both", "prompts"]:
        # Get NHS-approved professional prompts
        prompts_query = db.query(ProfessionalPrompt)
        if nhs_verified_only:
            prompts_query = prompts_query.filter(
                ProfessionalPrompt.nhs_quality_check == True,
                ProfessionalPrompt.professional_review_status == "approved"
            )
        
        prompts = prompts_query.all()
        training_data["prompts"] = [prompt.to_dict() for prompt in prompts]
    
    return {
        "message": "Training data retrieved for AI model training",
        "data_type": data_type,
        "nhs_verified_only": nhs_verified_only,
        "data": training_data,
        "summary": {
            "conditions_count": len(training_data.get("conditions", [])),
            "prompts_count": len(training_data.get("prompts", []))
        }
    }

@router.get("/admin/dashboard/")
async def admin_dashboard(
    current_admin = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Admin dashboard for prompt and condition management"""
    
    # Get statistics
    total_conditions = db.query(MedicalCondition).count()
    verified_conditions = db.query(MedicalCondition).filter(MedicalCondition.verified_by_nhs == True).count()
    pending_conditions = db.query(MedicalCondition).filter(MedicalCondition.nhs_review_status == "pending").count()
    
    total_prompts = db.query(ProfessionalPrompt).count()
    approved_prompts = db.query(ProfessionalPrompt).filtr(
        ProfessionalPrompt.professional_review_status == "approved",
        ProfessionalPrompt.nhs_quality_check == True
    ).count()
    
    pending_prompts = db.query(ProfessionalPrompt).filtr(
        ProfessionalPrompt.professional_review_status == "pending"
    ).count()
    
    # Recent submissions
    recent_conditions = db.query(MedicalCondition).order_by(MedicalCondition.last_updated.desc()).limit(5).all()
    recent_prompts = db.query(ProfessionalPrompt).order_by(ProfessionalPrompt.created_at.desc()).limit(5).all()
    
    return {
        "summary": {
            "conditions": {
                "total": total_conditions,
                "verified": verified_conditions,
                "pending_review": pending_conditions
            },
            "prompts": {
                "total": total_prompts,
                "approved": approved_prompts,
                "pending_review": pending_prompts
            }
        },
        "recent_submissions": {
            "conditions": [condition.to_dict() for condition in recent_conditions],
            "prompts": [prompt.to_dict() for prompt in recent_prompts]
        }
    }
