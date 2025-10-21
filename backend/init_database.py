"""
Database Initialization Script
Creates tables and initial admin/user data
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.auth_models import Base, Admin, User
from services.auth_database_service import AuthDatabaseService
from config.database import get_database_url
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_database():
    """Initialize database with tables and initial data"""
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
            
            # Create initial admin users
            logger.info("Creating initial admin users...")
            
            # Super Admin
            super_admin = auth_service.create_admin(
                username="admin",
                email="admin@digiclinic.com",
                password="admin123",
                full_name="Super Administrator",
                is_super_admin=True
            )
            
            if super_admin:
                logger.info("✅ Super Admin created: admin/admin123")
            else:
                logger.info("ℹ️ Super Admin already exists")
            
            # Regular Admin
            regular_admin = auth_service.create_admin(
                username="1234567891",
                email="admin123456@digiclinic.com", 
                password="Doctor123456@",
                full_name="Medical Administrator",
                is_super_admin=False
            )
            
            if regular_admin:
                logger.info("✅ Medical Admin created: 1234567891/Doctor123456@")
            else:
                logger.info("ℹ️ Medical Admin already exists")
            
            # Create sample regular users
            logger.info("Creating sample users...")
            
            # Sample User 1
            user1 = auth_service.create_user(
                username="patient001",
                email="patient001@example.com",
                password="patient123",
                full_name="John Smith",
                national_id="476176",
                phone_number="+1234567890",
                gender="Male"
            )
            
            if user1:
                logger.info("✅ Sample User 1 created: patient001/patient123")
            else:
                logger.info("ℹ️ Sample User 1 already exists")
            
            # Sample User 2
            user2 = auth_service.create_user(
                username="patient002",
                email="patient002@example.com",
                password="patient123",
                full_name="Jane Doe",
                national_id="789012",
                phone_number="+1234567891",
                gender="Female"
            )
            
            if user2:
                logger.info("✅ Sample User 2 created: patient002/patient123")
            else:
                logger.info("ℹ️ Sample User 2 already exists")
            
            # Create sample chat sessions
            if user1:
                logger.info("Creating sample chat sessions...")
                
                session1 = auth_service.create_chat_session(
                    user_id=user1.id,
                    session_id="session_476176_001"
                )
                
                if session1:
                    # Add sample messages
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
                    
                    logger.info("✅ Sample chat session created with messages")
            
            logger.info("🎉 Database initialization completed successfully!")
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise

if __name__ == "__main__":
    init_database()
