"""
Admin-specific authentication and role verification
"""

from fastapi import APIRouter, Depends, HTTPException, status
from auth import verify_token, verify_admin_role, verify_doctor_role
from typing import Dict

router = APIRouter(prefix="/api/admin", tags=["Admin Auth"])

def verify_admin_auth(user_info: Dict = Depends(verify_token)) -> Dict:
    """Verify that the authenticated user has admin role."""
    username = user_info["username"]
    role = user_info["role"]
    
    if not verify_admin_role(username):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Admin access required. Current role: {role}"
        )
    
    return user_info

def verify_doctor_auth(user_info: Dict = Depends(verify_token)) -> Dict:
    """Verify that the authenticated user has doctor or admin role."""
    username = user_info["username"]
    role = user_info["role"]
    
    if not verify_doctor_role(username):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Doctor or Admin access required. Current role: {role}"
        )
    
    return user_info

@router.get("/auth/verify-admin")
async def verify_admin_access(user_info: Dict = Depends(verify_admin_auth)):
    """Verify admin access."""
    return {
        "success": True,
        "message": "Admin access verified",
        "username": user_info["username"],
        "role": user_info["role"]
    }

@router.get("/auth/verify-doctor")
async def verify_doctor_access(user_info: Dict = Depends(verify_doctor_auth)):
    """Verify doctor access."""
    return {
        "success": True,
        "message": "Doctor access verified",
        "username": user_info["username"],
        "role": user_info["role"]
    }

@router.get("/auth/role-info")
async def get_role_info(user_info: Dict = Depends(verify_token)):
    """Get current user's role information."""
    return {
        "username": user_info["username"],
        "role": user_info["role"],
        "is_admin": verify_admin_role(user_info["username"]),
        "is_doctor": verify_doctor_role(user_info["username"])
    }

