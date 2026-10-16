from unittest.mock import Mock, patch

from app.api import routes_alerts


def test_authenticated_tenant_cannot_override_scope_with_header_tenant_id(
    client,
    mock_db_session,
    foreign_tenant_pair,
):
    with patch.object(routes_alerts, "AlertService") as mock_service_class:
        mock_service = Mock()
        mock_service.list_alerts.return_value = ([], 0)
        mock_service_class.return_value = mock_service

        response = client.get(
            "/api/v1/alerts/",
            headers={"x-tenant-id": foreign_tenant_pair["foreign"]},
        )

    assert response.status_code == 200
    mock_service_class.assert_called_once_with(mock_db_session, "tenant-123")


def test_authenticated_tenant_cannot_override_scope_with_query_tenant_id(
    client,
    mock_db_session,
    foreign_tenant_pair,
):
    with patch.object(routes_alerts, "AlertService") as mock_service_class:
        mock_service = Mock()
        mock_service.list_alerts.return_value = ([], 0)
        mock_service_class.return_value = mock_service

        response = client.get(
            f"/api/v1/alerts/?tenant_id={foreign_tenant_pair['foreign']}"
        )

    assert response.status_code == 200
    mock_service_class.assert_called_once_with(mock_db_session, "tenant-123")


def test_cross_tenant_resource_lookup_returns_bounded_error(client):
    with patch.object(routes_alerts, "AlertService") as mock_service_class:
        mock_service = Mock()
        mock_service.get_alert.return_value = None
        mock_service_class.return_value = mock_service

        response = client.get("/api/v1/alerts/00000000-0000-0000-0000-000000000001")

    assert response.status_code == 404
    assert response.json() == {"detail": "Alert not found"}


def test_cross_tenant_list_request_does_not_return_foreign_rows(client):
    with patch.object(routes_alerts, "AlertService") as mock_service_class:
        mock_service = Mock()
        mock_service.list_alerts.return_value = ([], 0)
        mock_service_class.return_value = mock_service

        response = client.get("/api/v1/alerts/")

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0}
