"""Tests for passwordless authentication API endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock

from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@patch('app.api.passwordless.MagicLinkService')
def test_send_magic_link(mock_service_class, client):
    """Test send magic link endpoint."""
    mock_service = Mock()
    mock_service.generate_magic_link = AsyncMock(return_value={
        "token": "magic-token-123",
        "expires_in_seconds": 900,
        "expires_at": "2025-01-28T15:00:00"
    })
    mock_service_class.return_value = mock_service
    
    response = client.post(
        "/api/v1/auth/passwordless/magic-link",
        json={
            "email": "user@example.com",
            "redirect_uri": "https://app.example.com/callback"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "message" in data


@patch('app.api.passwordless.OTPService')
def test_send_otp(mock_service_class, client):
    """Test send OTP endpoint."""
    mock_service = Mock()
    mock_service.generate_otp = AsyncMock(return_value={
        "token": "otp-token-123",
        "expires_in_seconds": 300,
        "expires_at": "2025-01-28T14:55:00"
    })
    mock_service_class.return_value = mock_service
    
    response = client.post(
        "/api/v1/auth/passwordless/otp",
        json={
            "email": "user@example.com"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "message" in data


@patch('app.api.passwordless.MagicLinkService')
def test_verify_magic_link(mock_service_class, client):
    """Test verify magic link endpoint."""
    mock_service = Mock()
    mock_service.verify_magic_link = AsyncMock(return_value={
        "valid": True,
        "email": "user@example.com",
        "user_id": "user-123",
        "access_token": "access-token-123",
        "refresh_token": "refresh-token-123",
        "expires_in": 3600
    })
    mock_service_class.return_value = mock_service
    
    response = client.post(
        "/api/v1/auth/passwordless/verify",
        json={
            "token": "magic-token-123"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "access_token" in data


@patch('app.api.passwordless.OTPService')
def test_verify_otp(mock_service_class, client):
    """Test verify OTP endpoint."""
    mock_service = Mock()
    mock_service.verify_otp = AsyncMock(return_value={
        "valid": True,
        "email": "user@example.com",
        "user_id": "user-123",
        "access_token": "access-token-123",
        "refresh_token": "refresh-token-123",
        "expires_in": 3600
    })
    mock_service_class.return_value = mock_service
    
    response = client.post(
        "/api/v1/auth/passwordless/verify",
        json={
            "token": "otp-token-123",
            "code": "123456"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
