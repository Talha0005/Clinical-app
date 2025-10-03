"""
Medical AI Agent Service
Trained on verified structured data and validated prompts from medical professionals
Follows structured medical condition format with role-based adaptation
"""

from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from models.medical_condition import MedicalCondition, ProfessionalPrompt
from models.database_models import get_db
from llm.base_llm import BaseLLM
from datetime import datetime
import json
import re

class MedicalAIAgent:
    """Medical AI Agent with structured medical knowledge and role adaptation"""
    
    def __init__(self, db: Session, llm_instance: BaseLLM):
        self.db = db
        self.llm = llm_instance
        self.current_role = None  # "patient" or "doctor"
        
        # Medical condition structure template
        self.condition_structure = {
            "condition_name": "",
            "definition": "",
            "classification": "",
            "epidemiology": {"incidence": "", "prevalence": ""},
            "aetiology": "",
            "risk_factors": [],
            "signs": [],
            "symptoms": [],
            "complications": "",
            "tests": {"diagnostic_tests": [], "diagnostic_criteria": ""},
            "differential_diagnoses": [],
            "associated_conditions": [],
            "management": {
                "conservative": "",
                "medical": "",
                "surgical": "",
                "care_pathways": ""
            },
            "prevention": {"primary": "", "secondary": ""}
        }
    
    def process_query(self, user_input: str, user_role: str = "patient") -> Dict[str, Any]:
        """
        Process medical query with role-specific behavior
        
        Args:
            user_input: User's medical question or prompt
            user_role: "patient" or "doctor" - determines response format and depth
        """
        self.current_role = user_role
        
        try:
            # Identify if this is about a specific condition
            condition_info = self._identify_condition(user_input)
            
            if condition_info:
                return self._generate_structured_response(user_input, condition_info)
            else:
                return self._generate_general_response(user_input)
                
        except Exception as e:
            return self._generate_error_response(str(e))
    
    def _identify_condition(self, user_input: str) -> Optional[MedicalCondition]:
        """Identify if user query is about a specific medical condition"""
        
        # Search for conditions in the query
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
            
            # Check if user is asking about symptoms that match this condition
            if condition.symptoms:
                for symptom in condition.symptoms:
                    if symptom.lower() in user_lower:
                        return condition
        
        return None
    
    def _generate_structured_response(self, user_input: str, condition: MedicalCondition) -> Dict[str, Any]:
        """Generate structured response for specific medical condition"""
        
        if self.current_role == "patient":
            return self._generate_patient_response(user_input, condition)
        else:
            return self._generate_doctor_response(user_input, condition)
    
    def _generate_patient_response(self, user_input: str, condition: MedicalCondition) -> Dict[str, Any]:
        """Generate empathetic, step-by-step response for patients"""
        
        # Analyze what specific aspect the patient is asking about
        query_type = self._analyze_patient_query_type(user_input, condition)
        
        response_parts = []
        
        if query_type == "general_info":
            response_parts.append({
                "section": "introduction",
                "content": f"I'm here to help you understand {condition.condition_name}. Let me explain this step by step."
            })
            
            response_parts.append({
                "section": "condition_overview",
                "content": f"{condition.condition_name} is {condition.definition.lower()}"
            })
            
            # Add symptoms if patient is asking about their symptoms
            if condition.symptoms:
                symptoms_text = f"Common symptoms include: {', '.join(condition.symptoms[:3])}"
                if len(condition.symptoms) > 3:
                    symptoms_text += f", and others."
                response_parts.append({
                    "section": "symptoms",
                    "content": symptoms_text,
                    "followup": "Do any of these symptoms sound familiar to you?"
                })
        
        elif query_type == "symptoms":
            if condition.symptoms:
                response_parts.append({
                    "section": "symptom_assessment",
                    "content": f"The main symptoms of {condition.condition_name} include:",
                    "symptoms": condition.symptoms[:5],
                    "followup": "I'd like to ask you some questions to better understand your situation."
                })
        
        elif query_type == "treatment":
            management_info = self._simplify_management_for_patient(condition)
            response_parts.append({
                "section": "treatment_overview",
                "content": f"Treatment for {condition.condition_name} typically includes:",
                "management": management_info,
                "followup": "Have you discussed treatment options with your doctor?"
            })
        
        elif query_type == "prevention":
            if condition.primary_prevention or condition.secondary_prevention:
                prevention_info = self._simplify_prevention_for_patient(condition)
                response_parts.append({
                    "section": "prevention",
                    "content": prevention_info,
                    "followup": "Would you like guidance on preventive measures?"
                })
        
        # Always remind patient to consult healthcare provider
        response_parts.append({
            "section": "medical_disclaimer",
            "content": "This information is for educational purposes. If you're experiencing symptoms or have concerns, please consult with a qualified healthcare professional.",
            "emergency_note": "If you're having severe symptoms or think you might need immediate medical attention, please call emergency services or visit your nearest emergency department."
        })
        
        return {
            "role": "patient",
            "condition": condition.condition_name,
            "query_type": query_type,
            "response_parts": response_parts,
            "structured_data": condition.to_dict(),
            "source": "NHS_verified_condition",
            "confidence": 0.95
        }
    
    def _generate_doctor_response(self, user_input: str, condition: MedicalCondition) -> Dict[str, Any]:
        """Generate detailed, structured response for medical professionals"""
        
        response_data = {
            "role": "doctor",
            "condition": condition.condition_name,
            "structured_info": self.condition_structure.copy()
        }
        
        # Fill structured format with condition data
        response_data["structured_info"]["condition_name"] = condition.condition_name
        response_data["structured_info"]["definition"] = condition.definition
        response_data["structured_info"]["classification"] = condition.classification or ""
        
        # Epidemiology
        if condition.incidence_rate or condition.prevalence_rate:
            response_data["structured_info"]["epidemiology"] = {
                "incidence": f"{condition.incidence_rate or 'N/A'} per 1000 population",
                "prevalence": f"{condition.prevalence_rate or 'N/A'} per 1000 population"
            }
            if condition.epidemiology_notes:
                response_data["structured_info"]["epidemiology"]["notes"] = condition.epidemiology_notes
        
        # Aetiology
        response_data["structured_info"]["aetiology"] = condition.aetiology or ""
        
        # Risk factors, signs, symptoms
        response_data["structured_info"]["risk_factors"] = condition.risk_factors or []
        response_data["structured_info"]["signs"] = condition.signs or []
        response_data["structured_info"]["symptoms"] = condition.symptoms or []
        
        # Complications
        response_data["structured_info"]["complications"] = condition.quality_complications or ""
        
        # Diagnostic information
        response_data["structured_info"]["tests"] = {
            "diagnostic_tests": condition.diagnostic_tests or [],
            "diagnostic_criteria": condition.diagnostic_criteria or ""
        }
        
        # Clinical reasoning
        response_data["structured_info"]["differential_diagnoses"] = condition.differential_diagnoses or []
        response_data["structured_info"]["associated_conditions"] = condition.associated_conditions or []
        
        # Management
        response_data["structured_info"]["management"] = {
            "conservative": condition.conservative_management or "",
            "medical": condition.medical_management or "",
            "surgical": condition.surgical_management or "",
            "care_pathways": condition.care_pathway or ""
        }
        if condition.treatment_criteria:
            response_data["structured_info"]["management"]["treatment_criteria"] = condition.treatment_criteria
        
        # Prevention
        response_data["structured_info"]["prevention"] = {
            "primary": condition.primary_prevention or "",
            "secondary": condition.secondary_prevention or ""
        }
        
        # Add clinical notes for physicians
        response_data["clinical_notes"] = {
            "nhs_verified": condition.verified_by_nhs,
            "evidence_sources": condition.source_references or [],
            "last_updated": condition.last_updated.isoformat() if condition.last_updated else None
        }
        
        # Professional validation reminder
        response_data["validation_note"] = "This information is based on NHS-verified structured data. Always validate with current clinical guidelines and your clinical judgment."
        
        return response_data
    
    def _generate_general_response(self, user_input: str) -> Dict[str, Any]:
        """Generate response for general medical queries without specific condition"""
        
        # Try to extract relevant professional prompts
        relevant_prompts = self._find_relevant_professional_prompts(user_input)
        
        response = {
            "role": self.current_role,
            "query": user_input,
            "response_type": "general_medical_guidance"
        }
        
        if relevant_prompts:
            response["professional_guidance"] = {
                "prompts_used": [prompt.title for prompt in relevant_prompts],
                "expertise_sources": [prompt.created_by_professional for prompt in relevant_prompts],
                "evidence_level": "professional_prompts_verified"
            }
            
            # Generate response based on professional prompts
            if self.current_role == "patient":
                response["content"] = self._adapt_prompt_for_patient(relevant_prompts[0], user_input)
            else:
                response["content"] = self._adapt_prompt_for_doctor(relevant_prompts[0], user_input)
        
        else:
            # No specific verified information available
            response["content"] = "This requires validation by a qualified medical professional."
            response["recommendation"] = "Please consult with a healthcare provider for accurate medical advice."
        
        return response
    
    def _find_relevant_professional_prompts(self, user_input: str) -> List[ProfessionalPrompt]:
        """Find relevant NHS-verified professional prompts for the query"""
        
        prompts = self.db.query(ProfessionalPrompt).filter(
            ProfessionalPrompt.nhs_quality_check == True,
            ProfessionalPrompt.professional_review_status == "approved"
        ).all()
        
        # Simple keyword matching (can be enhanced with semantic search)
        user_lower = user_input.lower()
        relevant_prompts = []
        
        for prompt in prompts:
            prompt_text_lower = prompt.prompt_text.lower()
            
            # Check if query keywords match prompt content
            query_words = set(user_lower.split())
            prompt_words = set(prompt_text_lower.split())
            
            # Find meaningful medical terms that overlap
            medical_terms = query_words.intersection(prompt_words)
            
            if len(medical_terms) > 2:  # Threshold for relevance
                relevant_prompts.append(prompt)
        
        return relevant_prompts[:3]  # Return top 3 most relevant
    
    def _analyze_patient_query_type(self, user_input: str, condition: MedicalCondition) -> str:
        """Analyze what type of question the patient is asking"""
        
        user_lower = user_input.lower()
        
        symptom_keywords = ["symptom", "feel", "hurt", "pain", "ache", "uncomfortable"]
        treatment_keywords = ["treat", "cure", "medicine", "therapy", "surgery"]
        prevention_keywords = ["prevent", "avoid", "stop", "risk"]
        
        if any(key(word in user_lower for key in symptom_keywords):
            return "symptoms"
        elif any(word in user_lower for word in treatment_keywords):
            return "treatment"
        elif any(word in user_lower for word in prevention_keywords):
            return "prevention"
        else:
            return "general_info"
    
    def _simplify_management_for_patient(self, condition: MedicalCondition) -> List[str]:
        """Simplify medical management info for patient understanding"""
        
        simplified = []
        
        if condition.conservative_management:
            simplified.append("Conservative approaches (lifestyle changes, rest, physical therapy)")
        
        if condition.medical_management:
            simplified.append("Medication and medical treatments")
        
        if condition.surgical_management:
            simplified.append("Surgical options (if needed)")
        
        return simplified
    
    def _simplify_prevention_for_patient(self, condition: MedicalCondition) -> str:
        """Simplify prevention info for patient understanding"""
        
        prevention_info = []
        
        if condition.primary_prevention:
            prevention_info.append(f"Prevention: {condition.primary_prevention}")
        
        if condition.secondary_prevention:
            prevention_info.append(f"Early intervention: {condition.secondary_prevention}")
        
        return ". ".join(prevention_info)
    
    def _adapt_prompt_for_patient(self, prompt: ProfessionalPrompt, user_input: str) -> str:
        """Adapt professional prompt content for patient understanding"""
        
        # Use LLM to adapt medical language to patient-friendly language
        adaptation_prompt = f"""
        You are helping translate medical information from a professional prompt for a patient.
        
        Professional prompt: {prompt.prompt_text}
        Patient's question: {user_input}
        
        Please provide a patient-friendly response that:
        - Uses simple, clear language
        - Is empathetic and supportive
        - Explains complex medical terms
        - Encourages consultation with healthcare providers
        - Avoids giving specific medical advice
        
        Respond in a conversational, caring tone.
        """
        
        try:
            adapted_response = self.llm.generate_response(adaptation_prompt)
            return adapted_response
        except:
            return "This requires validation by a qualified medical professional. Please consult with your healthcare provider for personalized medical advice."
    
    def _adapt_prompt_for_doctor(self, prompt: ProfessionalPrompt, user_input: str) -> str:
        """Adapt professional prompt content for medical professional"""
        
        doctor_response = f"""
        Professional Guideline (Verified by NHS):
        
        Title: {prompt.title}
        Category: {prompt.prompt_category}
        Clinical Context: {prompt.clinical_context or 'General clinical guidance'}
        
        Evidence Level: {prompt.evidence_level or 'Professional consensus'}
        Specialty Expert: {prompt.created_by_professional} ({prompt.professional_title or ''})
        
        Clinical Guidance:
        {prompt.prompt_text}
        
        Clinical Indicators for Use: {json.dumps(prompt.clinical_indicators or {}, indent=2)}
        
        Verification Status: NHS Quality Checked
        Usage Statistics: Used {prompt.usage_count} times by medical professionals
        
        Note: Always validate with current clinical guidelines and your clinical judgment.
        """
        
        return doctor_response
    
    def _generate_error_response(self, error: str) -> Dict[str, Any]:
        """Generate error response"""
        return {
            "role": self.current_role,
            "error": "This requires validation by a qualified medical professional.",
            "technical_issue": error,
            "recommendation": "Please consult with a healthcare provider for accurate medical advice."
        }


# API Integration Function
def create_medical_response(user_query: str, user_role: str, db: Session, llm_instance: BaseLLM) -> Dict[str, Any]:
    """Create medical AI agent response for API endpoints"""
    
    ai_agent = MedicalAIAgent(db, llm_instance)
    response = ai_agent.process_query(user_query, user_role)
    
    # Add API metadata
    response["timestamp"] = datetime.utcnow().isoformat()
    response["api_version"] = "1.0"
    response["nhs_compliance"] = "verified_sources_only"
    
    return response
