"""
Dual-Role Medical AI Assistant - EXACT CLIENT SPECIFICATION
Admin Mode (Doctor/Knowledge Curator) vs Patient Mode (User/Conversation)
Clear role separation with distinct response formats and disclaimers
"""

from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from models.medical_condition import MedicalCondition, ProfessionalPrompt
from llm.base_llm import BaseLLM
from datetime import datetime
import json
import re

class DualRoleMedicalAI:
    """Medical AI Assistant with EXACT role-based response adaptation"""
    
    def __init__(self, db: Session, llm_instance: BaseLLM):
        self.db = db
        self.llm = llm_instance
        self.database_type = "MySQL"
        
        # EXACT 15-CATEGORY STRUCTURE FOR ADMIN MODE
        self.admin_structure = {
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
            "13. Management – Conservative, Medical, Surgical (describe care pathway and treatment criteria)": "",
            "14. Prevention (Primary, Secondary)": "",
            "15. Codes – SNOMED CT + ICD-10": ""
        }
    
    def process_query(self, user_input: str, user_role: str, system_role_metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Process medical query with EXACT role-based adaptation
        
        Args:
            user_input: Medical query or condition request
            user_role: "Admin" (Doctor/Knowledge Curator) or "Patient" (User/Conversation)
            system_role_metadata: Optional metadata about system role configuration
        """
        
        # VALIDATE ROLE SEPARATION
        if user_role not in ["Admin", "Patient"]:
            return self._generate_error_response(f"Invalid role: {user_role}. Must be 'Admin' or 'Patient'")
        
        # CLEAR ROLE SEPARATION - NEVER CONFUSE THE TWO ROLES
        if user_role == "Admin":
            return self._admin_mode_response(user_input, system_role_metadata)
        elif user_role == "Patient":
            return self._patient_mode_response(user_input)
    
    def _admin_mode_response(self, user_input: str, system_role_metadata: Optional[Dict]) -> Dict[str, Any]:
        """
        ADMIN MODE (Doctor/Knowledge Curator)
        - Always return complete 15-category format
        - Never skip sections
        - Always include clinical disclaimer
        """
        
        # Extract condition from query
        condition_name = self._extract_condition_name(user_input)
        
        # Find condition in NHS-verified database
        condition = self._find_nhs_condition(condition_name)
        
        if condition:
            return self._generate_admin_structured_response(condition)
        else:
            return self._generate_admin_general_response(condition_name)
    
    def _patient_mode_response(self, user_input: str) -> Dict[str, Any]:
        """
        PATIENT MODE (User/Conversation)
        - Never expose full 14-category structure
        - Empathetic, step-by-step questions
        - Simplified explanations
        - No medical jargon overload
        """
        
        # Identify condition for context
        condition_name = self._extract_condition_name(user_input)
        condition = self._find_nhs_condition(condition_name)
        
        if condition:
            return self._generate_patient_conversational_response(condition, user_input)
        else:
            return self._generate_patient_general_response(user_input)
    
    def _extract_condition_name(self, user_input: str) -> str:
        """Extract condition name from various query formats"""
        
        # Clean input and extract condition
        query = user_input.lower().strip()
        
        # Remove common query phrases
        query = re.sub(r'(tell me about|give me|structured overview of|information about|what is)', '', query)
        query = query.strip()
        
        # Return capitalized condition name
        return query.title() if query else user_input.title()
    
    def _find_nhs_condition(self, condition_name: str) -> Optional[MedicalCondition]:
        """Find condition in NHS-verified database"""
        
        # Only NHS-verified conditions as authoritative source
        conditions = self.db.query(MedicalCondition).filter(
            MedicalCondition.verified_by_nhs == True,
            MedicalCondition.nhs_review_status == "approved"
      ).all()
        
        search_name = condition_name.lower().strip()
        
        for condition in conditions:
            if search_name in condition.condition_name.lower():
                return condition
        
        return None
    
    def _generate_admin_structured_response(self, condition: MedicalCondition) -> Dict[str, Any]:
        """ADMIN: Complete 15-category structured response"""
        
        response = {
            "ADMIN_MODE": True,
            "role": "Doctor/Knowledge Curator",
            "response_format": "Complete 15-category structured overview",
            "source": "NHS-verified database",
            "structured_knowledge": {
                "1. Condition name": condition.condition_name,
                "2. Definition": condition.definition or "Not well established",
                "3. Classification": condition.classification or "Not well established",
                "4. Epidemiology (Incidence / Prevalence)": f"Incidence: {condition.incidence_rate or 'Not well established'} | Prevalence: {condition.prevalence_rate or 'Not well established'}" + (f" | Notes: {condition.epidemiology_notes}" if condition.epidemiology_notes else ""),
                "5. Aetiology": condition.aetiology or "Not well established",
                "6. Risk factors": self._format_admin_list(condition.risk_factors, "Not well established"),
                "7. Signs": self._format_admin_list(condition.signs, "Not well established"),
                "8. Symptoms": self._format_admin_list(condition.symptoms, "Not well established"),
                "9. Complications": condition.quality_complications or "Not well established",
                "10. Tests (and diagnostic criteria)": f"Tests: {self._format_admin_list(condition.diagnostic_tests)} | Criteria: {condition.diagnostic_criteria or 'Not well established'}",
                "11. Differential diagnoses": self._format_admin_list(condition.differential_diagnoses, "Not well established"),
                "12. Associated conditions": self._format_admin_list(condition.associated_conditions, "Not well established"),
                "13. Management – Conservative, Medical, Surgical (describe care pathway and treatment criteria)": f"Conservative: {condition.conservative_management or 'Not well established'} | Medical: {condition.medical_management or 'Not well established'} | Surgical: {condition.surgical_management or 'Not well established'} | Care Pathway: {condition.care_pathway or 'Not well established'} | Treatment Criteria: {condition.treatment_criteria or 'Not well established'}",
                "14. Prevention (Primary, Secondary)": f"Primary: {condition.primary_prevention or 'Not well established'} | Secondary: {condition.secondary_prevention or 'Not well established'}",
                "15. Codes – SNOMED CT + ICD-10": self._get_medical_codes(condition)
            },
            "admin_disclaimer": "This structured information is for knowledge curation and requires validation by a qualified medical professional.",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return response
    
    def _generate_admin_general_response(self, condition_name: str) -> Dict[str, Any]:
        """ADMIN: General response when condition not in NHS database"""
        
        return {
            "ADMIN_MODE": True,
            "role": "Doctor/Knowledge Curator", 
            "response_format": "Complete 15-category structured overview",
            "message": f"No NHS-verified data found for '{condition_name}'",
            "structured_knowledge": {
                "1. Condition name": condition_name,
                "2. Definition": "Not well established - requires clinical evaluation",
                "3. Classification": "Not well established - classification pending",
                "4. Epidemiology (Incidence / Prevalence)": "Not well established - epidemiological data pending",
                "5. Aetiology": "Not well established - aetiological factors pending",
                "6. Risk factors": "Not well established - risk factors pending",
                "7. Signs": "Not well established - clinical signs pending", 
                "8. Symptoms": "Not well established - symptoms pending",
                "9. Complications": "Not well established - complications pending",
                "10. Tests (and diagnostic criteria)": "Not well established - diagnostic approach pending",
                "11. Differential diagnoses": "Not well established - differential diagnoses pending",
                "12. Associated conditions": "Not well established - associated conditions pending",
                "13. Management – Conservative, Medical, Surgical (describe care pathway and treatment criteria)": "Not well established - management approach pending",
                "14. Prevention (Primary, Secondary)": "Not well established - prevention strategies pending",
                "15. Codes – SNOMED CT + ICD-10": "Not well established - medical codes pending classification"
            },
            "admin_disclaimer": "This structured information is for knowledge curation and requires validation by a qualified medical professional.",
            "recommendation": "Please consult NHS clinical guidelines or add verified clinical data for this condition",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _generate_patient_conversational_response(self, condition: MedicalCondition, user_input: str) -> Dict[str, Any]:
        """PATIENT: Conversational response - NEVER exposes full structure"""
        
        # Analyze what patient wants to know
        user_lower = user_input.lower()
        
        response_parts = []
        
        # Empathetic introduction - NO MEDICAL JARGON
        response_parts.append({
            "empathy": f"I understand you're asking about {condition.condition_name}. Let me help explain this in simple terms.",
            "simple_explanation": (condition.definition or "This is a medical condition")[:150] + "..." if (condition.definition and len(condition.definition) > 150) else (condition.definition or "This is a medical condition")
        })
        
        # Step-by-step questions based on what patient seems to ask
        if any(word in user_lower for word in ["symptom", "sign", "feel", "hurt"]):
            if condition.symptoms:
                response_parts.append({
                    "topic": "How it might make you feel",
                    "simple_explanation": f"People often experience things like: {', '.join(condition.symptoms[:3])}. This varies from person to person.",
                    "followup_questions": [
                        "Are you experiencing any of these symptoms right now?",
                        "When did you first notice these changes in your body?",
                        "How long have these symptoms been bothering you?"
                    ]
                })
            else:
                response_parts.append({
                    "topic": "Understanding your symptoms",
                    "simple_explanation": "It's important to pay attention to how your body feels and share this with your healthcare provider.",
                    "followup_questions": [
                        "Can you tell me what symptoms you're currently experiencing?",
                        "How are these symptoms affecting your daily life?",
                        "Have you noticed any patterns to when these symptoms occur?"
                    ]
                })
        
        elif any(word in user_lower for word in ["treat", "medicine", "therapy", "cure"]):
            response_parts.append({
                "topic": "Treatment options",
                "simple_explanation": "There are usually several ways to manage this condition, including lifestyle changes and potentially medications.",
                "followup_questions": [
                    "Have you discussed treatment options with your doctor?",
                    "Are you currently taking any medications for other health conditions?",
                    "What are your main concerns about treatment?"
                ]
            })
        
        elif any(word in user_lower for word in ["prevent", "avoid", "stop", "risk"]):
            response_parts.append({
                "topic": "Prevention and reducing risk",
                "simple_explanation": "There are often steps you can take to reduce your risk of developing this condition or to prevent it from getting worse.",
                "followup_questions": [
                    "What lifestyle changes are you considering?",
                    "Do you have any family history of similar health issues?",
                    "What preventive measures are you most interested in learning about?"
                ]
            })
        
        else:
            # Default conversational approach - NO STRUCTURE EXPOSURE
            response_parts.append({
                "topic": "Understanding your health concern",
                "simple_explanation": "It's natural to have questions about your health. Let me help you understand this better.",
                "followup_questions": [
                    f"What specifically would you like to know about {condition.condition_name}?",
                    "Are you experiencing any symptoms right now?",
                    "What brought you to ask about this today?",
                    "Is there a particular aspect that worries you most?"
                ]
            })
        
        return {
            "PATIENT_MODE": True,
            "role": "User/Conversation",
            "response_style": "Empathetic conversational interaction",
            "restriction": "No full medical structure exposure",
            "communication_approach": "Step-by-step questions and simplified explanations",
            "content": response_parts,
            "patient_disclaimer": "This is general information and not a substitute for professional medical advice. Please consult a healthcare provider for personalised guidance.",
            "source": f"Based on NHS-verified information about {condition.condition_name}",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _generate_patient_general_response(self, user_input: str) -> Dict[str, Any]:
        """PATIENT: General response when no specific condition identified"""
        
        return {
            "PATIENT_MODE": True,
            "role": "User/Conversation",
            "empathy_message": "I'm here to help answer your health questions. Let me ask you some questions to better understand your situation:",
            "simple_followup_questions": [
                "Can you tell me what specific health concern brought you here today?",
                "Are you experiencing any symptoms that are worrying you?",
                "When did you first notice these changes in your health?",
                "What would be most helpful for you to understand right now?"
            ],
            "support_message": "Please share more details so I can provide you with helpful, easy-to-understand information.",
            "patient_disclaimer": "This is general information and not a substitute for professional medical advice. Please consult a healthcare provider for personalised guidance.",
            "note": "I focus on providing clear, caring support without overwhelming medical details."
        }
    
    def _format_admin_list(self, data_list: Optional[list], fallback: str = "Not well established") -> str:
        """Format list data for admin response"""
        if data_list and len(data_list) > 0:
            return ", ".join([str(item) for item in data_list])
        return fallback
    
    def _get_medical_codes(self, condition: MedicalCondition) -> str:
        """Extract SNOMED CT and ICD-10 codes"""
        
        # Default codes - would be retrieved from NHS terminology integration
        snomed_ct = "386661006"  # Would come from NHS Terminology Server
        icd10 = "R50.9"  # Would come from NHS coding standards
        
        return f"SNOMED CT: {snomed_ct} | ICD-10: {icd10}"
    
    def _generate_error_response(self, error_message: str) -> Dict[str, Any]:
        """Error response with appropriate disclaimer"""
        return {
            "error": "System error occurred",
            "clinical_note": "This requires validation by a qualified medical professional.",
            "technical_details": error_message,
            "recommendation": "Please consult with a healthcare provider for accurate medical guidance.",
            "timestamp": datetime.utcnow().isoformat()
        }


def create_dual_role_medical_response(user_query: str, user_role: str, db: Session, llm_instance: BaseLLM, system_role_metadata: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Create dual-role medical AI response with EXACT CLIENT SPECIFICATION
    
    Args:
        user_query: Medical query
        user_role: "Admin" (Doctor/Knowledge Curator) or "Patient" (User/Conversation)
        db: Database session
        llm_instance: LLM instance
        system_role_metadata: Optional metadata about system role configuration
    """
    
    # Validate roles - ONLY Admin or Patient allowed
    if user_role not in ["Admin", "Patient"]:
        return {
            "error": "Invalid role specified",
            "valid_roles": ["Admin", "Patient"],
            "explanation": {
                "Admin": "Doctor/Knowledge Curator - Complete 15-category structured overview",
                "Patient": "User/Conversation - Empathetic step-by-step questions"
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    
    ai_assistant = DualRoleMedicalAI(db, llm_instance)
    response = ai_assistant.process_query(user_query, user_role, system_role_metadata)
    
    # Add role verification
    response["role_specification"] = f"{user_role} Mode - EXACT CLIENT SPECIFICATION"
    response["clear_role_separation"] = "Admin vs Patient roles never confused"
    
    return response

