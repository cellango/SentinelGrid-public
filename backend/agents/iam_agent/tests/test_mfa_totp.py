"""
Tests for TOTP MFA implementation.

Verifies that MFA enrollment, verification, and management work correctly
with proper tenant isolation.
"""

import pytest
from fastapi import HTTPException
from unittest.mock import Mock, patch, AsyncMock
import pyotp

from app.api.mfa_totp import (
    enroll_mfa,
    verify_mfa_enrollment,
    get_mfa_status,
    disable_mfa,
    get_recovery_codes
)


@pytest.fixture
def mock_token_data():
    """Mock validated token data."""
    return {
        "valid": True,
        "user_id": "test-user-123",
        "tenant_id": "tenant-abc-123",
        "roles": ["TENANT_ADMIN"]
    }


@pytest.fixture
def mock_user_with_tenant():
    """Mock Keycloak user with tenant_id."""
    return {
        "id": "test-user-123",
        "username": "test@example.com",
        "email": "test@example.com",
        "attributes": {
            "tenant_id": ["tenant-abc-123"]
        }
    }


class TestMFAEnrollment:
    """Test MFA enrollment process."""
    
    @pytest.mark.asyncio
    async def test_mfa_enrollment_success(self, mock_token_data, mock_user_with_tenant):
        """Test successful MFA enrollment."""
        with patch("app.api.mfa_totp.get_token_data") as mock_get_token:
            mock_get_token.return_value = mock_token_data
            
            with patch("app.api.mfa_totp.KeycloakAdminClient") as mock_kc_class:
                mock_kc = AsyncMock()
                mock_kc.__aenter__.return_value = mock_kc
                mock_kc.get_user.return_value = mock_user_with_tenant
                
                mock_response = AsyncMock()
                mock_response.raise_for_status = Mock()
                mock_kc._make_request.return_value = mock_response
                
                mock_kc_class.return_value = mock_kc
                
                from app.api.mfa_totp import MFAEnrollmentRequest
                request = MFAEnrollmentRequest(user_id="test-user-123")
                
                result = await enroll_mfa(request, "mock-token")
                
                # Verify QR code and secret generated
                assert result.secret
                assert result.qr_code
                assert result.issuer == "SentinelGrid"
    
    @pytest.mark.asyncio
    async def test_mfa_enrollment_cross_tenant_blocked(self, mock_token_data):
        """Test that cross-tenant MFA enrollment is blocked."""
        with patch("app.api.mfa_totp.get_token_data") as mock_get_token:
            mock_get_token.return_value = mock_token_data
            
            # User belongs to different tenant
            other_tenant_user = {
                "id": "other-user",
                "attributes": {"tenant_id": ["other-tenant-456"]}
            }
            
            with patch("app.api.mfa_totp.KeycloakAdminClient") as mock_kc_class:
                mock_kc = AsyncMock()
                mock_kc.__aenter__.return_value = mock_kc
                mock_kc.get_user.return_value = other_tenant_user
                mock_kc_class.return_value = mock_kc
                
                from app.api.mfa_totp import MFAEnrollmentRequest
                request = MFAEnrollmentRequest(user_id="other-user")
                
                with pytest.raises(HTTPException) as exc_info:
                    await enroll_mfa(request, "mock-token")
                
                assert exc_info.value.status_code == 404


class TestMFAVerification:
    """Test MFA code verification."""
    
    @pytest.mark.asyncio
    async def test_mfa_status_check(self, mock_token_data, mock_user_with_tenant):
        """Test checking MFA status for a user."""
        with patch("app.api.mfa_totp.get_token_data") as mock_get_token:
            mock_get_token.return_value = mock_token_data
            
            with patch("app.api.mfa_totp.KeycloakAdminClient") as mock_kc_class:
                mock_kc = AsyncMock()
                mock_kc.__aenter__.return_value = mock_kc
                mock_kc.get_user.return_value = mock_user_with_tenant
                
                # Mock credentials response (OTP enabled)
                mock_creds_response = AsyncMock()
                mock_creds_response.raise_for_status = Mock()
                mock_creds_response.json.return_value = [
                    {"type": "otp", "createdDate": 1234567890}
                ]
                mock_kc._make_request.return_value = mock_creds_response
                mock_kc_class.return_value = mock_kc
                
                result = await get_mfa_status("test-user-123", "mock-token")
                
                assert result.mfa_enabled == True
                assert result.mfa_type == "totp"


class TestMFASecurity:
    """Test MFA security and tenant isolation."""
    
    @pytest.mark.asyncio
    async def test_cannot_disable_mfa_for_other_tenant_user(self, mock_token_data):
        """Test that disabling MFA respects tenant boundaries."""
        with patch("app.api.mfa_totp.get_token_data") as mock_get_token:
            mock_get_token.return_value = mock_token_data
            
            # User from different tenant
            other_tenant_user = {
                "id": "other-user",
                "attributes": {"tenant_id": ["other-tenant"]}
            }
            
            with patch("app.api.mfa_totp.KeycloakAdminClient") as mock_kc_class:
                mock_kc = AsyncMock()
                mock_kc.__aenter__.return_value = mock_kc
                mock_kc.get_user.return_value = other_tenant_user
                mock_kc_class.return_value = mock_kc
                
                with pytest.raises(HTTPException) as exc_info:
                    await disable_mfa("other-user", "mock-token")
                
                assert exc_info.value.status_code == 404


class TestRecoveryCodes:
    """Test MFA recovery codes."""
    
    @pytest.mark.asyncio
    async def test_recovery_codes_generated(self, mock_token_data, mock_user_with_tenant):
        """Test that recovery codes are generated."""
        with patch("app.api.mfa_totp.get_token_data") as mock_get_token:
            mock_get_token.return_value = mock_token_data
            
            with patch("app.api.mfa_totp.KeycloakAdminClient") as mock_kc_class:
                mock_kc = AsyncMock()
                mock_kc.__aenter__.return_value = mock_kc
                mock_kc.get_user.return_value = mock_user_with_tenant
                mock_kc_class.return_value = mock_kc
                
                result = await get_recovery_codes("test-user-123", "mock-token")
                
                assert len(result.codes) == 8  # 8 recovery codes
                assert all(len(code) == 8 for code in result.codes)  # Each code is 8 chars


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])

