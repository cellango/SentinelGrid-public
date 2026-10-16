"""
Model Provider Abstraction
Enables easy swapping of LLM models and backends.

Integrates with sg_core.llm_cache for:
- Response caching (Redis-backed, avoids redundant API calls)
- Token usage tracking per tenant (billing / cost visibility)
- Spending caps enforcement (prevents cost overruns)

All cache/tracking features degrade gracefully if Redis is unavailable.
"""

import logging
import os
import re
from typing import Optional, Dict, Any, List
from abc import ABC, abstractmethod
import httpx

from app.core.config import settings
from sg_core.service_metrics import get_service_metrics

logger = logging.getLogger(__name__)
runtime_metrics = get_service_metrics(settings.SERVICE_NAME)

# ---------------------------------------------------------------------------
# Optional LLM cache / tracking / spending guard initialisation
# ---------------------------------------------------------------------------
_llm_cache = None
_token_tracker = None
_spending_guard = None

try:
    from sg_core.llm_cache import LLMCache, TokenUsageTracker, SpendingGuard

    _llm_cache = LLMCache()
    _token_tracker = TokenUsageTracker()
    _spending_guard = SpendingGuard(_token_tracker)
    logger.info("LLM cache, token tracking and spending guard initialised")
except Exception as exc:
    logger.warning(f"LLM cache/tracking unavailable (Redis may be down): {exc}")


class SpendingCapExceeded(Exception):
    """Raised when a tenant has exceeded their LLM spending cap."""
    pass


def _provider_metric_name(provider_or_name: object) -> str:
    if isinstance(provider_or_name, str):
        raw_name = provider_or_name
    else:
        raw_name = provider_or_name.__class__.__name__
    raw_name = raw_name.replace("Provider", "")
    parts = re.findall(r"[A-Z]+(?=[A-Z][a-z]|$)|[A-Z]?[a-z0-9]+", raw_name)
    return "_".join(part.lower() for part in parts if part)


def _record_provider_health(provider_name: str, healthy: bool) -> None:
    runtime_metrics.increment_counter(
        "llm_provider_health_checks_total",
        provider=provider_name,
        outcome="healthy" if healthy else "unhealthy",
    )
    runtime_metrics.set_gauge("llm_provider_healthy", 1 if healthy else 0, provider=provider_name)


def _record_provider_request(provider_name: str, outcome: str, *, failure_type: str | None = None) -> None:
    runtime_metrics.increment_counter("llm_requests_total", provider=provider_name, outcome=outcome)
    if failure_type:
        runtime_metrics.increment_counter(
            "llm_provider_failures_total",
            provider=provider_name,
            failure_type=failure_type,
        )


class ModelProvider(ABC):
    """Abstract base class for model providers."""

    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate text from prompt."""
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """Check if model is available."""
        pass

    # ------------------------------------------------------------------
    # Cache / tracking / spending helpers (safe to call even w/o Redis)
    # ------------------------------------------------------------------

    def _check_spending(self, tenant_id: Optional[str]) -> None:
        """Raise SpendingCapExceeded if the tenant is over budget."""
        if not _spending_guard or not tenant_id:
            return
        try:
            result = _spending_guard.check(tenant_id)
            if result.get("warning"):
                logger.warning(f"Spending warning for tenant {tenant_id}: {result['warning']}")
            if not result["allowed"]:
                raise SpendingCapExceeded(result["warning"])
        except SpendingCapExceeded:
            raise
        except Exception as exc:
            logger.debug(f"Spending check failed (non-fatal): {exc}")

    def _cache_get(self, model: str, messages: list, temperature: float) -> Optional[str]:
        """Return cached response text or None."""
        if not _llm_cache:
            return None
        try:
            cached = _llm_cache.get(model, messages, temperature)
            if cached is not None:
                return cached.get("text", str(cached))
        except Exception as exc:
            logger.debug(f"Cache read failed (non-fatal): {exc}")
        return None

    def _cache_set(self, model: str, messages: list, temperature: float, text: str) -> None:
        """Store a response in the cache."""
        if not _llm_cache:
            return
        try:
            _llm_cache.set(model, messages, temperature, {"text": text})
        except Exception as exc:
            logger.debug(f"Cache write failed (non-fatal): {exc}")

    def _track_usage(self, tenant_id: Optional[str], model: str, prompt_tokens: int, completion_tokens: int) -> None:
        """Record token usage for a tenant."""
        if not _token_tracker or not tenant_id:
            return
        try:
            _token_tracker.record(tenant_id, model, prompt_tokens, completion_tokens)
        except Exception as exc:
            logger.debug(f"Usage tracking failed (non-fatal): {exc}")


class ModelGatewayProvider(ModelProvider):
    """Provider for Model Gateway service."""
    
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or getattr(settings, 'MODEL_GATEWAY_URL', 'http://model_gateway:8000')
        self.model_name = getattr(settings, 'LLM_MODEL_NAME', 'qwen2.5-coder-7b')
        self.temperature = float(getattr(settings, 'LLM_TEMPERATURE', '0.3'))
        self.max_tokens = int(getattr(settings, 'LLM_MAX_TOKENS', '500'))
    
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate text using Model Gateway."""
        temperature = kwargs.get('temperature', self.temperature)
        max_tokens = kwargs.get('max_tokens', self.max_tokens)
        tenant_id = kwargs.get('tenant_id')
        provider_name = _provider_metric_name(self)
        messages = [{"role": "user", "content": prompt}]

        # --- Spending guard ---
        self._check_spending(tenant_id)

        # --- Cache lookup ---
        cached = self._cache_get(self.model_name, messages, temperature)
        if cached is not None:
            return cached

        try:
            with httpx.Client(timeout=30.0) as client:
                headers = {}
                if tenant_id:
                    headers["X-Tenant-ID"] = tenant_id
                response = client.post(
                    f"{self.base_url}/v1/chat/completions",
                    json={
                        "model": self.model_name,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    },
                    headers=headers,
                )
                response.raise_for_status()
                result = response.json()
                choices = result.get("choices") or []
                if choices:
                    text = choices[0].get("message", {}).get("content", "")
                elif "text" in result:
                    text = result["text"]
                elif "response" in result:
                    text = result["response"]
                else:
                    text = str(result)

            # --- Cache store ---
            self._cache_set(self.model_name, messages, temperature, text)

            # --- Token tracking (estimate from text length when API doesn't return counts) ---
            usage = result.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", len(prompt) // 4)
            completion_tokens = usage.get("completion_tokens", len(text) // 4)
            self._track_usage(tenant_id, self.model_name, prompt_tokens, completion_tokens)

            _record_provider_request(provider_name, "success")
            return text

        except SpendingCapExceeded:
            _record_provider_request(provider_name, "failure", failure_type="SpendingCapExceeded")
            raise
        except Exception as e:
            logger.error(f"Error calling Model Gateway: {e}")
            _record_provider_request(provider_name, "failure", failure_type=type(e).__name__)
            raise
    
    def health_check(self) -> bool:
        """Check Model Gateway health."""
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{self.base_url}/health")
                healthy = response.status_code == 200
                _record_provider_health(_provider_metric_name(self), healthy)
                return healthy
        except Exception:
            _record_provider_health(_provider_metric_name(self), False)
            return False


class LlamaCppProvider(ModelProvider):
    """Provider for llama.cpp (direct integration)."""
    
    def __init__(self, model_path: Optional[str] = None):
        try:
            from llama_cpp import Llama
            
            model_path = model_path or getattr(settings, 'LLAMA_CPP_MODEL_PATH', None)
            if not model_path:
                raise ValueError("LLAMA_CPP_MODEL_PATH not configured")
            
            self.llm = Llama(
                model_path=model_path,
                n_ctx=4096,
                n_threads=int(getattr(settings, 'LLAMA_CPP_THREADS', '4')),
                verbose=False
            )
            self.temperature = float(getattr(settings, 'LLM_TEMPERATURE', '0.3'))
            self.max_tokens = int(getattr(settings, 'LLM_MAX_TOKENS', '500'))
        except ImportError:
            logger.error("llama-cpp-python not installed. Install with: pip install llama-cpp-python")
            self.llm = None
        except Exception as e:
            logger.error(f"Failed to initialize llama.cpp: {e}")
            self.llm = None
    
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate text using llama.cpp."""
        if not self.llm:
            raise RuntimeError("llama.cpp not initialized")

        temperature = kwargs.get('temperature', self.temperature)
        max_tokens = kwargs.get('max_tokens', self.max_tokens)
        tenant_id = kwargs.get('tenant_id')
        provider_name = _provider_metric_name(self)
        model_name = getattr(settings, 'LLAMA_CPP_MODEL_NAME', 'llama-cpp-local')
        messages = [{"role": "user", "content": prompt}]

        # --- Spending guard ---
        self._check_spending(tenant_id)

        # --- Cache lookup ---
        cached = self._cache_get(model_name, messages, temperature)
        if cached is not None:
            return cached

        try:
            response = self.llm(
                prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                stop=["\n\n"],
                echo=False
            )
            text = response["choices"][0]["text"]

            # --- Cache store ---
            self._cache_set(model_name, messages, temperature, text)

            # --- Token tracking ---
            usage = response.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", len(prompt) // 4)
            completion_tokens = usage.get("completion_tokens", len(text) // 4)
            self._track_usage(tenant_id, model_name, prompt_tokens, completion_tokens)

            _record_provider_request(provider_name, "success")
            return text
        except SpendingCapExceeded:
            _record_provider_request(provider_name, "failure", failure_type="SpendingCapExceeded")
            raise
        except Exception as e:
            logger.error(f"Error generating with llama.cpp: {e}")
            _record_provider_request(provider_name, "failure", failure_type=type(e).__name__)
            raise
    
    def health_check(self) -> bool:
        """Check if llama.cpp is available."""
        healthy = self.llm is not None
        _record_provider_health(_provider_metric_name(self), healthy)
        return healthy


class OpenAICompatibleProvider(ModelProvider):
    """Provider for OpenAI-compatible APIs (optional fallback)."""
    
    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        self.base_url = base_url or getattr(settings, 'OPENAI_COMPATIBLE_URL', None)
        self.api_key = api_key or getattr(settings, 'OPENAI_COMPATIBLE_API_KEY', None)
        self.model_name = getattr(settings, 'OPENAI_COMPATIBLE_MODEL', 'gpt-3.5-turbo')
        
        if not self.base_url:
            raise ValueError("OPENAI_COMPATIBLE_URL not configured")
    
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate text using OpenAI-compatible API."""
        provider_name = _provider_metric_name(self)
        try:
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{self.base_url}/v1/chat/completions",
                    headers=headers,
                    json={
                        "model": self.model_name,
                        "messages": [
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": kwargs.get('temperature', 0.3),
                        "max_tokens": kwargs.get('max_tokens', 500)
                    }
                )
                response.raise_for_status()
                result = response.json()
                
                if "choices" in result and len(result["choices"]) > 0:
                    text = result["choices"][0]["message"]["content"]
                else:
                    text = str(result)
                _record_provider_request(provider_name, "success")
                return text
                    
        except Exception as e:
            logger.error(f"Error calling OpenAI-compatible API: {e}")
            _record_provider_request(provider_name, "failure", failure_type=type(e).__name__)
            raise
    
    def health_check(self) -> bool:
        """Check if API is available."""
        try:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{self.base_url}/health", headers=headers)
                healthy = response.status_code == 200
                _record_provider_health(_provider_metric_name(self), healthy)
                return healthy
        except Exception:
            _record_provider_health(_provider_metric_name(self), False)
            return False


class ModelProviderFactory:
    """Factory for creating model providers based on configuration."""
    
    @staticmethod
    def create_provider(provider_type: Optional[str] = None) -> ModelProvider:
        """
        Create model provider based on configuration.
        
        Provider types:
        - 'model_gateway' (default): Use Model Gateway service
        - 'llama_cpp': Direct llama.cpp integration
        - 'openai_compatible': OpenAI-compatible API
        
        Falls back to next option if primary fails.
        """
        provider_type = provider_type or getattr(settings, 'LLM_PROVIDER', 'model_gateway')
        
        providers = []
        
        # Primary provider
        if provider_type == 'model_gateway':
            providers.append(('ModelGatewayProvider', lambda: ModelGatewayProvider()))
        elif provider_type == 'llama_cpp':
            providers.append(('LlamaCppProvider', lambda: LlamaCppProvider()))
        elif provider_type == 'openai_compatible':
            providers.append(('OpenAICompatibleProvider', lambda: OpenAICompatibleProvider()))
        
        # Fallback providers
        fallback_type = getattr(settings, 'LLM_FALLBACK_PROVIDER', None)
        if fallback_type and fallback_type != provider_type:
            if fallback_type == 'model_gateway':
                providers.append(('ModelGatewayProvider (fallback)', lambda: ModelGatewayProvider()))
            elif fallback_type == 'llama_cpp':
                providers.append(('LlamaCppProvider (fallback)', lambda: LlamaCppProvider()))
            elif fallback_type == 'openai_compatible':
                providers.append(('OpenAICompatibleProvider (fallback)', lambda: OpenAICompatibleProvider()))
        
        # Try providers in order
        last_error = None
        for provider_name, provider_factory in providers:
            metric_name = _provider_metric_name(provider_name.split(" ")[0])
            try:
                provider = provider_factory()
                if provider.health_check():
                    logger.info(f"Using model provider: {provider_name}")
                    runtime_metrics.increment_counter("llm_provider_selected_total", provider=metric_name)
                    return provider
                else:
                    logger.warning(f"Provider {provider_name} health check failed")
                    runtime_metrics.increment_counter("llm_provider_health_failures_total", provider=metric_name)
            except Exception as e:
                logger.warning(f"Failed to initialize {provider_name}: {e}")
                runtime_metrics.increment_counter(
                    "llm_provider_initialization_failures_total",
                    provider=metric_name,
                    failure_type=type(e).__name__,
                )
                last_error = e
        
        # If all fail, raise error
        raise RuntimeError(f"Failed to initialize any model provider. Last error: {last_error}")


# Singleton instance (initialized on first use)
_model_provider: Optional[ModelProvider] = None


def get_model_provider() -> ModelProvider:
    """Get or create model provider instance."""
    global _model_provider
    
    if _model_provider is None:
        _model_provider = ModelProviderFactory.create_provider()
    
    # Health check and reinitialize if needed
    if not _model_provider.health_check():
        logger.warning("Model provider health check failed, attempting to reinitialize...")
        runtime_metrics.increment_counter(
            "llm_provider_reinitializations_total",
            provider=_provider_metric_name(_model_provider),
            reason="health_check_failed",
        )
        _model_provider = ModelProviderFactory.create_provider()
    
    return _model_provider


def reset_model_provider():
    """Reset model provider (for testing or configuration changes)."""
    global _model_provider
    _model_provider = None
