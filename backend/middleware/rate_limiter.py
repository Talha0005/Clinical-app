"""
Rate limiting middleware for NHS API compliance
Implements token bucket algorithm for rate limiting
"""

import time
import asyncio
from typing import Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
import logging

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

@dataclass
class RateLimitBucket:
    """Token bucket for rate limiting"""
    capacity: int
    refill_rate: float  # tokens per second
    tokens: float = field(default_factory=lambda: 0)
    last_refill: float = field(default_factory=time.time)
    
    def consume(self, tokens: int = 1) -> bool:
        """
        Attempt to consume tokens from the bucket
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            True if tokens were consumed, False if insufficient tokens
        """
        now = time.time()
        self._refill(now)
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False
    
    def _refill(self, now: float):
        """Refill the bucket based on elapsed time"""
        elapsed = now - self.last_refill
        tokens_to_add = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now
    
    def time_until_available(self, tokens: int = 1) -> float:
        """Calculate time until tokens will be available"""
        if self.tokens >= tokens:
            return 0
        
        tokens_needed = tokens - self.tokens
        return tokens_needed / self.refill_rate

class RateLimiter:
    """Rate limiter for API endpoints"""
    
    def __init__(self):
        """Initialize rate limiter with different tiers"""
        self.buckets: Dict[str, Dict[str, RateLimitBucket]] = defaultdict(dict)
        
        # Define rate limit tiers (requests per minute)
        self.tiers = {
            "nhs_api": {"capacity": 1200, "per_minute": 1200},  # NHS production limit
            "nhs_sandbox": {"capacity": 60, "per_minute": 60},   # NHS sandbox limit
            "default": {"capacity": 100, "per_minute": 100},     # Default limit
            "auth": {"capacity": 10, "per_minute": 10},          # Strict limit for auth
            "admin": {"capacity": 1000, "per_minute": 1000}      # Higher limit for admin
        }
    
    def get_bucket(self, key: str, tier: str = "default") -> RateLimitBucket:
        """
        Get or create a rate limit bucket for a key
        
        Args:
            key: Unique identifier (e.g., IP address, API key)
            tier: Rate limit tier to use
            
        Returns:
            RateLimitBucket for the key
        """
        if key not in self.buckets[tier]:
            tier_config = self.tiers.get(tier, self.tiers["default"])
            capacity = tier_config["capacity"]
            per_minute = tier_config["per_minute"]
            refill_rate = per_minute / 60.0  # Convert to per second
            
            self.buckets[tier][key] = RateLimitBucket(
                capacity=capacity,
                refill_rate=refill_rate,
                tokens=capacity  # Start with full bucket
            )
        
        return self.buckets[tier][key]
    
    def check_rate_limit(
        self,
        key: str,
        tier: str = "default",
        tokens: int = 1
    ) -> tuple[bool, Optional[float]]:
        """
        Check if request is within rate limit
        
        Args:
            key: Unique identifier
            tier: Rate limit tier
            tokens: Number of tokens to consume
            
        Returns:
            Tuple of (allowed, retry_after_seconds)
        """
        bucket = self.get_bucket(key, tier)
        
        if bucket.consume(tokens):
            return (True, None)
        else:
            retry_after = bucket.time_until_available(tokens)
            return (False, retry_after)
    
    def cleanup_old_buckets(self, max_age_hours: int = 1):
        """Remove old unused buckets to prevent memory leaks"""
        # This would typically be run periodically
        # Implementation depends on tracking last access time
        pass

class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting"""
    
    def __init__(self, app, rate_limiter: Optional[RateLimiter] = None):
        super().__init__(app)
        self.rate_limiter = rate_limiter or RateLimiter()
    
    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting"""
        
        # Skip rate limiting for static files and health checks
        if request.url.path.startswith("/static") or request.url.path == "/health":
            return await call_next(request)
        
        # Determine rate limit key and tier
        key = self._get_rate_limit_key(request)
        tier = self._get_rate_limit_tier(request)
        
        # Check rate limit
        allowed, retry_after = self.rate_limiter.check_rate_limit(key, tier)
        
        if not allowed:
            # Return 429 Too Many Requests
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "retry_after": retry_after,
                    "tier": tier
                },
                headers={
                    "Retry-After": str(int(retry_after)),
                    "X-RateLimit-Limit": str(self.rate_limiter.tiers[tier]["per_minute"]),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time() + retry_after))
                }
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers to response
        bucket = self.rate_limiter.get_bucket(key, tier)
        tier_config = self.rate_limiter.tiers[tier]
        
        response.headers["X-RateLimit-Limit"] = str(tier_config["per_minute"])
        response.headers["X-RateLimit-Remaining"] = str(int(bucket.tokens))
        response.headers["X-RateLimit-Reset"] = str(int(time.time() + 60))
        
        return response
    
    def _get_rate_limit_key(self, request: Request) -> str:
        """Get unique key for rate limiting (IP or API key)"""
        # Try to get API key from headers
        api_key = request.headers.get("subscription-key") or \
                 request.headers.get("Ocp-Apim-Subscription-Key")
        
        if api_key:
            return f"api_key:{api_key}"
        
        # Try to get authenticated user
        if hasattr(request.state, "user"):
            return f"user:{request.state.user}"
        
        # Fall back to IP address
        client_ip = request.client.host if request.client else "unknown"
        return f"ip:{client_ip}"
    
    def _get_rate_limit_tier(self, request: Request) -> str:
        """Determine rate limit tier based on request"""
        path = request.url.path
        
        # NHS API endpoints
        if path.startswith("/api/terminology") or path.startswith("/api/nhs"):
            # Check if sandbox or production
            if "sandbox" in request.headers.get("X-Environment", "").lower():
                return "nhs_sandbox"
            return "nhs_api"
        
        # Authentication endpoints
        if path.startswith("/api/auth"):
            return "auth"
        
        # Admin endpoints
        if path.startswith("/api/admin"):
            return "admin"
        
        return "default"

def create_rate_limiter() -> RateLimiter:
    """Factory function to create rate limiter"""
    return RateLimiter()

# Decorator for rate limiting specific endpoints
def rate_limit(tier: str = "default", tokens: int = 1):
    """
    Decorator for rate limiting specific endpoints
    
    Usage:
        @app.get("/api/endpoint")
        @rate_limit(tier="nhs_api", tokens=1)
        async def endpoint():
            ...
    """
    def decorator(func):
        async def wrapper(request: Request, *args, **kwargs):
            rate_limiter = getattr(request.app.state, "rate_limiter", None)
            if not rate_limiter:
                rate_limiter = RateLimiter()
            
            # Get rate limit key
            client_ip = request.client.host if request.client else "unknown"
            key = f"ip:{client_ip}"
            
            # Check rate limit
            allowed, retry_after = rate_limiter.check_rate_limit(key, tier, tokens)
            
            if not allowed:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Retry after {retry_after:.1f} seconds",
                    headers={"Retry-After": str(int(retry_after))}
                )
            
            return await func(request, *args, **kwargs)
        
        return wrapper
    return decorator