"""Enhanced Langfuse observability with medical compliance tracking for DigiClinic Phase 2."""

import json
import logging
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime, timezone
import uuid
import asyncio
from functools import wraps

try:
    from langfuse import Langfuse
    from langfuse.decorators import observe
    from langfuse.client import StatefulGenerationClient
    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False
    # Mock classes for when Langfuse is not available
    class Langfuse:
        def __init__(self, *args, **kwargs): pass
        def trace(self, *args, **kwargs): return MockTrace()
        def generation(self, *args, **kwargs): return MockGeneration()
        def score(self, *args, **kwargs): pass
        def flush(self): pass
    
    class MockTrace:
        def __init__(self): self.id = str(uuid.uuid4())
        def generation(self, *args, **kwargs): return MockGeneration()
        def span(self, *args, **kwargs): return MockSpan()
        def score(self, *args, **kwargs): pass
        def update(self, *args, **kwargs): pass
        def end(self, *args, **kwargs): pass
    
    class MockGeneration:
        def __init__(self): self.id = str(uuid.uuid4())
        def end(self, *args, **kwargs): pass
        def score(self, *args, **kwargs): pass
    
    class MockSpan:
        def __init__(self): self.id = str(uuid.uuid4())
        def end(self, *args, **kwargs): pass
        def update(self, *args, **kwargs): pass
    
    def observe(*args, **kwargs):
        def decorator(func):
            return func
        return decorator


logger = logging.getLogger(__name__)


class ComplianceLevel(Enum):
    """Medical compliance levels."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    CRITICAL = "critical"


class EventType(Enum):
    """Types of medical events to track."""
    PATIENT_CONSULTATION = "patient_consultation"
    CLINICAL_DECISION = "clinical_decision"
    DIAGNOSIS_SUGGESTION = "diagnosis_suggestion"
    MEDICATION_ADVICE = "medication_advice"
    RISK_ASSESSMENT = "risk_assessment"
    IMAGE_ANALYSIS = "image_analysis"
    SYMPTOM_TRIAGE = "symptom_triage"
    TERMINOLOGY_LOOKUP = "terminology_lookup"
    CLINICAL_CODING = "clinical_coding"
    DATA_ACCESS = "data_access"
    USER_INTERACTION = "user_interaction"
    SYSTEM_ERROR = "system_error"


@dataclass
class ComplianceMetrics:
    """Medical compliance metrics."""
    gdpr_compliant: bool = True
    nhs_standards_met: bool = True
    clinical_governance_score: float = 1.0
    data_security_level: str = "high"
    audit_trail_complete: bool = True
    patient_consent_recorded: bool = False
    anonymization_applied: bool = False
    retention_policy_followed: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    def calculate_overall_score(self) -> float:
        """Calculate overall compliance score."""
        scores = [
            1.0 if self.gdpr_compliant else 0.0,
            1.0 if self.nhs_standards_met else 0.0,
            self.clinical_governance_score,
            1.0 if self.data_security_level == "high" else 0.5,
            1.0 if self.audit_trail_complete else 0.0,
            1.0 if self.patient_consent_recorded else 0.8,
            1.0 if self.anonymization_applied else 0.9,
            1.0 if self.retention_policy_followed else 0.0
        ]
        return sum(scores) / len(scores)


@dataclass
class MedicalEvent:
    """Medical event for compliance tracking."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType = EventType.USER_INTERACTION
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    user_id: Optional[str] = None
    patient_id: Optional[str] = None
    session_id: Optional[str] = None
    trace_id: Optional[str] = None
    
    # Medical context
    clinical_context: Dict[str, Any] = field(default_factory=dict)
    snomed_codes: List[str] = field(default_factory=list)
    icd_codes: List[str] = field(default_factory=list)
    medication_codes: List[str] = field(default_factory=list)
    
    # Compliance data
    compliance_metrics: ComplianceMetrics = field(default_factory=ComplianceMetrics)
    risk_level: str = "low"
    sensitivity_level: str = "standard"
    
    # System data
    system_metadata: Dict[str, Any] = field(default_factory=dict)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with proper serialization."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        data["event_type"] = self.event_type.value
        return data


class MedicalObservabilityClient:
    """Enhanced observability client for medical applications."""
    
    def __init__(
        self,
        langfuse_public_key: Optional[str] = None,
        langfuse_secret_key: Optional[str] = None,
        langfuse_host: Optional[str] = None,
        environment: str = "development",
        application_name: str = "DigiClinic"
    ):
        """
        Initialize medical observability client.
        
        Args:
            langfuse_public_key: Langfuse public key
            langfuse_secret_key: Langfuse secret key
            langfuse_host: Langfuse host URL
            environment: Deployment environment
            application_name: Application name for tracing
        """
        self.environment = environment
        self.application_name = application_name
        self.enabled = bool(langfuse_public_key and langfuse_secret_key)
        
        if self.enabled and LANGFUSE_AVAILABLE:
            try:
                self.langfuse = Langfuse(
                    public_key=langfuse_public_key,
                    secret_key=langfuse_secret_key,
                    host=langfuse_host
                )
                logger.info("Langfuse observability enabled")
            except Exception as e:
                logger.warning(f"Failed to initialize Langfuse: {e}")
                self.enabled = False
                self.langfuse = None
        else:
            self.langfuse = None
            if not LANGFUSE_AVAILABLE:
                logger.warning("Langfuse not available - observability disabled")
        
        # Event storage for compliance reporting (in production, use proper storage)
        self.events_store: List[MedicalEvent] = []
        self.max_stored_events = 10000  # Limit memory usage
    
    def create_medical_trace(
        self,
        name: str,
        event_type: EventType,
        user_id: Optional[str] = None,
        patient_id: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Dict[str, Any] = None
    ) -> Any:
        """
        Create a medical trace with compliance tracking.
        
        Args:
            name: Trace name
            event_type: Type of medical event
            user_id: User identifier
            patient_id: Patient identifier (will be anonymized)
            session_id: Session identifier
            metadata: Additional metadata
            
        Returns:
            Trace object (or mock if disabled)
        """
        if not self.enabled or not self.langfuse:
            return MockTrace()
        
        # Anonymize patient ID for observability
        anonymized_patient_id = self._anonymize_patient_id(patient_id) if patient_id else None
        
        # Create compliance metrics
        compliance_metrics = self._assess_compliance(event_type, metadata)
        
        # Enhanced metadata with medical context
        enhanced_metadata = {
            "environment": self.environment,
            "application": self.application_name,
            "event_type": event_type.value,
            "user_id": user_id,
            "patient_id_hash": anonymized_patient_id,
            "session_id": session_id,
            "compliance_score": compliance_metrics.calculate_overall_score(),
            "risk_level": self._assess_risk_level(event_type, metadata),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **(metadata or {})
        }
        
        try:
            trace = self.langfuse.trace(
                name=name,
                metadata=enhanced_metadata,
                tags=[
                    self.environment,
                    event_type.value,
                    f"risk_{self._assess_risk_level(event_type, metadata)}",
                    f"compliance_{compliance_metrics.calculate_overall_score():.1f}"
                ]
            )
            
            # Create medical event for compliance tracking
            medical_event = MedicalEvent(
                event_type=event_type,
                user_id=user_id,
                patient_id=anonymized_patient_id,
                session_id=session_id,
                trace_id=trace.id,
                clinical_context=metadata or {},
                compliance_metrics=compliance_metrics,
                risk_level=self._assess_risk_level(event_type, metadata),
                system_metadata=enhanced_metadata
            )
            
            # Store event for compliance reporting
            self._store_event(medical_event)
            
            return trace
            
        except Exception as e:
            logger.error(f"Failed to create medical trace: {e}")
            return MockTrace()
    
    def create_medical_generation(
        self,
        trace: Any,
        name: str,
        model: str,
        input_data: Any,
        agent_type: str = "clinical_ai",
        clinical_context: Dict[str, Any] = None
    ) -> Any:
        """
        Create a medical generation with clinical context.
        
        Args:
            trace: Parent trace object
            name: Generation name
            model: Model identifier
            input_data: Input data (will be sanitized)
            agent_type: Type of AI agent
            clinical_context: Clinical context information
            
        Returns:
            Generation object (or mock if disabled)
        """
        if not self.enabled or not hasattr(trace, 'generation'):
            return MockGeneration()
        
        # Sanitize input data for observability
        sanitized_input = self._sanitize_medical_data(input_data)
        
        # Enhanced metadata
        metadata = {
            "agent_type": agent_type,
            "model_type": "medical_llm",
            "clinical_context": clinical_context or {},
            "input_tokens_estimate": len(str(sanitized_input)) // 4,  # Rough estimate
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        try:
            generation = trace.generation(
                name=name,
                model=model,
                input=sanitized_input,
                metadata=metadata,
                tags=[agent_type, "medical_ai", self.environment]
            )
            
            return generation
            
        except Exception as e:
            logger.error(f"Failed to create medical generation: {e}")
            return MockGeneration()
    
    def score_medical_response(
        self,
        trace_or_generation: Any,
        clinical_accuracy: float,
        safety_score: float,
        compliance_score: float,
        user_feedback: Optional[str] = None,
        clinical_notes: Optional[str] = None
    ):
        """
        Score medical AI response across multiple dimensions.
        
        Args:
            trace_or_generation: Trace or generation to score
            clinical_accuracy: Clinical accuracy score (0-1)
            safety_score: Safety assessment score (0-1)
            compliance_score: Compliance score (0-1)
            user_feedback: Optional user feedback
            clinical_notes: Optional clinical notes
        """
        if not self.enabled or not hasattr(trace_or_generation, 'score'):
            return
        
        try:
            # Overall medical quality score
            overall_score = (clinical_accuracy + safety_score + compliance_score) / 3
            
            # Score the response
            trace_or_generation.score(
                name="medical_quality",
                value=overall_score,
                comment=f"Clinical: {clinical_accuracy}, Safety: {safety_score}, Compliance: {compliance_score}"
            )
            
            # Individual dimension scores
            trace_or_generation.score(name="clinical_accuracy", value=clinical_accuracy)
            trace_or_generation.score(name="safety_score", value=safety_score)
            trace_or_generation.score(name="compliance_score", value=compliance_score)
            
            # User feedback if provided
            if user_feedback:
                trace_or_generation.score(
                    name="user_feedback",
                    value=1.0 if "good" in user_feedback.lower() else 0.5,
                    comment=user_feedback
                )
            
            # Clinical notes if provided
            if clinical_notes:
                trace_or_generation.score(
                    name="clinical_notes",
                    value=1.0,
                    comment=clinical_notes
                )
                
        except Exception as e:
            logger.error(f"Failed to score medical response: {e}")
    
    def _anonymize_patient_id(self, patient_id: str) -> str:
        """Anonymize patient ID for observability."""
        import hashlib
        return hashlib.sha256(patient_id.encode()).hexdigest()[:16]
    
    def _assess_compliance(self, event_type: EventType, metadata: Dict[str, Any] = None) -> ComplianceMetrics:
        """Assess compliance metrics for the event."""
        metadata = metadata or {}
        
        compliance = ComplianceMetrics()
        
        # Assess based on event type
        if event_type in [EventType.PATIENT_CONSULTATION, EventType.CLINICAL_DECISION]:
            compliance.clinical_governance_score = 1.0
            compliance.patient_consent_recorded = metadata.get("consent_recorded", False)
        
        if event_type == EventType.DATA_ACCESS:
            compliance.data_security_level = metadata.get("security_level", "high")
        
        if "patient_id" in metadata:
            compliance.anonymization_applied = True
        
        return compliance
    
    def _assess_risk_level(self, event_type: EventType, metadata: Dict[str, Any] = None) -> str:
        """Assess risk level for the event."""
        metadata = metadata or {}
        
        # High-risk events
        if event_type in [EventType.CLINICAL_DECISION, EventType.DIAGNOSIS_SUGGESTION, EventType.MEDICATION_ADVICE]:
            return "high"
        
        # Medium-risk events
        if event_type in [EventType.RISK_ASSESSMENT, EventType.SYMPTOM_TRIAGE]:
            return "medium"
        
        # Check for risk indicators in metadata
        if metadata.get("emergency_indicators") or metadata.get("red_flags"):
            return "high"
        
        return "low"
    
    def _sanitize_medical_data(self, data: Any) -> Any:
        """Sanitize medical data for observability."""
        if isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                # Remove or hash sensitive fields
                if key.lower() in ['patient_id', 'national_insurance', 'nhs_number']:
                    sanitized[key] = "[REDACTED]"
                elif key.lower() in ['name', 'address', 'phone', 'email']:
                    sanitized[key] = "[PII_REMOVED]"
                else:
                    sanitized[key] = self._sanitize_medical_data(value)
            return sanitized
        
        elif isinstance(data, list):
            return [self._sanitize_medical_data(item) for item in data]
        
        elif isinstance(data, str) and len(data) > 1000:
            # Truncate very long strings
            return data[:1000] + "..."
        
        return data
    
    def _store_event(self, event: MedicalEvent):
        """Store medical event for compliance reporting."""
        self.events_store.append(event)
        
        # Limit storage to prevent memory issues
        if len(self.events_store) > self.max_stored_events:
            self.events_store = self.events_store[-self.max_stored_events//2:]
    
    def get_compliance_report(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        event_types: List[EventType] = None
    ) -> Dict[str, Any]:
        """
        Generate compliance report for medical events.
        
        Args:
            start_date: Start date for report
            end_date: End date for report
            event_types: Filter by event types
            
        Returns:
            Compliance report dictionary
        """
        # Filter events
        filtered_events = self.events_store
        
        if start_date:
            filtered_events = [e for e in filtered_events if e.timestamp >= start_date]
        
        if end_date:
            filtered_events = [e for e in filtered_events if e.timestamp <= end_date]
        
        if event_types:
            filtered_events = [e for e in filtered_events if e.event_type in event_types]
        
        # Calculate statistics
        total_events = len(filtered_events)
        
        if total_events == 0:
            return {
                "total_events": 0,
                "compliance_summary": {},
                "risk_distribution": {},
                "recommendations": []
            }
        
        # Compliance statistics
        compliance_scores = [e.compliance_metrics.calculate_overall_score() for e in filtered_events]
        avg_compliance = sum(compliance_scores) / len(compliance_scores)
        
        # Risk distribution
        risk_counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        for event in filtered_events:
            risk_counts[event.risk_level] = risk_counts.get(event.risk_level, 0) + 1
        
        # Event type distribution
        event_type_counts = {}
        for event in filtered_events:
            event_type = event.event_type.value
            event_type_counts[event_type] = event_type_counts.get(event_type, 0) + 1
        
        # Compliance issues
        compliance_issues = []
        for event in filtered_events:
            if not event.compliance_metrics.gdpr_compliant:
                compliance_issues.append("GDPR compliance failures detected")
            if not event.compliance_metrics.nhs_standards_met:
                compliance_issues.append("NHS standards not met")
            if not event.compliance_metrics.audit_trail_complete:
                compliance_issues.append("Incomplete audit trails")
        
        # Generate recommendations
        recommendations = []
        if avg_compliance < 0.8:
            recommendations.append("Review and improve compliance procedures")
        if risk_counts["high"] + risk_counts["critical"] > total_events * 0.1:
            recommendations.append("High-risk events above threshold - review safety protocols")
        if compliance_issues:
            recommendations.append("Address identified compliance issues")
        
        return {
            "report_period": {
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None
            },
            "total_events": total_events,
            "compliance_summary": {
                "average_compliance_score": avg_compliance,
                "gdpr_compliant_events": sum(1 for e in filtered_events if e.compliance_metrics.gdpr_compliant),
                "nhs_standards_met": sum(1 for e in filtered_events if e.compliance_metrics.nhs_standards_met),
                "complete_audit_trails": sum(1 for e in filtered_events if e.compliance_metrics.audit_trail_complete)
            },
            "risk_distribution": risk_counts,
            "event_type_distribution": event_type_counts,
            "compliance_issues": list(set(compliance_issues)),  # Remove duplicates
            "recommendations": recommendations,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
    
    def flush(self):
        """Flush pending observability data."""
        if self.enabled and self.langfuse:
            try:
                self.langfuse.flush()
            except Exception as e:
                logger.error(f"Failed to flush observability data: {e}")


# Global instance for easy access
medical_observability: Optional[MedicalObservabilityClient] = None


def init_medical_observability(
    langfuse_public_key: Optional[str] = None,
    langfuse_secret_key: Optional[str] = None,
    langfuse_host: Optional[str] = None,
    environment: str = "development"
):
    """Initialize global medical observability client."""
    global medical_observability
    medical_observability = MedicalObservabilityClient(
        langfuse_public_key=langfuse_public_key,
        langfuse_secret_key=langfuse_secret_key,
        langfuse_host=langfuse_host,
        environment=environment
    )


def medical_observe(
    event_type: EventType,
    name: Optional[str] = None,
    include_io: bool = True
):
    """
    Decorator for observing medical functions with compliance tracking.
    
    Args:
        event_type: Type of medical event
        name: Optional custom name for the trace
        include_io: Whether to include input/output in observability
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            if not medical_observability or not medical_observability.enabled:
                return await func(*args, **kwargs)
            
            trace_name = name or f"{func.__name__}_{event_type.value}"
            
            # Extract context from kwargs
            user_id = kwargs.get('user_id')
            patient_id = kwargs.get('patient_id')
            session_id = kwargs.get('session_id')
            
            # Create trace
            trace = medical_observability.create_medical_trace(
                name=trace_name,
                event_type=event_type,
                user_id=user_id,
                patient_id=patient_id,
                session_id=session_id,
                metadata={"function": func.__name__}
            )
            
            try:
                # Execute function
                result = await func(*args, **kwargs)
                
                # Update trace with success
                if hasattr(trace, 'update'):
                    trace.update(output=result if include_io else {"status": "success"})
                
                return result
                
            except Exception as e:
                # Update trace with error
                if hasattr(trace, 'update'):
                    trace.update(
                        output={"error": str(e), "status": "error"},
                        level="ERROR"
                    )
                raise
            
            finally:
                if hasattr(trace, 'end'):
                    trace.end()
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            if not medical_observability or not medical_observability.enabled:
                return func(*args, **kwargs)
            
            # Similar logic for sync functions
            trace_name = name or f"{func.__name__}_{event_type.value}"
            
            # Extract context from kwargs
            user_id = kwargs.get('user_id')
            patient_id = kwargs.get('patient_id')
            session_id = kwargs.get('session_id')
            
            # Create trace
            trace = medical_observability.create_medical_trace(
                name=trace_name,
                event_type=event_type,
                user_id=user_id,
                patient_id=patient_id,
                session_id=session_id,
                metadata={"function": func.__name__}
            )
            
            try:
                result = func(*args, **kwargs)
                
                if hasattr(trace, 'update'):
                    trace.update(output=result if include_io else {"status": "success"})
                
                return result
                
            except Exception as e:
                if hasattr(trace, 'update'):
                    trace.update(
                        output={"error": str(e), "status": "error"},
                        level="ERROR"
                    )
                raise
            
            finally:
                if hasattr(trace, 'end'):
                    trace.end()
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator