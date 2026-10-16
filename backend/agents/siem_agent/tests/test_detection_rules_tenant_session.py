"""Focused tenant-scoped DB coverage for SIEM detection rule routes."""

from contextlib import ExitStack
import sys
import types
from uuid import uuid4
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

opensearchpy_module = types.ModuleType("opensearchpy")
opensearchpy_module.OpenSearch = object
opensearchpy_module.RequestsHttpConnection = object
opensearchpy_exceptions_module = types.ModuleType("opensearchpy.exceptions")
opensearchpy_exceptions_module.OpenSearchException = Exception
sys.modules.setdefault("opensearchpy", opensearchpy_module)
sys.modules.setdefault("opensearchpy.exceptions", opensearchpy_exceptions_module)

from app.api import detection_rules as router_api


def _rule_payload(rule_id):
    return {
        "id": str(rule_id),
        "rule_key": "suspicious-login",
        "name": "Suspicious Login",
        "description": "Detect suspicious login activity",
        "category": "identity",
        "current_version": "1.0.0",
        "approval_required": False,
        "versions": [],
        "deployment": None,
        "mapping": None,
    }


@pytest.mark.parametrize(
    ("method", "path", "payload", "patches"),
    [
        (
            "post",
            "",
            {
                "rule_key": "rule-1",
                "name": "Rule 1",
                "description": "desc",
                "category": "identity",
                "approval_required": False,
                "version": {
                    "version": "1.0.0",
                    "index_pattern": "sg-tenant-auth-*",
                    "query": {"match_all": {}},
                    "trigger_condition": {"count": {"gt": 0}},
                    "severity": "high",
                },
            },
            {"app.api.detection_rules.detection_rule_service.create_rule": lambda db, payload, created_by: _rule_payload(uuid4())},
        ),
        (
            "get",
            "",
            None,
            {"app.api.detection_rules.detection_rule_service.list_rules": lambda db, tenant_id: [_rule_payload(uuid4())]},
        ),
        (
            "get",
            "/11111111-1111-1111-1111-111111111111",
            None,
            {"app.api.detection_rules.detection_rule_service.get_rule": lambda db, rule_id, tenant_id=None: _rule_payload(rule_id)},
        ),
        (
            "post",
            "/11111111-1111-1111-1111-111111111111/preview",
            {
                "index_pattern": "sg-tenant-auth-*",
                "query": {"match_all": {}},
                "trigger_condition": {"count": {"gt": 0}},
                "time_range_minutes": 60,
            },
            {
                "app.api.detection_rules.detection_rule_service.get_rule": lambda db, rule_id, tenant_id=None: _rule_payload(rule_id),
                "app.api.detection_rules.preview_rule_service": lambda tenant_id, realm, req: {
                    "hits": 1,
                    "sample": [],
                    "aggregations": {},
                },
            },
        ),
        (
            "post",
            "/11111111-1111-1111-1111-111111111111/deploy",
            {
                "destination_id": "dest-1",
                "auto_execute": False,
                "schedule_minutes": 5,
            },
            {
                "app.api.detection_rules.detection_rule_service.get_rule": lambda db, rule_id, tenant_id=None: _rule_payload(rule_id),
                "app.api.detection_rules.deploy_rule_service": lambda **kwargs: ("monitor-1", "dest-1", "approved"),
            },
        ),
        (
            "post",
            "/11111111-1111-1111-1111-111111111111/disable",
            None,
            {"app.api.detection_rules.disable_rule_service": lambda **kwargs: None},
        ),
        (
            "post",
            "/11111111-1111-1111-1111-111111111111/clone",
            {
                "name": "Cloned Rule",
                "rule_key": "cloned-rule",
                "description": "copy",
            },
            {"app.api.detection_rules.detection_rule_service.clone_rule": lambda db, rule_id, payload, created_by, tenant_id: _rule_payload(uuid4())},
        ),
        (
            "post",
            "/11111111-1111-1111-1111-111111111111/mapping",
            {
                "alert_type": "suspicious_login",
                "playbook_key": "investigate-login",
                "auto_execute": False,
                "requires_approval": True,
            },
            {
                "app.api.detection_rules.detection_rule_service.get_rule": lambda db, rule_id, tenant_id=None: _rule_payload(rule_id),
                "app.api.detection_rules.upsert_playbook_mapping": lambda **kwargs: None,
            },
        ),
        (
            "post",
            "/11111111-1111-1111-1111-111111111111/approve",
            None,
            {"app.api.detection_rules.detection_rule_service.set_rule_approval_status": lambda db, rule_id, tenant_id, approval_status: "approved"},
        ),
        (
            "post",
            "/11111111-1111-1111-1111-111111111111/reject",
            None,
            {"app.api.detection_rules.detection_rule_service.set_rule_approval_status": lambda db, rule_id, tenant_id, approval_status: "rejected"},
        ),
    ],
)
def test_detection_rule_routes_use_tenant_session(method, path, payload, patches):
    """Every routed DB path should resolve through the tenant-scoped session dependency."""
    calls = {"session": 0}
    app = FastAPI()
    app.include_router(router_api.router)

    def override_get_tenant_session():
        calls["session"] += 1
        yield object()

    app.dependency_overrides[router_api.get_tenant_session] = override_get_tenant_session
    client = TestClient(app)

    with ExitStack() as stack:
        for target, replacement in patches.items():
            stack.enter_context(patch(target, replacement))
        request_kwargs = {
            "headers": {"X-Tenant-ID": "11111111-1111-1111-1111-111111111111"},
        }
        if payload is not None:
            request_kwargs["json"] = payload
        response = getattr(client, method)(
            f"/detection-rules{path}",
            **request_kwargs,
        )

    assert response.status_code < 500
    assert calls == {"session": 1}
