"""
Security middleware for rate limiting and request validation.
"""

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import time
from collections import defaultdict
from typing import Optional
import logging

from app.services.security import SecurityService
from app.core.config import settings

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware.
    Prevents brute force attacks and abuse.
    """
    
    def __init__(self, app, redis_client=None):
        super().__init__(app)
        self.redis_client = redis_client
        self.memory_store: dict = defaultdict(list)  # Fallback if Redis unavailable
    
    async def dispatch(self, request: Request, call_next):
        """
        Check rate limits before processing request.
        """
        # Skip rate limiting if disabled in config (for dev environments)
        if not settings.ENABLE_RATE_LIMITING:
            return await call_next(request)
        
        # Rate limit login attempts
        if request.url.path.endswith("/login") and request.method == "POST":
            ip = self._get_client_ip(request)
            if not await self._check_rate_limit(ip, "login", max_attempts=5, window=900):
                logger.warning(f"Rate limit exceeded for login from {ip}")
                raise HTTPException(
                    status_code=429,
                    detail="Too many login attempts. Please try again in 15 minutes."
                )
        
        # Rate limit signup attempts
        if request.url.path.endswith("/signup") and request.method == "POST":
            ip = self._get_client_ip(request)
            if not await self._check_rate_limit(ip, "signup", max_attempts=3, window=3600):
                logger.warning(f"Rate limit exceeded for signup from {ip}")
                raise HTTPException(
                    status_code=429,
                    detail="Too many signup attempts. Please try again in 1 hour."
                )
        
        # Rate limit password reset attempts
        if request.url.path.endswith("/reset-password") and request.method == "POST":
            ip = self._get_client_ip(request)
            if not await self._check_rate_limit(ip, "reset_password", max_attempts=3, window=3600):
                logger.warning(f"Rate limit exceeded for password reset from {ip}")
                raise HTTPException(
                    status_code=429,
                    detail="Too many password reset attempts. Please try again in 1 hour."
                )
        
        response = await call_next(request)
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        if request.client:
            ip = request.client.host
        else:
            ip = "unknown"
        
        # Check for forwarded IP (from proxy/load balancer)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # Take first IP in chain
            ip = forwarded_for.split(',')[0].strip()
        
        return ip
    
    async def _check_rate_limit(
        self,
        identifier: str,
        action: str,
        max_attempts: int,
        window: int
    ) -> bool:
        """
        Check if rate limit is exceeded.
        Returns True if within limit, False if exceeded.
        """
        key = SecurityService.rate_limit_key(identifier, action)
        now = time.time()
        
        if self.redis_client:
            # Use Redis for distributed rate limiting
            try:
                count = await self.redis_client.incr(key)
                if count == 1:
                    await self.redis_client.expire(key, window)
                return count <= max_attempts
            except Exception as e:
                logger.warning(f"Redis rate limiting failed, falling back to memory: {e}")
                # Fallback to memory
        
        # Memory-based rate limiting (fallback)
        if identifier not in self.memory_store:
            self.memory_store[identifier] = []
        
        attempts = self.memory_store[identifier]
        # Remove old attempts
        attempts[:] = [t for t in attempts if now - t < window]
        
        if len(attempts) >= max_attempts:
            return False
        
        attempts.append(now)
        return True


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to all responses.
    """
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        
        return response

