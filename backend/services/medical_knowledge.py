"""Medical knowledge base with evidence-based responses for DigiClinic Phase 2."""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import re
from pathlib import Path

from .llm_router import DigiClinicLLMRouter, AgentType
from .nhs_terminology import NHSTerminologyService, ClinicalCodingService
from .medical_observability import medical_observe, EventType
from medical.nice_cks import NiceCksDataSource
from medical.base import MedicalCondition, SearchResult


logger = logging.getLogger(__name__)


class EvidenceLevel(Enum):
    """Evidence quality levels following medical hierarchy."""

    META_ANALYSIS = "meta_analysis"
    SYSTEMATIC_REVIEW = "systematic_review"
    RANDOMIZED_TRIAL = "randomized_trial"
    COHORT_STUDY = "cohort_study"
    CASE_CONTROL = "case_control"
    CASE_SERIES = "case_series"
    EXPERT_OPINION = "expert_opinion"
    CLINICAL_GUIDELINE = "clinical_guideline"
    NICE_GUIDANCE = "nice_guidance"


class RecommendationGrade(Enum):
    """Clinical recommendation grades."""

    GRADE_A = "A"  # High-quality evidence
    GRADE_B = "B"  # Moderate-quality evidence
    GRADE_C = "C"  # Low-quality evidence
    GRADE_D = "D"  # Very low-quality evidence
    GOOD_PRACTICE = "GP"  # Good practice point


@dataclass
class ClinicalEvidence:
    """Represents clinical evidence for medical recommendations."""

    source: str
    evidence_level: EvidenceLevel
    recommendation_grade: RecommendationGrade
    summary: str
    citation: Optional[str] = None
    url: Optional[str] = None
    publication_date: Optional[datetime] = None
    population: Optional[str] = None
    intervention: Optional[str] = None
    outcome: Optional[str] = None
    quality_score: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "source": self.source,
            "evidence_level": self.evidence_level.value,
            "recommendation_grade": self.recommendation_grade.value,
            "summary": self.summary,
            "citation": self.citation,
            "url": self.url,
            "publication_date": (
                self.publication_date.isoformat() if self.publication_date else None
            ),
            "population": self.population,
            "intervention": self.intervention,
            "outcome": self.outcome,
            "quality_score": self.quality_score,
        }


@dataclass
class ClinicalRecommendation:
    """Clinical recommendation with evidence base."""

    recommendation: str
    strength: str  # "strong", "conditional", "good_practice"
    evidence: List[ClinicalEvidence] = field(default_factory=list)
    contraindications: List[str] = field(default_factory=list)
    monitoring_requirements: List[str] = field(default_factory=list)
    patient_factors: List[str] = field(default_factory=list)
    implementation_notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "recommendation": self.recommendation,
            "strength": self.strength,
            "evidence": [e.to_dict() for e in self.evidence],
            "contraindications": self.contraindications,
            "monitoring_requirements": self.monitoring_requirements,
            "patient_factors": self.patient_factors,
            "implementation_notes": self.implementation_notes,
        }


@dataclass
class MedicalGuideline:
    """Medical guideline with evidence-based recommendations."""

    title: str
    organization: str
    guideline_id: str
    publication_date: datetime
    last_updated: datetime
    scope: str
    recommendations: List[ClinicalRecommendation] = field(default_factory=list)
    quality_indicators: List[str] = field(default_factory=list)
    audit_criteria: List[str] = field(default_factory=list)
    patient_information: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "organization": self.organization,
            "guideline_id": self.guideline_id,
            "publication_date": self.publication_date.isoformat(),
            "last_updated": self.last_updated.isoformat(),
            "scope": self.scope,
            "recommendations": [r.to_dict() for r in self.recommendations],
            "quality_indicators": self.quality_indicators,
            "audit_criteria": self.audit_criteria,
            "patient_information": self.patient_information,
        }


class MedicalKnowledgeBase:
    """Medical knowledge base with evidence-based information."""

    def __init__(
        self,
        nice_data_source: NiceCksDataSource,
        nhs_terminology: Optional[NHSTerminologyService] = None,
    ):
        """
        Initialize medical knowledge base.

        Args:
            nice_data_source: NICE Clinical Knowledge Summaries data source
            nhs_terminology: NHS terminology service for coding
        """
        self.nice_data_source = nice_data_source
        self.nhs_terminology = nhs_terminology
        self.clinical_coding = (
            ClinicalCodingService(nhs_terminology) if nhs_terminology else None
        )

        # Knowledge cache
        self.guidelines_cache: Dict[str, MedicalGuideline] = {}
        self.evidence_cache: Dict[str, List[ClinicalEvidence]] = {}

        # Load pre-defined guidelines
        self._load_core_guidelines()

    def _load_core_guidelines(self):
        """Load core medical guidelines."""
        # This would typically load from a database or file system
        # For now, we'll define some key NHS guidelines programmatically

        # Hypertension guideline
        hypertension_guideline = MedicalGuideline(
            title="Hypertension in adults: diagnosis and management",
            organization="NICE",
            guideline_id="NG136",
            publication_date=datetime(2019, 8, 28),
            last_updated=datetime(2022, 3, 18),
            scope="Diagnosis and management of hypertension in adults aged 18 and over",
            recommendations=[
                ClinicalRecommendation(
                    recommendation="Offer ambulatory blood pressure monitoring (ABPM) to confirm the diagnosis of hypertension if clinic blood pressure is 140/90 mmHg or higher",
                    strength="strong",
                    evidence=[
                        ClinicalEvidence(
                            source="NICE Evidence Review",
                            evidence_level=EvidenceLevel.SYSTEMATIC_REVIEW,
                            recommendation_grade=RecommendationGrade.GRADE_A,
                            summary="ABPM is more accurate than clinic measurements for diagnosing hypertension",
                            quality_score=0.9,
                        )
                    ],
                    contraindications=[
                        "Atrial fibrillation with frequent irregular heartbeats"
                    ],
                    monitoring_requirements=[
                        "Annual blood pressure check",
                        "Cardiovascular risk assessment",
                    ],
                ),
                ClinicalRecommendation(
                    recommendation="Offer antihypertensive drug treatment to adults aged under 80 with stage 1 hypertension who have target organ damage, established cardiovascular disease, renal disease, diabetes, or a 10‑year cardiovascular risk equivalent to 10% or greater",
                    strength="strong",
                    evidence=[
                        ClinicalEvidence(
                            source="NICE Clinical Evidence",
                            evidence_level=EvidenceLevel.META_ANALYSIS,
                            recommendation_grade=RecommendationGrade.GRADE_A,
                            summary="Antihypertensive treatment reduces cardiovascular events in high-risk patients",
                            quality_score=0.95,
                        )
                    ],
                    patient_factors=["Age", "Cardiovascular risk", "Comorbidities"],
                    monitoring_requirements=[
                        "Blood pressure monitoring",
                        "Renal function",
                        "Electrolytes",
                    ],
                ),
            ],
            quality_indicators=[
                "Percentage of patients with hypertension who have received ABPM",
                "Percentage of patients achieving blood pressure targets",
            ],
        )

        self.guidelines_cache["hypertension"] = hypertension_guideline

        # Type 2 Diabetes guideline
        diabetes_guideline = MedicalGuideline(
            title="Type 2 diabetes in adults: management",
            organization="NICE",
            guideline_id="NG28",
            publication_date=datetime(2015, 12, 2),
            last_updated=datetime(2022, 6, 29),
            scope="Management of type 2 diabetes in adults",
            recommendations=[
                ClinicalRecommendation(
                    recommendation="Offer metformin as first-line treatment for adults with type 2 diabetes",
                    strength="strong",
                    evidence=[
                        ClinicalEvidence(
                            source="NICE Guideline Evidence",
                            evidence_level=EvidenceLevel.META_ANALYSIS,
                            recommendation_grade=RecommendationGrade.GRADE_A,
                            summary="Metformin is effective and safe as first-line therapy for type 2 diabetes",
                            quality_score=0.92,
                        )
                    ],
                    contraindications=[
                        "eGFR < 30 mL/min/1.73m²",
                        "Severe hepatic impairment",
                    ],
                    monitoring_requirements=[
                        "HbA1c every 3-6 months",
                        "Annual renal function",
                        "Vitamin B12 levels",
                    ],
                )
            ],
            quality_indicators=[
                "Percentage of patients with type 2 diabetes achieving HbA1c targets",
                "Percentage of patients receiving structured education",
            ],
        )

        self.guidelines_cache["type2_diabetes"] = diabetes_guideline

    @medical_observe(EventType.TERMINOLOGY_LOOKUP)
    async def search_evidence(
        self, query: str, condition: Optional[str] = None, limit: int = 10
    ) -> List[ClinicalEvidence]:
        """
        Search for clinical evidence related to a query.

        Args:
            query: Search query
            condition: Specific medical condition
            limit: Maximum number of results

        Returns:
            List of clinical evidence
        """
        cache_key = f"{query}_{condition}_{limit}"

        if cache_key in self.evidence_cache:
            return self.evidence_cache[cache_key]

        evidence_list = []

        # Search NICE CKS for relevant conditions
        if condition:
            condition_result = await self.nice_data_source.get_condition_by_name(
                condition
            )
            if condition_result:
                evidence_list.extend(
                    self._extract_evidence_from_condition(condition_result)
                )

        # Search for conditions matching the query
        search_result = await self.nice_data_source.search_conditions(query, limit)
        for condition in search_result.results:
            evidence_list.extend(self._extract_evidence_from_condition(condition))

        # Search existing guidelines
        for guideline in self.guidelines_cache.values():
            if (
                query.lower() in guideline.title.lower()
                or query.lower() in guideline.scope.lower()
            ):
                for recommendation in guideline.recommendations:
                    evidence_list.extend(recommendation.evidence)

        # Remove duplicates and sort by quality
        unique_evidence = self._deduplicate_evidence(evidence_list)
        sorted_evidence = sorted(
            unique_evidence, key=lambda e: e.quality_score or 0, reverse=True
        )

        # Cache results
        self.evidence_cache[cache_key] = sorted_evidence[:limit]
        return sorted_evidence[:limit]

    def _extract_evidence_from_condition(
        self, condition: MedicalCondition
    ) -> List[ClinicalEvidence]:
        """Extract evidence from a medical condition."""
        evidence_list = []

        # Create evidence from NICE CKS information
        if condition.source_url:
            evidence = ClinicalEvidence(
                source="NICE Clinical Knowledge Summaries",
                evidence_level=EvidenceLevel.CLINICAL_GUIDELINE,
                recommendation_grade=RecommendationGrade.GRADE_B,
                summary=condition.description,
                url=condition.source_url,
                publication_date=(
                    datetime.fromisoformat(condition.last_updated)
                    if condition.last_updated
                    else None
                ),
                quality_score=0.8,  # NICE CKS is generally high quality
            )
            evidence_list.append(evidence)

        return evidence_list

    def _deduplicate_evidence(
        self, evidence_list: List[ClinicalEvidence]
    ) -> List[ClinicalEvidence]:
        """Remove duplicate evidence entries."""
        seen_sources = set()
        unique_evidence = []

        for evidence in evidence_list:
            source_key = f"{evidence.source}_{evidence.summary[:100]}"
            if source_key not in seen_sources:
                seen_sources.add(source_key)
                unique_evidence.append(evidence)

        return unique_evidence

    @medical_observe(EventType.CLINICAL_DECISION)
    async def get_clinical_recommendations(
        self,
        condition: str,
        patient_factors: Dict[str, Any] = None,
        clinical_context: Dict[str, Any] = None,
    ) -> List[ClinicalRecommendation]:
        """
        Get evidence-based clinical recommendations for a condition.

        Args:
            condition: Medical condition
            patient_factors: Patient-specific factors
            clinical_context: Clinical context information

        Returns:
            List of clinical recommendations
        """
        patient_factors = patient_factors or {}
        clinical_context = clinical_context or {}

        recommendations = []

        # Search existing guidelines
        condition_lower = condition.lower()
        for guideline_key, guideline in self.guidelines_cache.items():
            if (
                condition_lower in guideline_key
                or condition_lower in guideline.title.lower()
            ):
                # Filter recommendations based on patient factors
                filtered_recs = self._filter_recommendations_by_patient(
                    guideline.recommendations, patient_factors
                )
                recommendations.extend(filtered_recs)

        # Search NICE CKS for additional recommendations
        nice_condition = await self.nice_data_source.get_condition_by_name(condition)
        if nice_condition:
            nice_recommendations = self._extract_recommendations_from_condition(
                nice_condition
            )
            recommendations.extend(nice_recommendations)

        # Sort by evidence quality and strength
        recommendations.sort(
            key=lambda r: (
                r.strength == "strong",
                max((e.quality_score or 0) for e in r.evidence) if r.evidence else 0,
            ),
            reverse=True,
        )

        return recommendations

    def _filter_recommendations_by_patient(
        self,
        recommendations: List[ClinicalRecommendation],
        patient_factors: Dict[str, Any],
    ) -> List[ClinicalRecommendation]:
        """Filter recommendations based on patient factors."""
        filtered = []

        for rec in recommendations:
            # Check contraindications
            age = patient_factors.get("age")
            comorbidities = patient_factors.get("medical_history", [])
            medications = patient_factors.get("current_medications", [])

            is_contraindicated = False

            for contraindication in rec.contraindications:
                # Simple contraindication checking (would be more sophisticated in production)
                if age and "age" in contraindication.lower():
                    if "under 80" in contraindication.lower() and age >= 80:
                        is_contraindicated = True
                        break

                for condition in comorbidities:
                    if condition.lower() in contraindication.lower():
                        is_contraindicated = True
                        break

                if is_contraindicated:
                    break

            if not is_contraindicated:
                filtered.append(rec)

        return filtered

    def _extract_recommendations_from_condition(
        self, condition: MedicalCondition
    ) -> List[ClinicalRecommendation]:
        """Extract recommendations from a medical condition."""
        recommendations = []

        # Create recommendations from treatment information
        for treatment in condition.treatments:
            recommendation = ClinicalRecommendation(
                recommendation=f"Consider {treatment} for {condition.name}",
                strength="conditional",
                evidence=[
                    ClinicalEvidence(
                        source="NICE Clinical Knowledge Summaries",
                        evidence_level=EvidenceLevel.CLINICAL_GUIDELINE,
                        recommendation_grade=RecommendationGrade.GRADE_C,
                        summary=f"Treatment option for {condition.name}",
                        url=condition.source_url,
                        quality_score=0.7,
                    )
                ],
            )
            recommendations.append(recommendation)

        return recommendations

    @medical_observe(EventType.RISK_ASSESSMENT)
    async def assess_drug_interactions(
        self, medications: List[str], new_medication: str
    ) -> Dict[str, Any]:
        """
        Assess potential drug interactions.

        Args:
            medications: Current medications
            new_medication: New medication to assess

        Returns:
            Drug interaction assessment
        """
        # This would integrate with a proper drug interaction database
        # For now, provide basic assessment framework

        interactions = []
        warnings = []

        # Basic interaction patterns (would be much more comprehensive in production)
        interaction_patterns = {
            "warfarin": {
                "interacts_with": ["aspirin", "ibuprofen", "amiodarone"],
                "severity": "high",
                "mechanism": "Increased bleeding risk",
            },
            "metformin": {
                "interacts_with": ["contrast agents", "alcohol"],
                "severity": "moderate",
                "mechanism": "Risk of lactic acidosis",
            },
            "ace inhibitor": {
                "interacts_with": ["nsaids", "potassium supplements"],
                "severity": "moderate",
                "mechanism": "Renal function impairment",
            },
        }

        # Check for interactions
        new_med_lower = new_medication.lower()
        for current_med in medications:
            current_med_lower = current_med.lower()

            # Check both directions
            for pattern_med, pattern_data in interaction_patterns.items():
                if pattern_med in new_med_lower and any(
                    interacting_med in current_med_lower
                    for interacting_med in pattern_data["interacts_with"]
                ):

                    interactions.append(
                        {
                            "medication1": current_med,
                            "medication2": new_medication,
                            "severity": pattern_data["severity"],
                            "mechanism": pattern_data["mechanism"],
                            "recommendation": "Monitor closely and consider alternatives",
                        }
                    )

                elif pattern_med in current_med_lower and any(
                    interacting_med in new_med_lower
                    for interacting_med in pattern_data["interacts_with"]
                ):

                    interactions.append(
                        {
                            "medication1": current_med,
                            "medication2": new_medication,
                            "severity": pattern_data["severity"],
                            "mechanism": pattern_data["mechanism"],
                            "recommendation": "Monitor closely and consider alternatives",
                        }
                    )

        # Generate warnings based on interactions
        high_severity_count = sum(1 for i in interactions if i["severity"] == "high")
        if high_severity_count > 0:
            warnings.append(
                "High-severity drug interactions detected - clinical review required"
            )

        moderate_severity_count = sum(
            1 for i in interactions if i["severity"] == "moderate"
        )
        if moderate_severity_count > 0:
            warnings.append(
                "Moderate drug interactions detected - monitoring recommended"
            )

        return {
            "new_medication": new_medication,
            "current_medications": medications,
            "interactions": interactions,
            "warnings": warnings,
            "recommendation": (
                "Consult pharmacist for comprehensive interaction review"
                if interactions
                else "No major interactions detected"
            ),
            "assessment_timestamp": datetime.utcnow().isoformat(),
        }


class EvidenceBasedResponseGenerator:
    """Generates evidence-based medical responses."""

    def __init__(
        self,
        llm_router: DigiClinicLLMRouter,
        knowledge_base: MedicalKnowledgeBase,
        nhs_terminology: Optional[NHSTerminologyService] = None,
    ):
        """
        Initialize evidence-based response generator.

        Args:
            llm_router: LLM router for AI responses
            knowledge_base: Medical knowledge base
            nhs_terminology: NHS terminology service
        """
        self.llm_router = llm_router
        self.knowledge_base = knowledge_base
        self.nhs_terminology = nhs_terminology
        self.clinical_coding = (
            ClinicalCodingService(nhs_terminology) if nhs_terminology else None
        )

    @medical_observe(EventType.CLINICAL_DECISION)
    async def generate_evidence_based_response(
        self,
        query: str,
        clinical_context: Dict[str, Any] = None,
        patient_factors: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Generate evidence-based medical response.

        Args:
            query: Medical query
            clinical_context: Clinical context information
            patient_factors: Patient-specific factors

        Returns:
            Evidence-based response with citations
        """
        clinical_context = clinical_context or {}
        patient_factors = patient_factors or {}

        # Extract medical conditions from query
        potential_conditions = await self._extract_conditions_from_query(query)

        # Gather relevant evidence
        evidence_list = []
        recommendations = []

        for condition in potential_conditions:
            # Get evidence for each condition
            condition_evidence = await self.knowledge_base.search_evidence(
                query, condition, limit=5
            )
            evidence_list.extend(condition_evidence)

            # Get clinical recommendations
            condition_recommendations = (
                await self.knowledge_base.get_clinical_recommendations(
                    condition, patient_factors, clinical_context
                )
            )
            recommendations.extend(condition_recommendations)

        # If no specific conditions identified, search broadly
        if not potential_conditions:
            evidence_list = await self.knowledge_base.search_evidence(query, limit=10)

        # Generate AI response using evidence
        ai_response = await self._generate_ai_response_with_evidence(
            query, evidence_list, recommendations, clinical_context, patient_factors
        )

        # Add clinical coding if available
        snomed_codes = []
        if self.clinical_coding and potential_conditions:
            for condition in potential_conditions:
                coded_diagnoses = await self.clinical_coding.code_diagnosis(condition)
                snomed_codes.extend(coded_diagnoses[:3])  # Top 3 for each condition

        return {
            "query": query,
            "response": ai_response,
            "evidence": [e.to_dict() for e in evidence_list],
            "recommendations": [r.to_dict() for r in recommendations],
            "snomed_codes": snomed_codes,
            "conditions_identified": potential_conditions,
            "evidence_quality_score": self._calculate_evidence_quality(evidence_list),
            "response_timestamp": datetime.utcnow().isoformat(),
        }

    async def _extract_conditions_from_query(self, query: str) -> List[str]:
        """Extract potential medical conditions from query."""
        # Use NLP techniques to identify medical terms
        # This is simplified - would use more sophisticated NLP in production

        medical_terms = []

        # Common medical condition patterns
        condition_patterns = [
            r"\b(diabetes|hypertension|asthma|copd|pneumonia|influenza|migraine|arthritis)\b",
            r"\b(heart disease|kidney disease|liver disease|lung disease)\b",
            r"\b(depression|anxiety|bipolar|schizophrenia)\b",
            r"\b(cancer|tumor|malignancy|carcinoma|lymphoma)\b",
        ]

        query_lower = query.lower()
        for pattern in condition_patterns:
            matches = re.findall(pattern, query_lower)
            medical_terms.extend(matches)

        # Search NICE CKS for additional matches
        if medical_terms:
            search_result = (
                await self.knowledge_base.nice_data_source.search_conditions(
                    " ".join(medical_terms), limit=5
                )
            )
            for condition in search_result.results:
                if condition.name not in medical_terms:
                    medical_terms.append(condition.name)

        return list(set(medical_terms))  # Remove duplicates

    async def _generate_ai_response_with_evidence(
        self,
        query: str,
        evidence_list: List[ClinicalEvidence],
        recommendations: List[ClinicalRecommendation],
        clinical_context: Dict[str, Any],
        patient_factors: Dict[str, Any],
    ) -> str:
        """Generate AI response incorporating evidence and recommendations."""

        # Create evidence summary
        evidence_summary = ""
        if evidence_list:
            evidence_summary = "Relevant Clinical Evidence:\n"
            for i, evidence in enumerate(evidence_list[:5], 1):
                evidence_summary += f"{i}. {evidence.summary} (Source: {evidence.source}, Quality: {evidence.recommendation_grade.value})\n"

        # Create recommendations summary
        recommendations_summary = ""
        if recommendations:
            recommendations_summary = "\nClinical Recommendations:\n"
            for i, rec in enumerate(recommendations[:3], 1):
                recommendations_summary += (
                    f"{i}. {rec.recommendation} (Strength: {rec.strength})\n"
                )

        # Create context summary
        context_summary = ""
        if clinical_context or patient_factors:
            context_summary = "\nPatient Context:\n"
            if patient_factors.get("age"):
                context_summary += f"- Age: {patient_factors['age']}\n"
            if patient_factors.get("medical_history"):
                context_summary += f"- Medical History: {', '.join(patient_factors['medical_history'])}\n"
            if patient_factors.get("current_medications"):
                context_summary += f"- Current Medications: {', '.join(patient_factors['current_medications'])}\n"

        # Create comprehensive prompt
        system_prompt = """You are Dr. Hervix, a senior NHS GP providing evidence-based medical advice through DigiClinic. 

Your responses must be:
- Based on provided clinical evidence and guidelines
- Appropriate for the patient's specific context
- Clear and professionally written
- Include appropriate disclaimers about seeking professional medical care
- Cite evidence sources when making clinical statements

Always structure your response with:
1. Direct answer to the query
2. Evidence-based rationale
3. Practical recommendations
4. When to seek further medical care
5. References to evidence sources

Remember: You are providing educational information and guidance, not replacing professional medical examination."""

        user_prompt = f"""
Patient Query: {query}

{evidence_summary}

{recommendations_summary}

{context_summary}

Please provide an evidence-based response that:
1. Directly addresses the patient's question
2. Incorporates the relevant clinical evidence
3. Provides practical, actionable advice
4. Includes appropriate safety netting advice
5. Maintains a professional, empathetic tone

Ensure you reference the evidence sources and indicate the strength of recommendations where appropriate.
"""

        # Generate response using clinical reasoning agent
        response = await self.llm_router.route_request(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            agent_type=AgentType.CLINICAL_REASONING,
            metadata={
                "task": "evidence_based_response",
                "evidence_count": len(evidence_list),
                "recommendation_count": len(recommendations),
            },
        )

        return response

    def _calculate_evidence_quality(
        self, evidence_list: List[ClinicalEvidence]
    ) -> float:
        """Calculate overall evidence quality score."""
        if not evidence_list:
            return 0.0

        quality_scores = []
        for evidence in evidence_list:
            # Base score from quality score if available
            base_score = evidence.quality_score or 0.5

            # Adjust based on evidence level
            level_multipliers = {
                EvidenceLevel.META_ANALYSIS: 1.0,
                EvidenceLevel.SYSTEMATIC_REVIEW: 0.95,
                EvidenceLevel.RANDOMIZED_TRIAL: 0.9,
                EvidenceLevel.CLINICAL_GUIDELINE: 0.85,
                EvidenceLevel.NICE_GUIDANCE: 0.85,
                EvidenceLevel.COHORT_STUDY: 0.7,
                EvidenceLevel.CASE_CONTROL: 0.6,
                EvidenceLevel.CASE_SERIES: 0.4,
                EvidenceLevel.EXPERT_OPINION: 0.3,
            }

            multiplier = level_multipliers.get(evidence.evidence_level, 0.5)
            quality_scores.append(base_score * multiplier)

        return sum(quality_scores) / len(quality_scores)
