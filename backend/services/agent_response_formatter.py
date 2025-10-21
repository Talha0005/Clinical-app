"""
Agent Response Formatter - EXACT CLIENT REQUIREMENT
All agents must return responses to Admin in this EXACT 14-category format
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import json

class AgentResponseFormatter:
    """Formats ALL agent responses for Admin in standardized 14-category format."""
    
    def __init__(self):
        # EXACT ADMIN FORMAT REQUIREMENT - 14 CATEGORIES (CLIENT SPECIFICATION)
        self.admin_format = {
            "Condition name": "",
            "Definition": "",
            "Classification": "",
            "Epidemiology - Incidence / Prevalence": "",
            "Aetiology": "",
            "Risk factors": [],
            "Signs": [],
            "Symptoms": [],
            "Complications": "",
            "Tests (and diagnostic criteria)": "",
            "Differential diagnoses": [],
            "Associated conditions": [],
            "Management - conservative, medical, surgical": "",
            "Prevention (primary, secondary)": "",
        }
    
    def format_agent_response_for_admin(
        self,
        agent_response: Dict[str, Any],
        condition_name: str,
        agent_type: str = "Unknown",
    ) -> Dict[str, Any]:
        """Format ANY agent response for Admin in EXACT 14-category format."""
        
        formatted_response = {
            "ADMIN_RESPONSE": True,
            "agent_source": agent_type,
            "condition": condition_name,
            "formatted_at": datetime.utcnow().isoformat(),
            "standardized_format": self.admin_format.copy()
        }
        
        # Extract ALL field data first
        extracted_data = (
            self._extract_field_data(agent_response, condition_name)
            if isinstance(agent_response, dict)
            else {}
        )
        
        # Fill standardized format with extracted data
        formatted_response["standardized_format"] = extracted_data
        formatted_response["condition_name"] = condition_name
        
        return formatted_response
    
    def _extract_field_data(
        self, agent_response: Dict[str, Any], condition_name: str
    ) -> Dict[str, Any]:
        """Extract data and map into the exact 14 categories."""
        
        # Initialize with admin format template
        extracted_data = self.admin_format.copy()
        
        # Condition name (prefer parameter, then payload)
        condition_name_from_response = agent_response.get(
            "condition_name", ""
        )
        effective_condition_name = (
            condition_name
            or condition_name_from_response
            or "Not well established"
        )
        extracted_data["Condition name"] = effective_condition_name
        
        extracted_data["Definition"] = self._get_field_value(agent_response, [
            "definition", "definition_text", "overview", "description", "define", "what_is", "meaning", "concept"
        ])
        
        extracted_data["Classification"] = self._get_field_value(agent_response, [
            "classification", "type", "category", "classification_system", "disease_type",
            "clinical_classification", "diagnostic_classification", "severity_classification"
        ])
        
        # Epidemiology combines specific incidence/prevalence if available
        epi_combined = self._combine_epidemiology_data(agent_response)
        if epi_combined != "Not well established":
            extracted_data["Epidemiology - Incidence / Prevalence"] = epi_combined
        else:
            extracted_data["Epidemiology - Incidence / Prevalence"] = self._get_field_value(
                agent_response,
                [
                    "epidemiology",
                    "epidemiological_data",
                    "population_data",
                    "occurrence_rates",
                    "demographic_data",
                    "statistical_data",
                    "frequency",
                ],
            )
        
        extracted_data["Aetiology"] = self._get_field_value(agent_response, [
            "aetiology", "etiology", "causes", "cause", "causation", "pathogenic_factors", 
            "reason", "source", "origin", "trigger", "what_causes", "why", "underlying_cause"
        ])
        
        extracted_data["Risk factors"] = self._get_field_list(agent_response, [
            "risk_factors", "risk_factors_list", "risks", "predisposing_factors",
            "risk_groups", "susceptibility", "vulnerability", "contributing_factors",
            "predisposition", "risk_population", "risk_conditions"
        ])
        
        extracted_data["Signs"] = self._get_field_list(agent_response, [
            "signs", "clinical_signs", "exam_signs", "objective_findings", "exam_findings",
            "clinical_indicators", "observable_signs", "physical_signs"
        ])
        
        extracted_data["Symptoms"] = self._get_field_list(agent_response, [
            "symptoms", "patient_symptoms", "clinical_symptoms", "manifestations", 
            "subjective_symptoms", "indicators", "presentation", "complaints"
        ])
        
        extracted_data["Complications"] = self._get_field_value(agent_response, [
            "complications", "complication_text", "adverse_outcomes", "sequelae",
            "side_effects", "consequences", "negative_outcomes", "associated_problems", "worsening_conditions"
        ])
        
        extracted_data["Tests (and diagnostic criteria)"] = self._combine_diagnostic_data(
            agent_response
        )
        
        extracted_data["Differential diagnoses"] = self._get_field_list(agent_response, [
            "differential_diagnoses", "differentials", "alternative_diagnoses", "possible_diagnoses",
            "diagnostic_alternatives", "rule_out_diagnoses", "competing_diagnoses"
        ])
        
        extracted_data["Associated conditions"] = self._get_field_list(agent_response, [
            "associated_conditions", "comorbidities", "related_conditions", "concurrent_conditions",
            "accompanying_conditions", "linked_conditions", "co_occurring_conditions"
        ])
        
        extracted_data[
            "Management - conservative, medical, surgical"
        ] = self._combined_treatment_data(agent_response)
        
        extracted_data[
            "Prevention (primary, secondary)"
        ] = self._combine_prevention_data(agent_response)
        
        # INTELLIGENT FALLBACKS - if specific data not found, provide generic info
        extracted_data = self._apply_intelligent_fallbacks(extracted_data, agent_response)
        
        return extracted_data
    
    def _apply_intelligent_fallbacks(
        self, extracted_data: Dict[str, Any], agent_response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply robust fallbacks for any missing categories."""

        agent_text = str(agent_response).lower()

        # Definition
        if extracted_data["Definition"] == "Not well established":
            extracted_data["Definition"] = (
                "General medical condition requiring clinical assessment and "
                "appropriate diagnostic evaluation."
            )

        # Classification
        if extracted_data["Classification"] == "Not well established":
            extracted_data["Classification"] = (
                "Varies by condition (e.g., severity, acute/chronic, primary/"
                "secondary). Use clinical classification frameworks."
            )

        # Epidemiology
        epi_key = "Epidemiology - Incidence / Prevalence"
        if extracted_data[epi_key] == "Not well established":
            extracted_data[epi_key] = (
                "Incidence and prevalence depend on population and region; "
                "consult epidemiological studies and registries."
            )

        # Aetiology
        if extracted_data["Aetiology"] == "Not well established":
            if any(w in agent_text for w in ["infection", "bacterial", "viral", "immuno"]):
                extracted_data["Aetiology"] = (
                    "May relate to infections, immune responses, or inflammatory "
                    "processes."
                )
            else:
                extracted_data["Aetiology"] = (
                    "Varies by condition and may include infections, inflammatory "
                    "processes, metabolic factors, genetics, or environmental "
                    "triggers."
                )

        # Risk factors
        if extracted_data["Risk factors"] == ["Not well established"]:
            extracted_data["Risk factors"] = [
                "Age",
                "Chronic medical conditions",
                "Immunocompromised state",
                "Lifestyle and environmental exposures",
            ]

        # Signs
        if extracted_data["Signs"] == ["Not well established"]:
            extracted_data["Signs"] = [
                "Objective findings on examination vary by condition; "
                "clinician assessment required."
            ]

        # Symptoms
        if extracted_data["Symptoms"] == ["Not well established"]:
            extracted_data["Symptoms"] = [
                "Patient-reported features depend on the condition; common "
                "symptoms include malaise and condition-specific complaints."
            ]

        # Complications
        if extracted_data["Complications"] == "Not well established":
            extracted_data["Complications"] = (
                "Potential complications depend on severity, duration, and "
                "underlying cause; monitor for deterioration."
            )

        # Tests (and diagnostic criteria)
        tests_key = "Tests (and diagnostic criteria)"
        if extracted_data[tests_key] == "Not well established":
            extracted_data[tests_key] = (
                "History, physical examination, and targeted investigations; "
                "apply diagnostic thresholds/criteria where available."
            )

        # Differential diagnoses
        if extracted_data["Differential diagnoses"] == ["Not well established"]:
            extracted_data["Differential diagnoses"] = [
                "Differentials depend on presentation and should be refined by "
                "red flags, exam, and investigations."
            ]

        # Associated conditions
        if extracted_data["Associated conditions"] == ["Not well established"]:
            extracted_data["Associated conditions"] = [
                "Common comorbidities and related disorders may coexist; "
                "individual factors apply."
            ]

        # Management - conservative, medical, surgical
        mgmt_key = "Management - conservative, medical, surgical"
        if extracted_data[mgmt_key] == "Not well established":
            extracted_data[mgmt_key] = (
                "Conservative: self-care and lifestyle; Medical: guideline-"
                "directed pharmacotherapy; Surgical: reserved for specific "
                "indications; Care pathway and treatment criteria per local "
                "guidelines."
            )

        # Prevention (primary, secondary)
        prev_key = "Prevention (primary, secondary)"
        if extracted_data[prev_key] == "Not well established":
            extracted_data[prev_key] = (
                "Primary: reduce risk factors and promote health; Secondary: "
                "screening and early detection to prevent progression."
            )

        return extracted_data
    
    def _get_field_value(self, data: Dict[str, Any], possible_keys: List[str]) -> str:
        """Get field value from multiple possible key combinations"""
        
        for key in possible_keys:
            if key in data:
                value = data[key]
                if value and value != "Not well established":
                    return str(value)
        
        # If no data found, return standardized "Not well established"
        return "Not well established"
    
    def _get_field_list(self, data: Dict[str, Any], possible_keys: List[str]) -> List[str]:
        """Get field list from multiple possible key combinations"""
        
        for key in possible_keys:
            if key in data:
                value = data[key]
                if isinstance(value, list):
                    return [str(item) for item in value if item]
                elif isinstance(value, str) and value:
                    return [value]
        
        # If no data found
        return ["Not well established"]
    
    def _combine_epidemiology_data(self, data: Dict[str, Any]) -> str:
        """Combine incidence and prevalence data"""
        
        incidence = self._get_field_value(data, ["incidence", "incidence_rate", "incidence_data"])
        prevalence = self._get_field_value(data, ["prevalence", "prevalence_rate", "prevalence_data"])
        
        if incidence != "Not well established" or prevalence != "Not well established":
            return f"Incidence: {incidence} | Prevalence: {prevalence}"
        
        return "Not well established"
    
    def _combine_diagnostic_data(self, data: Dict[str, Any]) -> str:
        """Combine tests and diagnostic criteria."""
        
        tests = self._get_field_list(data, [
            "tests", "diagnostic_tests", "test_list", "lab_tests", "medical_tests",
            "examinations", "diagnostic_procedures", "clinical_tests", "screening_tests"
        ])
        criteria = self._get_field_value(data, [
            "diagnostic_criteria", "diagnosis_criteria", "criteria", "diagnostic_standards",
            "diagnosis_guidelines", "clinical_criteria", "diagnostic_threshold"
        ])
        
        tests_str = (
            ", ".join(tests)
            if tests != ["Not well established"]
            else "Not well established"
        )
        
        if criteria != "Not well established":
            return f"Tests: {tests_str} | Criteria: {criteria}"
        
        return tests_str
    
    def _combine_management_data(self, data: Dict[str, Any]) -> str:
        """Combine conservative, medical, surgical management."""
        
        conservative = self._get_field_value(data, ["conservative", "conservative_management", "conservative_treatment"])
        medical = self._get_field_value(data, ["medical", "medical_management", "medical_treatment"])
        surgical = self._get_field_value(data, ["surgical", "surgical_management", "surgical_treatment"])
        pathway = self._get_field_value(data, ["care_pathway", "treatment_pathway", "pathway"])
        criteria = self._get_field_value(data, ["treatment_criteria", "criteria", "management_criteria"])
        
        parts = []
        if conservative != "Not well established":
            parts.append(f"Conservative: {conservative}")
        if medical != "Not well established":
            parts.append(f"Medical: {medical}")
        if surgical != "Not well established":
            parts.append(f"Surgical: {surgical}")
        if pathway != "Not well established":
            parts.append(f"Care Pathway: {pathway}")
        if criteria != "Not well established":
            parts.append(f"Treatment Criteria: {criteria}")
        
        if parts:
            return " | ".join(parts)
        
        return "Not well established"
    
    def _combine_prevention_data(self, data: Dict[str, Any]) -> str:
        """Combine prevention strategies."""
        
        prevention = self._get_field_value(data, [
            "prevention", "prevention_strategies", "preventive_measures", 
            "prevent", "avoid", "stop", "reduce_risk", "precautionary_measures",
            "prophylaxis", "risk_reduction", "preventive_care"
        ])
        
        if prevention != "Not well established":
            return prevention
        
        # Try to combine primary and secondary prevention
        primary = self._get_field_value(data, [
            "primary_prevention", "primary", "prevention_primary", 
            "prevent_occurrence", "initial_prevention", "first_prevention"
        ])
        secondary = self._get_field_value(data, [
            "secondary_prevention", "secondary", "prevention_secondary",
            "prevent_progression", "early_detection", "screening_prevention"
        ])
        
        if primary != "Not well established" or secondary != "Not well established":
            return f"Primary: {primary} | Secondary: {secondary}"
        
        return "Not well established"
    
    def _combined_treatment_data(self, data: Dict[str, Any]) -> str:
        """Combine all treatment-related data into one string."""
        
        treatment = self._get_field_value(data, [
            "treatment", "treatments", "management", "therapy", "therapies", 
            "care", "intervention", "medications", "drugs", "medication"
        ])
        
        if treatment != "Not well established":
            return treatment
        
        # Try to combine different treatment approaches
        conservative = self._get_field_value(data, [
            "conservative", "conservative_treatment", "conservative_management", 
            "lifestyle_changes", "non_medical", "supportive_care"
        ])
        medical = self._get_field_value(data, [
            "medical", "medical_treatment", "medical_management", 
            "pharmacological", "drug_treatment", "medication_therapy"
        ])
        surgical = self._get_field_value(data, [
            "surgical", "surgical_treatment", "surgical_management",
            "surgery", "operative", "procedural_treatment"
        ])
        
        parts = []
        if conservative != "Not well established":
            parts.append(f"Conservative: {conservative}")
        if medical != "Not well established":
            parts.append(f"Medical: {medical}")
        if surgical != "Not well established":
            parts.append(f"Surgical: {surgical}")
        
        if parts:
            return " | ".join(parts)
        
        return "Not well established"
    
    def _combined_references_disclaimers_data(self, data: Dict[str, Any]) -> str:
        """Combine references and disclaimers"""
        
        references = self._get_field_value(data, ["references", "source_references", "citations"])
        disclaimers = self._get_field_value(data, ["disclaimer", "disclaimers", "legal_notice"])
        
        parts = []
        if references != "Not well established":
            parts.append(f"References: {references}")
        if disclaimers != "Not well established":
            parts.append(f"Disclaimer: {disclaimers}")
        
        if parts:
            return " | ".join(parts)
        
        # Default disclaimer for medical information
        return "This is general medical information and not a substitute for professional medical advice."


class AgentResponseStandardizer:
    """Standardizes ALL agent outputs to Admin in consistent 14-category format"""
    
    def __init__(self):
        self.formatter = AgentResponseFormatter()
        
        # Agent types that must comply with format
        self.registered_agents = {
            "clinical_reasoning_agent": "Clinical Reasoning Agent",
            "coding_agent": "Medical Coding Agent", 
            "summarization_agent": "Medical Summarization Agent",
            "triage_agent": "Clinical Triage Agent",
            "history_agent": "Patient History Agent",
            "medical_record_agent": "Medical Record Agent",
            "hitl_agent": "Human-in-the-Loop Agent",
            "orchestrator": "Medical Orchestrator Agent",
            "support_nice_checker": "NICE Guidelines Agent",
            "support_red_flag_agent": "Red Flag Detection Agent",
            "support_snomed_mapper": "SNOMED Mapping Agent",
            "sentiment_risk_agent": "Sentiment Risk Agent"
        }
    
    def standardize_all_agent_responses(self, 
                                      agent_responses: List[Dict[str, Any]], 
                                      condition_name: str) -> Dict[str, Any]:
        """
        Standardize responses from ALL agents to Admin in 14-category format
        """
        
        standardized_output = {
            "ALL_AGENTS_STANDARDIZED": True,
            "condition": condition_name,
            "standardization_timestamp": datetime.utcnow().isoformat(),
            "agent_count": len(agent_responses),
            "standardized_responses": []
        }
        
        # Standardize each agent response
        for response_data in agent_responses:
            agent_type = response_data.get("agent_type", "unknown")
            agent_output = response_data.get("output", {})
            
            standardized_response = self.formatter.format_agent_response_for_admin(
                agent_response=agent_output,
                condition_name=condition_name,
                agent_type=agent_type
            )
            
            standardized_output["standardized_responses"].append(standardized_response)
        
        return standardized_output
    
    def ensure_admin_format_compliance(self, agent_response: Dict[str, Any], condition_name: str) -> Dict[str, Any]:
        """
        Ensure any agent response complies with Admin format requirement
        """
        
        agent_type = agent_response.get("agent_type", "unknown")
        response_content = agent_response.get("content", agent_response)
        
        return self.formatter.format_agent_response_for_admin(
            agent_response=response_content,
            condition_name=condition_name,
            agent_type=agent_type
        )


if __name__ == "__main__":
    print("Agent Response Formatter: Ready for Admin format compliance")
