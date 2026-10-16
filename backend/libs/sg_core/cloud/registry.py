"""Cloud provider registry loading and normalization.

The registry is intentionally non-secret configuration. Tenant credentials stay
in each service's secret storage path and are referenced from account metadata.
"""

from __future__ import annotations

import copy
import os
from functools import lru_cache
from pathlib import Path
from typing import Any


BUILT_IN_PROVIDER_ALIASES = {
    "amazon": "aws",
    "amazon_web_services": "aws",
    "hcloud": "hetzner",
    "hetzner_cloud": "hetzner",
    "google": "gcp",
    "google_cloud": "gcp",
    "google_cloud_platform": "gcp",
    "oci": "oracle",
    "oracle_cloud": "oracle",
}

CLOUD_RESOURCE_BASELINE_SCANNER_ID = "cloud-resource-baseline"


def _default_registry_paths() -> list[Path]:
    paths: list[Path] = []
    env_path = os.getenv("CLOUD_PROVIDER_REGISTRY_PATH")
    if env_path:
        paths.append(Path(env_path).expanduser())

    backend_dir = Path(__file__).resolve().parents[3]
    paths.extend(
        [
            backend_dir / "config" / "cloud_provider_registry.yaml",
            backend_dir / "config" / "cloud_provider_registry.example.yaml",
        ]
    )
    return paths


def _resolve_registry_path(path: str | os.PathLike[str] | None = None) -> Path:
    if path:
        candidate = Path(path).expanduser()
        if candidate.exists():
            return candidate
        raise FileNotFoundError(f"Cloud provider registry not found: {candidate}")

    for candidate in _default_registry_paths():
        if candidate.exists():
            return candidate

    searched = ", ".join(str(p) for p in _default_registry_paths())
    raise FileNotFoundError(f"Cloud provider registry not found. Searched: {searched}")


@lru_cache(maxsize=8)
def _load_registry_cached(path: str | None = None) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - dependency failure path
        raise RuntimeError("PyYAML is required to load the cloud provider registry") from exc

    registry_path = _resolve_registry_path(path)
    with registry_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}

    if not isinstance(data, dict):
        raise ValueError(f"Cloud provider registry must be a mapping: {registry_path}")
    if not isinstance(data.get("providers"), dict):
        raise ValueError(f"Cloud provider registry is missing providers: {registry_path}")

    data["_registry_path"] = str(registry_path)
    return data


def load_cloud_provider_registry(path: str | os.PathLike[str] | None = None) -> dict[str, Any]:
    """Load the provider registry and return a copy callers can safely mutate."""

    cache_key = str(path) if path is not None else None
    return copy.deepcopy(_load_registry_cached(cache_key))


def canonical_provider_id(
    provider_id: str,
    registry: dict[str, Any] | None = None,
) -> str:
    """Resolve a provider id or alias to its canonical registry id."""

    normalized = str(provider_id or "").strip().lower().replace("-", "_").replace(" ", "_")
    if not normalized:
        return normalized

    registry_data = registry if registry is not None else load_cloud_provider_registry()
    providers = registry_data.get("providers") or {}
    if normalized in providers:
        return normalized

    if normalized in BUILT_IN_PROVIDER_ALIASES:
        return BUILT_IN_PROVIDER_ALIASES[normalized]

    for provider_key, provider in providers.items():
        aliases = provider.get("aliases") or []
        adapter = provider.get("adapter")
        provider_aliases = {str(alias).strip().lower().replace("-", "_") for alias in aliases}
        if adapter:
            provider_aliases.add(str(adapter).strip().lower().replace("-", "_"))
        if normalized in provider_aliases:
            return provider_key

    return normalized


def _safe_target_payload(target_id: str, target: dict[str, Any]) -> dict[str, Any]:
    resource = target.get("resource") or {}
    relationships = target.get("relationships") or {}
    iac = target.get("iac") or {}
    return {
        "id": target_id,
        "provider": target.get("provider"),
        "environment": target.get("environment"),
        "mode": target.get("mode"),
        "resource": resource,
        "relationships": relationships,
        "expected_exposure": target.get("expected_exposure") or {},
        "edge": target.get("edge") or {},
        "iac": {
            "managed": bool(iac.get("managed")),
            "tool": iac.get("tool"),
            "project": iac.get("project"),
            "workspace": iac.get("workspace"),
            "preferred_apply_mode": iac.get("preferred_apply_mode"),
            "direct_api_apply_allowed": bool(iac.get("direct_api_apply_allowed")),
        },
    }


def provider_registry_payload(registry: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return a sanitized provider registry payload suitable for onboarding UI."""

    registry_data = registry if registry is not None else load_cloud_provider_registry()
    providers = registry_data.get("providers") or {}
    targets = registry_data.get("targets") or {}
    provider_payloads: list[dict[str, Any]] = []

    for provider_id, provider in providers.items():
        onboarding = provider.get("onboarding") or {}
        provider_targets = [
            _safe_target_payload(target_id, target)
            for target_id, target in targets.items()
            if target.get("provider") == provider_id
        ]
        provider_payloads.append(
            {
                "id": provider_id,
                "display_name": provider.get("display_name") or provider_id,
                "aliases": provider.get("aliases") or [],
                "adapter": provider.get("adapter"),
                "auth": provider.get("auth") or {},
                "resources": provider.get("resources") or {},
                "capabilities": provider.get("capabilities") or {},
                "controls": provider.get("controls") or [],
                "onboarding": {
                    "enabled": onboarding.get("enabled", True),
                    "default": bool(onboarding.get("default")),
                    "badge": onboarding.get("badge"),
                    "order": onboarding.get("order", 100),
                    "target_mode": onboarding.get("target_mode"),
                    "description": onboarding.get("description"),
                    "integration_method": onboarding.get("integration_method"),
                },
                "onboarding_fields": provider.get("onboarding_fields") or [],
                "targets": provider_targets,
            }
        )

    provider_payloads.sort(key=lambda p: (p["onboarding"]["order"], p["display_name"]))
    return {
        "providers": provider_payloads,
        "targets": [_safe_target_payload(target_id, target) for target_id, target in targets.items()],
        "scanner_aliases": registry_data.get("scanner_aliases") or {},
        "source": registry_data.get("_registry_path"),
    }


def resolve_scanner_alias(
    scanner_id: str,
    registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve a scanner alias to its canonical scanner and target metadata."""

    requested = str(scanner_id or "").strip()
    registry_data = registry if registry is not None else load_cloud_provider_registry()
    aliases = registry_data.get("scanner_aliases") or {}
    alias = aliases.get(requested)
    if not isinstance(alias, dict):
        return {
            "requested_scanner": requested,
            "scanner": requested,
            "target": None,
            "alias": False,
            "metadata": {},
        }

    return {
        "requested_scanner": requested,
        "scanner": alias.get("scanner") or requested,
        "target": alias.get("target"),
        "alias": True,
        "metadata": alias,
    }


def get_cloud_target(
    target_id: str | None,
    registry: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Return a target manifest by ID, or None when the target is not configured."""

    if not target_id:
        return None
    registry_data = registry if registry is not None else load_cloud_provider_registry()
    target = (registry_data.get("targets") or {}).get(str(target_id))
    if not isinstance(target, dict):
        return None
    return copy.deepcopy(target)


def default_cloud_target_id(
    provider_id: str | None = None,
    registry: dict[str, Any] | None = None,
) -> str | None:
    """Return the default target manifest ID for a provider or registry."""

    registry_data = registry if registry is not None else load_cloud_provider_registry()
    targets = registry_data.get("targets") or {}
    if not isinstance(targets, dict) or not targets:
        return None

    provider = canonical_provider_id(provider_id, registry_data) if provider_id else None
    if not provider:
        providers = registry_data.get("providers") or {}
        default_providers = [
            provider_key
            for provider_key, provider_config in providers.items()
            if (provider_config.get("onboarding") or {}).get("default")
        ]
        provider = default_providers[0] if default_providers else None

    for target_id, target in targets.items():
        if provider is None or canonical_provider_id(target.get("provider"), registry_data) == provider:
            return str(target_id)
    return next(iter(targets.keys()))
