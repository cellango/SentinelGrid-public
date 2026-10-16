import pytest
from fastapi.testclient import TestClient

from tests.constants import TEST_ORG_ID


def test_create_ai_app(db_client: TestClient, internal_headers: dict[str, str]):
    """Test creating an AI app"""
    response = db_client.post(
        "/api/v1/ai-apps",
        headers=internal_headers,
        json={
            "org_id": TEST_ORG_ID,
            "name": "TestApp",
            "environment": "dev",
            "description": "Test application",
            "allowed_models": ["gpt-4"],
            "allow_external_providers": True,
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "TestApp"
    assert data["environment"] == "dev"
    assert "api_key" in data
    assert data["api_key"].startswith("sg-ai-")

def test_list_ai_apps(db_client: TestClient, internal_headers: dict[str, str]):
    """Test listing AI apps"""
    # Create an app first
    db_client.post(
        "/api/v1/ai-apps",
        headers=internal_headers,
        json={
            "org_id": TEST_ORG_ID,
            "name": "App1",
            "environment": "dev",
        }
    )
    
    # List apps
    response = db_client.get(f"/api/v1/ai-apps?org_id={TEST_ORG_ID}", headers=internal_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["name"] == "App1"

def test_get_ai_app(db_client: TestClient, internal_headers: dict[str, str]):
    """Test getting a specific AI app"""
    # Create app
    create_response = db_client.post(
        "/api/v1/ai-apps",
        headers=internal_headers,
        json={
            "org_id": TEST_ORG_ID,
            "name": "GetTest",
            "environment": "dev",
        }
    )
    app_id = create_response.json()["id"]
    
    # Get app
    response = db_client.get(f"/api/v1/ai-apps/{app_id}", headers=internal_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "GetTest"

def test_update_ai_app(db_client: TestClient, internal_headers: dict[str, str]):
    """Test updating an AI app"""
    # Create app
    create_response = db_client.post(
        "/api/v1/ai-apps",
        headers=internal_headers,
        json={
            "org_id": TEST_ORG_ID,
            "name": "UpdateTest",
            "environment": "dev",
        }
    )
    app_id = create_response.json()["id"]
    
    # Update app
    response = db_client.put(
        f"/api/v1/ai-apps/{app_id}",
        headers=internal_headers,
        json={"name": "UpdatedName"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "UpdatedName"

def test_delete_ai_app(db_client: TestClient, internal_headers: dict[str, str]):
    """Test deleting an AI app"""
    # Create app
    create_response = db_client.post(
        "/api/v1/ai-apps",
        headers=internal_headers,
        json={
            "org_id": TEST_ORG_ID,
            "name": "DeleteTest",
            "environment": "dev",
        }
    )
    app_id = create_response.json()["id"]
    
    # Delete app
    response = db_client.delete(f"/api/v1/ai-apps/{app_id}", headers=internal_headers)
    assert response.status_code == 200
    
    # Verify deleted
    response = db_client.get(f"/api/v1/ai-apps/{app_id}", headers=internal_headers)
    assert response.status_code == 404

def test_regenerate_api_key(db_client: TestClient, internal_headers: dict[str, str]):
    """Test regenerating API key"""
    # Create app
    create_response = db_client.post(
        "/api/v1/ai-apps",
        headers=internal_headers,
        json={
            "org_id": TEST_ORG_ID,
            "name": "KeyTest",
            "environment": "dev",
        }
    )
    app_id = create_response.json()["id"]
    original_key = create_response.json()["api_key"]
    
    # Regenerate key
    response = db_client.post(f"/api/v1/ai-apps/{app_id}/keys", headers=internal_headers)
    assert response.status_code == 200
    new_key = response.json()["api_key"]
    
    assert new_key != original_key
    assert new_key.startswith("sg-ai-")
