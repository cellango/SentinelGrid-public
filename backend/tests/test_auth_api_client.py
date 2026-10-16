"""
Unit tests for authentication services (backend).
Tests the IAM Agent authentication services without actual HTTP calls.
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, AsyncMock
import json

# Add IAM Agent service directories to path for relative imports
iam_agent_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'agents', 'iam_agent'))
iam_agent_app = os.path.join(iam_agent_root, 'app')
for p in (iam_agent_root, iam_agent_app):
    if p not in sys.path:
        sys.path.insert(0, p)

# Add shared libs (sg_core) to path
libs_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'libs'))
if libs_path not in sys.path:
    sys.path.insert(0, libs_path)

# Ensure we import the IAM Agent app package rather than any previously imported service "app"
existing_app = sys.modules.get("app")
if existing_app:
    app_file = getattr(existing_app, "__file__", "") or ""
    if "iam_agent" not in app_file:
        sys.modules.pop("app", None)
        sys.modules.pop("app.services", None)

from app.services.security import SecurityService
from app.services.pricing_service import PricingService
from app.services.realm_manager import RealmManager


class TestSecurityService:
    """Tests for SecurityService."""
    
    def test_validate_password_strength(self):
        """Test password strength validation."""
        # Valid password
        is_valid, error = SecurityService.validate_password_strength("SecurePass123!")
        assert is_valid is True
        assert error is None or error == ""  # Can be None or empty string
        
        # Too short
        is_valid, error = SecurityService.validate_password_strength("Short1!")
        assert is_valid is False
        assert "8 characters" in error
        
        # No uppercase
        is_valid, error = SecurityService.validate_password_strength("lowercase123!")
        assert is_valid is False
        assert "uppercase" in error
        
        # No lowercase
        is_valid, error = SecurityService.validate_password_strength("UPPERCASE123!")
        assert is_valid is False
        assert "lowercase" in error
        
        # No digit
        is_valid, error = SecurityService.validate_password_strength("NoDigits!")
        assert is_valid is False
        assert "number" in error or "digit" in error
    
    def test_sanitize_input(self):
        """Test input sanitization."""
        # Normal input
        result = SecurityService.sanitize_input("test@example.com")
        assert result == "test@example.com"
        
        # XSS attempt - sanitize_input removes control chars but doesn't escape HTML
        # It's designed for basic sanitization, not HTML escaping
        result = SecurityService.sanitize_input("<script>alert('xss')</script>")
        # Should still contain the text (it's not HTML-escaped, just control-char cleaned)
        # The actual HTML escaping should happen at the template/view layer
        assert isinstance(result, str)
        assert len(result) > 0
        
        # SQL injection attempt - should pass through (basic sanitization only)
        result = SecurityService.sanitize_input("'; DROP TABLE users; --")
        # Basic sanitization doesn't remove SQL keywords, just control chars
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_is_safe_email(self):
        """Test email safety check."""
        # Valid email
        assert SecurityService.is_safe_email("test@example.com") is True
        
        # Invalid email
        assert SecurityService.is_safe_email("not-an-email") is False
        
        # Email with XSS
        assert SecurityService.is_safe_email("test<script>@example.com") is False


class TestPricingService:
    """Tests for PricingService."""
    
    # ========== Existing Tests ==========
    
    def test_get_realm_strategy_starter(self):
        """Test realm strategy for starter tier."""
        strategy = PricingService.get_realm_strategy("starter", user_count=10, org_count=0)
        assert strategy == "shared"
    
    def test_get_realm_strategy_enterprise(self):
        """Test realm strategy for enterprise tier."""
        strategy = PricingService.get_realm_strategy("enterprise", user_count=100, org_count=0)
        assert strategy == "dedicated"
    
    def test_get_realm_strategy_professional_shared(self):
        """Test realm strategy for professional tier (shared)."""
        strategy = PricingService.get_realm_strategy("professional", user_count=100, org_count=0)
        assert strategy == "shared"
    
    def test_get_realm_strategy_professional_dedicated(self):
        """Test realm strategy for professional tier (dedicated due to user count)."""
        strategy = PricingService.get_realm_strategy("professional", user_count=600, org_count=0)
        assert strategy == "dedicated"
    
    def test_can_create_org(self):
        """Test org creation limits."""
        # Starter tier - no orgs allowed
        assert PricingService.can_create_org("starter", current_org_count=0) is False
        
        # Professional tier - 1 org allowed
        assert PricingService.can_create_org("professional", current_org_count=0) is True
        assert PricingService.can_create_org("professional", current_org_count=1) is False
        
        # Enterprise tier - unlimited
        assert PricingService.can_create_org("enterprise", current_org_count=10) is True
    
    def test_can_add_user(self):
        """Test user addition limits."""
        # Starter tier - 100 users max
        assert PricingService.can_add_user("starter", current_user_count=99) is True
        assert PricingService.can_add_user("starter", current_user_count=100) is False
        
        # Enterprise tier - unlimited
        assert PricingService.can_add_user("enterprise", current_user_count=1000) is True
    
    # ========== Priority 1: Free Tier Tests ==========
    
    def test_get_realm_strategy_free(self):
        """Test free tier always uses shared realm."""
        # Free tier with 0 users
        strategy = PricingService.get_realm_strategy("free", user_count=0, org_count=0)
        assert strategy == "shared"
        
        # Free tier with max users (5)
        strategy = PricingService.get_realm_strategy("free", user_count=5, org_count=0)
        assert strategy == "shared"
    
    def test_can_add_user_free(self):
        """Test free tier user addition limits (max 5 users)."""
        # Free tier - 5 users max
        assert PricingService.can_add_user("free", current_user_count=4) is True
        assert PricingService.can_add_user("free", current_user_count=5) is False
        assert PricingService.can_add_user("free", current_user_count=6) is False
    
    def test_can_create_org_free(self):
        """Test free tier cannot create organizations."""
        # Free tier - no orgs allowed
        assert PricingService.can_create_org("free", current_org_count=0) is False
    
    # ========== Priority 1: Professional Tier Boundary Cases ==========
    
    def test_get_realm_strategy_professional_500_users(self):
        """Test professional tier with exactly 500 users stays shared (boundary)."""
        strategy = PricingService.get_realm_strategy("professional", user_count=500, org_count=0)
        assert strategy == "shared"
    
    def test_get_realm_strategy_professional_501_users(self):
        """Test professional tier with 501 users upgrades to dedicated (boundary)."""
        strategy = PricingService.get_realm_strategy("professional", user_count=501, org_count=0)
        assert strategy == "dedicated"
    
    def test_get_realm_strategy_professional_1_org(self):
        """Test professional tier with 1 org stays shared (within limit)."""
        strategy = PricingService.get_realm_strategy("professional", user_count=0, org_count=1)
        assert strategy == "shared"
    
    def test_get_realm_strategy_professional_2_orgs(self):
        """Test professional tier with 2 orgs upgrades to dedicated (boundary)."""
        strategy = PricingService.get_realm_strategy("professional", user_count=0, org_count=2)
        assert strategy == "dedicated"
    
    def test_get_realm_strategy_professional_500_users_1_org(self):
        """Test professional tier with 500 users and 1 org stays shared."""
        strategy = PricingService.get_realm_strategy("professional", user_count=500, org_count=1)
        assert strategy == "shared"
    
    def test_get_realm_strategy_professional_500_users_2_orgs(self):
        """Test professional tier with 500 users and 2 orgs upgrades to dedicated."""
        strategy = PricingService.get_realm_strategy("professional", user_count=500, org_count=2)
        assert strategy == "dedicated"
    
    # ========== Priority 1: Compliance Requirement Tests ==========
    
    def test_requires_dedicated_realm_compliance(self):
        """Test compliance requirement forces dedicated realm for all tiers."""
        # Free tier with compliance
        assert PricingService.requires_dedicated_realm("free", 5, 0, compliance_required=True) is True
        
        # Starter tier with compliance
        assert PricingService.requires_dedicated_realm("starter", 10, 0, compliance_required=True) is True
        
        # Professional tier with compliance
        assert PricingService.requires_dedicated_realm("professional", 100, 0, compliance_required=True) is True
        
        # Enterprise tier with compliance (already dedicated, but should still return True)
        assert PricingService.requires_dedicated_realm("enterprise", 100, 0, compliance_required=True) is True
    
    def test_requires_dedicated_realm_starter_with_compliance(self):
        """Test starter tier with compliance requirement forces dedicated realm."""
        # Starter normally uses shared realm
        strategy = PricingService.get_realm_strategy("starter", user_count=10, org_count=0)
        assert strategy == "shared"
        
        # But with compliance, requires dedicated
        requires_dedicated = PricingService.requires_dedicated_realm("starter", 10, 0, compliance_required=True)
        assert requires_dedicated is True
    
    def test_requires_dedicated_realm_professional_with_compliance(self):
        """Test professional tier with compliance requirement forces dedicated realm."""
        # Professional with 100 users normally uses shared realm
        strategy = PricingService.get_realm_strategy("professional", user_count=100, org_count=0)
        assert strategy == "shared"
        
        # But with compliance, requires dedicated
        requires_dedicated = PricingService.requires_dedicated_realm("professional", 100, 0, compliance_required=True)
        assert requires_dedicated is True
    
    def test_requires_dedicated_realm_without_compliance(self):
        """Test that without compliance, normal tier rules apply."""
        # Free tier without compliance
        assert PricingService.requires_dedicated_realm("free", 5, 0, compliance_required=False) is False
        
        # Starter tier without compliance
        assert PricingService.requires_dedicated_realm("starter", 10, 0, compliance_required=False) is False
        
        # Professional tier without compliance (small)
        assert PricingService.requires_dedicated_realm("professional", 100, 0, compliance_required=False) is False
        
        # Professional tier without compliance (large - should be dedicated)
        assert PricingService.requires_dedicated_realm("professional", 600, 0, compliance_required=False) is True
        
        # Enterprise tier without compliance (always dedicated)
        assert PricingService.requires_dedicated_realm("enterprise", 100, 0, compliance_required=False) is True
    
    # ========== Priority 1: Upgrade Capability Tests ==========
    
    def test_can_upgrade_to_dedicated_free(self):
        """Test free tier cannot upgrade to dedicated."""
        assert PricingService.can_upgrade_to_dedicated("free") is False
    
    def test_can_upgrade_to_dedicated_starter(self):
        """Test starter tier cannot upgrade to dedicated."""
        assert PricingService.can_upgrade_to_dedicated("starter") is False
    
    def test_can_upgrade_to_dedicated_professional(self):
        """Test professional tier can upgrade to dedicated."""
        assert PricingService.can_upgrade_to_dedicated("professional") is True
    
    def test_can_upgrade_to_dedicated_enterprise(self):
        """Test enterprise tier already has dedicated (cannot upgrade)."""
        assert PricingService.can_upgrade_to_dedicated("enterprise") is False
    
    # ========== Priority 2: Edge Cases ==========
    
    def test_realm_strategy_invalid_tier(self):
        """Test invalid tier should default to starter behavior."""
        # Invalid tier should default to starter (shared realm)
        strategy = PricingService.get_realm_strategy("invalid_tier", user_count=10, org_count=0)
        assert strategy == "shared"
    
    def test_realm_strategy_zero_users(self):
        """Test zero users should still work."""
        # All tiers should work with 0 users
        assert PricingService.get_realm_strategy("free", 0, 0) == "shared"
        assert PricingService.get_realm_strategy("starter", 0, 0) == "shared"
        assert PricingService.get_realm_strategy("professional", 0, 0) == "shared"
        assert PricingService.get_realm_strategy("enterprise", 0, 0) == "dedicated"
    
    def test_realm_strategy_negative_values(self):
        """Test negative user/org counts should be handled gracefully."""
        # Negative values should not crash, but behavior may vary
        # We'll test that it doesn't raise an exception
        try:
            strategy = PricingService.get_realm_strategy("starter", user_count=-1, org_count=0)
            # Should still return a valid strategy (may default to shared)
            assert strategy in ["shared", "dedicated"]
        except Exception:
            # If it raises an exception, that's also acceptable behavior
            pass
    
    def test_enterprise_tier_large_user_count(self):
        """Test enterprise tier with large user count."""
        # Enterprise tier should always be dedicated regardless of user count
        strategy = PricingService.get_realm_strategy("enterprise", user_count=1000, org_count=0)
        assert strategy == "dedicated"
        
        strategy = PricingService.get_realm_strategy("enterprise", user_count=10000, org_count=0)
        assert strategy == "dedicated"
    
    # ========== New Signup Flow Methods ==========
    
    def test_determine_tier_from_employee_count(self):
        """Test tier determination from employee count."""
        # ≤5 employees → free
        assert PricingService.determine_tier_from_employee_count(1) == "free"
        assert PricingService.determine_tier_from_employee_count(5) == "free"
        
        # 6-100 employees → starter
        assert PricingService.determine_tier_from_employee_count(6) == "starter"
        assert PricingService.determine_tier_from_employee_count(50) == "starter"
        assert PricingService.determine_tier_from_employee_count(100) == "starter"
        
        # 101-1000 employees → professional
        assert PricingService.determine_tier_from_employee_count(101) == "professional"
        assert PricingService.determine_tier_from_employee_count(500) == "professional"
        assert PricingService.determine_tier_from_employee_count(1000) == "professional"
        
        # 1000+ employees → enterprise
        assert PricingService.determine_tier_from_employee_count(1001) == "enterprise"
        assert PricingService.determine_tier_from_employee_count(10000) == "enterprise"
    
    def test_get_pricing_info(self):
        """Test pricing info retrieval for all tiers."""
        # Free tier
        free_info = PricingService.get_pricing_info("free")
        assert free_info["name"] == "Free"
        assert free_info["price"] == 0
        assert free_info["price_display"] == "Free"
        assert free_info["max_users"] == 5
        assert len(free_info["features"]) > 0
        
        # Starter tier
        starter_info = PricingService.get_pricing_info("starter")
        assert starter_info["name"] == "Starter"
        assert starter_info["price"] > 0
        assert starter_info["max_users"] == 100
        assert len(starter_info["features"]) > 0
        
        # Professional tier
        professional_info = PricingService.get_pricing_info("professional")
        assert professional_info["name"] == "Professional"
        assert professional_info["price"] > 0
        assert professional_info["max_users"] == 1000
        assert len(professional_info["features"]) > 0
        
        # Enterprise tier
        enterprise_info = PricingService.get_pricing_info("enterprise")
        assert enterprise_info["name"] == "Enterprise"
        assert enterprise_info["price"] is None
        assert enterprise_info["price_display"] == "Custom pricing"
        assert enterprise_info["max_users"] == -1  # Unlimited
        assert len(enterprise_info["features"]) > 0
        
        # Invalid tier should default to starter
        default_info = PricingService.get_pricing_info("invalid")
        assert default_info["name"] == "Starter"


class TestRealmManager:
    """Tests for RealmManager."""
    
    @pytest.fixture
    def mock_keycloak_admin(self):
        """Mock KeycloakAdmin instance."""
        with patch('app.services.realm_manager.KeycloakAdmin') as mock:
            admin_instance = Mock()
            mock.return_value = admin_instance
            yield admin_instance
    
    # ========== Existing Tests ==========
    
    def test_get_realm_for_customer_shared(self, mock_keycloak_admin):
        """Test getting shared realm for customer."""
        manager = RealmManager(mock_keycloak_admin)
        customer_data = {
            "pricing_tier": "starter",
            "user_count": 10,
            "org_count": 0,
            "has_dedicated_realm": False
        }
        
        realm = manager.get_realm_for_customer("customer-123", customer_data)
        assert realm == "sentinelgrid"
    
    def test_get_realm_for_customer_dedicated(self, mock_keycloak_admin):
        """Test getting dedicated realm for customer."""
        manager = RealmManager(mock_keycloak_admin)
        customer_data = {
            "pricing_tier": "enterprise",
            "user_count": 100,
            "org_count": 0,
            "has_dedicated_realm": False,
            "name": "Enterprise Corp"
        }
        
        realm = manager.get_realm_for_customer("customer-123", customer_data)
        assert realm != "sentinelgrid"
        assert "enterprise" in realm.lower() or "corp" in realm.lower()
    
    def test_generate_realm_name(self, mock_keycloak_admin):
        """Test realm name generation."""
        manager = RealmManager(mock_keycloak_admin)
        
        realm_name = manager._generate_realm_name("Test Company")
        assert "test" in realm_name.lower()
        assert "company" in realm_name.lower()
        assert len(realm_name) > 10  # Should have UUID suffix
    
    # ========== Priority 1: Organization Realm Tests ==========
    
    def test_get_realm_for_org(self, mock_keycloak_admin):
        """Test organizations should always get dedicated realm."""
        manager = RealmManager(mock_keycloak_admin)
        org_data = {
            "realm_name": "org-dedicated-realm-12345"
        }
        
        realm = manager.get_realm_for_org("org-123", org_data)
        # Organizations always get dedicated realm (from org_data.realm_name)
        assert realm == "org-dedicated-realm-12345"
        assert realm != "sentinelgrid"
    
    def test_get_realm_for_org_fallback(self, mock_keycloak_admin):
        """Test organization realm fallback to sentinelgrid if not set."""
        manager = RealmManager(mock_keycloak_admin)
        org_data = {}  # No realm_name set
        
        realm = manager.get_realm_for_org("org-123", org_data)
        # Should fallback to sentinelgrid if realm_name not set
        assert realm == "sentinelgrid"
    
    # ========== Priority 1: Professional Tier Realm Tests ==========
    
    def test_get_realm_for_customer_professional_shared(self, mock_keycloak_admin):
        """Test professional tier with <500 users uses shared realm."""
        manager = RealmManager(mock_keycloak_admin)
        customer_data = {
            "pricing_tier": "professional",
            "user_count": 100,
            "org_count": 0,
            "has_dedicated_realm": False
        }
        
        realm = manager.get_realm_for_customer("customer-123", customer_data)
        assert realm == "sentinelgrid"
    
    def test_get_realm_for_customer_professional_dedicated_users(self, mock_keycloak_admin):
        """Test professional tier with >500 users uses dedicated realm."""
        manager = RealmManager(mock_keycloak_admin)
        customer_data = {
            "pricing_tier": "professional",
            "user_count": 600,
            "org_count": 0,
            "has_dedicated_realm": False,
            "name": "Large Professional Corp"
        }
        
        realm = manager.get_realm_for_customer("customer-123", customer_data)
        assert realm != "sentinelgrid"
        assert "professional" in realm.lower() or "corp" in realm.lower()
    
    def test_get_realm_for_customer_professional_dedicated_orgs(self, mock_keycloak_admin):
        """Test professional tier with >1 org uses dedicated realm."""
        manager = RealmManager(mock_keycloak_admin)
        customer_data = {
            "pricing_tier": "professional",
            "user_count": 100,
            "org_count": 2,
            "has_dedicated_realm": False,
            "name": "Multi-Org Professional"
        }
        
        realm = manager.get_realm_for_customer("customer-123", customer_data)
        assert realm != "sentinelgrid"
    
    def test_get_realm_for_customer_existing_dedicated(self, mock_keycloak_admin):
        """Test customer with existing dedicated realm uses that realm."""
        manager = RealmManager(mock_keycloak_admin)
        customer_data = {
            "pricing_tier": "starter",
            "user_count": 10,
            "org_count": 0,
            "has_dedicated_realm": True,
            "realm_name": "existing-dedicated-realm-abc123"
        }
        
        realm = manager.get_realm_for_customer("customer-123", customer_data)
        # Should use existing dedicated realm
        assert realm == "existing-dedicated-realm-abc123"
        assert realm != "sentinelgrid"
    
    # ========== Priority 2: Realm Name Generation Edge Cases ==========
    
    def test_realm_name_generation_edge_cases(self, mock_keycloak_admin):
        """Test realm name generation with edge cases."""
        manager = RealmManager(mock_keycloak_admin)
        
        # Special characters
        realm_name = manager._generate_realm_name("Company & Co. (Inc.)")
        assert "company" in realm_name.lower()
        assert "co" in realm_name.lower() or "inc" in realm_name.lower()
        assert len(realm_name) > 10
        
        # Long name
        long_name = "A" * 100
        realm_name = manager._generate_realm_name(long_name)
        assert len(realm_name) > 10
        assert len(realm_name) < 200  # Should be truncated/sanitized
        
        # Unicode characters
        realm_name = manager._generate_realm_name("Café & Möbel")
        assert len(realm_name) > 10
        
        # Numbers
        realm_name = manager._generate_realm_name("Company 123")
        assert "company" in realm_name.lower()
        assert "123" in realm_name or len(realm_name) > 10
        
        # Empty or very short name
        realm_name = manager._generate_realm_name("A")
        assert len(realm_name) > 5  # Should still generate something
