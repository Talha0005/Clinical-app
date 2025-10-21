"""
Updated Authentication System with Database Support
Role-based authentication using separate Admin and User tables
"""

import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from sqlalchemy.orm import Session
from config.database import SessionLocal
from services.auth_database_service import AuthDatabaseService
from models.auth_models import Admin, User
import logging

logger = logging.getLogger(__name__)

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

security = HTTPBearer()

# Database dependency
def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_auth_service(db: Session = Depends(get_db)) -> AuthDatabaseService:
    """Get authentication database service"""
    return AuthDatabaseService(db)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Verify JWT token and return user info"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role", "user")
        user_id: int = payload.get("user_id")
        
        if username is None:
            raise credentials_exception
            
    except jwt.PyJWTError:
        raise credentials_exception

    return {
        "username": username,
        "role": role,
        "user_id": user_id
    }

def authenticate_user(username: str, password: str, auth_service: AuthDatabaseService) -> Optional[Dict[str, Any]]:
    """Authenticate user and return user info with role"""
    # Try admin first
    admin = auth_service.verify_admin_password(username, password)
    if admin:
        return {
            "user_id": admin.id,
            "username": admin.username,
            "role": "admin",
            "is_super_admin": admin.is_super_admin,
            "user_type": "admin"
        }
    
    # Try regular user
    user = auth_service.verify_user_password(username, password)
    if user:
        return {
            "user_id": user.id,
            "username": user.username,
            "role": "user",
            "national_id": user.national_id,
            "user_type": "user"
        }
    
    return None

def verify_admin_role(user_info: Dict[str, Any] = Depends(verify_token)) -> Dict[str, Any]:
    """Verify that the authenticated user has admin role"""
    if user_info["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Admin access required. Current role: {user_info['role']}"
        )
    return user_info

def verify_user_role(user_info: Dict[str, Any] = Depends(verify_token)) -> Dict[str, Any]:
    """Verify that the authenticated user has user role"""
    if user_info["role"] != "user":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User access required. Current role: {user_info['role']}"
        )
    return user_info

def verify_super_admin_role(user_info: Dict[str, Any] = Depends(verify_admin_role)) -> Dict[str, Any]:
    """Verify that the authenticated user has super admin role"""
    # This would need to be checked against the database
    # For now, we'll use a simple check
    if not user_info.get("is_super_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required"
        )
    return user_info

# Legacy functions for backward compatibility
def verify_password(username: str, password: str) -> bool:
    """Legacy password verification - now uses database"""
    db = SessionLocal()
    try:
        auth_service = AuthDatabaseService(db)
        user_info = authenticate_user(username, password, auth_service)
        return user_info is not None
    finally:
        db.close()

def get_user_role(username: str) -> str:
    """Get user role from database"""
    db = SessionLocal()
    try:
        auth_service = AuthDatabaseService(db)
        
        # Check admin first
        admin = auth_service.get_admin_by_username(username)
        if admin:
            return "admin"
        
        # Check user
        user = auth_service.get_user_by_username(username)
        if user:
            return "user"
        
        return "user"  # Default role
    finally:
        db.close()

def verify_admin_role_legacy(username: str) -> bool:
    """Legacy admin role verification"""
    return get_user_role(username) == "admin"

def verify_doctor_role(username: str) -> bool:
    """Check if user has doctor role (admin or special doctor role)"""
    role = get_user_role(username)
    return role in ["admin", "doctor"]

