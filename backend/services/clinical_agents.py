"""Enhanced clinical reasoning agents for DigiClinic Phase 2."""

import asyncio
import json
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from .llm_router import DigiClinicLLMRouter, AgentType
from medical.base import MedicalCondition, SearchResult
from medical.nice_cks import NiceCksDataSource
from model.patient import Patient


class ClinicalSeverity(Enum):
    """Clinical severity levels for symptom triage."""

    EMERGENCY = "emergency"
    URGENT = "urgent"
    ROUTINE = "routine"
    SELF_CARE = "self_care"


class TriageRecommendation(Enum):
    """Triage recommendations."""

    CALL_999 = "call_999"
    A_E_IMMEDIATE = "a_e_immediate"
    GP_URGENT = "gp_urgent"
    GP_ROUTINE = "gp_routine"
    PHARMACY = "pharmacy"
    SELF_CARE = "self_care"


@dataclass
class ClinicalHistory:
    """Structured clinical history."""

    chief_complaint: str
    history_present_illness: str
    symptom_onset: Optional[str] = None
    symptom_duration: Optional[str] = None
    symptom_severity: Optional[str] = None
    associated_symptoms: List[str] = field(default_factory=list)
    aggravating_factors: List[str] = field(default_factory=list)
    relieving_factors: List[str] = field(default_factory=list)
    past_medical_history: List[str] = field(default_factory=list)
    current_medications: List[str] = field(default_factory=list)
    allergies: List[str] = field(default_factory=list)
    social_history: Optional[str] = None
    family_history: List[str] = field(default_factory=list)
    review_of_systems: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "chief_complaint": self.chief_complaint,
            "history_present_illness": self.history_present_illness,
            "symptom_onset": self.symptom_onset,
            "symptom_duration": self.symptom_duration,
            "symptom_severity": self.symptom_severity,
            "associated_symptoms": self.associated_symptoms,
            "aggravating_factors": self.aggravating_factors,
            "relieving_factors": self.relieving_factors,
            "past_medical_history": self.past_medical_history,
            "current_medications": self.current_medications,
            "allergies": self.allergies,
            "social_history": self.social_history,
            "family_history": self.family_history,
            "review_of_systems": self.review_of_systems,
        }


@dataclass
class TriageAssessment:
    """Structured triage assessment."""

    severity: ClinicalSeverity
    recommendation: TriageRecommendation
    red_flags: List[str] = field(default_factory=list)
    amber_flags: List[str] = field(default_factory=list)
    green_flags: List[str] = field(default_factory=list)
    rationale: Optional[str] = None
    timeframe: Optional[str] = None  # "immediately", "within 4 hours", "within 2 weeks"
    advice: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "severity": self.severity.value,
            "recommendation": self.recommendation.value,
            "red_flags": self.red_flags,
            "amber_flags": self.amber_flags,
            "green_flags": self.green_flags,
            "rationale": self.rationale,
            "timeframe": self.timeframe,
            "advice": self.advice,
        }


@dataclass
class DifferentialDiagnosis:
    """Structured differential diagnosis."""

    primary_diagnosis: Optional[str] = None
    differential_diagnoses: List[Dict[str, Any]] = field(default_factory=list)
    excluded_diagnoses: List[Dict[str, str]] = field(default_factory=list)
    required_investigations: List[str] = field(default_factory=list)
    clinical_reasoning: Optional[str] = None
    confidence_level: Optional[str] = None  # "high", "moderate", "low"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "primary_diagnosis": self.primary_diagnosis,
            "differential_diagnoses": self.differential_diagnoses,
            "excluded_diagnoses": self.excluded_diagnoses,
            "required_investigations": self.required_investigations,
            "clinical_reasoning": self.clinical_reasoning,
            "confidence_level": self.confidence_level,
        }


class HistoryTakingAgent:
    """Agent specialized in structured clinical history taking."""

    def __init__(self, llm_router: DigiClinicLLMRouter):
        """Initialize history taking agent."""
        self.llm_router = llm_router
        self.agent_type = AgentType.HISTORY_TAKING

    async def take_history(
        self,
        patient_message: str,
        patient: Optional[Patient] = None,
        context: Dict[str, Any] = None,
    ) -> Tuple[ClinicalHistory, List[str]]:
        """
        Take comprehensive clinical history from patient input.

        Args:
            patient_message: Patient's description of their problem
            patient: Patient object if available
            context: Additional context from conversation

        Returns:
            Tuple of (ClinicalHistory, List of follow-up questions)
        """
        # Create structured prompt for history taking
        system_prompt = self._create_history_prompt()

        # Prepare context
        context_str = ""
        if patient:
            context_str += f"Patient: {patient.name}, Age: {patient.age}\n"
            context_str += f"Medical History: {', '.join(patient.medical_history)}\n"
            context_str += (
                f"Current Medications: {', '.join(patient.current_medications)}\n"
            )

        if context:
            context_str += f"Previous Context: {json.dumps(context, indent=2)}\n"

        user_prompt = f"""
        Patient Message: {patient_message}
        
        {context_str}
        
        Please extract structured clinical history and generate appropriate follow-up questions.
        """

        # Get response from LLM
        response = await self.llm_router.route_request(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            agent_type=self.agent_type,
            metadata={
                "task": "history_taking",
                "patient_id": patient.national_insurance if patient else None,
            },
        )

        # Parse response into structured format
        return self._parse_history_response(response, patient)

    def _create_history_prompt(self) -> str:
        """Create specialized prompt for history taking."""
        return """You are a specialized clinical history-taking agent for DigiClinic. Your role is to extract and structure clinical information from patient communications and generate appropriate follow-up questions.

CORE RESPONSIBILITIES:
1. Extract structured clinical history from patient messages
2. Identify missing critical information
3. Generate appropriate follow-up questions using medical best practices
4. Maintain professional, empathetic communication style

EXTRACTION GUIDELINES:
- Chief Complaint: Main reason for consultation
- History of Present Illness: Detailed description of current problem
- Symptom Characteristics: Onset, duration, severity (1-10 scale), quality
- Associated Symptoms: Related symptoms patient may not have mentioned
- Modifying Factors: What makes it better/worse
- Review of Systems: Systematic inquiry about other symptoms
- Red Flags: Any concerning features requiring urgent attention

FOLLOW-UP QUESTION STRATEGY:
- Use open-ended questions first, then closed-ended for specifics
- Ask about SOCRATES (Site, Onset, Character, Radiation, Associated symptoms, Time course, Exacerbating/relieving factors, Severity)
- Screen for red flag symptoms based on presentation
- Be culturally sensitive and use patient-friendly language

OUTPUT FORMAT:
Return structured JSON with:
- extracted_history: Structured clinical history object
- follow_up_questions: Array of relevant questions to ask next
- red_flag_screening: Boolean indicating if red flag screening is needed
- priority_level: "high", "medium", or "low" based on presentation

Always prioritize patient safety and comprehensive assessment."""

    def _parse_history_response(
        self, response: str, patient: Optional[Patient]
    ) -> Tuple[ClinicalHistory, List[str]]:
        """Parse LLM response into structured history and follow-up questions."""
        try:
            # Try to parse JSON response
            data = json.loads(response)

            # Extract history information
            extracted = data.get("extracted_history", {})

            # Create ClinicalHistory object
            history = ClinicalHistory(
                chief_complaint=extracted.get("chief_complaint", ""),
                history_present_illness=extracted.get("history_present_illness", ""),
                symptom_onset=extracted.get("symptom_onset"),
                symptom_duration=extracted.get("symptom_duration"),
                symptom_severity=extracted.get("symptom_severity"),
                associated_symptoms=extracted.get("associated_symptoms", []),
                aggravating_factors=extracted.get("aggravating_factors", []),
                relieving_factors=extracted.get("relieving_factors", []),
                past_medical_history=patient.medical_history if patient else [],
                current_medications=patient.current_medications if patient else [],
                allergies=extracted.get("allergies", []),
                social_history=extracted.get("social_history"),
                family_history=extracted.get("family_history", []),
                review_of_systems=extracted.get("review_of_systems", {}),
            )

            # Extract follow-up questions
            questions = data.get("follow_up_questions", [])

            return history, questions

        except (json.JSONDecodeError, KeyError) as e:
            # Fallback parsing if JSON fails
            return self._fallback_parse_history(response, patient)

    def _fallback_parse_history(
        self, response: str, patient: Optional[Patient]
    ) -> Tuple[ClinicalHistory, List[str]]:
        """Fallback parsing if JSON parsing fails."""
        # Create basic history from response
        history = ClinicalHistory(
            chief_complaint=response[:200] if response else "Not specified",
            history_present_illness=response,
            past_medical_history=patient.medical_history if patient else [],
            current_medications=patient.current_medications if patient else [],
        )

        # Generate basic follow-up questions
        questions = [
            "Can you tell me more about when these symptoms started?",
            "How would you rate the severity on a scale of 1-10?",
            "Have you noticed anything that makes it better or worse?",
        ]

        return history, questions


class SymptomTriageAgent:
    """Agent specialized in symptom triage and risk assessment."""

    def __init__(
        self,
        llm_router: DigiClinicLLMRouter,
        nice_data_source: Optional[NiceCksDataSource] = None,
    ):
        """Initialize symptom triage agent."""
        self.llm_router = llm_router
        self.agent_type = AgentType.SYMPTOM_TRIAGE
        self.nice_data_source = nice_data_source or NiceCksDataSource()

    async def assess_symptoms(
        self, clinical_history: ClinicalHistory, patient: Optional[Patient] = None
    ) -> TriageAssessment:
        """
        Perform symptom triage and risk assessment.

        Args:
            clinical_history: Structured clinical history
            patient: Patient information if available

        Returns:
            TriageAssessment with risk level and recommendations
        """
        # Create triage prompt
        system_prompt = self._create_triage_prompt()

        # Prepare clinical information
        history_json = json.dumps(clinical_history.to_dict(), indent=2)
        patient_info = ""
        if patient:
            patient_info = f"""
            Patient Information:
            - Name: {patient.name}
            - Age: {patient.age}
            - Medical History: {', '.join(patient.medical_history)}
            - Current Medications: {', '.join(patient.current_medications)}
            """

        user_prompt = f"""
        Clinical History:
        {history_json}
        
        {patient_info}
        
        Please assess the clinical risk and provide structured triage recommendations.
        """

        # Get triage assessment from LLM
        response = await self.llm_router.route_request(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            agent_type=self.agent_type,
            metadata={
                "task": "symptom_triage",
                "patient_id": patient.national_insurance if patient else None,
            },
        )

        # Parse response into structured assessment
        return self._parse_triage_response(response)

    def _create_triage_prompt(self) -> str:
        """Create specialized prompt for symptom triage."""
        return """You are a specialized clinical triage agent for DigiClinic. Your role is to assess symptom severity, identify risk factors, and provide evidence-based triage recommendations following NHS guidelines.

RISK ASSESSMENT FRAMEWORK:
RED FLAGS (Emergency - Call 999):
- Chest pain with cardiac features
- Severe breathing difficulties
- Altered consciousness/confusion
- Severe bleeding
- Severe abdominal pain
- Signs of sepsis
- Severe allergic reactions

AMBER FLAGS (Urgent - Same day assessment):
- Moderate pain with concerning features
- Persistent symptoms with risk factors
- Worsening chronic conditions
- New neurological symptoms

GREEN FLAGS (Routine care):
- Mild symptoms with reassuring features
- Stable chronic conditions
- Minor injuries
- Self-limiting conditions

TRIAGE CRITERIA:
1. Symptom severity and acuity
2. Patient age and comorbidities
3. Red flag symptoms present
4. Functional impact
5. Patient anxiety/concerns

OUTPUT REQUIREMENTS:
Return structured JSON with:
- severity: "emergency", "urgent", "routine", or "self_care"
- recommendation: Specific action (call_999, a_e_immediate, gp_urgent, gp_routine, pharmacy, self_care)
- red_flags: Array of identified red flag symptoms
- amber_flags: Array of amber flag symptoms
- green_flags: Array of reassuring features
- rationale: Clinical reasoning for decision
- timeframe: When to seek care
- advice: Specific advice for patient

Always err on the side of caution and prioritize patient safety."""

    def _parse_triage_response(self, response: str) -> TriageAssessment:
        """Parse LLM response into structured triage assessment."""
        try:
            data = json.loads(response)

            # Map string values to enums
            severity_map = {
                "emergency": ClinicalSeverity.EMERGENCY,
                "urgent": ClinicalSeverity.URGENT,
                "routine": ClinicalSeverity.ROUTINE,
                "self_care": ClinicalSeverity.SELF_CARE,
            }

            recommendation_map = {
                "call_999": TriageRecommendation.CALL_999,
                "a_e_immediate": TriageRecommendation.A_E_IMMEDIATE,
                "gp_urgent": TriageRecommendation.GP_URGENT,
                "gp_routine": TriageRecommendation.GP_ROUTINE,
                "pharmacy": TriageRecommendation.PHARMACY,
                "self_care": TriageRecommendation.SELF_CARE,
            }

            severity = severity_map.get(
                data.get("severity", "routine"), ClinicalSeverity.ROUTINE
            )
            recommendation = recommendation_map.get(
                data.get("recommendation", "gp_routine"),
                TriageRecommendation.GP_ROUTINE,
            )

            return TriageAssessment(
                severity=severity,
                recommendation=recommendation,
                red_flags=data.get("red_flags", []),
                amber_flags=data.get("amber_flags", []),
                green_flags=data.get("green_flags", []),
                rationale=data.get("rationale"),
                timeframe=data.get("timeframe"),
                advice=data.get("advice", []),
            )

        except (json.JSONDecodeError, KeyError):
            # Fallback to conservative assessment
            return TriageAssessment(
                severity=ClinicalSeverity.ROUTINE,
                recommendation=TriageRecommendation.GP_ROUTINE,
                rationale="Unable to parse assessment - recommend routine GP review",
                advice=["Please contact your GP for a routine appointment"],
            )


class DifferentialDiagnosisAgent:
    """Agent specialized in generating differential diagnoses."""

    def __init__(
        self,
        llm_router: DigiClinicLLMRouter,
        nice_data_source: Optional[NiceCksDataSource] = None,
    ):
        """Initialize differential diagnosis agent."""
        self.llm_router = llm_router
        self.agent_type = AgentType.CLINICAL_REASONING
        self.nice_data_source = nice_data_source or NiceCksDataSource()

    async def generate_differential(
        self,
        clinical_history: ClinicalHistory,
        triage_assessment: TriageAssessment,
        patient: Optional[Patient] = None,
    ) -> DifferentialDiagnosis:
        """
        Generate differential diagnosis based on clinical information.

        Args:
            clinical_history: Structured clinical history
            triage_assessment: Triage assessment results
            patient: Patient information if available

        Returns:
            DifferentialDiagnosis with possible conditions and reasoning
        """
        # Search NICE CKS for relevant conditions based on symptoms
        relevant_conditions = await self._search_relevant_conditions(clinical_history)

        # Create differential diagnosis prompt
        system_prompt = self._create_differential_prompt()

        # Prepare clinical information
        history_json = json.dumps(clinical_history.to_dict(), indent=2)
        triage_json = json.dumps(triage_assessment.to_dict(), indent=2)

        patient_info = ""
        if patient:
            patient_info = f"""
            Patient Information:
            - Name: {patient.name}
            - Age: {patient.age}
            - Medical History: {', '.join(patient.medical_history)}
            - Current Medications: {', '.join(patient.current_medications)}
            """

        conditions_context = ""
        if relevant_conditions.results:
            conditions_context = "Relevant Medical Conditions from NICE CKS:\n"
            for condition in relevant_conditions.results[
                :5
            ]:  # Top 5 relevant conditions
                conditions_context += f"- {condition.name}: {condition.description}\n"

        user_prompt = f"""
        Clinical History:
        {history_json}
        
        Triage Assessment:
        {triage_json}
        
        {patient_info}
        
        {conditions_context}
        
        Please generate a structured differential diagnosis with clinical reasoning.
        """

        # Get differential diagnosis from LLM
        response = await self.llm_router.route_request(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            agent_type=self.agent_type,
            metadata={
                "task": "differential_diagnosis",
                "patient_id": patient.national_insurance if patient else None,
            },
        )

        # Parse response into structured diagnosis
        return self._parse_differential_response(response)

    async def _search_relevant_conditions(
        self, clinical_history: ClinicalHistory
    ) -> SearchResult:
        """Search for relevant medical conditions based on symptoms."""
        # Create search query from symptoms and chief complaint
        search_terms = [clinical_history.chief_complaint]
        search_terms.extend(clinical_history.associated_symptoms)

        # Remove empty terms and create search query
        search_terms = [term for term in search_terms if term and term.strip()]
        search_query = " ".join(search_terms[:5])  # Limit to avoid overly long queries

        if search_query:
            return await self.nice_data_source.search_conditions(search_query, limit=10)
        else:
            return SearchResult(
                query="", results=[], total_results=0, source="NICE CKS"
            )

    def _create_differential_prompt(self) -> str:
        """Create specialized prompt for differential diagnosis."""
        return """You are a specialized clinical reasoning agent for DigiClinic. Your role is to generate evidence-based differential diagnoses following medical best practices and NHS guidelines.

DIFFERENTIAL DIAGNOSIS APPROACH:
1. Consider common diagnoses first (common things occur commonly)
2. Consider serious diagnoses that cannot be missed
3. Use clinical pattern recognition
4. Apply epidemiological factors (age, gender, risk factors)
5. Consider medication effects and interactions

STRUCTURED REASONING:
- Primary Diagnosis: Most likely diagnosis based on presentation
- Differential List: Other possible diagnoses in order of likelihood
- Excluded Diagnoses: Conditions ruled out and why
- Required Investigations: Tests needed to confirm/exclude diagnoses
- Clinical Reasoning: Detailed explanation of diagnostic reasoning

EVIDENCE-BASED APPROACH:
- Use NICE guidance and clinical evidence
- Consider patient-specific factors
- Account for social determinants of health
- Include medication review impacts

OUTPUT FORMAT:
Return structured JSON with:
- primary_diagnosis: Most likely diagnosis
- differential_diagnoses: Array of objects with {diagnosis, likelihood, supporting_features, contradicting_features}
- excluded_diagnoses: Array of objects with {diagnosis, reason_excluded}
- required_investigations: Array of recommended tests/examinations
- clinical_reasoning: Detailed explanation of reasoning process
- confidence_level: "high", "moderate", or "low"

Always maintain diagnostic uncertainty appropriately and recommend further assessment when needed."""

    def _parse_differential_response(self, response: str) -> DifferentialDiagnosis:
        """Parse LLM response into structured differential diagnosis."""
        try:
            data = json.loads(response)

            return DifferentialDiagnosis(
                primary_diagnosis=data.get("primary_diagnosis"),
                differential_diagnoses=data.get("differential_diagnoses", []),
                excluded_diagnoses=data.get("excluded_diagnoses", []),
                required_investigations=data.get("required_investigations", []),
                clinical_reasoning=data.get("clinical_reasoning"),
                confidence_level=data.get("confidence_level"),
            )

        except (json.JSONDecodeError, KeyError):
            # Fallback differential
            return DifferentialDiagnosis(
                primary_diagnosis="Further assessment required",
                clinical_reasoning="Unable to generate structured differential - recommend comprehensive clinical evaluation",
                confidence_level="low",
                required_investigations=[
                    "Comprehensive clinical assessment",
                    "Consider relevant investigations based on presentation",
                ],
            )


class ClinicalAgentOrchestrator:
    """Orchestrates the clinical agents for comprehensive patient assessment."""

    def __init__(
        self,
        llm_router: DigiClinicLLMRouter,
        nice_data_source: Optional[NiceCksDataSource] = None,
    ):
        """Initialize clinical agent orchestrator."""
        self.llm_router = llm_router
        self.nice_data_source = nice_data_source or NiceCksDataSource()

        # Initialize agents
        self.history_agent = HistoryTakingAgent(llm_router)
        self.triage_agent = SymptomTriageAgent(llm_router, nice_data_source)
        self.differential_agent = DifferentialDiagnosisAgent(
            llm_router, nice_data_source
        )

    async def comprehensive_assessment(
        self,
        patient_message: str,
        patient: Optional[Patient] = None,
        context: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Perform comprehensive clinical assessment using all agents.

        Args:
            patient_message: Patient's description of their problem
            patient: Patient object if available
            context: Additional context from conversation

        Returns:
            Dictionary containing all assessment results
        """
        # Step 1: Take clinical history
        clinical_history, follow_up_questions = await self.history_agent.take_history(
            patient_message, patient, context
        )

        # Step 2: Perform symptom triage
        triage_assessment = await self.triage_agent.assess_symptoms(
            clinical_history, patient
        )

        # Step 3: Generate differential diagnosis (if not emergency)
        differential = None
        if triage_assessment.severity != ClinicalSeverity.EMERGENCY:
            differential = await self.differential_agent.generate_differential(
                clinical_history, triage_assessment, patient
            )

        # Compile comprehensive assessment
        return {
            "clinical_history": clinical_history.to_dict(),
            "triage_assessment": triage_assessment.to_dict(),
            "differential_diagnosis": differential.to_dict() if differential else None,
            "follow_up_questions": follow_up_questions,
            "assessment_timestamp": datetime.utcnow().isoformat(),
            "patient_id": patient.national_insurance if patient else None,
        }

    async def get_follow_up_questions(
        self,
        patient_message: str,
        patient: Optional[Patient] = None,
        context: Dict[str, Any] = None,
    ) -> List[str]:
        """
        Get follow-up questions for ongoing history taking.

        Args:
            patient_message: Patient's latest message
            patient: Patient object if available
            context: Previous assessment context

        Returns:
            List of relevant follow-up questions
        """
        _, questions = await self.history_agent.take_history(
            patient_message, patient, context
        )
        return questions
