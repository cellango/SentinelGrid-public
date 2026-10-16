import pytest

from app.services import model_provider
from sg_core.service_metrics import get_service_metrics, reset_service_metrics


class _ExplodingClient:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def post(self, *args, **kwargs):
        raise RuntimeError("provider boom")


class _SuccessfulClient:
    def __init__(self):
        self.posts = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def post(self, *args, **kwargs):
        self.posts.append({"args": args, "kwargs": kwargs})
        return _SuccessfulResponse()


class _SuccessfulResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "choices": [{"message": {"role": "assistant", "content": "iam response"}}],
            "usage": {"prompt_tokens": 2, "completion_tokens": 3},
        }


def test_model_gateway_provider_records_generation_failure_metrics(monkeypatch):
    reset_service_metrics("iam-agent")
    provider = model_provider.ModelGatewayProvider(base_url="http://model-gateway")

    monkeypatch.setattr(model_provider.httpx, "Client", lambda *args, **kwargs: _ExplodingClient())

    with pytest.raises(RuntimeError):
        provider.generate("hello world")

    snapshot = get_service_metrics("iam-agent").snapshot()
    assert snapshot["counters"]["llm_requests_total"]["series"]["outcome=failure,provider=model_gateway"] == 1
    assert (
        snapshot["counters"]["llm_provider_failures_total"]["series"][
            "failure_type=RuntimeError,provider=model_gateway"
        ]
        == 1
    )


def test_model_gateway_provider_uses_openai_compatible_chat_contract(monkeypatch):
    provider = model_provider.ModelGatewayProvider(base_url="http://model-gateway")
    fake_client = _SuccessfulClient()
    monkeypatch.setattr(model_provider.httpx, "Client", lambda *args, **kwargs: fake_client)

    result = provider.generate("hello world", tenant_id="tenant-1")

    assert result == "iam response"
    post = fake_client.posts[0]
    assert post["args"][0] == "http://model-gateway/v1/chat/completions"
    assert post["kwargs"]["headers"] == {"X-Tenant-ID": "tenant-1"}
    payload = post["kwargs"]["json"]
    assert payload["messages"] == [{"role": "user", "content": "hello world"}]
    assert payload["model"] == provider.model_name


def test_provider_factory_records_primary_health_failure_and_fallback_selection(monkeypatch):
    reset_service_metrics("iam-agent")

    class _BrokenPrimary:
        def health_check(self):
            return False

    class _HealthyFallback:
        def health_check(self):
            return True

    monkeypatch.setattr(model_provider.settings, "LLM_PROVIDER", "model_gateway", raising=False)
    monkeypatch.setattr(model_provider.settings, "LLM_FALLBACK_PROVIDER", "openai_compatible", raising=False)
    monkeypatch.setattr(model_provider, "ModelGatewayProvider", lambda: _BrokenPrimary())
    monkeypatch.setattr(model_provider, "OpenAICompatibleProvider", lambda: _HealthyFallback())

    provider = model_provider.ModelProviderFactory.create_provider()

    assert isinstance(provider, _HealthyFallback)
    snapshot = get_service_metrics("iam-agent").snapshot()
    assert snapshot["counters"]["llm_provider_health_failures_total"]["series"]["provider=model_gateway"] == 1
    assert snapshot["counters"]["llm_provider_selected_total"]["series"]["provider=open_ai_compatible"] == 1
