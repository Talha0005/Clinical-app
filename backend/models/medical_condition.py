"""
Medical Condition Data Model
Structured data organization for medical conditions as requested by client
"""

from sqlalchemy import Column, Integer, String, Text, JSON, DateTime, Boolean, Float
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from typing import Dict, Any

Base = declarative_base()


class MedicalCondition(Base):
    __tablename__ = 'medical_conditions'
    
    id = Column(Integer, primary_key=True, index=True)
    condition_name = Column(String(255), nullable=False, unique=True, index=True)
    
    # Core information
    definition = Column(Text, nullable=False)
    classification = Column(String(500), nullable=True)
    
    # Epidemiology
    incidence_rate = Column(Float, nullable=True, comment="Incidence per 1000 population")
    prevalence_rate = Column(Float, nullable=True, comment="Prevalence per 1000 population")
    epidemiology_notes = Column(Text, nullable=True)
    
    # Disease processes
    aetiology = Column(Text, nullable=True)
    risk_factors = Column(JSON, nullable=True)  # Structured risk factors
    
    # Clinical presentation
    signs = Column(JSON, nullable=True)  # List of signs
    symptoms = Column(JSON, nullable=True)  # List of symptoms
    
    # Complications and outcomes
    complications = Column(Text, nullable=True)
    
    # Diagnostic information
    diagnostic_tests = Column(JSON, nullable=True)  # List of tests with criteria
    diagnostic_criteria = Column(Text, nullable=True)
    
    # Clinical reasoning
    differential_diagnoses = Column(JSON, nullable=True)  # List of differentials
    associated_conditions = Column(JSON, nullable=True)  # List of comorbidities
    
    # Management structured data
    conservative_management = Column(JSON, nullable=True)
    medical_management = Column(JSON, nullable=True)
    surgical_management = Column(JSON, nullable=True)
    care_pathway = Column(Text, nullable=True)
    treatment_criteria = Column(Text, nullable=True)
    
    # Prevention
    primary_prevention = Column(Text, nullable=True)
    secondary_prevention = Column(Text, nullable=True)
    
    # Metadata
    created_by = Column(String(255), nullable=True)  # Professional who added
    verified_by_nhs = Column(Boolean, default=False)
    last_updated = Column(DateTime, default=datetime.utcnow)
    source_references = Column(JSON, nullable=True)
    
    # Quality control
    professional_review_status = Column(String(50), default='pending')  # pending, approved, rejected
    nhs_review_status = Column(String(50), default='pending')
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'condition_name': self.condition_name,
            'definition': self.definition,
            'classification': self.classification,
            'incidence_rate': self.incidence_rate,
            'prevalence_rate': self.prevalence_rate,
            'epidemiology_notes': self.epidemiology_notes,
            'aetiology': self.aetiology,
            'risk_factors': self.risk_factors,
            'signs': self.signs,
            'symptoms': self.symptoms,
            'complications': self.complications,
            'diagnostic_tests': self.diagnostic_tests,
            'diagnostic_criteria': self.diagnostic_criteria,
            'differential_diagnoses': self.differential_diagnoses,
            'associated_conditions': self.associated_conditions,
            'conservative_management': self.conservative_management,
            'medical_management': self.medical_management,
            'surgical_management': self.surgical_management,
            'care_pathway': self.care_pathway,
            'treatment_criteria': self.treatment_criteria,
            'primary_prevention': self.primary_prevention,
            'secondary_prevention': self.secondary_prevention,
            'created_by': self.created_by,
            'verified_by_nhs': self.verified_by_nhs,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'professional_review_status': self.professional_review_status,
            'nhs_review_status': self.nhs_review_status,
            'source_references': self.source_references
        }

class ProfessionalPrompt(Base):
    __tablename__ = 'professional_prompts'
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Prompt content
    title = Column(String(500), nullable=False)
    prompt_text = Column(Text, nullable=False)
    prompt_category = Column(String(100), nullable=False)  # diagnosis, treatment, assessment, etc.
    
    # Context and usage
    clinical_context = Column(Text, nullable=True)
    specialty = Column(String(100), nullable=True)  # cardiology, neurology, etc.
    difficulty_level = Column(String(50), default='intermediate')  # basic, intermediate, advanced
    
    # Quality metrics
    evidence_level = Column(String(50), nullable=True)  # high, moderate, low
    clinical_indicators = Column(JSON, nullable=True)  # When to use this prompt
    
    # Professional info
    created_by_professional = Column(String(255), nullable=False)
    professional_title = Column(String(100), nullable=True)  # Dr., Consultant, etc.
    specialty_expertise = Column(String(100), nullable=True)
    years_experience = Column(Integer, nullable=True)
    
    # Quality assurance
    professional_review_status = Column(String(50), default='pending')
    nhs_quality_check = Column(Boolean, default=False)
    peer_review_score = Column(Float, nullable=True)  # 1-5 rating
    usage_count = Column(Integer, default=0)
    
    # Learning integration
    training_data_quality = Column(String(50), default='pending')  # excellent, good, fair, poor
    model_performance_impact = Column(Float, nullable=True)  # How much this improves model
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used = Column(DateTime, nullable=True)
    tags = Column(JSON, nullable=True)  # Searchable tags
    version = Column(Integer, default=1)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            'id': self.id
            , 'title': self.title,
            'prompt_text': self.prompt_text,
            'prompt_category': self.prompt_category,
            'clinical_context': self.clinical_context,
            'specialty': self.specialty,
            'difficulty_level': self.difficulty_level,
            'evidence_level': self.evidence_level,
            'clinical_indicators': self.clinical_indicators,
            'created_by_professional': self.created_by_professional,
            'professional_title': self.professional_title,
            'specialty_expertise': self.specialty_expertise,
            'years_experience': self.years_experience, 'professional_review_status': self.professional_review_status,
            'nhs_quality_check': self.nhs_quality_check,
            'peer_review_score': self.peer_review_score,
            'usage_count': self.usage_count,
            'training_data_quality': self.training_data_quality,
            'model_performance_impact': self.model_performance_impact,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_used': self.last_used.isoformat() if self.last_used else None,
            'tags': self.tags,
            'version': self.version
        }

class QualityAnalysis(Base):
    __tablename__ = 'quality_analysis'
    
    id = Column(Integer, primary_key=True, index=True)
    
    # What's being analyzed
    analysis_type = Column(String(100), nullable=False)  # condition, prompt, model_performance
    resource_id = Column(Integer, nullable=False)  # ID of the condition or prompt
    
    # Analysis metrics
    clinical_accuracy_score = Column(Float, nullable=True)  # 0-100
    evidence_strength = Column(String(50), nullable=True)  # weak, moderate, strong
    comprehensiveness_score = Column(Float, nullable=True)  # Completeness of information
    
    # Professional review
    reviewed_by_nhs_professional = Column(String(255), nullable=True)
    review_notes = Column(Text, nullable=True)
    approval_status = Column(String(50), default='pending')  # approved, rejected, needs_revision
    
    # Quality flags
    red_flags = Column(JSON, nullable=True)  # Critical issues to address
    improvement_suggestions = Column(JSON, nullable=True)
    
    # Timestamps
    analyzed_at = Column(DateTime, default=datetime.utcnow)
    last_review = Column(DateTime, nullable=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'analysis_type': self.analysis_type,
            'resource_id': self.resource_id,
            'clinical_accuracy_score': self.clinical_accuracy_score,
            'evidence_strength': self.evidence_strength,
            'comprehensiveness_score': self.comprehensiveness_score,
            'reviewed_by_nhs_professional': self.reviewed_by_nhs_professional,
            'review_notes': self.review_notes,
            'approval_status': self.approval_status,
            'red_flags': self.red_flags,
            'improvement_suggestions': self.improvement_suggestions,
            'analyzed_at': self.analyzed_at.isoformat() if self.analyzed_at else None,
            'last_review': self.last_review.isoformat() if self.last_review else None
        }
