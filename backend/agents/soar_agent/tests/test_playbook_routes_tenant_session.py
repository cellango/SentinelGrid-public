"""Header-only legacy requests cannot initialize a session or restore effects.

Positive owned list/detail session behavior is covered with current RSA/actual
reader in test_soar_identity_boundary.py; no fake execution-service module is used.
"""
from unittest.mock import Mock
from fastapi.testclient import TestClient
import pytest
import app.main as main
from app.core import database

TEST_ID="11111111-1111-4111-8111-111111111111"
P="/soar/playbooks/"+TEST_ID

@pytest.mark.parametrize("method,path,status",[("POST","/soar/playbooks",503),
 ("GET","/soar/playbooks",401),("GET",P,401),
 *[("POST",P+"/"+tail,503) for tail in ["approve","reject","preview","validate"]],
 ("PUT",P,503),("DELETE",P,503),("POST",P+"/copy",503),("POST",P+"/execute",503),
 ("GET","/soar/executions/"+TEST_ID,503)])
def test_legacy_route_requests_do_not_open_session(monkeypatch,method,path,status):
    effect=Mock(side_effect=AssertionError("No SQL session or legacy service factory"))
    monkeypatch.setattr(database,"SessionLocal",effect);monkeypatch.setattr(main,"PlaybookService",effect)
    with TestClient(main.app) as client:r=client.request(method,path,headers={"X-Tenant-ID":TEST_ID},
        json={"approved":True} if method in {"POST","PUT"} else None)
    assert r.status_code==status;effect.assert_not_called()
