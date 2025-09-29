"""Authentication utilities for DigiClinic API endpoints."""

import os
from typing import Optional
from datetime import datetime, timedelta

from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt


# JWT settings with safe local fallbacks
def _load_secret_key() -> str:
    """Resolve JWT secret.
    Order of precedence:
    1) JWT_SECRET from environment
    2) Try loading from .env (if available)
    3) Development fallback (prints a warning)
    """
    secret = os.getenv("JWT_SECRET")
    if secret:
        return secret

    # Try to load from .env if available
    try:
        from dotenv import load_dotenv

        load_dotenv()
        secret = os.getenv("JWT_SECRET")
        if secret:
            return secret
    except Exception:
        # dotenv not installed or other issue; continue to fallback
        pass

    # Last resort: dev fallback for local runs
    dev_secret = "dev-secret-please-change"
    print(
        "⚠️  JWT_SECRET not set; using development fallback. Set JWT_SECRET in your environment or backend/.env."
    )
    return dev_secret


SECRET_KEY = _load_secret_key()
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

security = HTTPBearer()


def verify_password(username: str, password: str) -> bool:
    """Verify username and password against environment variables.
    If no env var is found for the given user, allow a simple local fallback: doctor/doctor.
    """
    password_key = f"{username.upper()}_PASSWORD"
    expected_password = os.getenv(password_key)
    if expected_password is not None:
        return password == expected_password

    # Dev fallback when no password is configured in env
    if username.lower() == "doctor" and password == "doctor":
        print(
            "🔓 Using development default credentials for 'doctor'. Configure DOCTOR_PASSWORD to override."
        )
        return True
    return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Verify JWT token and return username."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM]
        )
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    return username
