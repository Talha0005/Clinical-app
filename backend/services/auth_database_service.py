"""
Database Service for Role-Based Authentication
Handles Admin and User operations
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from models.auth_models import Admin, User, ChatSession, ChatMessage, AuditLog
from datetime import datetime
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class AuthDatabaseService:
    """Service for handling authentication database operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # Admin Operations
    def create_admin(self, username: str, email: str, password: str, full_name: str, is_super_admin: bool = False) -> Optional[Admin]:
        """Create a new admin user"""
        try:
            # Check if admin already exists
            existing_admin = self.db.query(Admin).filter(
                or_(Admin.username == username, Admin.email == email)
            ).first()
            
            if existing_admin:
                logger.warning(f"Admin with username {username} or email {email} already exists")
                return None
            
            admin = Admin(
                username=username,
                email=email,
                full_name=full_name,
                is_super_admin=is_super_admin
            )
            admin.set_password(password)
            
            self.db.add(admin)
            self.db.commit()
            self.db.refresh(admin)
            
            logger.info(f"Created admin user: {username}")
            return admin
            
        except Exception as e:
            logger.error(f"Error creating admin {username}: {e}")
            self.db.rollback()
            return None
    
    def get_admin_by_username(self, username: str) -> Optional[Admin]:
        """Get admin by username"""
        return self.db.query(Admin).filter(
            and_(Admin.username == username, Admin.is_active == True)
        ).first()
    
    def get_admin_by_email(self, email: str) -> Optional[Admin]:
        """Get admin by email"""
        return self.db.query(Admin).filter(
            and_(Admin.email == email, Admin.is_active == True)
        ).first()
    
    def verify_admin_password(self, username: str, password: str) -> Optional[Admin]:
        """Verify admin password and return admin if valid"""
        admin = self.get_admin_by_username(username)
        if admin and admin.verify_password(password):
            # Update last login
            admin.last_login = datetime.utcnow()
            self.db.commit()
            return admin
        return None
    
    def get_all_admins(self) -> List[Admin]:
        """Get all active admins"""
        return self.db.query(Admin).filter(Admin.is_active == True).all()
    
    # User Operations
    def create_user(self, username: str, email: str, password: str, full_name: str, 
                   national_id: str = None, phone_number: str = None, 
                   date_of_birth: datetime = None, gender: str = None) -> Optional[User]:
        """Create a new regular user"""
        try:
            # Check if user already exists
            existing_user = self.db.query(User).filter(
                or_(User.username == username, User.email == email)
            ).first()
            
            if existing_user:
                logger.warning(f"User with username {username} or email {email} already exists")
                return None
            
            # Check national_id uniqueness if provided
            if national_id:
                existing_national_id = self.db.query(User).filter(User.national_id == national_id).first()
                if existing_national_id:
                    logger.warning(f"User with national_id {national_id} already exists")
                    return None
            
            user = User(
                username=username,
                email=email,
                full_name=full_name,
                national_id=national_id,
                phone_number=phone_number,
                date_of_birth=date_of_birth,
                gender=gender
            )
            user.set_password(password)
            
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            
            logger.info(f"Created user: {username}")
            return user
            
        except Exception as e:
            logger.error(f"Error creating user {username}: {e}")
            self.db.rollback()
            return None
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        return self.db.query(User).filter(
            and_(User.username == username, User.is_active == True)
        ).first()
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        return self.db.query(User).filter(
            and_(User.email == email, User.is_active == True)
        ).first()
    
    def get_user_by_national_id(self, national_id: str) -> Optional[User]:
        """Get user by national ID"""
        return self.db.query(User).filter(
            and_(User.national_id == national_id, User.is_active == True)
        ).first()
    
    def verify_user_password(self, username: str, password: str) -> Optional[User]:
        """Verify user password and return user if valid"""
        user = self.get_user_by_username(username)
        if user and user.verify_password(password):
            # Update last login
            user.last_login = datetime.utcnow()
            self.db.commit()
            return user
        return None
    
    def get_all_users(self) -> List[User]:
        """Get all active users"""
        return self.db.query(User).filter(User.is_active == True).all()
    
    # Chat Session Operations
    def create_chat_session(self, user_id: int, session_id: str) -> Optional[ChatSession]:
        """Create a new chat session"""
        try:
            session = ChatSession(
                session_id=session_id,
                user_id=user_id
            )
            
            self.db.add(session)
            self.db.commit()
            self.db.refresh(session)
            
            logger.info(f"Created chat session {session_id} for user {user_id}")
            return session
            
        except Exception as e:
            logger.error(f"Error creating chat session {session_id}: {e}")
            self.db.rollback()
            return None
    
    def get_chat_session(self, session_id: str) -> Optional[ChatSession]:
        """Get chat session by session ID"""
        return self.db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
    
    def get_user_chat_sessions(self, user_id: int) -> List[ChatSession]:
        """Get all chat sessions for a user"""
        return self.db.query(ChatSession).filter(ChatSession.user_id == user_id).all()
    
    def add_chat_message(self, session_id: str, message_type: str, content: str, message_metadata: str = None) -> Optional[ChatMessage]:
        """Add a message to a chat session"""
        try:
            session = self.get_chat_session(session_id)
            if not session:
                logger.error(f"Chat session {session_id} not found")
                return None
            
            message = ChatMessage(
                session_id=session.id,
                message_type=message_type,
                content=content,
                message_metadata=message_metadata
            )
            
            self.db.add(message)
            
            # Update session message count
            session.total_messages += 1
            
            self.db.commit()
            self.db.refresh(message)
            
            return message
            
        except Exception as e:
            logger.error(f"Error adding message to session {session_id}: {e}")
            self.db.rollback()
            return None
    
    def get_chat_messages(self, session_id: str) -> List[ChatMessage]:
        """Get all messages for a chat session"""
        session = self.get_chat_session(session_id)
        if not session:
            return []
        
        return self.db.query(ChatMessage).filter(ChatMessage.session_id == session.id).all()
    
    # Audit Log Operations
    def log_activity(self, user_id: int = None, admin_id: int = None, action: str = "", 
                     resource: str = "", details: str = None, ip_address: str = None, 
                     user_agent: str = None) -> Optional[AuditLog]:
        """Log user or admin activity"""
        try:
            audit_log = AuditLog(
                user_id=user_id,
                admin_id=admin_id,
                action=action,
                resource=resource,
                details=details,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            self.db.add(audit_log)
            self.db.commit()
            self.db.refresh(audit_log)
            
            return audit_log
            
        except Exception as e:
            logger.error(f"Error logging activity: {e}")
            self.db.rollback()
            return None
    
    def get_audit_logs(self, user_id: int = None, admin_id: int = None, limit: int = 100) -> List[AuditLog]:
        """Get audit logs"""
        query = self.db.query(AuditLog)
        
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        if admin_id:
            query = query.filter(AuditLog.admin_id == admin_id)
        
        return query.order_by(AuditLog.timestamp.desc()).limit(limit).all()
