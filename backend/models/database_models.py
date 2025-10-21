"""
SQLAlchemy database models for DigiClinic.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from config.database import Base

class User(Base):
    """User model with enhanced security features."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    national_id = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    email = Column(String(255), index=True)
    phone = Column(String(20), index=True)
    role = Column(String(20), nullable=False, default="User")
    
    # Verification status
    email_verified = Column(Boolean, default=False)
    phone_verified = Column(Boolean, default=False)
    national_id_verified = Column(Boolean, default=False)
    
    # Security features
    two_factor_enabled = Column(Boolean, default=False)
    two_factor_secret = Column(String(32))
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime)
    
    # Audit fields
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    last_login = Column(DateTime)
    verified_at = Column(DateTime)
    
    # Relationships
    sessions = relationship("UserSession", back_populates="user")
    verification_codes = relationship("VerificationCode", back_populates="user")
    chat_histories = relationship("ChatHistory", back_populates="user")
    
    def __repr__(self):
        return f"<User(username='{self.username}', national_id='{self.national_id}')>"

class UserSession(Base):
    """User session model for tracking active sessions."""
    __tablename__ = "user_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_token = Column(String(255), unique=True, index=True, nullable=False)
    national_insurance = Column(String(50), nullable=False)
    patient_name = Column(String(255))
    
    # Session metadata
    created_at = Column(DateTime, default=func.now())
    last_accessed = Column(DateTime, default=func.now())
    expires_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)
    
    # Session data
    conversation_ids = Column(Text)  # JSON array
    session_metadata = Column(Text)  # JSON object
    ip_address = Column(String(45))
    user_agent = Column(Text)
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    
    def __repr__(self):
        return f"<UserSession(user_id={self.user_id}, token='{self.session_token[:10]}...')>"

class VerificationCode(Base):
    """Verification code model for email/phone verification."""
    __tablename__ = "verification_codes"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    national_id = Column(String(50), nullable=False)
    method = Column(String(10), nullable=False)  # 'email' or 'phone'
    code_hash = Column(String(255), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="verification_codes")
    
    def __repr__(self):
        return f"<VerificationCode(national_id='{self.national_id}', method='{self.method}')>"

class Patient(Base):
    """Patient model for medical data."""
    __tablename__ = "patients"
    
    id = Column(Integer, primary_key=True, index=True)
    national_insurance = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    age = Column(Integer)
    
    # Medical data
    medical_history = Column(Text)  # JSON array
    current_medications = Column(Text)  # JSON array
    
    # Audit fields
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    conditions = relationship("PatientCondition", back_populates="patient")
    medications = relationship("PatientMedication", back_populates="patient")
    
    def __repr__(self):
        return f"<Patient(ni='{self.national_insurance}', name='{self.name}')>"

class PatientCondition(Base):
    """Patient condition model."""
    __tablename__ = "patient_conditions"
    
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    condition_text = Column(String(500), nullable=False)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    patient = relationship("Patient", back_populates="conditions")
    
    # Unique constraint
    __table_args__ = (UniqueConstraint('patient_id', 'condition_text', name='_patient_condition_uc'),)
    
    def __repr__(self):
        return f"<PatientCondition(patient_id={self.patient_id}, condition='{self.condition_text}')>"

class PatientMedication(Base):
    """Patient medication model."""
    __tablename__ = "patient_medications"
    
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    medication_text = Column(String(500), nullable=False)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    patient = relationship("Patient", back_populates="medications")
    
    # Unique constraint
    __table_args__ = (UniqueConstraint('patient_id', 'medication_text', name='_patient_medication_uc'),)
    
    def __repr__(self):
        return f"<PatientMedication(patient_id={self.patient_id}, medication='{self.medication_text}')>"

class AuditLog(Base):
    """Audit log model for security compliance."""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String(100), nullable=False)
    resource = Column(String(100))
    resource_id = Column(String(100))
    details = Column(Text)  # JSON object
    ip_address = Column(String(45))
    user_agent = Column(Text)
    timestamp = Column(DateTime, default=func.now())
    
    def __repr__(self):
        return f"<AuditLog(user_id={self.user_id}, action='{self.action}')>"

class ChatHistory(Base):
    """Chat history model for tracking user conversations."""
    __tablename__ = "chat_histories"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    conversation_id = Column(String(100), index=True, nullable=False)
    message_type = Column(String(20), nullable=False)  # 'user' or 'assistant'
    message_content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=func.now())
    
    # Additional metadata
    session_id = Column(String(100), index=True)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    
    # Relationships
    user = relationship("User", back_populates="chat_histories")
    
    def __repr__(self):
        return f"<ChatHistory(user_id={self.user_id}, conversation_id='{self.conversation_id}', type='{self.message_type}')>"
