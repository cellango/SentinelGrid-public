"""Dashboard API endpoints for welcome dashboard."""

import asyncio
import logging
import os
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Header, Query
from typing import Any, Dict, Optional
from datetime import datetime, timezone
import httpx

from app.core.config import settings
from app.services.ai_risk_summary_service import AiRiskSummaryService
from app.services.posture_scoring import PostureScoringService
from app.services.welcome_prioritization import (
    build_cloud_posture_snapshot,
    build_dashboard_health,
    build_first_value_section,
    build_recommendations,
)
from app.services.now_queue_service import NowQueueService
from sg_core.circuit_breaker import AsyncCircuitBreaker
from sg_core.service_security import build_internal_auth_headers, verify_internal_service_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tenant", tags=["dashboard"])


def verify_internal_token(
    authorization: Optional[str] = Header(None),
    x_internal_service_token: Optional[str] = Header(None, alias="X-Internal-Service-Token"),
) -> bool:
    """Verify internal service token."""
    verify_internal_service_token(
        settings.INTERNAL_SERVICE_TOKEN,
        authorization=authorization,
        x_internal_service_token=x_internal_service_token,
        missing_detail="Missing authorization header",
        invalid_detail="Invalid internal service token",
    )
    return True


async def get_tenant_id(
    tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
) -> str:
    """Extract tenant_id from header."""
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Tenant-ID header is required"
        )
    
    try:
        UUID(tenant_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid tenant_id format (must be UUID)"
        )
    
    return tenant_id


_posture_scorer = PostureScoringService()
_now_queue_service = NowQueueService()
_ai_risk_summary_service = AiRiskSummaryService()
_service_circuit_breaker = AsyncCircuitBreaker(fail_max=5, reset_timeout=30.0)


def _people_access_fallback() -> Dict[str, Any]:
    return {
        "users_total": 0,
        "users_active": 0,
        "users_inactive": 0,
        "users_admins": 0,
        "mfa_coverage_percent": 0,
        "mfa_missing_count": 0,
        "dormant_accounts_count": 0,
        "failed_logins_24h": 0,
        "anomalies_count": 0,
        "anomalies_critical": 0,
        "devices_total": 0,
        "devices_trusted": 0,
        "devices_untrusted": 0,
    }


def _onboarding_status_fallback() -> Dict[str, Any]:
    return {
        "idp_connected": False,
        "cloud_connected": False,
        "endpoint_deployed": False,
        "git_connected": False,
        "appsec_connected": False,
        "ai_connected": False,
        "ticketing_connected": False,
        "services_selected": {
            "cloud": True,
            "git": True,
            "appsec": True,
            "aiShield": "hosted",
            "socManaged": False,
        },
        "cloud_health": None,
        "ticketing_health": None,
    }


def _score_posture(tenant_id: str) -> Dict[str, Any]:
    try:
        return _posture_scorer.score_tenant(tenant_id)
    except Exception as exc:
        logger.warning("Posture scoring failed for tenant %s: %s", tenant_id, exc)
        return {
            "overall_score": 68,
            "domain_scores": {},
            "top_risks": [],
            "last_computed_at": datetime.now(timezone.utc).isoformat(),
        }


async def _fetch_service_payload(
    client: httpx.AsyncClient,
    url: str,
    tenant_id: str,
    fallback: Dict[str, Any],
) -> Dict[str, Any]:
    async def _request() -> Dict[str, Any]:
        response = await client.get(
            url,
            headers=build_internal_auth_headers(
                settings.INTERNAL_SERVICE_TOKEN,
                tenant_id=tenant_id,
            ),
        )
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, dict) else fallback

    try:
        return await _service_circuit_breaker.call(
            f"orchestrator:{url}",
            _request,
            fallback=fallback,
        )
    except Exception as exc:
        logger.warning("Service payload fetch failed for %s tenant %s: %s", url, tenant_id, exc)
        return fallback


async def _probe_health_status(client: httpx.AsyncClient, url: str | None) -> str:
    if not url:
        return "unknown"
    try:
        response = await client.get(url)
        if response.status_code == 200:
            return "healthy"
        return f"degraded ({response.status_code})"
    except Exception:
        return "unreachable"


async def _build_source_health() -> Dict[str, Any]:
    ingest_url = os.getenv("INGESTION_SERVICE_URL", "http://ingestion_service:8000/health")
    siem_agent_url = os.getenv("SIEM_AGENT_URL", "http://siem_agent:8000/health")
    opensearch_url = os.getenv("OPENSEARCH_URL", "http://opensearch:9200")
    wazuh_health = os.getenv("WAZUH_HEALTH_URL")
    openedr_health = os.getenv("OPENEDR_HEALTH_URL")
    velociraptor_health = os.getenv("VELOCIRAPTOR_HEALTH_URL")

    async with httpx.AsyncClient(timeout=5.0, verify=settings.UPSTREAM_TLS_VERIFY) as client:
        ingestion_service, siem_agent, opensearch, wazuh, openedr, velociraptor = await asyncio.gather(
            _probe_health_status(client, ingest_url),
            _probe_health_status(client, siem_agent_url),
            _probe_health_status(client, f"{opensearch_url}/_cluster/health"),
            _probe_health_status(client, wazuh_health),
            _probe_health_status(client, openedr_health),
            _probe_health_status(client, velociraptor_health),
        )

    return {
        "ingestion_service": ingestion_service,
        "siem_agent": siem_agent,
        "opensearch": opensearch,
        "wazuh": wazuh,
        "openedr": openedr,
        "velociraptor": velociraptor,
    }


async def _load_operator_context(tenant_id: str) -> tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    posture_score = _score_posture(tenant_id)
    people_access_fallback = _people_access_fallback()
    onboarding_status_fallback = _onboarding_status_fallback()

    async with httpx.AsyncClient(timeout=settings.SERVICE_TIMEOUT, verify=settings.UPSTREAM_TLS_VERIFY) as client:
        people_access, onboarding_status = await asyncio.gather(
            _fetch_service_payload(
                client,
                f"{settings.IAM_AGENT_URL}/api/v1/iam/dashboard-snapshot",
                tenant_id,
                people_access_fallback,
            ),
            _fetch_service_payload(
                client,
                f"{settings.IAM_AGENT_URL}/api/v1/onboarding/status",
                tenant_id,
                onboarding_status_fallback,
            ),
        )

    return posture_score, people_access, onboarding_status


async def _build_operator_overview(tenant_id: str) -> Dict[str, Any]:
    posture_score, people_access, onboarding_status = await _load_operator_context(tenant_id)
    now_queue, source_health = await asyncio.gather(
        asyncio.to_thread(
            _now_queue_service.build_queue,
            tenant_id,
            posture_score,
            people_access,
            onboarding_status,
        ),
        _build_source_health(),
    )

    return {
        "tenant_id": tenant_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "posture_score": posture_score,
        "now_queue": now_queue,
        "recommendations": build_recommendations(posture_score, people_access, onboarding_status),
        "ai_risk_summary": _ai_risk_summary_service.build_summary(tenant_id),
        "source_health": {
            "tenant_id": tenant_id,
            **source_health,
        },
    }


def _security_pulse_from_posture(posture_score: Dict[str, Any]) -> Dict[str, Any]:
    def domain_val(domain: str) -> int:
        score_payload = posture_score.get("domain_scores", {}).get(domain, {})
        return score_payload.get("score_adjusted") or score_payload.get("score") or 0

    return {
        "overall_score": posture_score.get("overall_score", 68),
        "breakdown": {
            "identity": domain_val("identity"),
            "cloud": domain_val("cloud"),
            "endpoint": domain_val("endpoint"),
            "detection": domain_val("app"),
        },
        "breakdown_explanations": {
            "identity": "Identity posture derived from IAM-related findings and coverage.",
            "cloud": "Cloud posture derived from CSPM findings and recent cloud scans.",
            "endpoint": "Endpoint posture derived from connected endpoint coverage and agent reporting.",
            "detection": "Application/security detection posture derived from app and code findings.",
        },
        "trend": {
            "change": 0,
            "period": "last 7 days",
        },
    }

@router.get("/{tenant_id}/dashboard-snapshot")
async def get_dashboard_snapshot(
    tenant_id: str,
):
    """
    Get comprehensive dashboard snapshot for welcome dashboard.
    Returns security pulse, incidents, posture, IAM, health, and recommendations.
    """
    posture_score, people_access, onboarding_status = await _load_operator_context(tenant_id)
    recommendations = build_recommendations(posture_score, people_access, onboarding_status)
    open_incidents = await asyncio.to_thread(_now_queue_service.list_open_incidents, tenant_id)

    return {
        "tenant_id": tenant_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "security_pulse": _security_pulse_from_posture(posture_score),
        "open_incidents": open_incidents,
        "cloud_posture": build_cloud_posture_snapshot(posture_score),
        "ai_risk": _ai_risk_summary_service.build_summary(tenant_id),
        "people_access": people_access,
        "health": build_dashboard_health(onboarding_status, posture_score),
        "recommendations": recommendations,
        "first_value": build_first_value_section(tenant_id, posture_score, people_access),
    }


@router.get("/{tenant_id}/dashboard-health")
async def get_dashboard_health(
    tenant_id: str,
):
    """Get dashboard health and usage statistics."""
    posture_score = _score_posture(tenant_id)
    onboarding_status_fallback = {
        "idp_connected": False,
        "cloud_connected": False,
        "endpoint_deployed": False,
        "ticketing_health": None,
        "cloud_health": None,
    }
    async with httpx.AsyncClient(timeout=settings.SERVICE_TIMEOUT, verify=settings.UPSTREAM_TLS_VERIFY) as client:
        onboarding_status = await _fetch_service_payload(
            client,
            f"{settings.IAM_AGENT_URL}/api/v1/onboarding/status",
            tenant_id,
            onboarding_status_fallback,
        )
    return build_dashboard_health(onboarding_status, posture_score)


@router.get("/{tenant_id}/recommendations")
async def get_recommendations(
    tenant_id: str,
):
    """Get AI-generated recommendations for the tenant."""
    posture_score, people_access, onboarding_status = await _load_operator_context(tenant_id)

    return {
        "recommendations": build_recommendations(posture_score, people_access, onboarding_status),
    }


@router.get("/{tenant_id}/ai-risk-summary")
async def get_ai_risk_summary(
    tenant_id: str,
    lookback_days: int = Query(default=7, ge=1, le=90),
):
    """Get AI-risk summary for the core dashboard."""
    return _ai_risk_summary_service.build_summary(tenant_id, lookback_days=lookback_days)


@router.get("/{tenant_id}/now-queue")
async def get_now_queue(
    tenant_id: str,
):
    """Get the cross-domain operator queue for the main dashboard."""
    posture_score, people_access, onboarding_status = await _load_operator_context(tenant_id)

    return _now_queue_service.build_queue(
        tenant_id,
        posture_score,
        people_access,
        onboarding_status,
    )


@router.get("/{tenant_id}/operator-overview")
async def get_operator_overview(
    tenant_id: str,
):
    """Get a composite operator payload for the Now dashboard and War Room."""
    return await _build_operator_overview(tenant_id)
