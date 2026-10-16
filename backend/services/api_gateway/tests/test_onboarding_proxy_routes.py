import json

import httpx

from app.api import routes_onboarding
from sg_core.service_metrics import reset_service_metrics


def test_onboarding_status_proxy_forwards_auth_and_tenant_headers(
    client,
    proxy_async_client_factory,
    proxy_response_factory,
    tenant_header_matrix,
):
    calls = proxy_async_client_factory(
        routes_onboarding,
        responses=[
            proxy_response_factory(
                payload={"next_step": "cloud", "status_version": "ver-123"},
            )
        ],
    )

    response = client.get(
        "/api/v1/onboarding/status",
        headers={
            **tenant_header_matrix,
            "authorization": "Bearer gateway-token",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"next_step": "cloud", "status_version": "ver-123"}
    assert calls[0]["method"] == "GET"
    assert calls[0]["headers"]["X-Tenant-ID"] == "tenant-123"
    assert calls[0]["headers"]["Authorization"] == "Bearer gateway-token"


def test_onboarding_status_proxy_ignores_spoofed_tenant_header(
    client,
    proxy_async_client_factory,
    proxy_response_factory,
):
    calls = proxy_async_client_factory(
        routes_onboarding,
        responses=[proxy_response_factory(payload={"next_step": "cloud"})],
    )

    response = client.get(
        "/api/v1/onboarding/status",
        headers={
            "x-tenant-id": "foreign-tenant",
            "authorization": "Bearer gateway-token",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"next_step": "cloud"}
    assert calls[0]["headers"]["X-Tenant-ID"] == "tenant-123"
    assert calls[0]["headers"]["Authorization"] == "Bearer gateway-token"


def test_connect_ticketing_proxy_preserves_payload_and_headers(
    client,
    proxy_async_client_factory,
    proxy_response_factory,
    tenant_header_matrix,
):
    calls = proxy_async_client_factory(
        routes_onboarding,
        responses=[
            proxy_response_factory(
                payload={
                    "success": True,
                    "status": "healthy",
                    "health": {"status": "healthy", "provider": "jira"},
                }
            )
        ],
    )

    payload = {
        "provider": "jira",
        "url": "https://example.atlassian.net",
        "project": "SECOPS",
        "api_key": "Bearer jira-token",
        "assignment_mode": "named_owner",
        "default_assignee": "acct-123",
        "assignee_identifier_type": "account_id",
    }

    response = client.post(
        "/api/v1/onboarding/connect-ticketing",
        json=payload,
        headers={
            **tenant_header_matrix,
            "authorization": "Bearer gateway-token",
        },
    )

    assert response.status_code == 200
    assert response.json()["health"]["provider"] == "jira"
    assert calls[0]["method"] == "POST"
    assert calls[0]["headers"]["X-Tenant-ID"] == "tenant-123"
    assert calls[0]["headers"]["Authorization"] == "Bearer gateway-token"
    assert json.loads(calls[0]["content"].decode()) == payload


def test_cloud_provider_registry_proxy_preserves_auth_and_tenant_headers(
    client,
    proxy_async_client_factory,
    proxy_response_factory,
    tenant_header_matrix,
):
    calls = proxy_async_client_factory(
        routes_onboarding,
        responses=[
            proxy_response_factory(
                payload={
                    "providers": [
                        {
                            "id": "hetzner",
                            "display_name": "Hetzner Cloud",
                            "onboarding_fields": [],
                        }
                    ]
                }
            )
        ],
    )

    response = client.get(
        "/api/v1/onboarding/cloud/providers",
        headers={
            **tenant_header_matrix,
            "authorization": "Bearer gateway-token",
        },
    )

    assert response.status_code == 200
    assert response.json()["providers"][0]["id"] == "hetzner"
    assert calls[0]["method"] == "GET"
    assert calls[0]["url"].endswith("/api/v1/onboarding/cloud/providers")
    assert calls[0]["headers"]["X-Tenant-ID"] == "tenant-123"
    assert calls[0]["headers"]["Authorization"] == "Bearer gateway-token"


def test_connect_cloud_proxy_preserves_payload_and_headers(
    client,
    proxy_async_client_factory,
    proxy_response_factory,
    tenant_header_matrix,
):
    calls = proxy_async_client_factory(
        routes_onboarding,
        responses=[
            proxy_response_factory(
                payload={
                    "success": True,
                    "status": "connected",
                    "health": {"status": "healthy", "provider": "hetzner"},
                }
            )
        ],
    )

    payload = {
        "tenant_id": "tenant-123",
        "cloud_provider": "hetzner",
        "config": {
            "server_id": "123456789",
            "server_name": "websites-prod",
            "firewall_id": "98765432",
            "api_token": "hcloud-token",
        },
    }

    response = client.post(
        "/api/v1/onboarding/connect-cloud",
        json=payload,
        headers={
            **tenant_header_matrix,
            "authorization": "Bearer gateway-token",
        },
    )

    assert response.status_code == 200
    assert response.json()["health"]["provider"] == "hetzner"
    assert calls[0]["method"] == "POST"
    assert calls[0]["url"].endswith("/api/v1/onboarding/connect-cloud")
    assert calls[0]["headers"]["X-Tenant-ID"] == "tenant-123"
    assert calls[0]["headers"]["Authorization"] == "Bearer gateway-token"
    assert json.loads(calls[0]["content"].decode()) == payload


def test_infrastructure_change_request_approval_proxy_preserves_path_and_payload(
    client,
    proxy_async_client_factory,
    proxy_response_factory,
):
    calls = proxy_async_client_factory(
        routes_onboarding,
        responses=[proxy_response_factory(payload={"success": True, "status": "approved"})],
    )

    payload = {
        "provider": "hetzner",
        "inputs": {"admin_ssh_cidrs": ["203.0.113.10/32"]},
        "notes": "pilot approval",
    }
    response = client.post(
        "/api/v1/onboarding/cloud/change-requests/cr-123/approve",
        json=payload,
        headers={"authorization": "Bearer gateway-token"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "approved"
    assert calls[0]["url"].endswith("/api/v1/onboarding/cloud/change-requests/cr-123/approve")
    assert calls[0]["headers"]["X-Tenant-ID"] == "tenant-123"
    assert calls[0]["headers"]["Authorization"] == "Bearer gateway-token"
    assert json.loads(calls[0]["content"].decode()) == payload


def test_infrastructure_change_request_apply_proxy_preserves_path_and_payload(
    client,
    proxy_async_client_factory,
    proxy_response_factory,
):
    calls = proxy_async_client_factory(
        routes_onboarding,
        responses=[proxy_response_factory(payload={"success": True, "status": "applied"})],
    )

    payload = {"provider": "hetzner", "confirm": True}
    response = client.post(
        "/api/v1/onboarding/cloud/change-requests/cr-123/apply",
        json=payload,
        headers={"authorization": "Bearer gateway-token"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "applied"
    assert calls[0]["url"].endswith("/api/v1/onboarding/cloud/change-requests/cr-123/apply")
    assert calls[0]["headers"]["X-Tenant-ID"] == "tenant-123"
    assert calls[0]["headers"]["Authorization"] == "Bearer gateway-token"
    assert json.loads(calls[0]["content"].decode()) == payload


def test_connect_ticketing_proxy_ignores_spoofed_tenant_header(
    client,
    proxy_async_client_factory,
    proxy_response_factory,
):
    calls = proxy_async_client_factory(
        routes_onboarding,
        responses=[proxy_response_factory(payload={"success": True})],
    )

    response = client.post(
        "/api/v1/onboarding/connect-ticketing",
        json={"provider": "jira"},
        headers={
            "x-tenant-id": "foreign-tenant",
            "authorization": "Bearer gateway-token",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"success": True}
    assert calls[0]["headers"]["X-Tenant-ID"] == "tenant-123"



def test_recheck_health_proxy_returns_structured_health_payload(
    client,
    proxy_async_client_factory,
    proxy_response_factory,
):
    proxy_async_client_factory(
        routes_onboarding,
        responses=[
            proxy_response_factory(
                payload={
                    "success": True,
                    "health": {
                        "status": "degraded",
                        "provider": "ticketing",
                        "warnings": ["Named owner routing requires a default assignee."],
                    },
                }
            )
        ],
    )

    response = client.post(
        "/api/v1/onboarding/recheck-health",
        json={"target": "ticketing"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "health": {
            "status": "degraded",
            "provider": "ticketing",
            "warnings": ["Named owner routing requires a default assignee."],
        },
    }


def test_complete_proxy_returns_success_when_scan_enqueue_fails(
    client,
    proxy_async_client_factory,
    proxy_response_factory,
    tenant_header_matrix,
):
    calls = proxy_async_client_factory(
        routes_onboarding,
        responses=[
            proxy_response_factory(payload={"success": True, "status": "completed"}),
            httpx.ConnectError("orchestrator unavailable"),
        ],
    )

    response = client.post(
        "/api/v1/onboarding/complete",
        headers={
            **tenant_header_matrix,
            "authorization": "Bearer gateway-token",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"success": True, "status": "completed"}
    assert len(calls) == 2
    assert calls[0]["url"].endswith("/api/v1/onboarding/complete")
    assert str(calls[1]["url"]).endswith("/api/v1/orchestrator/scans")
    assert calls[1]["json"] == {
        "scanner_id": "baseline",
        "target_ref": "onboarding",
    }


def test_complete_proxy_ignores_spoofed_tenant_header_for_iam_and_scan_enqueue(
    client,
    proxy_async_client_factory,
    proxy_response_factory,
):
    calls = proxy_async_client_factory(
        routes_onboarding,
        responses=[
            proxy_response_factory(payload={"success": True, "status": "completed"}),
            proxy_response_factory(payload={"queued": True}),
        ],
    )

    response = client.post(
        "/api/v1/onboarding/complete",
        headers={
            "x-tenant-id": "foreign-tenant",
            "authorization": "Bearer gateway-token",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"success": True, "status": "completed"}
    assert len(calls) == 2
    assert calls[0]["headers"]["X-Tenant-ID"] == "tenant-123"
    assert calls[0]["headers"]["Authorization"] == "Bearer gateway-token"
    assert calls[1]["headers"]["X-Tenant-ID"] == "tenant-123"
    assert calls[1]["headers"]["Authorization"] == "Bearer gateway-token"


def test_onboarding_status_records_proxy_success_metrics(
    client,
    proxy_async_client_factory,
    proxy_response_factory,
):
    reset_service_metrics("api-gateway")
    proxy_async_client_factory(
        routes_onboarding,
        responses=[proxy_response_factory(payload={"next_step": "cloud"})],
    )

    response = client.get("/api/v1/onboarding/status")
    metrics_response = client.get("/metrics")

    assert response.status_code == 200
    assert metrics_response.status_code == 200
    payload = metrics_response.json()
    assert payload["counters"]["gateway_proxy_requests_total"]["series"][
        "outcome=success,route=onboarding_status,upstream=iam_agent"
    ] == 1


def test_connect_ticketing_records_upstream_error_metrics(
    client,
    proxy_async_client_factory,
    proxy_response_factory,
):
    reset_service_metrics("api-gateway")
    proxy_async_client_factory(
        routes_onboarding,
        responses=[proxy_response_factory(status_code=503, payload={"detail": "unavailable"})],
    )

    response = client.post(
        "/api/v1/onboarding/connect-ticketing",
        json={"provider": "jira"},
    )
    metrics_response = client.get("/metrics")

    assert response.status_code == 503
    assert metrics_response.status_code == 200
    payload = metrics_response.json()
    assert payload["counters"]["gateway_proxy_requests_total"]["series"][
        "outcome=upstream_error,route=onboarding_connect_ticketing,upstream=iam_agent"
    ] == 1


def test_complete_proxy_records_initial_scan_enqueue_connect_error_metrics(
    client,
    proxy_async_client_factory,
    proxy_response_factory,
):
    reset_service_metrics("api-gateway")
    proxy_async_client_factory(
        routes_onboarding,
        responses=[
            proxy_response_factory(payload={"success": True, "status": "completed"}),
            httpx.ConnectError("orchestrator unavailable"),
        ],
    )

    response = client.post("/api/v1/onboarding/complete")
    metrics_response = client.get("/metrics")

    assert response.status_code == 200
    assert metrics_response.status_code == 200
    payload = metrics_response.json()
    assert payload["counters"]["gateway_proxy_requests_total"]["series"][
        "outcome=success,route=onboarding_complete,upstream=iam_agent"
    ] == 1
    assert payload["counters"]["gateway_proxy_requests_total"]["series"][
        "outcome=connect_error,route=onboarding_complete_initial_scan_enqueue,upstream=orchestrator"
    ] == 1
