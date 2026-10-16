"""
Security utilities for authentication and authorization.
Cybersecurity-grade security measures for SentinelGrid.
"""

import hashlib
import os
import logging
from typing import Optional, Tuple
from fastapi import Request

logger = logging.getLogger(__name__)


class SecurityService:
    """Security service for authentication and data protection."""
    
    @staticmethod
    def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
        """
        Hash password with salt (for local validation before Keycloak).
        Note: Keycloak handles password hashing, but this can be used for
        pre-validation or local checks.
        """
        if salt is None:
            salt = os.urandom(32).hex()
        
        # Use PBKDF2 (Keycloak uses this internally)
        key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return key.hex(), salt
    
    @staticmethod
    def validate_password_strength(password: str) -> Tuple[bool, str]:
        """
        Validate password strength before sending to Keycloak.
        Returns (is_valid, error_message)
        """
        if len(password) < 8:
            return False, "Password must be at least 8 characters"
        
        if not any(c.isupper() for c in password):
            return False, "Password must contain at least one uppercase letter"
        
        if not any(c.islower() for c in password):
            return False, "Password must contain at least one lowercase letter"
        
        if not any(c.isdigit() for c in password):
            return False, "Password must contain at least one number"
        
        # Check for common passwords (simplified list)
        common_passwords = [
            'password', '12345678', 'qwerty', 'admin', 'letmein',
            'welcome', 'monkey', '1234567890', 'password123', 'admin123'
        ]
        if password.lower() in common_passwords:
            return False, "Password is too common. Please choose a stronger password"
        
        # Check for repeated characters
        if len(set(password)) < 4:
            return False, "Password must contain at least 4 unique characters"
        
        return True, ""
    
    @staticmethod
    def rate_limit_key(identifier: str, action: str) -> str:
        """Generate rate limit key for Redis or memory store."""
        return f"rate_limit:{action}:{identifier}"
    
    @staticmethod
    def sanitize_input(input_str: str, max_length: int = 1000) -> str:
        """
        Sanitize user input to prevent injection attacks.
        Removes null bytes, trims whitespace, limits length.
        """
        if not isinstance(input_str, str):
            return ""
        
        # Remove null bytes
        input_str = input_str.replace('\x00', '')
        
        # Trim whitespace
        input_str = input_str.strip()
        
        # Limit length
        if len(input_str) > max_length:
            input_str = input_str[:max_length]
        
        # Remove control characters (except newline, tab, carriage return)
        sanitized = ""
        for char in input_str:
            if ord(char) >= 32 or char in ['\n', '\t', '\r']:
                sanitized += char
        
        return sanitized
    
    @staticmethod
    def extract_client_info(request: Request) -> dict:
        """
        Extract client information for audit logging.
        Returns dict with ip_address, user_agent, forwarded_for.
        """
        ip_address = None
        if request.client:
            ip_address = request.client.host
        
        # Check for forwarded IP (from proxy/load balancer)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # Take first IP in chain
            ip_address = forwarded_for.split(',')[0].strip()
        
        return {
            "ip_address": ip_address,
            "user_agent": request.headers.get("user-agent"),
            "forwarded_for": forwarded_for,
        }
    
    @staticmethod
    def is_safe_email(email: str) -> bool:
        """
        Basic email validation (additional to Pydantic EmailStr).
        Checks for suspicious patterns.
        """
        if not email or '@' not in email:
            return False
        
        # Check for suspicious patterns
        suspicious_patterns = [
            '<script',
            'javascript:',
            'onerror=',
            'onclick=',
        ]
        
        email_lower = email.lower()
        for pattern in suspicious_patterns:
            if pattern in email_lower:
                return False
        
        return True
    
    @staticmethod
    def mask_sensitive_data(data: str, visible_chars: int = 4) -> str:
        """
        Mask sensitive data for logging (e.g., email, tokens).
        Shows first N characters, masks the rest.
        """
        if not data or len(data) <= visible_chars:
            return "***"
        
        return data[:visible_chars] + "*" * (len(data) - visible_chars)

