from fastapi import APIRouter, Depends, HTTPException, status
from datetime import timedelta

from auth import verify_password, create_access_token, verify_token, ACCESS_TOKEN_EXPIRE_MINUTES
from model.auth import LoginRequest, LoginResponse

router = APIRouter(
    prefix="/api/auth",
    tags=["auth"],
)

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Authenticate user and return JWT token."""
    if not verify_password(request.username, request.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": request.username}, expires_delta=access_token_expires
    )
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        username=request.username
    )

@router.get("/verify")
async def verify_auth(current_user: str = Depends(verify_token)):
    """Verify current authentication status."""
    return {"username": current_user, "authenticated": True}

@router.post("/logout")
async def logout():
    """Logout endpoint (token invalidation handled client-side)."""
    return {"message": "Logged out successfully"}
