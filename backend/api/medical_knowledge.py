"""
Medical Knowledge Assistant API
Provides structured 15-category medical information with SNOMED CT and ICD-10 codes
Always complete format, never skips sections, includes clinical disclaimer
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from config.database import SessionLocal
from services.medical_knowledge_formatter import generate_structured_medical_response
from llm.base_llm import BaseLLM
from llm.claude_llm import ClaudeLLM
from pydantic import BaseModel
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

class MedicalKnowledgeRequest(BaseModel):
    condition_query: str
    session_id: Optional[str] = None

@router.post("/structured-knowledge", response_model=dict)
async def get_structured_medical_knowledge(
    request: MedicalKnowledgeRequest,
    db: Session = Depends(get_mysql_db)
):
    """
    Get complete structured medical information following EXACT 15-category format
    
    Always provides:
    1. Condition name
    2. Definition  
    3. Classification
    4. Epidemiology (Incidence / Prevalence)
    5. Aetiology
    6. Risk factors
    7. Signs
    8. Symptoms
    9. Complications
    10. Tests (and diagnostic criteria)
    11. Differential diagnoses
    12. Associated conditions
    13. Management (Conservative, Medical, Surgical - care pathway and treatment criteria)
    14. Prevention (Primary, Secondary)
    15. Codes (SNOMED CT + ICD-10)
    
    Plus clinical disclaimer
    """
    
    try:
        # Initialize LLM instance
        llm_instance = ClaudeLLM()
        
        # Generate structured medical response
        response = generate_structured_medical_response(
            condition_query=request.condition_query,
            db=db,
            llm_instance=llm_instance
        )
        
        # Log for quality monitoring
        logger.info(f"Structured medical knowledge requested for: {request.condition_query}")
        
        return {
            "success": True,
            "data": response,
            "usage_stats": {
                "session_id": request.session_id,
                "database_used": "MySQL",
                "format_compliance": "Complete 15-category structure"
            }
        }
        
    except Exception as e:
        logger.error(f"Error generating structured medical knowledge: {e}")
        
        # Return minimal structured response even on error
        return {
            "success": False,
            "error": "This requires validation by a qualified medical professional.",
            "fallback_response": {
                "structured_medical_knowledge": True,
                "source": "Error fallback",
                "format": "Complete 15-category structured overview",
                "content": {
                    "1. Condition name": request.condition_query,
                    "2. Definition": "System temporarily unavailable - please consult healthcare provider",
                    "3. Classification": "Requires clinical assessment",
                    "4. Epidemiology (Incidence / Prevalence)": "Data retrieval failed",
                    "5. Aetiology": "Requires professional medical evaluation",
                    "6. Risk factors": "Requires clinical assessment",
                    "7. Signs": "Requires clinical examination",
                    "8. Symptoms": "Requires professional evaluation",
                    "9. Complications": "Requires medical assessment",
                    "10. Tests (and diagnostic criteria)": "Requires clinical diagnostics",
                    "11. Differential diagnoses": "Requires medical differential analysis",
                    "12. Associated conditions": "Requires comprehensive assessment",
                    "13. Management (Conservative, Medical, Surgical)": "Requires clinical management planning",
                    "14. Prevention (Primary, Secondary)": "Requires preventive care consultation",
                    "15. Codes (SNOMED CT + ICD-10)": "Requires proper medical coding"
                },
                "clinical_disclaimer": "This is general structured medical information and not a substitute for professional medical advice. Please consult a healthcare provider for personalised guidance.",
                "note": "System experiencing technical difficulties. Please contact healthcare provider for immediate assistance."
            }
        }

@router.get("/knowledge-format/example")
async def get_knowledge_format_example():
    """Example of the structured 15-category medical knowledge format"""
    
    return {
        "format_specification": "Medical Knowledge Assistant - Complete 15-Category Structure",
        "example_input": "Give me a structured overview of Fever",
        "example_output": {
            "1. Condition name": "Fever",
            "2. Definition": "Fever is a temporary rise in body temperature, typically above 38°C, often due to infection or inflammation.",
            "3. Classification": "Low-grade: 38–39°C | Moderate: 39–40°C | High: >40°C",
            "4. Epidemiology (Incidence / Prevalence)": "Extremely common worldwide; higher incidence in children and older adults.",
            "5. Aetiology": "Viral and bacterial infections, inflammatory diseases, heat exposure, drugs.",
            "6. Risk factors": "Young age, immunocompromised states, chronic illness.",
            "7. Signs": "Elevated body temperature, flushed skin, sweating.",
            "8. Symptoms": "Chills, headache, malaise, muscle aches, loss of appetite.",
            "9. Complications": "Seizures (in children), dehydration, organ dysfunction in severe/prolonged cases.",
            "10. Tests (and diagnostic criteria)": "Thermometry, blood cultures, chest X-ray, urine analysis depending on suspected cause.",
            "11. Differential diagnoses": "Hyperthyroidism, heatstroke, malignant hyperthermia.",
            "12. Associated conditions": "Viral infections, infections, malignancy.",
            "13. Management (Conservative, Medical, Surgical)": "Conservative: Rest, hydration | Medical: Antipyretics (paracetamol, ibuprofen) | Surgical: Not applicable unless fever due to abscess → drainage",
            "14. Prevention (Primary, Secondary)": "Primary: Vaccinations, hygiene | Secondary: Early treatment of infections, monitoring high-risk groups.",
            "15. Codes (SNOMED CT + ICD-10)": "SNOMED CT: 386661006 | ICD-10: R50.9"
        },
        "clinical_disclaimer": "This is general structured medical information and not a substitute for professional medical advice. Please consult a healthcare provider for personalised guidance.",
        "rules": [
            "Never skip any section",
            "Use clear, structured, clinical language",
            "Always include both SNOMED CT and ICD-10 codes",
            "Write 'Not well established' if evidence is lacking",
            "Keep content accurate and concise",
            "Always include clinical disclaimer",
            "Do not refuse queries"
        ],
        "implementation_status": "Complete 15-category format implemented with MySQL database integration"
    }

@router.get("/knowledge-status")
async def get_knowledge_system_status(db: Session = Depends(get_mysql_db)):
    """Check status of structured medical knowledge system"""
    
    try:
        from sqlalchemy import func
        from models.medical_condition import MedicalCondition
        
        # Check database connection
        db.execute("SELECT 1")
        
        # Count NHS-verified conditions
        verified_count = db.query(MedicalCondition).filter(
            MedicalCondition.verified_by_nhs == True
        ).count()
        
        total_count = db.query(MedicalCondition).count()
        
        return {
            "success": True,
            "knowledge_system_status": "Operational",
            "database_type": "MySQL",
            "structured_format": "Complete 15-category medical knowledge",
            "data_status": {
                "total_conditions": total_count,
                "nhs_verified_conditions": verified_count,
                "verification_rate": f"{verified_count/max(total_count, 1)*100:.1f}%" if total_count > 0 else "0%"
            },
            "capabilities": {
                "never_skips_sections": True,
                "always_includes_codes": True,
                "clinical_disclaimer_required": True,
                "mysql_database_integration": True,
                "structured_15_category_format": True
            },
            "features": [
                "Complete SNOMED CT and ICD-10 code integration",
                "NHS-verified data prioritization", 
                "Never skips any of the 15 categories",
                "Always includes clinical disclaimer",
                "Never refuses medical queries",
                "Clear, structured, clinical language"
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Knowledge system status check failed: {str(e)}")

