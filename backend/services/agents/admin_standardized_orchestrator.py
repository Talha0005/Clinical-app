"""
Admin Standardized Orchestrator - EXACT CLIENT REQUIREMENT
Ensures ALL agents return responses to Admin in standardized 14-category format
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import json
from ..agent_response_formatter import AgentResponseStandardizer
from sqlalchemy.orm import Session

class AdminStandardizedOrchestrator:
    """Orchestrates all agents to ensure Admin receives standardized 14-category format"""
    
    def __init__(self, db: Session):
        self.db = db
        self.standardizer = AgentResponseStandardizer()
        
        # EXACT 14-CATEGORY FORMAT FOR ADMIN (CLIENT SPECIFICATION)
        self.admin_format_categories = [
            "Condition name",
            "Definition",
            "Classification",
            "Epidemiology - Incidence / Prevalence",
            "Aetiology",
            "Risk factors",
            "Signs",
            "Symptoms",
            "Complications",
            "Tests (and diagnostic criteria)",
            "Differential diagnoses",
            "Associated conditions",
            "Management - conservative, medical, surgical",
            "Prevention (primary, secondary)"
        ]
    
    def process_admin_query(self, condition_name: str) -> Dict[str, Any]:
        """
        Process query for Admin - ALWAYS returns standardized 14-category format
        """
        
        # Simulate agent responses (in real scenario, these would be actual agent outputs)
        agent_responses = self._simulate_all_agent_responses(condition_name)
        
        # Standardize ALL agent responses to 14-category format
        standardized_response = self.standardizer.standardize_all_agent_responses(
            agent_responses=agent_responses,
            condition_name=condition_name
        )
        
        # Return ALWAYS in 14-category format
        return {
            "admin_response": True,
            "compliance_guarantee": "ALL agents return standardized 14-category format",
            "format_categories": self.admin_format_categories,
            "standardized_data": standardized_response,
            "compliance_note": "Every agent response has been standardized to EXACT 14-category format",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _simulate_all_agent_responses(self, condition_name: str) -> List[Dict[str, Any]]:
        """Simulate responses from all agents (replace with actual agent calls)"""
        
        agent_responses = [
            {
                "agent_type": "clinical_reasoning_agent",
                "output": self._clinical_reasoning_agent_response(condition_name)
            },
            {
                "agent_type": "coding_agent", 
                "output": self._coding_agent_response(condition_name)
            },
            {
                "agent_type": "summarization_agent",
                "output": self._summarization_agent_response(condition_name)
            },
            {
                "agent_type": "triage_agent",
                "output": self._triage_agent_response(condition_name)
            },
            {
                "agent_type": "history_agent",
                "output": self._history_agent_response(condition_name)
            },
            {
                "agent_type": "medical_record_agent",
                "output": self._medical_record_agent_response(condition_name)
            }
        ]
        
        return agent_responses
    
    def _clinical_reasoning_agent_response(self, condition_name: str) -> Dict[str, Any]:
        """Clinical Reasoning Agent - MUST format for Admin"""
        
        # Raw agent response
        raw_response = {
            "clinical_assessment": f"Assessment of {condition_name}",
            "diagnosis_probability": "High likelihood based on clinical presentation",
            "reasoning_steps": ["Symptom analysis", "Rule out conditions", "Clinical correlation"]
        }
        
        return raw_response
    
    def _coding_agent_response(self, condition_name: str) -> Dict[str, Any]:
        """Medical Coding Agent - MUST format for Admin"""
        
        # Raw agent response
        raw_response = {
            "snomed_codes": ["386661006", "236577007"],
            "icd10_codes": ["R50.9", "G89.3"],
            "coding_system": "NHS Classification",
            "code_confidence": 0.95
        }
        
        return raw_response
    
    def _summarization_agent_response(self, condition_name: str) -> Dict[str, Any]:
        """Medical Summarization Agent - MUST format for Admin"""
        
        # Raw agent response
        raw_response = {
            "summary": f"Complete medical summary for {condition_name}",
            "key_points": ["Clinical significance", "Management approach", "Prognosis"],
            "evidence_level": "Strong clinical evidence",
            "source_references": ["NICE Guidelines", "Medical Literature"]
        }
        
        return raw_response
    
    def _triage_agent_response(self, condition_name: str) -> Dict[str, Any]:
        """Clinical Triage Agent - MUST format for Admin"""
        
        # Raw agent response  
        raw_response = {
            "urgency_level": "Moderate",
            "triage_recommendation": "Timely clinical assessment required",
            "risk_stratification": "Medium risk",
            "recommended_pathway": "Primary to secondary care pathway"
        }
        
        return raw_response
    
    def _history_agent_response(self, condition_name: str) -> Dict[str, Any]:
        """Patient History Agent - MUST format for Admin"""
        
        # Raw agent response
        raw_response = {
            "family_history": "Relevant family medical history",
            "past_medical_history": "Previous related conditions",
            "social_history": "Lifestyle factors affecting condition",
            "medication_history": "Current and past medications"
        }
        
        return raw_response
    
    def _medical_record_agent_response(self, condition_name: str) -> Dict[str, Any]:
        """Medical Record Agent - MUST format for Admin"""
        
        # Raw agent response
        raw_response = {
            "existing_records": f"Available medical records for {condition_name}",
            "record_summary": "Comprehensive medical history documentation",
            "data_completeness": "80% complete",
            "validation_status": "NHS verified"
        }
        
        return raw_response


    def ensure_admin_format_compliance(self, agent_output: Dict[str, Any], condition_name: str) -> Dict[str, Any]:
        """
        GUARANTEE: ALL agents must return standardized 14-category format to Admin
        """
        
        standardizer = AgentResponseStandardizer()
        
        return standardizer.ensure_admin_format_compliance(
            agent_response=agent_output,
            condition_name=condition_name
        )
