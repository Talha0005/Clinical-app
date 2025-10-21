"""
Updated Authentication API with Database Support
Role-based authentication using separate Admin and User tables
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from datetime import timedelta
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

from auth_database import (
    authenticate_user,
    create_access_token,
    verify_token,
    verify_admin_role,
    verify_user_role,
    get_auth_service,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from services.auth_database_service import AuthDatabaseService
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"],
)

# Pydantic Models
class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    username: str
    role: str
    user_id: int
    user_type: str
    redirect: str = "/"  # Default redirect to home page

class RegisterUserRequest(BaseModel):
    username: str
    email: str
    password: str
    full_name: str
    national_id: Optional[str] = None
    phone_number: Optional[str] = None
    date_of_birth: Optional[datetime] = None
    gender: Optional[str] = None

class RegisterAdminRequest(BaseModel):
    username: str
    email: str
    password: str
    full_name: str
    is_super_admin: bool = False

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: str
    national_id: Optional[str]
    phone_number: Optional[str]
    date_of_birth: Optional[str]
    gender: Optional[str]
    is_active: bool
    is_verified: bool
    created_at: str
    last_login: Optional[str]

class AdminResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: str
    is_active: bool
    is_super_admin: bool
    created_at: str
    last_login: Optional[str]

# Authentication Endpoints
@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    auth_service: AuthDatabaseService = Depends(get_auth_service)
):
    """Authenticate user and return JWT token with role information."""
    try:
        user_info = authenticate_user(request.username, request.password, auth_service)
        
        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={
                "sub": user_info["username"],
                "role": user_info["role"],
                "user_id": user_info["user_id"]
            },
            expires_delta=access_token_expires
        )

        logger.info(f"User {request.username} logged in with role {user_info['role']}")

        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            username=user_info["username"],
            role=user_info["role"],
            user_id=user_info["user_id"],
            user_type=user_info["user_type"],
            redirect="/"  # Always redirect to home page (React app will handle routing)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error for {request.username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )

@router.get("/verify")
async def verify_auth(user_info: dict = Depends(verify_token)):
    """Verify current authentication status."""
    return {
        "username": user_info["username"],
        "role": user_info["role"],
        "user_id": user_info["user_id"],
        "authenticated": True
    }

@router.post("/logout")
async def logout():
    """Logout endpoint (token invalidation handled client-side)."""
    return {"message": "Logged out successfully"}

# User Registration Endpoints
@router.post("/register/user", response_model=UserResponse)
async def register_user(
    request: RegisterUserRequest,
    auth_service: AuthDatabaseService = Depends(get_auth_service)
):
    """Register a new regular user."""
    try:
        user = auth_service.create_user(
            username=request.username,
            email=request.email,
            password=request.password,
            full_name=request.full_name,
            national_id=request.national_id,
            phone_number=request.phone_number,
            date_of_birth=request.date_of_birth,
            gender=request.gender
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User registration failed. Username or email may already exist."
            )
        
        logger.info(f"New user registered: {request.username}")
        
        return UserResponse(**user.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"User registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User registration failed"
        )

@router.post("/register/admin")
async def register_admin(
    request: RegisterAdminRequest,
    current_admin: dict = Depends(verify_admin_role),
    auth_service: AuthDatabaseService = Depends(get_auth_service)
):
    """Register a new admin user (admin access required)."""
    try:
        admin = auth_service.create_admin(
            username=request.username,
            email=request.email,
            password=request.password,
            full_name=request.full_name,
            is_super_admin=request.is_super_admin
        )
        
        if not admin:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Admin registration failed. Username or email may already exist."
            )
        
        logger.info(f"New admin registered by {current_admin['username']}: {request.username}")
        
        # Return success response with redirect instruction
        return {
            "success": True,
            "message": "Admin registered successfully",
            "admin": admin.to_dict(),
            "redirect": "/"  # Redirect to home page instead of /dashboard
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Admin registration failed"
        )

# User Management Endpoints (Admin Only)
@router.get("/users", response_model=list[UserResponse])
async def get_all_users(
    current_admin: dict = Depends(verify_admin_role),
    auth_service: AuthDatabaseService = Depends(get_auth_service)
):
    """Get all users (admin access required)."""
    try:
        users = auth_service.get_all_users()
        return [UserResponse(**user.to_dict()) for user in users]
        
    except Exception as e:
        logger.error(f"Error fetching users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch users"
        )

@router.get("/admins", response_model=list[AdminResponse])
async def get_all_admins(
    current_admin: dict = Depends(verify_admin_role),
    auth_service: AuthDatabaseService = Depends(get_auth_service)
):
    """Get all admins (admin access required)."""
    try:
        admins = auth_service.get_all_admins()
        return [AdminResponse(**admin.to_dict()) for admin in admins]
        
    except Exception as e:
        logger.error(f"Error fetching admins: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch admins"
        )

@router.get("/user/{username}")
async def get_user_by_username(
    username: str,
    current_admin: dict = Depends(verify_admin_role),
    auth_service: AuthDatabaseService = Depends(get_auth_service)
):
    """Get user by username (admin access required)."""
    try:
        user = auth_service.get_user_by_username(username)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return UserResponse(**user.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user {username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch user"
        )

@router.get("/user/national-id/{national_id}")
async def get_user_by_national_id(
    national_id: str,
    current_admin: dict = Depends(verify_admin_role),
    auth_service: AuthDatabaseService = Depends(get_auth_service)
):
    """Get user by national ID (admin access required)."""
    try:
        user = auth_service.get_user_by_national_id(national_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return UserResponse(**user.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user with national_id {national_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch user"
        )

