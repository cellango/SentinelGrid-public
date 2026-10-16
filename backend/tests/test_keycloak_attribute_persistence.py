"""
Test to reproduce Keycloak user attribute persistence issue.

This test documents and reproduces the problem where user attributes
set via kcadm.sh or Admin API are not persisting in Keycloak v25.0.
"""

import pytest
import subprocess
import json
import time
import httpx
import base64
import os
from typing import Dict, Any, Optional

# Test configuration
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://localhost:8081")
REALM = os.getenv("TEST_REALM", "agribotsai")
ADMIN_USER = os.getenv("KEYCLOAK_ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("KEYCLOAK_ADMIN_PASSWORD", "admin")
TEST_USERNAME = os.getenv("TEST_USERNAME", "admin@agribotsai.com")
TEST_TENANT_ID = os.getenv("TEST_TENANT_ID", "6306bd5e-0bf2-4622-b789-ba0d18ae8003")
CONTAINER_NAME = os.getenv("KEYCLOAK_CONTAINER", "sentinelgrid-keycloak-1")


def run_kcadm(command: str, realm: str = "master") -> tuple[bool, str]:
    """Run kcadm.sh command in Keycloak container."""
    auth_cmd = (
        f"/opt/keycloak/bin/kcadm.sh config credentials "
        f"--server http://localhost:8080 --realm master "
        f"--user {ADMIN_USER} --password {ADMIN_PASSWORD}"
    )
    full_cmd = f"{auth_cmd} && {command}"
    
    docker_cmd = [
        "docker", "exec", CONTAINER_NAME, "bash", "-c", full_cmd
    ]
    
    try:
        result = subprocess.run(
            docker_cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode == 0, result.stdout if result.returncode == 0 else result.stderr
    except Exception as e:
        return False, str(e)


def get_user_id(username: str, realm: str) -> Optional[str]:
    """Get user ID by username."""
    command = f"/opt/keycloak/bin/kcadm.sh get users -r {realm} -q username={username} --fields id --format csv --noquotes | tail -1"
    success, output = run_kcadm(command, realm)
    if success and output.strip():
        return output.strip()
    return None


def get_user_attributes(user_id: str, realm: str) -> Dict[str, Any]:
    """Get user attributes."""
    command = f"/opt/keycloak/bin/kcadm.sh get users/{user_id} -r {realm} --fields attributes"
    success, output = run_kcadm(command, realm)
    if success:
        try:
            data = json.loads(output)
            return data.get("attributes", {})
        except json.JSONDecodeError:
            # Sometimes returns just "{ }" as plain text
            if "{" in output and "}" in output:
                return {}
    return {}


def set_user_attribute_via_kcadm(user_id: str, realm: str, attribute_name: str, attribute_value: str, method: str = "direct") -> bool:
    """Set user attribute using different kcadm.sh methods."""
    
    if method == "direct":
        # Method 1: Direct -s flag
        command = f"/opt/keycloak/bin/kcadm.sh update users/{user_id} -r {realm} -s 'attributes.{attribute_name}=[\"{attribute_value}\"]'"
    elif method == "json_body":
        # Method 2: JSON body with -b flag
        json_body = json.dumps({"attributes": {attribute_name: [attribute_value]}})
        command = f"/opt/keycloak/bin/kcadm.sh update users/{user_id} -r {realm} -b '{json_body}'"
    elif method == "full_json":
        # Method 3: Get full user, modify, update with -f flag
        # This requires two steps
        get_cmd = f"/opt/keycloak/bin/kcadm.sh get users/{user_id} -r {realm}"
        success, user_json = run_kcadm(get_cmd, realm)
        if not success:
            return False
        
        try:
            user_data = json.loads(user_json)
            user_data.setdefault("attributes", {})
            user_data["attributes"][attribute_name] = [attribute_value]
            modified_json = json.dumps(user_data)
            
            # Write to temp file in container
            write_cmd = f"echo '{modified_json}' > /tmp/user_update.json"
            run_kcadm(write_cmd, realm)
            
            command = f"/opt/keycloak/bin/kcadm.sh update users/{user_id} -r {realm} -f /tmp/user_update.json"
        except json.JSONDecodeError:
            return False
    else:
        return False
    
    success, _ = run_kcadm(command, realm)
    return success


def get_token_and_check_claim(realm: str, username: str, password: str, client_id: str, claim_name: str) -> tuple[bool, Optional[Any]]:
    """Get token and check if claim exists."""
    token_url = f"{KEYCLOAK_URL}/realms/{realm}/protocol/openid-connect/token"
    data = {
        "client_id": client_id,
        "username": username,
        "password": password,
        "grant_type": "password",
        "scope": "openid profile email",
    }
    
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(token_url, data=data)
            if response.status_code != 200:
                return False, None
            
            token_data = response.json()
            access_token = token_data.get("access_token")
            if not access_token:
                return False, None
            
            # Decode token payload
            parts = access_token.split('.')
            if len(parts) < 2:
                return False, None
            
            payload_part = parts[1]
            payload_part += '=' * (4 - len(payload_part) % 4)
            payload = json.loads(base64.urlsafe_b64decode(payload_part).decode('utf-8'))
            
            return claim_name in payload, payload.get(claim_name)
    except Exception as e:
        print(f"Error getting token: {e}")
        return False, None


class TestKeycloakAttributePersistence:
    """Test suite to reproduce attribute persistence issue."""
    
    @pytest.fixture(autouse=True)
    def setup_user(self):
        """Ensure test user exists and is active."""
        user_id = get_user_id(TEST_USERNAME, REALM)
        if not user_id:
            pytest.skip(f"Test user {TEST_USERNAME} does not exist")
        yield user_id
        # Cleanup: Remove tenant_id attribute after test
        # (we'll test persistence, so we might want to keep it)
    
    def test_attribute_persistence_method1_direct(self, setup_user):
        """Test Method 1: Setting attribute with direct -s flag."""
        user_id = setup_user
        
        # Set attribute
        success = set_user_attribute_via_kcadm(user_id, REALM, "tenant_id", TEST_TENANT_ID, method="direct")
        assert success, "Setting attribute should succeed"
        
        # Wait a moment
        time.sleep(1)
        
        # Check if attribute persists
        attributes = get_user_attributes(user_id, REALM)
        
        # Document the issue
        if "tenant_id" not in attributes or not attributes.get("tenant_id"):
            pytest.fail(
                f"❌ ATTRIBUTE PERSISTENCE ISSUE REPRODUCED:\n"
                f"   Method: Direct -s flag\n"
                f"   Expected: tenant_id = [{TEST_TENANT_ID}]\n"
                f"   Actual: attributes = {attributes}\n"
                f"   Attribute was set but did not persist!"
            )
        
        assert attributes.get("tenant_id") == [TEST_TENANT_ID]
    
    def test_attribute_persistence_method2_json_body(self, setup_user):
        """Test Method 2: Setting attribute with JSON body -b flag."""
        user_id = setup_user
        
        # Set attribute
        success = set_user_attribute_via_kcadm(user_id, REALM, "tenant_id", TEST_TENANT_ID, method="json_body")
        assert success, "Setting attribute should succeed"
        
        time.sleep(1)
        
        # Check if attribute persists
        attributes = get_user_attributes(user_id, REALM)
        
        if "tenant_id" not in attributes or not attributes.get("tenant_id"):
            pytest.fail(
                f"❌ ATTRIBUTE PERSISTENCE ISSUE REPRODUCED:\n"
                f"   Method: JSON body -b flag\n"
                f"   Expected: tenant_id = [{TEST_TENANT_ID}]\n"
                f"   Actual: attributes = {attributes}\n"
                f"   Attribute was set but did not persist!"
            )
        
        assert attributes.get("tenant_id") == [TEST_TENANT_ID]
    
    def test_attribute_persistence_method3_full_json(self, setup_user):
        """Test Method 3: Setting attribute with full JSON -f flag."""
        user_id = setup_user
        
        # Set attribute
        success = set_user_attribute_via_kcadm(user_id, REALM, "tenant_id", TEST_TENANT_ID, method="full_json")
        assert success, "Setting attribute should succeed"
        
        time.sleep(1)
        
        # Check if attribute persists
        attributes = get_user_attributes(user_id, REALM)
        
        if "tenant_id" not in attributes or not attributes.get("tenant_id"):
            pytest.fail(
                f"❌ ATTRIBUTE PERSISTENCE ISSUE REPRODUCED:\n"
                f"   Method: Full JSON -f flag\n"
                f"   Expected: tenant_id = [{TEST_TENANT_ID}]\n"
                f"   Actual: attributes = {attributes}\n"
                f"   Attribute was set but did not persist!"
            )
        
        assert attributes.get("tenant_id") == [TEST_TENANT_ID]
    
    def test_attribute_appears_in_token(self, setup_user):
        """Test that if attribute exists, it appears in token."""
        user_id = setup_user
        
        # Try all methods
        methods = ["direct", "json_body", "full_json"]
        attribute_set = False
        
        for method in methods:
            success = set_user_attribute_via_kcadm(user_id, REALM, "tenant_id", TEST_TENANT_ID, method=method)
            if success:
                time.sleep(1)
                attributes = get_user_attributes(user_id, REALM)
                if "tenant_id" in attributes and attributes.get("tenant_id"):
                    attribute_set = True
                    break
        
        if not attribute_set:
            pytest.skip("Could not set attribute via any method - issue reproduced")
        
        # Get token and check for claim
        has_claim, claim_value = get_token_and_check_claim(
            REALM, TEST_USERNAME, "ChangeMe123!", "agribotsai-web", "tenant_id"
        )
        
        assert has_claim, f"tenant_id claim should appear in token. Value: {claim_value}"
        assert claim_value == TEST_TENANT_ID, f"tenant_id value should match. Got: {claim_value}"
    
    def test_admin_rest_api_approach(self, setup_user):
        """Test setting attribute via Admin REST API (if accessible)."""
        # This test requires Admin REST API access
        # May be blocked by HTTPS requirement
        
        # For now, document the approach
        pytest.skip("Admin REST API approach - requires HTTPS or internal network access")
    
    def test_protocol_mapper_configuration(self):
        """Verify protocol mapper is correctly configured."""
        command = (
            f"/opt/keycloak/bin/kcadm.sh get clients -r {REALM} "
            f"-q clientId=agribotsai-web --fields id --format csv --noquotes | tail -1"
        )
        success, client_id = run_kcadm(command, REALM)
        
        if not success or not client_id.strip():
            pytest.skip("Web client not found")
        
        # Check protocol mappers
        command = f"/opt/keycloak/bin/kcadm.sh get clients/{client_id.strip()}/protocol-mappers/models -r {REALM}"
        success, mappers_json = run_kcadm(command, REALM)
        
        if not success:
            pytest.fail("Could not retrieve protocol mappers")
        
        try:
            mappers = json.loads(mappers_json)
            tenant_mapper = next(
                (m for m in mappers if m.get("name") == "tenant-id-mapper"),
                None
            )
            
            assert tenant_mapper is not None, "tenant-id-mapper should exist"
            assert tenant_mapper.get("protocolMapper") == "oidc-usermodel-attribute-mapper"
            assert tenant_mapper.get("config", {}).get("user.attribute") == "tenant_id"
            assert tenant_mapper.get("config", {}).get("claim.name") == "tenant_id"
        except json.JSONDecodeError:
            pytest.fail("Could not parse protocol mappers JSON")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

