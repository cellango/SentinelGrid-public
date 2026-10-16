from unittest.mock import Mock
from uuid import uuid4

from app import schemas
from app.core.config import settings
from app.services.platform_alert_forwarder import forward_event_to_platform


def test_forward_event_to_platform_posts_expected_payload(mocker):
    mock_response = Mock()
    mock_response.content = b'{"status":"created"}'
    mock_response.json.return_value = {"status": "created"}
    mock_response.raise_for_status.return_value = None
    post_mock = mocker.patch("app.services.platform_alert_forwarder.httpx.post", return_value=mock_response)

    original_enabled = settings.PLATFORM_ALERT_INGEST_ENABLED
    original_url = settings.PLATFORM_API_URL
    original_path = settings.PLATFORM_ALERT_INGEST_PATH
    original_timeout = settings.PLATFORM_ALERT_INGEST_TIMEOUT_SECONDS
    original_token = settings.INTERNAL_SERVICE_TOKEN

    settings.PLATFORM_ALERT_INGEST_ENABLED = True
    settings.PLATFORM_API_URL = "http://platform-api:8000"
    settings.PLATFORM_ALERT_INGEST_PATH = "/api/v1/internal/ai-shield/events"
    settings.PLATFORM_ALERT_INGEST_TIMEOUT_SECONDS = 7
    settings.INTERNAL_SERVICE_TOKEN = "test-token"

    try:
        event = schemas.TelemetryEventCreate(
            event_id="evt-123",
            org_id=uuid4(),
            ai_app_id="support-assistant",
            user_id="owner@example.com",
            provider="openai",
            model="gpt-4.1",
            prompt_injection_suspected=True,
            policy_decision="blocked",
        )

        result = forward_event_to_platform(event)
    finally:
        settings.PLATFORM_ALERT_INGEST_ENABLED = original_enabled
        settings.PLATFORM_API_URL = original_url
        settings.PLATFORM_ALERT_INGEST_PATH = original_path
        settings.PLATFORM_ALERT_INGEST_TIMEOUT_SECONDS = original_timeout
        settings.INTERNAL_SERVICE_TOKEN = original_token

    assert result == {"status": "created"}
    post_mock.assert_called_once()
    _, kwargs = post_mock.call_args
    assert kwargs["timeout"] == 7
    assert kwargs["headers"]["Authorization"] == "Bearer test-token"
    assert kwargs["headers"]["X-Tenant-ID"] == str(event.org_id)
    assert kwargs["json"]["event_id"] == "evt-123"
    assert kwargs["json"]["ai_app_id"] == "support-assistant"


def test_forward_event_to_platform_noops_when_disabled(mocker):
    post_mock = mocker.patch("app.services.platform_alert_forwarder.httpx.post")
    original_enabled = settings.PLATFORM_ALERT_INGEST_ENABLED
    settings.PLATFORM_ALERT_INGEST_ENABLED = False

    try:
        event = schemas.TelemetryEventCreate(
            org_id=uuid4(),
            policy_decision="blocked",
        )
        result = forward_event_to_platform(event)
    finally:
        settings.PLATFORM_ALERT_INGEST_ENABLED = original_enabled

    assert result is None
    post_mock.assert_not_called()
