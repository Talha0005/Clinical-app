"""
Complete Authentication System Setup with Dummy Data
Creates all tables and populates with test data
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.auth_models import Base, Admin, User, ChatSession, ChatMessage, AuditLog
from services.auth_database_service import AuthDatabaseService
from config.database import get_database_url
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_complete_auth_system():
    """Setup complete authentication system with dummy data"""
    try:
        # Create engine
        database_url = get_database_url()
        engine = create_engine(database_url)
        
        # Create all tables
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully!")
        
        # Create session
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        try:
            auth_service = AuthDatabaseService(db)
            
            # Create Admin Users
            logger.info("Creating Admin Users...")
            
            # Super Admin
            super_admin = auth_service.create_admin(
                username="admin",
                email="admin@digiclinic.com",
                password="admin123",
                full_name="Super Administrator",
                is_super_admin=True
            )
            logger.info("✅ Super Admin: admin/admin123")
            
            # Medical Admin
            medical_admin = auth_service.create_admin(
                username="1234567891",
                email="admin123456@digiclinic.com", 
                password="Doctor123456@",
                full_name="Dr. Medical Administrator",
                is_super_admin=False
            )
            logger.info("✅ Medical Admin: 1234567891/Doctor123456@")
            
            # Doctor Admin
            doctor_admin = auth_service.create_admin(
                username="doctor",
                email="doctor@digiclinic.com",
                password="doctor123",
                full_name="Dr. John Smith",
                is_super_admin=False
            )
            logger.info("✅ Doctor Admin: doctor/doctor123")
            
            # Create Regular Users
            logger.info("Creating Regular Users...")
            
            # Patient 1
            patient1 = auth_service.create_user(
                username="patient001",
                email="patient001@example.com",
                password="patient123",
                full_name="John Smith",
                national_id="476176",
                phone_number="+1234567890",
                date_of_birth=datetime(1985, 5, 15),
                gender="Male"
            )
            logger.info("✅ Patient 1: patient001/patient123 (National ID: 476176)")
            
            # Patient 2
            patient2 = auth_service.create_user(
                username="patient002",
                email="patient002@example.com",
                password="patient123",
                full_name="Jane Doe",
                national_id="789012",
                phone_number="+1234567891",
                date_of_birth=datetime(1990, 8, 22),
                gender="Female"
            )
            logger.info("✅ Patient 2: patient002/patient123 (National ID: 789012)")
            
            # Patient 3
            patient3 = auth_service.create_user(
                username="patient003",
                email="patient003@example.com",
                password="patient123",
                full_name="Ahmed Khan",
                national_id="345678",
                phone_number="+1234567892",
                date_of_birth=datetime(1988, 12, 10),
                gender="Male"
            )
            logger.info("✅ Patient 3: patient003/patient123 (National ID: 345678)")
            
            # Create Chat Sessions and Messages
            logger.info("Creating Chat Sessions and Messages...")
            
            if patient1:
                # Session 1 for Patient 1
                session1 = auth_service.create_chat_session(
                    user_id=patient1.id,
                    session_id="session_476176_001"
                )
                
                if session1:
                    # Add messages to session 1
                    auth_service.add_chat_message(
                        session_id="session_476176_001",
                        message_type="user",
                        content="I have been experiencing chest pain for the past few days"
                    )
                    
                    auth_service.add_chat_message(
                        session_id="session_476176_001",
                        message_type="ai",
                        content="I understand you're experiencing chest pain. This could be due to various causes ranging from minor issues to serious conditions. It's important to note that chest pain should always be taken seriously, especially if it's new, severe, or accompanied by other symptoms like shortness of breath, sweating, or nausea."
                    )
                    
                    auth_service.add_chat_message(
                        session_id="session_476176_001",
                        message_type="user",
                        content="The pain is sharp and comes and goes"
                    )
                    
                    auth_service.add_chat_message(
                        session_id="session_476176_001",
                        message_type="ai",
                        content="Sharp, intermittent chest pain can have several causes. It's important to monitor the pattern and any associated symptoms. If the pain becomes severe or persistent, please seek immediate medical attention."
                    )
                    
                    logger.info("✅ Chat Session 1 created with 4 messages")
                
                # Session 2 for Patient 1
                session2 = auth_service.create_chat_session(
                    user_id=patient1.id,
                    session_id="session_476176_002"
                )
                
                if session2:
                    auth_service.add_chat_message(
                        session_id="session_476176_002",
                        message_type="user",
                        content="I also have some stomach pain"
                    )
                    
                    auth_service.add_chat_message(
                        session_id="session_476176_002",
                        message_type="ai",
                        content="Stomach pain can be related to various digestive issues. Can you describe the location and nature of the pain? Is it sharp, dull, or cramping?"
                    )
                    
                    logger.info("✅ Chat Session 2 created with 2 messages")
            
            if patient2:
                # Session for Patient 2
                session3 = auth_service.create_chat_session(
                    user_id=patient2.id,
                    session_id="session_789012_001"
                )
                
                if session3:
                    auth_service.add_chat_message(
                        session_id="session_789012_001",
                        message_type="user",
                        content="I have a headache that won't go away"
                    )
                    
                    auth_service.add_chat_message(
                        session_id="session_789012_001",
                        message_type="ai",
                        content="Persistent headaches can have various causes. How long have you been experiencing this headache? Are there any other symptoms accompanying it?"
                    )
                    
                    logger.info("✅ Chat Session 3 created with 2 messages")
            
            # Create Audit Logs
            logger.info("Creating Audit Logs...")
            
            if super_admin:
                auth_service.log_activity(
                    admin_id=super_admin.id,
                    action="SYSTEM_INITIALIZATION",
                    resource="DATABASE",
                    details="System initialized with dummy data",
                    ip_address="127.0.0.1"
                )
                
                auth_service.log_activity(
                    admin_id=super_admin.id,
                    action="USER_CREATION",
                    resource="ADMIN",
                    details="Created medical admin user",
                    ip_address="127.0.0.1"
                )
            
            if patient1:
                auth_service.log_activity(
                    user_id=patient1.id,
                    action="USER_REGISTRATION",
                    resource="USER",
                    details="User registered successfully",
                    ip_address="127.0.0.1"
                )
                
                auth_service.log_activity(
                    user_id=patient1.id,
                    action="CHAT_SESSION_START",
                    resource="CHAT",
                    details="Started chat session for chest pain consultation",
                    ip_address="127.0.0.1"
                )
            
            logger.info("✅ Audit logs created")
            
            # Test Authentication
            logger.info("Testing Authentication System...")
            
            # Test Admin Login
            admin_test = auth_service.verify_admin_password("admin", "admin123")
            if admin_test:
                logger.info("✅ Admin authentication test PASSED")
            else:
                logger.error("❌ Admin authentication test FAILED")
            
            # Test User Login
            user_test = auth_service.verify_user_password("patient001", "patient123")
            if user_test:
                logger.info("✅ User authentication test PASSED")
            else:
                logger.error("❌ User authentication test FAILED")
            
            # Test Wrong Password
            wrong_test = auth_service.verify_user_password("patient001", "wrongpassword")
            if not wrong_test:
                logger.info("✅ Wrong password test PASSED (correctly rejected)")
            else:
                logger.error("❌ Wrong password test FAILED (should have been rejected)")
            
            # Test Data Retrieval
            logger.info("Testing Data Retrieval...")
            
            # Get all admins
            admins = auth_service.get_all_admins()
            logger.info(f"✅ Retrieved {len(admins)} admin users")
            
            # Get all users
            users = auth_service.get_all_users()
            logger.info(f"✅ Retrieved {len(users)} regular users")
            
            # Get user by national ID
            user_by_id = auth_service.get_user_by_national_id("476176")
            if user_by_id:
                logger.info(f"✅ Retrieved user by National ID: {user_by_id.full_name}")
            else:
                logger.error("❌ Failed to retrieve user by National ID")
            
            # Get chat sessions for user
            if patient1:
                sessions = auth_service.get_user_chat_sessions(patient1.id)
                logger.info(f"✅ Retrieved {len(sessions)} chat sessions for user")
                
                # Get messages for first session
                if sessions:
                    messages = auth_service.get_chat_messages(sessions[0].session_id)
                    logger.info(f"✅ Retrieved {len(messages)} messages for first session")
            
            # Get audit logs
            audit_logs = auth_service.get_audit_logs(limit=10)
            logger.info(f"✅ Retrieved {len(audit_logs)} audit log entries")
            
            logger.info("🎉 Complete Authentication System Setup Successful!")
            logger.info("=" * 60)
            logger.info("TEST CREDENTIALS:")
            logger.info("=" * 60)
            logger.info("ADMIN USERS:")
            logger.info("  Super Admin: admin / admin123")
            logger.info("  Medical Admin: 1234567891 / Doctor123456@")
            logger.info("  Doctor Admin: doctor / doctor123")
            logger.info("")
            logger.info("REGULAR USERS:")
            logger.info("  Patient 1: patient001 / patient123 (National ID: 476176)")
            logger.info("  Patient 2: patient002 / patient123 (National ID: 789012)")
            logger.info("  Patient 3: patient003 / patient123 (National ID: 345678)")
            logger.info("=" * 60)
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"❌ Authentication system setup failed: {e}")
        raise

if __name__ == "__main__":
    setup_complete_auth_system()

