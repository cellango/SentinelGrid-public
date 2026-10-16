import pytest
from fastapi.testclient import TestClient

from tests.constants import TEST_APP_ID, TEST_ORG_ID


def test_ingest_event(db_client: TestClient, internal_headers: dict[str, str]):
    """Test ingesting telemetry event"""
    response = db_client.post(
        "/api/v1/telemetry/events",
        headers=internal_headers,
        json={
            "org_id": TEST_ORG_ID,
            "ai_app_id": TEST_APP_ID,
            "user_id": "user-123",
            "provider": "openai",
            "model": "gpt-4",
            "has_pii": False,
            "has_secrets": False,
            "prompt_injection_suspected": False,
            "policy_decision": "allowed",
            "tokens_in": 10,
            "tokens_out": 20,
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ingested"

def test_ingest_tool_call(db_client: TestClient, internal_headers: dict[str, str]):
    """Test ingesting tool call"""
    response = db_client.post(
        "/api/v1/telemetry/tool-calls",
        headers=internal_headers,
        json={
            "org_id": TEST_ORG_ID,
            "ai_app_id": TEST_APP_ID,
            "tool_name": "aws.ec2.stop",
            "allowed": False,
            "policy_violated": True,
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ingested"
