"""Unit tests for onboarding ticketing assignee lookup helpers."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import onboarding


def test_normalize_ticketing_lookup_config_prefers_draft_values():
    stored = {
        "provider": "jira",
        "url": "https://stored.atlassian.net",
        "project": "OLD",
        "api_key": "Bearer stored-token",
        "assignee_identifier_type": "username",
    }
    request = onboarding.TicketingAssigneeLookupRequest(
        query="alice",
        provider="jira",
        url="https://draft.atlassian.net",
        project="SECOPS",
        api_key="Bearer draft-token",
        assignee_identifier_type="account_id",
        limit=5,
    )

    config = onboarding._normalize_ticketing_lookup_config(stored, request)

    assert config["provider"] == "jira"
    assert config["url"] == "https://draft.atlassian.net"
    assert config["project"] == "SECOPS"
    assert config["api_key"] == "Bearer draft-token"
    assert config["assignee_identifier_type"] == "account_id"
    assert config["query"] == "alice"
    assert config["limit"] == 5


def test_format_jira_assignee_results_uses_requested_identifier():
    results = onboarding._format_jira_assignee_results(
        [
            {
                "displayName": "Alice Example",
                "accountId": "acct-123",
                "emailAddress": "alice@example.com",
                "name": "alice",
                "accountType": "atlassian",
            }
        ],
        "account_id",
        8,
    )

    assert results == [
        {
            "value": "acct-123",
            "label": "Alice Example",
            "description": "alice@example.com • username: alice • atlassian",
            "identifier_type": "account_id",
            "identifiers": {
                "account_id": "acct-123",
                "email": "alice@example.com",
                "username": "alice",
            },
        }
    ]


def test_format_servicenow_assignee_results_uses_requested_identifier():
    results = onboarding._format_servicenow_assignee_results(
        [
            {
                "sys_id": "6816f79cc0a8016401c5a33be04be441",
                "name": "Alice Example",
                "user_name": "alice.secops",
                "email": "alice@example.com",
                "active": True,
            }
        ],
        "username",
        8,
    )

    assert results == [
        {
            "value": "alice.secops",
            "label": "Alice Example",
            "description": "alice@example.com • active",
            "identifier_type": "username",
            "identifiers": {
                "sys_id": "6816f79cc0a8016401c5a33be04be441",
                "username": "alice.secops",
                "email": "alice@example.com",
            },
        }
    ]


class _FakeResponse:
    def __init__(self, status_code, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self):
        return self._payload


class _FakeDb:
    def __init__(self, stored_config):
        self.stored_config = stored_config

    def execute(self, _statement, _params=None):
        class _Result:
            def mappings(self_inner):
                return self_inner

            def fetchone(self_inner):
                return {"ticketing_config": self.stored_config}

        return _Result()


def _build_client(fake_db):
    app = FastAPI()
    app.include_router(onboarding.router)
    app.dependency_overrides[onboarding.get_db] = lambda: fake_db
    app.dependency_overrides[onboarding.get_tenant_session] = lambda: fake_db
    app.dependency_overrides[onboarding.get_onboarding_customer_id] = lambda: "tenant-123"
    return TestClient(app)


@pytest.mark.asyncio
async def test_lookup_ticketing_assignees_queries_jira_assignable_search(monkeypatch):
    calls = []

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url, headers=None, params=None):
            calls.append({"url": url, "headers": headers, "params": params})
            return _FakeResponse(
                200,
                [
                    {
                        "displayName": "Alice Example",
                        "accountId": "acct-123",
                        "emailAddress": "alice@example.com",
                        "name": "alice",
                    }
                ],
            )

    monkeypatch.setattr(onboarding.httpx, "AsyncClient", FakeAsyncClient)

    results = await onboarding._lookup_ticketing_assignees(
        {
            "provider": "jira",
            "url": "https://example.atlassian.net",
            "project": "SECOPS",
            "api_key": "Bearer jira-token",
            "assignee_identifier_type": "account_id",
            "query": "alice",
            "limit": 5,
        }
    )

    assert calls
    assert calls[0]["url"].endswith("/rest/api/3/user/assignable/search")
    assert calls[0]["params"]["project"] == "SECOPS"
    assert calls[0]["params"]["query"] == "alice"
    assert results[0]["value"] == "acct-123"


@pytest.mark.asyncio
async def test_lookup_ticketing_assignees_queries_servicenow_directory(monkeypatch):
    calls = []

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url, headers=None, params=None):
            calls.append({"url": url, "headers": headers, "params": params})
            return _FakeResponse(
                200,
                {
                    "result": [
                        {
                            "sys_id": "6816f79cc0a8016401c5a33be04be441",
                            "name": "Alice Example",
                            "user_name": "alice.secops",
                            "email": "alice@example.com",
                            "active": True,
                        }
                    ]
                },
            )

    monkeypatch.setattr(onboarding.httpx, "AsyncClient", FakeAsyncClient)

    results = await onboarding._lookup_ticketing_assignees(
        {
            "provider": "servicenow",
            "url": "https://example.service-now.com",
            "api_key": "Bearer sn-token",
            "assignee_identifier_type": "sys_id",
            "query": "alice",
            "limit": 5,
        }
    )

    assert calls
    assert calls[0]["url"].endswith("/api/now/table/sys_user")
    assert "user_nameLIKEalice" in calls[0]["params"]["sysparm_query"]
    assert results[0]["value"] == "6816f79cc0a8016401c5a33be04be441"


def test_search_ticketing_assignees_uses_stored_config_when_request_is_minimal(monkeypatch):
    client = _build_client(
        _FakeDb(
            stored_config={
                "provider": "jira",
                "url": "https://stored.atlassian.net",
                "project": "SECOPS",
                "api_key": "Bearer stored-token",
                "assignee_identifier_type": "account_id",
            }
        )
    )

    async def _fake_lookup(_config):
        return [
            {
                "value": "acct-123",
                "label": "Alice Example",
                "description": "alice@example.com",
                "identifier_type": "account_id",
                "identifiers": {"account_id": "acct-123"},
            }
        ]

    monkeypatch.setattr(onboarding, "_resolve_progress_key", lambda customer_id, db: customer_id)
    monkeypatch.setattr(onboarding, "_lookup_ticketing_assignees", _fake_lookup)

    response = client.post(
        "/api/v1/onboarding/ticketing-assignees/search",
        headers={"X-Tenant-ID": "tenant-123"},
        json={"query": "alice"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "provider": "jira",
        "assigneeIdentifierType": "account_id",
        "source": "stored_config",
        "results": [
            {
                "value": "acct-123",
                "label": "Alice Example",
                "description": "alice@example.com",
                "identifierType": "account_id",
                "identifiers": {"account_id": "acct-123"},
            }
        ],
    }
