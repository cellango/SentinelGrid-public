"""Cloud provider adapter factory.

The provider registry names adapter keys, while this module maps those keys to
runtime classes. Product workflows should ask for an adapter by provider ID
instead of importing provider-specific classes directly.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

from sg_core.cloud.registry import canonical_provider_id, load_cloud_provider_registry
from sg_core.cloud.types import CloudProviderAdapter


BUILT_IN_ADAPTERS = {
    "hetzner": "sg_core.cloud.adapters.hetzner.HetznerCloudAdapter",
    "hcloud": "sg_core.cloud.adapters.hetzner.HetznerCloudAdapter",
    "hetzner_cloud": "sg_core.cloud.adapters.hetzner.HetznerCloudAdapter",
}


class UnsupportedCloudProviderError(ValueError):
    """Raised when no runtime adapter is registered for a provider."""


def _normalize_adapter_key(value: str | None) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def get_cloud_adapter_class(
    provider_id: str,
    registry: dict[str, Any] | None = None,
) -> type[CloudProviderAdapter]:
    """Resolve the runtime adapter class for a provider registry ID or alias."""

    registry_data = registry if registry is not None else load_cloud_provider_registry()
    provider = canonical_provider_id(provider_id, registry_data)
    provider_config = (registry_data.get("providers") or {}).get(provider) or {}
    adapter_value = str(provider_config.get("adapter") or provider).strip()
    adapter_key = _normalize_adapter_key(adapter_value)

    adapter_path = BUILT_IN_ADAPTERS.get(adapter_key) or BUILT_IN_ADAPTERS.get(provider)
    if not adapter_path and "." in adapter_value:
        adapter_path = adapter_value
    if not adapter_path:
        raise UnsupportedCloudProviderError(f"No cloud adapter is registered for provider {provider}")

    module_name, class_name = adapter_path.rsplit(".", 1)
    module = import_module(module_name)
    adapter_class = getattr(module, class_name)
    return adapter_class


def create_cloud_adapter(
    provider_id: str,
    registry: dict[str, Any] | None = None,
    **kwargs: Any,
) -> CloudProviderAdapter:
    """Instantiate the adapter registered for a provider."""

    adapter_class = get_cloud_adapter_class(provider_id, registry)
    return adapter_class(**kwargs)


def provider_has_adapter(
    provider_id: str,
    registry: dict[str, Any] | None = None,
) -> bool:
    try:
        get_cloud_adapter_class(provider_id, registry)
        return True
    except UnsupportedCloudProviderError:
        return False
