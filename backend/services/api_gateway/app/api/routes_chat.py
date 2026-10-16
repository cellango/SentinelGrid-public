"""Chat proxy routes with extra debug logging."""

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Header
import httpx
import logging
from sg_core.security import get_current_tenant
from sg_core.service_metrics import get_service_metrics
from app.core.config import settings

logger = logging.getLogger(__name__)
runtime_metrics = get_service_metrics("api-gateway")

# No prefix here; main.py mounts us at /api/v1/chat
router = APIRouter(tags=["chat"])


def _build_proxy_headers(
    current_tenant_id: str,
    x_realm: Optional[str] = None,
    *,
    include_internal_token: bool = False,
) -> dict[str, str]:
    headers = {"X-Tenant-ID": current_tenant_id}
    if x_realm:
        headers["X-Realm"] = x_realm
    if include_internal_token:
        token = getattr(settings, "INTERNAL_SERVICE_TOKEN", None)
        if token:
            headers["Authorization"] = f"Bearer {token}"
    return headers


def _with_authenticated_tenant(payload: dict, current_tenant_id: str) -> dict:
    requested_tenant_id = payload.get("tenant_id")
    if requested_tenant_id and str(requested_tenant_id) != str(current_tenant_id):
        raise HTTPException(
            status_code=403,
            detail="Tenant ID mismatch. You can only access your own tenant's data.",
        )
    normalized_payload = dict(payload)
    normalized_payload["tenant_id"] = current_tenant_id
    return normalized_payload


def _record_proxy_outcome(route: str, outcome: str) -> None:
    runtime_metrics.increment_counter(
        "gateway_proxy_requests_total",
        route=route,
        upstream="model_gateway",
        outcome=outcome,
    )


def _extract_active_agent(payload: dict[str, Any], context: dict[str, Any]) -> str | None:
    active_agent = payload.get("active_agent") or context.get("active_agent")
    dashboard_data = context.get("dashboard_data") if isinstance(context, dict) else None
    if not active_agent and isinstance(dashboard_data, dict):
        active_agent = dashboard_data.get("active_agent")
    return str(active_agent) if active_agent else None


def _is_compliance_chat(query: str, payload: dict[str, Any], context: dict[str, Any]) -> bool:
    active_agent = _extract_active_agent(payload, context)
    if active_agent == "compliance_agent":
        return True
    if str(payload.get("module") or "").lower() == "compliance":
        return True

    query_lower = query.strip().lower()
    if query_lower.startswith("/compliance"):
        return True

    compliance_terms = {
        "compliance",
        "soc 2",
        "soc2",
        "audit",
        "framework",
        "control",
        "evidence",
        "attestation",
        "pci",
        "hipaa",
        "iso 27001",
        "nist 800-171",
    }
    return any(term in query_lower for term in compliance_terms)


def _compliance_retrieval_categories(query: str) -> list[str]:
    query_lower = query.lower()
    categories: set[str] = {"controls", "gaps"}
    if any(term in query_lower for term in ("report", "audit", "attestation", "export")):
        categories.add("reports")
    if any(term in query_lower for term in ("evidence", "artifact", "proof", "package")):
        categories.add("evidence")
    if query_lower.startswith("/compliance") or "compliance" in query_lower:
        categories.update({"reports", "evidence"})
    return [category for category in ("reports", "controls", "evidence", "gaps") if category in categories]


def _user_proxy_headers(current_tenant_id: str, authorization: str | None, x_realm: str | None) -> dict[str, str]:
    headers = {"X-Tenant-ID": current_tenant_id, "Content-Type": "application/json"}
    if authorization:
        headers["Authorization"] = authorization
    elif getattr(settings, "INTERNAL_SERVICE_TOKEN", None):
        headers["Authorization"] = f"Bearer {settings.INTERNAL_SERVICE_TOKEN}"
    if x_realm:
        headers["X-Realm"] = x_realm
    return headers


async def _safe_json_request(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    headers: dict[str, str],
    params: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    try:
        response = await client.request(method, url, headers=headers, params=params)
        if response.status_code >= 400:
            logger.warning(
                "Compliance chat context fetch failed",
                extra={"url": url, "status": response.status_code},
            )
            return None
        data = response.json()
        return data if isinstance(data, dict) else {"items": data}
    except Exception as exc:
        logger.warning("Compliance chat context fetch error for %s: %s", url, exc)
        return None


def _summarize_coverage(coverage: dict[str, Any] | None) -> dict[str, Any]:
    if not coverage:
        return {"status": "unavailable", "items": [], "high_priority_gaps": []}

    items = []
    high_priority_gaps = []
    for framework in coverage.get("items", []) or []:
        controls = framework.get("controls") or []
        framework_summary = {
            "framework_id": framework.get("framework_id"),
            "framework_name": framework.get("framework_name"),
            "status": framework.get("status"),
            "control_count": framework.get("control_count"),
            "status_counts": framework.get("status_counts") or {},
            "average_confidence": framework.get("average_confidence"),
        }
        items.append(framework_summary)
        for control in controls:
            for gap in control.get("gaps") or []:
                if str(gap.get("severity") or "").lower() in {"critical", "high"}:
                    high_priority_gaps.append(
                        {
                            "framework_id": framework.get("framework_id"),
                            "control_id": control.get("control_id") or control.get("id"),
                            "title": gap.get("title"),
                            "severity": gap.get("severity"),
                            "summary": gap.get("remediation_hint") or gap.get("description"),
                        }
                    )

    return {
        "status": "available",
        "tenant_id": coverage.get("tenant_id"),
        "items": items,
        "framework_count": len(items),
        "high_priority_gaps": high_priority_gaps[:10],
        "high_priority_gap_count": len(high_priority_gaps),
    }


def _summarize_list_payload(payload: dict[str, Any] | None, fields: tuple[str, ...]) -> dict[str, Any]:
    if not payload:
        return {"status": "unavailable", "items": [], "count": 0}
    raw_items = payload.get("items") or payload.get("results") or []
    if not isinstance(raw_items, list):
        raw_items = []
    items = [
        {field: item.get(field) for field in fields if isinstance(item, dict) and field in item}
        for item in raw_items[:5]
        if isinstance(item, dict)
    ]
    return {
        "status": "available",
        "count": payload.get("count", len(raw_items)),
        "items": items,
    }


async def _log_compliance_chat_context_access(
    client: httpx.AsyncClient,
    *,
    tenant_id: str,
    realm_name: str | None,
    query: str,
    conversation_id: str | None,
    accessed_categories: list[str],
) -> None:
    sensitive_categories = [category for category in accessed_categories if category in {"evidence", "reports"}]
    if not sensitive_categories:
        return

    payload = {
        "tenant_id": tenant_id,
        "realm_name": realm_name or "unknown",
        "action": "compliance_chat_context_accessed",
        "action_category": "ai",
        "metadata": {
            "query": query[:500],
            "conversation_id": conversation_id,
            "accessed_categories": sensitive_categories,
            "source": "api_gateway.chat.dashboard",
        },
    }
    headers = {"Content-Type": "application/json"}
    if getattr(settings, "INTERNAL_SERVICE_TOKEN", None):
        headers["Authorization"] = f"Bearer {settings.INTERNAL_SERVICE_TOKEN}"

    try:
        await client.post(
            f"{settings.AUDIT_SERVICE_URL.rstrip('/')}/api/v1/audit/ai-activity",
            json=payload,
            headers=headers,
        )
    except Exception as exc:
        logger.warning("Failed to audit compliance chat context access: %s", exc)


async def _build_compliance_chat_context(
    client: httpx.AsyncClient,
    *,
    current_tenant_id: str,
    query: str,
    context: dict[str, Any],
    conversation_id: str | None,
    authorization: str | None,
    x_realm: str | None,
) -> dict[str, Any]:
    categories = _compliance_retrieval_categories(query)
    headers = _user_proxy_headers(current_tenant_id, authorization, x_realm)
    compliance_url = settings.COMPLIANCE_SERVICE_URL.rstrip("/")
    reporting_url = settings.REPORTING_SERVICE_URL.rstrip("/")

    coverage = await _safe_json_request(
        client,
        "GET",
        f"{compliance_url}/api/v1/compliance/coverage",
        headers=headers,
        params={"limit": 50, "offset": 0},
    )

    evidence = None
    if "evidence" in categories:
        evidence = await _safe_json_request(
            client,
            "GET",
            f"{compliance_url}/api/v1/compliance/evidence",
            headers=headers,
            params={"tenant_id": current_tenant_id, "limit": 5, "offset": 0},
        )

    reports = None
    if "reports" in categories:
        reports = await _safe_json_request(
            client,
            "GET",
            f"{reporting_url}/api/v1/reports/",
            headers=headers,
            params={"limit": 5, "offset": 0},
        )

    recommendations = await _safe_json_request(
        client,
        "GET",
        f"{compliance_url}/api/v1/compliance/agent/recommendations",
        headers=headers,
        params={"state": "proposed", "limit": 5, "offset": 0},
    )

    accessed_categories = ["controls", "gaps"]
    if evidence:
        accessed_categories.append("evidence")
    if reports:
        accessed_categories.append("reports")

    await _log_compliance_chat_context_access(
        client,
        tenant_id=current_tenant_id,
        realm_name=x_realm,
        query=query,
        conversation_id=conversation_id,
        accessed_categories=accessed_categories,
    )

    enriched = dict(context)
    enriched["active_agent"] = "compliance_agent"
    enriched["compliance_live_context"] = {
        "retrieval_categories": categories,
        "accessed_categories": accessed_categories,
        "coverage": _summarize_coverage(coverage),
        "evidence": _summarize_list_payload(
            evidence,
            ("id", "title", "review_status", "valid_until", "source_system"),
        ),
        "reports": _summarize_list_payload(
            reports,
            ("id", "name", "status", "template_id", "generated_at"),
        ),
        "recommendations": _summarize_list_payload(
            recommendations,
            ("id", "title", "state", "priority", "recommendation_type", "source_type"),
        ),
    }
    return enriched


@router.post("/vuln")
async def vuln_chat(
    payload: dict,
    current_tenant_id: str = Depends(get_current_tenant),
    x_realm: str | None = Header(None, alias="X-Realm"),
):
    """
    Proxy vuln/FixGroup chat to model_gateway (tenant-scoped).
    Expects payload {query, limit?, conversation_id?}
    """
    model_gateway = settings.MODEL_GATEWAY_URL.rstrip("/")
    headers = _build_proxy_headers(current_tenant_id, x_realm)
    normalized_payload = _with_authenticated_tenant(payload, current_tenant_id)
    try:
        async with httpx.AsyncClient(timeout=15.0, verify=settings.UPSTREAM_TLS_VERIFY) as client:
            resp = await client.post(
                f"{model_gateway}/api/v1/chat/vuln",
                json=normalized_payload,
                headers=headers,
            )
        if resp.status_code >= 400:
            _record_proxy_outcome("chat_vuln", "upstream_error")
            try:
                detail = resp.json()
            except Exception:
                detail = resp.text
            logger.error(
                "Model gateway chat error",
                extra={
                    "status": resp.status_code,
                    "detail": detail,
                    "tenant_id": current_tenant_id,
                },
            )
            raise HTTPException(status_code=resp.status_code, detail=detail)
        data = resp.json()
        _record_proxy_outcome("chat_vuln", "success")
        logger.info(
            "Chat/vuln success",
            extra={
                "tenant_id": current_tenant_id,
                "has_sources": bool(data.get("sources")),
            },
        )
        return data
    except HTTPException:
        raise
    except Exception as exc:
        _record_proxy_outcome("chat_vuln", "request_error")
        logger.error(
            "Chat gateway error",
            extra={"tenant_id": current_tenant_id, "error": str(exc)},
        )
        raise HTTPException(status_code=502, detail=f"Chat gateway error: {exc}")


@router.post("/dashboard")
async def dashboard_chat(
    payload: dict,
    current_tenant_id: str = Depends(get_current_tenant),
    x_realm: str | None = Header(None, alias="X-Realm"),
    authorization: str | None = Header(None, alias="Authorization"),
):
    """
    Proxy dashboard chat to model_gateway unified chat (/internal/llm/chat).
    Accepts {query or message, context?, conversation_id?}.
    """
    model_gateway = settings.MODEL_GATEWAY_URL.rstrip("/")
    headers = _build_proxy_headers(current_tenant_id, x_realm, include_internal_token=True)
    normalized_payload = _with_authenticated_tenant(payload, current_tenant_id)

    query = normalized_payload.get("query") or normalized_payload.get("message") or ""
    context = normalized_payload.get("context") or {}
    convo = normalized_payload.get("conversation_id")
    active_agent = _extract_active_agent(normalized_payload, context)

    if not query:
        _record_proxy_outcome("chat_dashboard", "bad_request")
        raise HTTPException(status_code=400, detail="Missing query/message")

    try:
        async with httpx.AsyncClient(timeout=20.0, verify=settings.UPSTREAM_TLS_VERIFY) as client:
            module = normalized_payload.get("module")
            if _is_compliance_chat(query, normalized_payload, context):
                module = "compliance"
                active_agent = active_agent or "compliance_agent"
                context = await _build_compliance_chat_context(
                    client,
                    current_tenant_id=current_tenant_id,
                    query=query,
                    context=context,
                    conversation_id=convo,
                    authorization=authorization,
                    x_realm=x_realm,
                )

            resp = await client.post(
                f"{model_gateway}/internal/llm/chat",
                json={
                    "query": query,
                    "tenant_id": current_tenant_id,
                    "module": module,
                    "active_agent": active_agent,
                    "context": context,
                    "conversation_id": convo,
                },
                headers=headers,
            )
        if resp.status_code >= 400:
            _record_proxy_outcome("chat_dashboard", "upstream_error")
            try:
                detail = resp.json()
            except Exception:
                detail = resp.text
            logger.error(
                "Dashboard chat error",
                extra={
                    "status": resp.status_code,
                    "detail": detail,
                    "tenant_id": current_tenant_id,
                },
            )
            raise HTTPException(status_code=resp.status_code, detail=detail)
        data = resp.json()
        if not data.get("response") and not data.get("text") and not data.get("message"):
            logger.warning(
                "Dashboard chat returned empty response",
                extra={"tenant_id": current_tenant_id, "payload": payload},
            )
        _record_proxy_outcome("chat_dashboard", "success")
        logger.info(
            "Dashboard chat success",
            extra={
                "tenant_id": current_tenant_id,
                "has_sources": bool(data.get("sources")),
            },
        )
        # Normalize a lightweight response for the frontend
        return {
            "reply": data.get("response") or data.get("text") or data.get("message", ""),
            "conversation_id": data.get("conversation_id"),
            "suggestions": data.get("suggestions", []),
            "sources": data.get("sources", []),
            "module": data.get("module", "general"),
            "answer_type": data.get("answer_type") or data.get("source_kind") or "knowledge_base",
            "source_kind": data.get("source_kind") or data.get("answer_type") or "knowledge_base",
            "retrieval_categories": data.get("retrieval_categories", []),
            "actions": data.get("actions", []),
        }
    except HTTPException:
        raise
    except Exception as exc:
        _record_proxy_outcome("chat_dashboard", "request_error")
        logger.error(
            "Dashboard chat gateway error",
            extra={"tenant_id": current_tenant_id, "error": str(exc)},
        )
        raise HTTPException(status_code=502, detail=f"Chat gateway error: {exc}")


@router.post("/suggestions")
async def chat_suggestions(
    payload: dict,
    current_tenant_id: str = Depends(get_current_tenant),
):
    """
    Provide chat suggestions. Currently returns an empty list to avoid 404/UI errors.
    Can be extended to call model_gateway once implemented.
    """
    logger.info("Chat suggestions requested", extra={"tenant_id": current_tenant_id})
    return {"suggestions": []}
