#!/usr/bin/env python3
"""Validate agent-runtime wiring in the resolved Docker Compose model."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen


EXPECTED_RUNTIME_ENV = {
    "REDIS_URL": "redis://redis:6379",
    "MODEL_GATEWAY_URL": "http://model_gateway:8000",
    "COMPLIANCE_AGENT_ENABLED": "false",
    "COMPLIANCE_SERVICE_URL": "http://compliance_service:8000",
    "REPORTING_SERVICE_URL": "http://reporting_service:8000",
    "IAM_AGENT_URL": "http://iam_agent:8000",
    "INTERNAL_SERVICE_TOKEN": "internal-service-token-change-in-production",
}

RUNTIME_CONSUMERS = {
    "api_gateway",
    "soar_agent",
    "ticketing_service",
    "compliance_service",
    "detection_service",
    "reporting_service",
}

LEGACY_SERVICE_NAMES = {
    "entitlement_agent",
    "ai_enrichment_agent",
}

LEGACY_DOCKERFILE_PREFIXES = (
    "services/siem_agent/",
    "services/entitlement_agent/",
    "services/ai_enrichment_agent/",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-f",
        "--compose-file",
        default="docker-compose.dev.yml",
        help="Compose file to validate.",
    )
    parser.add_argument(
        "--probe-ready",
        action="store_true",
        help="Also probe a running runtime /ready endpoint.",
    )
    parser.add_argument(
        "--runtime-url",
        default="http://localhost:8029",
        help="Runtime base URL for --probe-ready.",
    )
    args = parser.parse_args()

    try:
        compose = load_compose(args.compose_file)
        validate_compose(compose)
        if args.probe_ready:
            probe_ready(args.runtime_url)
    except CheckFailure as exc:
        print(f"agent-runtime compose wiring check failed: {exc}", file=sys.stderr)
        return 1

    print("agent-runtime compose wiring check passed")
    return 0


def load_compose(compose_file: str) -> dict[str, Any]:
    command = ["docker", "compose", "-f", compose_file, "config", "--format", "json"]
    try:
        result = subprocess.run(command, check=False, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise CheckFailure("docker CLI is required for compose validation") from exc

    if result.returncode != 0:
        stderr = result.stderr.strip()
        raise CheckFailure(f"`{' '.join(command)}` failed: {stderr or result.stdout.strip()}")

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise CheckFailure("docker compose did not return valid JSON") from exc
    if not isinstance(payload, dict):
        raise CheckFailure("docker compose JSON root is not an object")
    return payload


def validate_compose(compose: dict[str, Any]) -> None:
    services = compose.get("services")
    if not isinstance(services, dict):
        raise CheckFailure("compose model has no services object")

    require_service_absent(services, LEGACY_SERVICE_NAMES)
    require_service_present(services, "agent_runtime")
    validate_runtime_service(services["agent_runtime"])
    validate_runtime_consumers(services)
    validate_legacy_dockerfiles_absent(services)


def validate_runtime_service(service: dict[str, Any]) -> None:
    dockerfile = ((service.get("build") or {}).get("dockerfile") or "").strip()
    if dockerfile != "services/agent_runtime/Dockerfile":
        raise CheckFailure(f"agent_runtime dockerfile mismatch: {dockerfile!r}")

    env = service.get("environment") or {}
    for key, expected in EXPECTED_RUNTIME_ENV.items():
        actual = env.get(key)
        if actual != expected:
            raise CheckFailure(f"agent_runtime env {key}={actual!r}, expected {expected!r}")

    depends_on = service.get("depends_on") or {}
    for dependency in ("redis", "model_gateway"):
        if dependency not in depends_on:
            raise CheckFailure(f"agent_runtime must depend on {dependency}")

    ports = service.get("ports") or []
    if not any(port.get("target") == 8000 and str(port.get("published")) == "8029" for port in ports):
        raise CheckFailure("agent_runtime must publish 8029:8000")


def validate_runtime_consumers(services: dict[str, Any]) -> None:
    for service_name in sorted(RUNTIME_CONSUMERS):
        require_service_present(services, service_name)
        service = services[service_name]
        env = service.get("environment") or {}
        actual_url = env.get("AGENT_RUNTIME_URL")
        if actual_url != "http://agent_runtime:8000":
            raise CheckFailure(
                f"{service_name} AGENT_RUNTIME_URL={actual_url!r}, expected 'http://agent_runtime:8000'"
            )

        depends_on = service.get("depends_on") or {}
        if "agent_runtime" not in depends_on:
            raise CheckFailure(f"{service_name} must depend on agent_runtime")


def validate_legacy_dockerfiles_absent(services: dict[str, Any]) -> None:
    for service_name, service in services.items():
        dockerfile = str(((service.get("build") or {}).get("dockerfile") or "")).strip()
        if dockerfile.startswith(LEGACY_DOCKERFILE_PREFIXES):
            raise CheckFailure(f"{service_name} uses legacy dockerfile path {dockerfile}")

    siem_dockerfile = str(((services["siem_agent"].get("build") or {}).get("dockerfile") or ""))
    if siem_dockerfile != "agents/siem_agent/Dockerfile":
        raise CheckFailure(f"siem_agent must use canonical dockerfile, got {siem_dockerfile!r}")


def probe_ready(runtime_url: str) -> None:
    url = runtime_url.rstrip("/") + "/ready"
    request = Request(url, headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise CheckFailure(f"runtime readiness probe failed for {url}: {exc}") from exc

    if not payload.get("ready"):
        raise CheckFailure(f"runtime readiness probe returned not ready: {payload}")


def require_service_present(services: dict[str, Any], service_name: str) -> None:
    if service_name not in services:
        raise CheckFailure(f"missing compose service: {service_name}")


def require_service_absent(services: dict[str, Any], service_names: set[str]) -> None:
    present = sorted(service_names.intersection(services))
    if present:
        raise CheckFailure(f"legacy compose services are still active: {', '.join(present)}")


class CheckFailure(RuntimeError):
    pass


if __name__ == "__main__":
    raise SystemExit(main())
