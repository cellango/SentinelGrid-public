"""
Unit tests for RealmCreationService.

Tests the core realm creation logic, including:
- User Profile configuration
- Naming convention enforcement
- Standard client/role/mapper creation
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from keycloak.exceptions import KeycloakError

# Import path setup
import sys
from pathlib import Path
backend_agents_path = Path(__file__).parent.parent.parent.parent / "agents" / "iam_agent"
if str(backend_agents_path) not in sys.path:
    sys.path.insert(0, str(backend_agents_path))
backend_libs_path = Path(__file__).parent.parent.parent.parent / "libs"
if str(backend_libs_path) not in sys.path:
    sys.path.insert(0, str(backend_libs_path))

from app.services.realm_creation_service import (
    RealmCreationService,
    RealmType,
    RealmCreationError,
    RealmNamingError
)


@pytest.fixture
def mock_keycloak_admin():
    """Create a mock KeycloakAdmin instance."""
    admin = Mock()
    admin.realm_name = "master"
    admin.get_realm = Mock(side_effect=KeycloakError("Realm not found", 404))
    admin.create_realm = Mock()
    admin.get_clients = Mock(return_value=[])
    admin.create_client = Mock()
    admin.create_realm_role = Mock()
    admin.get_mappers_from_client = Mock(return_value=[])
    admin.add_mapper_to_client = Mock()
    return admin


@pytest.fixture
def realm_creation_service(mock_keycloak_admin):
    """Create a RealmCreationService instance with mocked KeycloakAdmin."""
    with patch('app.services.realm_creation_service.settings') as mock_settings:
        mock_settings.KEYCLOAK_URL = "http://keycloak:8080"
        service = RealmCreationService(mock_keycloak_admin)
        # Provide a stable server_url used by user profile configurator
        mock_keycloak_admin.connection = Mock()
        mock_keycloak_admin.connection.server_url = mock_settings.KEYCLOAK_URL
        return service


class TestNamingConventionEnforcement:
    """Test naming convention enforcement."""
    
    def test_platform_admin_valid_name(self, realm_creation_service, mock_keycloak_admin):
        """Test valid platform admin realm name."""
        # Should not raise exception
        realm_creation_service._validate_realm_name(
            "sg-admin",
            RealmType.PLATFORM_ADMIN
        )
    
    def test_platform_admin_invalid_name(self, realm_creation_service):
        """Test invalid platform admin realm name."""
        with pytest.raises(RealmNamingError, match="must be named 'sg-admin'"):
            realm_creation_service._validate_realm_name(
                "invalid-name",
                RealmType.PLATFORM_ADMIN
            )
    
    def test_multi_tenant_valid_name(self, realm_creation_service):
        """Test valid multi-tenant realm name."""
        realm_creation_service._validate_realm_name(
            "sg-mt-us-1",
            RealmType.MULTI_TENANT,
            region="us",
            shard_number=1
        )
    
    def test_multi_tenant_invalid_name(self, realm_creation_service):
        """Test invalid multi-tenant realm name."""
        with pytest.raises(RealmNamingError):
            realm_creation_service._validate_realm_name(
                "sg-mt-us-1",
                RealmType.MULTI_TENANT,
                region="eu",  # Mismatch
                shard_number=1
            )
    
    def test_multi_tenant_missing_region(self, realm_creation_service):
        """Test multi-tenant realm without region."""
        with pytest.raises(RealmNamingError, match="requires region"):
            realm_creation_service._validate_realm_name(
                "sg-mt-us-1",
                RealmType.MULTI_TENANT
            )
    
    def test_dedicated_customer_valid_name(self, realm_creation_service):
        """Test valid dedicated customer realm name."""
        realm_creation_service._validate_realm_name(
            "agribotsai",
            RealmType.DEDICATED_CUSTOMER,
            customer_slug="agribotsai"
        )
    
    def test_dedicated_customer_invalid_slug(self, realm_creation_service):
        """Test invalid customer slug."""
        with pytest.raises(RealmNamingError):
            realm_creation_service._validate_realm_name(
                "Invalid-Slug!",
                RealmType.DEDICATED_CUSTOMER,
                customer_slug="Invalid-Slug!"
            )
    
    def test_demo_valid_name(self, realm_creation_service):
        """Test valid demo realm name."""
        realm_creation_service._validate_realm_name(
            "demo",
            RealmType.DEMO
        )
    
    def test_demo_invalid_name(self, realm_creation_service):
        """Test invalid demo realm name."""
        with pytest.raises(RealmNamingError, match="must be named 'demo'"):
            realm_creation_service._validate_realm_name(
                "not-demo",
                RealmType.DEMO
            )


class TestRealmCreation:
    """Test realm creation flow."""
    
    @patch('app.services.realm_creation_service.configure_realm_user_profile')
    def test_create_realm_success(self, mock_configure_profile, realm_creation_service, mock_keycloak_admin):
        """Test successful realm creation."""
        mock_configure_profile.return_value = True
        # first call -> not found, second call -> exists
        mock_keycloak_admin.get_realm.side_effect = [KeycloakError("Realm not found", 404), {"id": "realm-123"}]
        mock_keycloak_admin.create_realm.return_value = None

        result = realm_creation_service.create_realm(
            realm_name="sg-mt-us-1",
            realm_type=RealmType.MULTI_TENANT,
            region="us",
            shard_number=1
        )
        
        assert result["realm_name"] == "sg-mt-us-1"
        assert result["status"] == "created"
        assert result["user_profile_configured"] is True
        mock_keycloak_admin.create_realm.assert_called_once()
        mock_configure_profile.assert_called_once()
    
    @patch('app.services.realm_creation_service.configure_realm_user_profile')
    def test_create_realm_already_exists(self, mock_configure_profile, realm_creation_service, mock_keycloak_admin):
        """Test realm creation when realm already exists."""
        mock_configure_profile.return_value = True
        mock_keycloak_admin.get_realm.side_effect = None
        mock_keycloak_admin.get_realm.return_value = {"id": "realm-123"}
        
        result = realm_creation_service.create_realm(
            realm_name="sg-mt-us-1",
            realm_type=RealmType.MULTI_TENANT,
            region="us",
            shard_number=1
        )
        
        assert result["status"] == "exists"
        assert result["user_profile_configured"] is True
        mock_keycloak_admin.create_realm.assert_not_called()
        mock_configure_profile.assert_called_once()
    
    @patch('app.services.realm_creation_service.configure_realm_user_profile')
    def test_create_realm_user_profile_fails(self, mock_configure_profile, realm_creation_service, mock_keycloak_admin):
        """Test realm creation when User Profile configuration fails."""
        mock_configure_profile.return_value = False
        mock_keycloak_admin.get_realm.side_effect = [KeycloakError("Realm not found", 404), {"id": "realm-123"}]
        mock_keycloak_admin.create_realm.return_value = None
        
        result = realm_creation_service.create_realm(
            realm_name="sg-mt-us-1",
            realm_type=RealmType.MULTI_TENANT,
            region="us",
            shard_number=1
        )
        
        # Realm is still created, but User Profile configuration failed
        assert result["status"] == "created"
        assert result["user_profile_configured"] is False


class TestUserProfileConfiguration:
    """Test User Profile configuration."""
    
    @patch('app.services.realm_creation_service.configure_realm_user_profile')
    def test_user_profile_configured_success(self, mock_configure, realm_creation_service):
        """Test successful User Profile configuration."""
        mock_configure.return_value = True
        
        result = realm_creation_service._configure_user_profile("sg-mt-us-1")
        
        assert result is True
        # Accept kwargs order
        mock_configure.assert_called_once()
        called_args, called_kwargs = mock_configure.call_args
        assert "sg-mt-us-1" in called_args or called_kwargs.get("realm_name") == "sg-mt-us-1"
    
    @patch('app.services.realm_creation_service.configure_realm_user_profile')
    def test_user_profile_configured_failure(self, mock_configure, realm_creation_service):
        """Test User Profile configuration failure."""
        mock_configure.return_value = False
        
        result = realm_creation_service._configure_user_profile("sg-mt-us-1")
        
        assert result is False


class TestStandardConfiguration:
    """Test standard client/role/mapper creation."""
    
    def test_create_standard_clients(self, realm_creation_service, mock_keycloak_admin):
        """Test standard client creation."""
        mock_keycloak_admin.get_clients.return_value = []
        
        realm_creation_service._create_standard_clients("sg-mt-us-1", RealmType.MULTI_TENANT)
        
        # Should create web, api, and iam-agent clients
        assert mock_keycloak_admin.create_client.call_count == 3
    
    def test_create_standard_roles(self, realm_creation_service, mock_keycloak_admin):
        """Test standard role creation."""
        realm_creation_service._create_standard_roles("sg-mt-us-1")
        
        # Should create 4 standard roles
        assert mock_keycloak_admin.create_realm_role.call_count == 4
    
    def test_create_protocol_mappers(self, realm_creation_service, mock_keycloak_admin):
        """Test protocol mapper creation."""
        # Mock API client
        mock_keycloak_admin.get_clients.return_value = [
            {"clientId": "sg-mt-us-1-api", "id": "client-123"}
        ]
        mock_keycloak_admin.get_mappers_from_client.return_value = []
        
        realm_creation_service._create_protocol_mappers("sg-mt-us-1")
        
        mock_keycloak_admin.add_mapper_to_client.assert_called_once()


class TestErrorHandling:
    """Test error handling."""
    
    def test_realm_creation_error(self, realm_creation_service, mock_keycloak_admin):
        """Test handling of realm creation errors."""
        mock_keycloak_admin.get_realm.side_effect = KeycloakError("Realm not found", 404)
        mock_keycloak_admin.create_realm.side_effect = KeycloakError("Internal error", 500)
        
        with pytest.raises(RealmCreationError):
            realm_creation_service.create_realm(
                realm_name="sg-mt-us-1",
                realm_type=RealmType.MULTI_TENANT,
                region="us",
                shard_number=1
            )
    
    def test_naming_error(self, realm_creation_service):
        """Test naming convention error."""
        with pytest.raises(RealmNamingError):
            realm_creation_service.create_realm(
                realm_name="invalid-name",
                realm_type=RealmType.MULTI_TENANT,
                region="us",
                shard_number=1
            )
