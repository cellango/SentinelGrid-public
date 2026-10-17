"""Legacy chat/onboarding cannot call models or provision applications."""
import asyncio
import inspect
from unittest.mock import Mock
import pytest
from fastapi import HTTPException
from app.services.ai_chat_service import IAMChatService
from app.services.ai_app_onboarding import AIAppOnboardingService

@pytest.mark.parametrize('kind', ['chat', 'onboarding'])
def test_all_legacy_service_entrypoints_are_unavailable(kind):
    provider = Mock()
    service = IAMChatService(provider, provider) if kind == 'chat' else AIAppOnboardingService()
    for name, method in inspect.getmembers(service, inspect.ismethod):
        if name == '__init__': continue
        kwargs = {n: None for n,p in inspect.signature(method).parameters.items() if p.default is inspect.Parameter.empty}
        with pytest.raises(HTTPException) as error:
            result = method(**kwargs)
            if inspect.isawaitable(result): asyncio.run(result)
        assert error.value.status_code == 501
    assert provider.mock_calls == []
