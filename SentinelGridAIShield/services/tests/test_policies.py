import pytest
from fastapi.testclient import TestClient

from tests.constants import TEST_ORG_ID


def test_create_policy(db_client: TestClient, internal_headers: dict[str, str]):
    """Test creating a policy"""
    response = db_client.post(
        "/api/v1/ai-policies",
        headers=internal_headers,
        json={
            "org_id": TEST_ORG_ID,
            "block_pii_outbound": True,
            "block_secrets_outbound": True,
            "block_external_llms": False,
            "block_jailbreak_patterns": True,
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["block_pii_outbound"] == True
    assert data["block_secrets_outbound"] == True

def test_list_policies(db_client: TestClient, internal_headers: dict[str, str]):
    """Test listing policies"""
    # Create a policy first
    db_client.post(
        "/api/v1/ai-policies",
        headers=internal_headers,
        json={
            "org_id": TEST_ORG_ID,
            "block_pii_outbound": False,
        }
    )
    
    # List policies
    response = db_client.get(f"/api/v1/ai-policies?org_id={TEST_ORG_ID}", headers=internal_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1

def test_update_policy(db_client: TestClient, internal_headers: dict[str, str]):
    """Test updating a policy"""
    # Create policy
    create_response = db_client.post(
        "/api/v1/ai-policies",
        headers=internal_headers,
        json={
            "org_id": TEST_ORG_ID,
            "block_pii_outbound": False,
        }
    )
    policy_id = create_response.json()["id"]
    
    # Update policy
    response = db_client.put(
        f"/api/v1/ai-policies/{policy_id}",
        headers=internal_headers,
        json={"block_pii_outbound": True}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["block_pii_outbound"] == True
