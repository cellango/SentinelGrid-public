"""Canonical entity and evidence helpers for operator-facing security stories."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import quote


CanonicalEntity = Dict[str, Any]
CanonicalEvidence = Dict[str, Any]
CanonicalStorySummary = Dict[str, Any]


def _clean_string(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _clean_metadata(metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    cleaned: Dict[str, Any] = {}
    for key, value in (metadata or {}).items():
        if value in (None, "", [], {}):
            continue
        cleaned[key] = value
    return cleaned


def _domain_from_provider(provider: Optional[str]) -> str:
    provider_name = (provider or "").lower()
    if provider_name in {"aws", "azure", "gcp", "google_cloud"}:
        return "cloud"
    if provider_name in {"git", "github", "gitlab", "bitbucket"}:
        return "application"
    if provider_name in {"openai", "anthropic", "google_ai", "bedrock"}:
        return "ai"
    return "security"


def _domain_label(domain: Optional[str]) -> str:
    normalized = _clean_string(domain) or "security"
    mapping = {
        "identity": "Identity",
        "endpoint": "Endpoint",
        "cloud": "Cloud",
        "application": "Application",
        "ai": "AI",
        "security": "Security",
    }
    return mapping.get(normalized, normalized.replace("_", " ").title())


def _href_for_entity(entity_type: str, entity_id: str, domain: str) -> str:
    if entity_type == "identity":
        return f"/dashboard/iam/people?user_id={quote(entity_id)}"
    if entity_type == "device":
        return f"/dashboard/endpoint-protection?asset_id={quote(entity_id)}"
    if entity_type == "resource" and domain == "cloud":
        return "/dashboard/compliance"
    if entity_type == "resource" and domain == "application":
        return "/dashboard/posture"
    if entity_type == "ai_app":
        return "/dashboard/compliance/ai-activity"
    return "/dashboard"


def _href_for_evidence(evidence_type: str, evidence_id: str) -> Optional[str]:
    if evidence_type == "alert":
        return f"/dashboard/alerts/{quote(evidence_id)}"
    if evidence_type == "incident":
        return f"/dashboard/incidents/{quote(evidence_id)}"
    if evidence_type == "ticket":
        return f"/dashboard/tickets/{quote(evidence_id)}"
    if evidence_type == "detection_rule":
        return f"/dashboard/siem/detection-rules/{quote(evidence_id)}"
    if evidence_type == "playbook":
        return f"/dashboard/playbooks?playbook_id={quote(evidence_id)}"
    return None


def _append_unique(items: List[Dict[str, Any]], seen: set[tuple[str, str]], item: Optional[Dict[str, Any]]) -> None:
    if not item:
        return
    key = (_clean_string(item.get("type")) or "", _clean_string(item.get("id")) or "")
    if not all(key):
        return
    if key in seen:
        return
    seen.add(key)
    items.append(item)


def _entity_ref(
    entity_type: str,
    entity_id: Any,
    *,
    label: Optional[str] = None,
    domain: Optional[str] = None,
    role: Optional[str] = None,
    provider: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[CanonicalEntity]:
    normalized_id = _clean_string(entity_id)
    if not normalized_id:
        return None
    normalized_domain = _clean_string(domain) or _domain_from_provider(provider)
    item: CanonicalEntity = {
        "type": entity_type,
        "id": normalized_id,
        "label": _clean_string(label) or normalized_id,
        "domain": normalized_domain,
        "href": _href_for_entity(entity_type, normalized_id, normalized_domain),
    }
    if role:
        item["role"] = role
    if provider:
        item["provider"] = provider
    cleaned_metadata = _clean_metadata(metadata)
    if cleaned_metadata:
        item["metadata"] = cleaned_metadata
    return item


def _evidence_ref(
    evidence_type: str,
    evidence_id: Any,
    *,
    title: Optional[str] = None,
    domain: Optional[str] = None,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    source: Optional[str] = None,
    href: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[CanonicalEvidence]:
    normalized_id = _clean_string(evidence_id)
    if not normalized_id:
        return None
    item: CanonicalEvidence = {
        "type": evidence_type,
        "id": normalized_id,
        "title": _clean_string(title) or normalized_id,
    }
    if domain:
        item["domain"] = domain
    if severity:
        item["severity"] = severity
    if status:
        item["status"] = status
    if source:
        item["source"] = source
    item["href"] = href or _href_for_evidence(evidence_type, normalized_id)
    cleaned_metadata = _clean_metadata(metadata)
    if cleaned_metadata:
        item["metadata"] = cleaned_metadata
    return item


def _normalize_existing_entity(entry: Any) -> Optional[CanonicalEntity]:
    if not isinstance(entry, dict):
        return None
    return _entity_ref(
        _clean_string(entry.get("type")) or "resource",
        entry.get("id"),
        label=entry.get("label"),
        domain=entry.get("domain"),
        role=entry.get("role"),
        provider=entry.get("provider"),
        metadata=entry.get("metadata"),
    )


def _normalize_existing_evidence(entry: Any) -> Optional[CanonicalEvidence]:
    if not isinstance(entry, dict):
        return None
    return _evidence_ref(
        _clean_string(entry.get("type")) or "attachment",
        entry.get("id"),
        title=entry.get("title"),
        domain=entry.get("domain"),
        severity=entry.get("severity"),
        status=entry.get("status"),
        source=entry.get("source"),
        href=entry.get("href"),
        metadata=entry.get("metadata"),
    )


def _domain_from_category(raw_payload: Dict[str, Any]) -> str:
    category = (
        _clean_string((raw_payload.get("sg") or {}).get("category"))
        or _clean_string(raw_payload.get("category"))
        or _clean_string((raw_payload.get("finding") or {}).get("type"))
    )
    if not category:
        if raw_payload.get("ai"):
            return "ai"
        if raw_payload.get("repo"):
            return "application"
        if raw_payload.get("cloud"):
            return "cloud"
        if raw_payload.get("host"):
            return "endpoint"
        if raw_payload.get("user") or raw_payload.get("identity"):
            return "identity"
        return "security"
    lower = category.lower()
    if lower in {"identity", "iam", "access", "authentication"}:
        return "identity"
    if lower in {"endpoint", "host", "process"}:
        return "endpoint"
    if lower in {"cloud", "network", "data", "storage"}:
        return "cloud"
    if lower in {"app", "application", "git", "repo", "secret"}:
        return "application"
    if lower in {"ai", "llm", "guardrail"}:
        return "ai"
    return "security"


def _extend_existing_story(
    raw_payload: Dict[str, Any],
    entities: List[CanonicalEntity],
    evidence: List[CanonicalEvidence],
    entity_seen: set[tuple[str, str]],
    evidence_seen: set[tuple[str, str]],
) -> None:
    for entry in raw_payload.get("entities") or []:
        _append_unique(entities, entity_seen, _normalize_existing_entity(entry))
    for entry in raw_payload.get("evidence") or []:
        _append_unique(evidence, evidence_seen, _normalize_existing_evidence(entry))


def build_story_context(
    *,
    raw_payload: Optional[Dict[str, Any]] = None,
    asset_id: Optional[str] = None,
    user_identifier: Optional[str] = None,
    detection_rule_id: Optional[str] = None,
    detection_rule_version_id: Optional[str] = None,
    playbook_id: Optional[str] = None,
    playbook_version_id: Optional[str] = None,
    related_detections: Optional[Iterable[Dict[str, Any]]] = None,
    ticket_id: Optional[str] = None,
    external_ticket_id: Optional[str] = None,
    external_ticket_provider: Optional[str] = None,
    cve_ids: Optional[Iterable[str]] = None,
) -> Dict[str, Any]:
    payload = raw_payload if isinstance(raw_payload, dict) else {}
    default_domain = _domain_from_category(payload)

    entities: List[CanonicalEntity] = []
    evidence: List[CanonicalEvidence] = []
    entity_seen: set[tuple[str, str]] = set()
    evidence_seen: set[tuple[str, str]] = set()
    domains: set[str] = set()

    _extend_existing_story(payload, entities, evidence, entity_seen, evidence_seen)

    def add_entity(item: Optional[CanonicalEntity]) -> None:
        if not item:
            return
        _append_unique(entities, entity_seen, item)
        if item.get("domain"):
            domains.add(str(item["domain"]))

    def add_evidence(item: Optional[CanonicalEvidence]) -> None:
        if not item:
            return
        _append_unique(evidence, evidence_seen, item)
        if item.get("domain"):
            domains.add(str(item["domain"]))

    user = payload.get("user") if isinstance(payload.get("user"), dict) else {}
    host = payload.get("host") if isinstance(payload.get("host"), dict) else {}
    repo = payload.get("repo") if isinstance(payload.get("repo"), dict) else {}
    ai = payload.get("ai") if isinstance(payload.get("ai"), dict) else {}
    cloud = payload.get("cloud") if isinstance(payload.get("cloud"), dict) else {}

    identity_id = (
        _clean_string(user_identifier)
        or _clean_string(user.get("email"))
        or _clean_string(user.get("id"))
        or _clean_string(user.get("name"))
        or _clean_string(ai.get("user_id"))
    )
    identity_label = (
        _clean_string(user.get("email"))
        or _clean_string(user.get("name"))
        or _clean_string(user.get("id"))
        or identity_id
    )
    add_entity(
        _entity_ref(
            "identity",
            identity_id,
            label=identity_label,
            domain="identity",
            role="affected_identity",
            provider=_clean_string((payload.get("identity") or {}).get("provider")),
            metadata={"email": user.get("email"), "name": user.get("name")},
        )
    )

    host_id = _clean_string(host.get("hostname")) or _clean_string(host.get("id"))
    asset_value = _clean_string(asset_id)
    add_entity(
        _entity_ref(
            "device",
            host_id or asset_value,
            label=_clean_string(host.get("hostname")) or asset_value,
            domain="endpoint",
            role="affected_asset",
            metadata={"host_id": host.get("id"), "ip": host.get("ip")},
        )
    )

    cloud_account = cloud.get("account") if isinstance(cloud.get("account"), dict) else {}
    cloud_provider = _clean_string(cloud.get("provider"))
    cloud_account_id = _clean_string(cloud_account.get("id"))
    add_entity(
        _entity_ref(
            "resource",
            f"{cloud_provider or 'cloud'}:{cloud_account_id}" if cloud_account_id else None,
            label=f"{(cloud_provider or 'cloud').upper()} account {cloud_account_id}" if cloud_account_id else None,
            domain="cloud",
            role="cloud_account",
            provider=cloud_provider,
            metadata={"account_id": cloud_account_id},
        )
    )

    repo_id = _clean_string(repo.get("id")) or _clean_string(repo.get("name"))
    add_entity(
        _entity_ref(
            "resource",
            f"repo:{repo_id}" if repo_id else None,
            label=_clean_string(repo.get("name")) or repo_id,
            domain="application",
            role="repository",
            provider="git",
            metadata={"branch": repo.get("branch")},
        )
    )

    ai_app_id = _clean_string(ai.get("app_id")) or _clean_string(ai.get("application"))
    ai_label = ai_app_id or _clean_string(ai.get("provider"))
    add_entity(
        _entity_ref(
            "ai_app",
            ai_app_id,
            label=ai_label,
            domain="ai",
            role="ai_application",
            provider=_clean_string(ai.get("provider")),
            metadata={"model": ai.get("model"), "policy_decision": ai.get("policy_decision")},
        )
    )

    if asset_value and not host_id and not cloud_account_id and not repo_id and not ai_app_id:
        add_entity(
            _entity_ref(
                "resource",
                asset_value,
                label=asset_value,
                domain=default_domain,
                role="affected_resource",
            )
        )

    incident_ids = list(payload.get("incident_ids") or payload.get("incidents") or [])
    incident_id = _clean_string(payload.get("incident_id"))
    if incident_id:
        incident_ids.append(incident_id)
    for linked_incident_id in incident_ids:
        if isinstance(linked_incident_id, dict):
            add_evidence(
                _evidence_ref(
                    "incident",
                    linked_incident_id.get("id"),
                    title=linked_incident_id.get("title") or "Related incident",
                    domain=default_domain,
                    severity=linked_incident_id.get("severity"),
                )
            )
        else:
            add_evidence(
                _evidence_ref(
                    "incident",
                    linked_incident_id,
                    title="Related incident",
                    domain=default_domain,
                )
            )

    for linked_detection in related_detections or []:
        detection_id = linked_detection.get("id") if isinstance(linked_detection, dict) else linked_detection
        detection_title = linked_detection.get("title") if isinstance(linked_detection, dict) else None
        detection_severity = linked_detection.get("severity") if isinstance(linked_detection, dict) else None
        add_evidence(
            _evidence_ref(
                "alert",
                detection_id,
                title=detection_title or "Linked alert",
                domain=default_domain,
                severity=detection_severity,
            )
        )

    for alert_id in payload.get("related_alert_ids") or []:
        add_evidence(
            _evidence_ref(
                "alert",
                alert_id,
                title="Linked alert",
                domain=default_domain,
            )
        )

    finding = payload.get("finding") if isinstance(payload.get("finding"), dict) else {}
    finding_type = _clean_string(finding.get("type"))
    finding_id = finding_type and ":".join(
        value for value in [finding_type, _clean_string(finding.get("path")), _clean_string(finding.get("line"))] if value
    )
    if finding_id:
        add_evidence(
            _evidence_ref(
                "finding",
                finding_id,
                title=finding_type.replace("_", " ").title(),
                domain=default_domain,
                severity=_clean_string(finding.get("severity")),
                metadata={"path": finding.get("path"), "line": finding.get("line")},
            )
        )

    add_evidence(
        _evidence_ref(
            "detection_rule",
            detection_rule_id,
            title=detection_rule_id,
            domain=default_domain,
            metadata={"version_id": detection_rule_version_id},
        )
    )
    add_evidence(
        _evidence_ref(
            "playbook",
            playbook_id,
            title=playbook_id,
            domain=default_domain,
            metadata={"version_id": playbook_version_id},
        )
    )

    if ticket_id:
        add_evidence(
            _evidence_ref(
                "ticket",
                ticket_id,
                title=f"Local ticket {ticket_id}",
                domain=default_domain,
                metadata={"provider": "internal"},
            )
        )
    elif external_ticket_id:
        add_evidence(
            _evidence_ref(
                "ticket",
                external_ticket_id,
                title=f"{external_ticket_provider or 'ticket'}:{external_ticket_id}",
                domain=default_domain,
                source=external_ticket_provider,
            )
        )

    for attachment in payload.get("evidence") or payload.get("attachments") or []:
        if isinstance(attachment, dict):
            attachment_id = attachment.get("id") or attachment.get("url") or attachment.get("filename") or attachment.get("name")
            add_evidence(
                _evidence_ref(
                    "attachment",
                    attachment_id,
                    title=attachment.get("name") or attachment.get("filename") or "Attachment",
                    href=attachment.get("url"),
                    metadata={"size": attachment.get("size"), "content_type": attachment.get("content_type")},
                )
            )
        else:
            add_evidence(_evidence_ref("attachment", attachment, title="Attachment"))

    for cve_id in cve_ids or []:
        add_evidence(
            _evidence_ref(
                "cve",
                cve_id,
                title=cve_id,
                domain=default_domain,
            )
        )

    if not domains:
        domains.add(default_domain)

    return {
        "entities": entities,
        "evidence": evidence,
        "story_domains": sorted(domains),
    }


def build_story_summary(
    *,
    story_context: Optional[Dict[str, Any]] = None,
    entities: Optional[Iterable[Dict[str, Any]]] = None,
    evidence: Optional[Iterable[Dict[str, Any]]] = None,
    story_domains: Optional[Iterable[str]] = None,
) -> CanonicalStorySummary:
    context = story_context or {}
    entity_items = [
        item
        for item in (context.get("entities") if isinstance(context, dict) else entities) or entities or []
        if isinstance(item, dict)
    ]
    evidence_items = [
        item
        for item in (context.get("evidence") if isinstance(context, dict) else evidence) or evidence or []
        if isinstance(item, dict)
    ]
    domains = [
        _clean_string(domain)
        for domain in (
            (context.get("story_domains") if isinstance(context, dict) else story_domains)
            or story_domains
            or []
        )
    ]
    domains = [domain for domain in domains if domain]
    if not domains:
        domains = [
            _clean_string(item.get("domain"))
            for item in [*entity_items, *evidence_items]
            if isinstance(item, dict) and _clean_string(item.get("domain"))
        ]
    unique_domains = list(dict.fromkeys(domain for domain in domains if domain)) or ["security"]

    primary_entity = entity_items[0] if entity_items else None
    entity_labels: List[str] = []
    for item in entity_items:
        label = _clean_string(item.get("label")) or _clean_string(item.get("id"))
        if label and label not in entity_labels:
            entity_labels.append(label)

    evidence_type_counts: Dict[str, int] = {}
    for item in evidence_items:
        evidence_type = _clean_string(item.get("type")) or "attachment"
        evidence_type_counts[evidence_type] = evidence_type_counts.get(evidence_type, 0) + 1

    if len(unique_domains) == 1:
        headline = f"{_domain_label(unique_domains[0])} story"
    elif len(unique_domains) <= 3:
        headline = f"{' + '.join(_domain_label(domain) for domain in unique_domains)} story"
    else:
        headline = f"{_domain_label(unique_domains[0])} + {len(unique_domains) - 1} more domains"

    detail_parts: List[str] = []
    if primary_entity:
        detail_parts.append(_clean_string(primary_entity.get("label")) or _clean_string(primary_entity.get("id")) or "Linked entity")
    elif entity_labels:
        detail_parts.append(f"{len(entity_labels)} linked {'entity' if len(entity_labels) == 1 else 'entities'}")
    if evidence_items:
        detail_parts.append(f"{len(evidence_items)} evidence item{'s' if len(evidence_items) != 1 else ''}")
    detail = " · ".join(detail_parts) if detail_parts else "No linked story context yet"

    return {
        "headline": headline,
        "detail": detail,
        "domains": unique_domains,
        "primary_entity": primary_entity,
        "entity_count": len(entity_items),
        "entity_labels": entity_labels[:3],
        "evidence_count": len(evidence_items),
        "evidence_types": [
            {"type": evidence_type, "count": count}
            for evidence_type, count in sorted(
                evidence_type_counts.items(),
                key=lambda item: (-item[1], item[0]),
            )
        ],
    }
