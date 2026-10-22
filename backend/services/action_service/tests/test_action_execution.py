"""Legacy callers cannot bypass durable authority or obtain placeholder success."""

import pytest
from fastapi import HTTPException
from app.services.action_executor import ActionExecutor


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "kind",
    [
        "iam_disable_user",
        "iam_reset_password",
        "iam_revoke_sessions",
        "endpoint_quarantine",
        "endpoint_isolate",
        "network_block_ip",
        "network_add_firewall_rule",
        "email_quarantine",
        "cloud_stop_instance",
        "unknown",
    ],
)
@pytest.mark.parametrize("approval", [False, True, None])
async def test_legacy_execution_is_unavailable_even_with_approval_override(
    kind, approval
):
    with pytest.raises(HTTPException) as denied:
        await ActionExecutor().execute_action(
            action_type=kind,
            action_params={},
            tenant_id="11111111-1111-4111-8111-111111111111",
            requires_approval=approval,
        )
    assert denied.value.status_code == 503


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method",
    [
        "_execute_iam_action",
        "_execute_endpoint_action",
        "_execute_network_action",
        "_execute_email_action",
        "_execute_cloud_action",
        "_update_ticket_with_action",
    ],
)
async def test_direct_legacy_helpers_cannot_bypass_boundary(method):
    with pytest.raises(HTTPException) as denied:
        await getattr(ActionExecutor(), method)()
    assert denied.value.status_code == 503


def test_legacy_http_rejects_anonymous_bypass_and_bounds_body():
    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app) as client:
        path = "/api/v1/actions/execute?tenant_id=11111111-1111-4111-8111-111111111111"
        response = client.post(
            path,
            json={
                "action_type": "iam_disable_user",
                "action_params": {},
                "requires_approval": False,
            },
        )
        assert response.status_code == 401
        assert client.post(path, content=b"x" * 32769).status_code == 413
        assert client.get("/health").status_code == 200
