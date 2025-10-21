"""
Medical AI Agent - CLIENT EXACT SPECIFICATION
Implements role-based responses: Doctor (Admin Mode) vs Patient (User Mode)
Only NHS-verified data and professional prompts as source of truth
"""

from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from models.medical_condition import MedicalCondition, ProfessionalPrompt
from llm.base_llm import BaseLLM
from datetime import datetime
import json
import re
from services.medical_knowledge_formatter import generate_structured_medical_response

class MedicalAIAgent:
    """Medical AI Agent with EXACT CLIENT SPECIFICATION"""
    
    def __init__(self, db: Session, llm_instance: BaseLLM):
        self.db = db
        self.llm = llm_instance
        self.current_role = None  # "Doctor" (Admin) or "Patient" (User)
        self.database_type = "MySQL"
        
        # EXACT CLIENT 14-CATEGORY STRUCTURE
        self.medical_condition_structure = {
            "1. Condition name": "",
            "2. Definition": "",
            "3. Classification": "",
            "4. Epidemiology (Incidence / Prevalence)": "",
            "5. Aetiology": "",
            "6. Risk factors": [],
            "7. Signs": [],
            "8. Symptoms": [],
            "9. Complications": "",
            "10. Tests (and diagnostic criteria)": "",
            "11. Differential diagnoses": [],
            "12. Associated conditions": [],
            "13. Management (conservative, medical, surgical – care pathways)": "",
            "14. Prevention (primary, secondary)": ""
        }
    
    def process_query(self, user_input: str, user_role: str) -> Dict[str, Any]:
        """
        Process medical query with EXACT role-based behavior per client specification
        
        Args:
            user_input: User's medical question or prompt  
            user_role: "Doctor" (Admin Mode) or "Patient" (User Mode)
        """
        self.current_role = user_role
        
        # CHECK WHO IS ASKING (Doctor = Admin, Patient = User)
        if user_role == "Doctor":
            return self._doctor_admin_response(user_input)
        elif user_role == "Patient":
            return self._patient_user_response(user_input)
        else:
            return self._generate_error_response(f"Invalid role: {user_role}")
    
    def _doctor_admin_response(self, user_input: str) -> Dict[str, Any]:
        """
        DOCTOR (Admin Mode) Response
        - Provide structured data, verified prompts, clinical instructions
        - Return COMPLETE structured overview using 14 categories
        - Only NHS-verified data as authoritative truth
        """
        try:
            # Identify condition from user_input
            condition_info = self._identify_condition(user_input)
            
            if condition_info:
                return self._generate_doctor_complete_structure(condition_info)
            else:
                return self._generate_doctor_general_response(user_input)
                
        except Exception as e:
            return self._generate_error_response(str(e))
    
    def _patient_user_response(self, user_input: str) -> Dict[str, Any]:
        """
        PATIENT (User Mode) Response  
        - Respond with empathy, clarity, simple explanations
        - Ask questions step-by-step, don't overwhelm
        - Do NOT provide full structured medical overview unless doctor requests it
        - Conversational tone while clinically accurate
        """
        try:
            # Identify condition from user_input
            condition_info = self._identify_condition(user_input)
            
            if condition_info:
                return self._generate_patient_conversational_response(condition_info, user_input)
            else:
                return self._generate_patient_general_response(user_input)
                
        except Exception as e:
            return self._generate_error_response(str(e))
    
    def _identify_condition(self, user_input: str) -> Optional[MedicalCondition]:
        """Identify condition from NHS-verified data only"""
        
        # Only NHS-verified conditions as source of truth
        conditions = self.db.query(MedicalCondition).filter(
            MedicalCondition.verified_by_nhs == True,
            MedicalCondition.nhs_review_status == "approved"
        ).all()
        
        user_lower = user_input.lower()
        
        for condition in conditions:
            condition_name_lower = condition.condition_name.lower()
            
            # Direct name match
            if condition_name_lower in user_lower:
                return condition
            
            # Symptom-based matching
            if condition.symptoms:
                for symptom in condition.symptoms:
                    if symptom.lower() in user_lower:
                        return condition
        
        return None
    
    def _generate_doctor_complete_structure(self, condition: MedicalCondition) -> Dict[str, Any]:
        """DOCTOR: Complete 14-category structured overview"""
        
        # Fill EXACT 14-category structure
        structured_response = {
            "DOCTOR_ADMIN_RESPONSE": True,
            "NHS_VERIFIED": True,
            "Complete Medical Condition Overview": {
                "1. Condition name": condition.condition_name,
                "2. Definition": condition.definition or "Definition not available in database",
                "3. Classification": condition.classification or "Classification pending",
                "4. Epidemiology (Incidence / Prevalence)": f"Incidence: {condition.incidence_rate or 'N/A'} | Prevalence: {condition.prevalence_rate or 'N/A'}",
                "5. Aetiology": condition.aetiology or "Aetiology data pending NHS review",
                "6. Risk factors": condition.risk_factors or [],
                "7. Signs": condition.signs or [],
                "8. Symptoms": condition.symptoms or [],
                "9. Complications": condition.quality_complications or "Complications data pending",
                "10. Tests (and diagnostic criteria)": f"Tests: {condition.diagnostic_tests or []} | Criteria: {condition.diagnostic_criteria or 'Criteria pending'}",
                "11. Differential diagnoses": condition.differential_diagnoses or [],
                "12. Associated conditions": condition.associated_conditions or [],
                "13. Management (conservative, medical, surgical – care pathways)": f"Conservative: {condition.conservative_management or 'N/A'} | Medical: {condition.medical_management or 'N/A'} | Surgical: {condition.surgical_management or 'N/A'} | Care Pathway: {condition.care_pathway or 'N/A'}",
                "14. Prevention (primary, secondary)": f"Primary: {condition.primary_prevention or 'N/A'} | Secondary: {condition.secondary_prevention or 'N/A'}"
            },
            "Source": "NHS-verified structured data",
            "Database": self.database_type,
            "Timestamp": datetime.utcnow().isoformat()
        }
        
        return structured_response
    
    def _generate_doctor_general_response(self, user_input: str) -> Dict[str, Any]:
        """DOCTOR: General clinical response for unrecognized conditions"""
        
        # Check for relevant professional prompts (NHS-verified only)
        relevant_prompts = self._find_nhs_verified_prompts(user_input)
        
        if relevant_prompts:
            return {
                "DOCTOR_ADMIN_RESPONSE": True,
                "message": "Based on NHS-verified professional prompts:",
                "clinical_guidance": relevant_prompts[0].prompt_text,
                "source": "NHS-verified professional prompt",
                "specialty": relevant_prompts[0].specialty,
                "evidence_level": relevant_prompts[0].evidence_level,
                "professional": relevant_prompts[0].created_by_professional,
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            return {
                "DOCTOR_ADMIN_RESPONSE": True,
                "message": "This requires validation by a qualified medical professional.",
                "reason": "No NHS-verified data or professional prompts found for this query",
                "recommendation": "Please consult NHS clinical guidelines or submit professional prompts for this condition",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def _generate_patient_conversational_response(self, condition: MedicalCondition, user_input: str) -> Dict[str, Any]:
        """PATIENT: Conversational, empathetic response without overwhelming"""
        
        # Simple, conversational introduction
        response_parts = [
            {
                "empathy": f"I understand you're asking about {condition.condition_name}. Let me help explain this in a simple way.",
                "context": condition.definition[:200] + "..." if len(condition.definition or "") > 200 else condition.definition
            }
        ]
        
        # Analyze what patient is asking for
        user_lower = user_input.lower()
        
        # Only provide relevant information, don't overwhelm
        if any(word in user_lower for word in ["symptom", "sign", "feel"]):
            if condition.symptoms:
                response_parts.append({
                    "topic": "Symptoms",
                    "simple_explanation": f"Common symptoms include: {', '.join(condition.symptoms[:3])}",
                    "followup_questions": [
                        "Do any of these symptoms sound familiar to you?", 
                        "How long have you been experiencing these symptoms?",
                        "Are there any other concerns you'd like to discuss?"
                    ]
                })
        
        elif any(word in user_lower for word in ["treat", "medicine", "therapy"]):
            if condition.medical_management or condition.conservative_management:
                response_parts.append({
                    "topic": "Treatment", 
                    "simple_explanation": "Treatment usually involves lifestyle changes and possibly medication",
                    "followup_questions": [
                        "Have you discussed treatment options with your doctor?",
                        "Are you currently taking any medications?",
                        "What concerns do you have about treatment?"
                    ]
                })
        
        elif any(word in user_lower for word in ["prevent", "avoid", "risk"]):
            if condition.primary_prevention:
                response_parts.append({
                    "topic": "Prevention",
                    "simple_explanation": "There are steps you can take to help reduce your risk",
                    "followup_questions": [
                        "What lifestyle changes are you considering?",
                        "Do you have any family history of this condition?"
                    ]
                })
        
        else:
            # Default conversational response - don't overwhelm with full structure
            response_parts.append({
                "topic": "General Information",
                "simple_explanation": condition.definition,
                "followup_questions": [
                    f"What specifically would you like to know about {condition.condition_name}?",
                    "Are you experiencing any symptoms right now?",
                    "Do you have any particular concerns?"
                ]
            })
        
        # Always include clinical disclaimer
        response_parts.append({
            "clinical_disclaimer": "This requires validation by a qualified medical professional.",
            "emergency_note": "If you're having severe symptoms or think you need immediate medical attention, please call emergency services.",
            "general_advice": "I encourage you to speak with your healthcare provider for personalized medical advice."
        })
        
        return {
            "PATIENT_USER_RESPONSE": True,
            "conversational_tone": "Empathetic and supportive",
            "information_level": "Simple explanations without medical overwhelm",
            "interaction_type": "Step-by-step questions",
            "response_content": response_parts,
            "source": "NHS-verified condition data",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _generate_patient_general_response(self, user_input: str) -> Dict[str, Any]:
        """PATIENT: General response when no specific condition identified"""
        
        return {
            "PATIENT_USER_RESPONSE": True,
            "message": "I'm here to help with your health questions. Let me ask you some questions to better understand your situation:",
            "followup_questions": [
                "What specific symptoms or concerns are you experiencing?",
                "When did these symptoms start?", 
                "Have you spoken with a healthcare provider about this?",
                "Are there any other symptoms you're worried about?"
            ],
            "support_message": "Please provide more details so I can assist you better.",
            "clinical_disclaimer": "This requires validation by a qualified medical professional.",
            "recommendation": "Consider speaking with your healthcare provider for personalized medical advice."
        }
    
    def _find_nhs_verified_prompts(self, user_input: str) -> List[ProfessionalPrompt]:
        """Find NHS-verified professional prompts only"""
        
        # Only NHS-verified professional prompts as source of truth
        prompts = self.db.query(ProfessionalPrompt).filter(
            ProfessionalPrompt.nhs_quality_check == True,
            ProfessionalPrompt.professional_review_status == "approved"
        ).all()
        
        # Simple keyword matching for relevance
        user_lower = user_input.lower()
        relevant_prompts = []
        
        for prompt in prompts:
            if any(word in user_lower for word in prompt.prompt_text.lower().split()):
                relevant_prompts.append(prompt)
        
        return relevant_prompts[:2]  # Return top 2 most relevant
    
    def _generate_error_response(self, error: str) -> Dict[str, Any]:
        """Error response with clinical disclaimer"""
        return {
            "error": "This requires validation by a qualified medical professional.",
            "technical_details": error,
            "recommendation": "Please consult with a healthcare provider for accurate medical advice.",
            "timestamp": datetime.utcnow().isoformat()
        }


# API Integration Function
def create_medical_response(user_query: str, user_role: str, db: Session, llm_instance: BaseLLM) -> Dict[str, Any]:
    """Create medical AI agent response with EXACT CLIENT SPECIFICATION"""
    
    # Validate roles - only "Doctor" (Admin) or "Patient" (User) allowed
    if user_role not in ["Doctor", "Patient"]:
        return {
            "error": "Invalid role. Must be 'Doctor' (Admin Mode) or 'Patient' (User Mode)",
            "valid_roles": ["Doctor", "Patient"],
            "timestamp": datetime.utcnow().isoformat()
        }
    
    ai_agent = MedicalAIAgent(db, llm_instance)
    response = ai_agent.process_query(user_query, user_role)
    
    # Add role verification
    response["role_specification"] = f"{user_role} Mode Implementation per Client Requirements"
    response["nhs_compliance"] = "Only NHS-verified sources used"
    
    return response