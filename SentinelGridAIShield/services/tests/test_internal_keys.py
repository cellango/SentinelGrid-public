from fastapi.testclient import TestClient

from tests.constants import TEST_ORG_ID


def test_internal_key_fetch_requires_token(client: TestClient):
    response = client.get(f"/internal/provider-keys/{TEST_ORG_ID}/openai")
    assert response.status_code == 403


def test_internal_key_fetch_reads_env(monkeypatch, client: TestClient):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-openai-key-1234567890")
    response = client.get(
        f"/internal/provider-keys/{TEST_ORG_ID}/openai",
        headers={"Authorization": "Bearer internal-service-token-change-in-production"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["key"] == "sk-test-openai-key-1234567890"
    assert len(data["key_fingerprint"]) == 16
