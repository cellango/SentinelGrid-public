"""
Job handlers for async scans.

These handlers invoke scanners, parse results, and persist assets/findings.
"""

import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any

from sg_core.jobs import parsers, executors
from sg_core.cloud.registry import (
    CLOUD_RESOURCE_BASELINE_SCANNER_ID,
    canonical_provider_id,
    get_cloud_target,
    resolve_scanner_alias,
)
from sg_core.cloud.adapters import create_cloud_adapter, provider_has_adapter
from sg_core.cloud.baseline import (
    ADMIN_PORT_RESTRICT_ACTION,
    active_cloud_findings_from_checks,
    admin_port_change_description,
    admin_port_change_guidance,
    admin_port_cidrs_required_plan,
    admin_port_open_from_checks,
    cloud_resource_baseline_checks,
    fixed_target_ref,
    posture_framework,
    posture_remediation_plan,
    posture_remediation_status,
    posture_status,
    summarize_cloud_baseline,
)
from sg_core.cloud.baseline_state import load_cloud_baseline_state
from sg_core.cloud.targets import CloudTargetContext, cloud_target_context
from sqlalchemy import text

logger = logging.getLogger(__name__)


def _get_or_create_asset(session, tenant_id, asset_type, external_id=None, name=None, metadata=None):
    row = None
    if external_id:
        row = session.execute(
            text(
                "SELECT id FROM assets WHERE tenant_id = :tenant_id AND external_id = :external_id AND asset_type = :asset_type"
            ),
            {"tenant_id": tenant_id, "external_id": external_id, "asset_type": asset_type},
        ).first()
    if row:
        return row.id
    res = session.execute(
        text(
            """
            INSERT INTO assets (tenant_id, asset_type, external_id, name, metadata, created_at, updated_at)
            VALUES (:tenant_id, :asset_type, :external_id, :name, :metadata, now(), now())
            RETURNING id
            """
        ),
        {
            "tenant_id": tenant_id,
            "asset_type": asset_type,
            "external_id": external_id,
            "name": name or external_id or asset_type,
            "metadata": json.dumps(metadata or {}),
        },
    ).first()
    session.commit()
    return res.id


def _insert_findings(session, tenant_id, asset_id, findings, scan_id=None, scanner_id=None):
    for f in findings:
        # Persist evidence/raw_payload as JSON strings to avoid psycopg adapting dicts
        evidence_json = json.dumps(f.get("evidence") or {})
        raw_json = json.dumps(f.get("raw_payload") or {})
        detected_at = f.get("detected_at") or datetime.utcnow().isoformat()
        session.execute(
            text(
                """
                INSERT INTO findings
                    (tenant_id, source_tool, asset_id, asset_type, severity, category, title, description, remediation, evidence, raw_payload, detected_at, created_at, updated_at, scan_id, scanner_id, fingerprint, tags)
                VALUES
                    (:tenant_id, :source_tool, :asset_id, :asset_type, :severity, :category, :title, :description, :remediation, :evidence, :raw_payload, :detected_at, now(), now(), :scan_id, :scanner_id, :fingerprint, :tags)
                """
            ),
            {
                "tenant_id": tenant_id,
                "source_tool": f.get("source_tool"),
                "asset_id": asset_id,
                "asset_type": f.get("asset_type"),
                "severity": f.get("severity"),
                "category": f.get("category"),
                "title": f.get("title"),
                "description": f.get("description"),
                "remediation": f.get("remediation"),
                "evidence": evidence_json,
                "raw_payload": raw_json,
                "detected_at": detected_at,
                "scan_id": scan_id,
                "scanner_id": scanner_id or f.get("source_tool"),
                "fingerprint": f.get("fingerprint"),
                "tags": json.dumps(f.get("tags") or {}),
            },
        )
    session.commit()


def handle_cloud_scan(session, job: Dict[str, Any], scan_id=None, scanner_id=None):
    logger.info(f"[JOB] Cloud scan for tenant={job.get('tenant_id')} payload={job.get('payload')}")
    tenant_id = job.get("tenant_id")
    payload = job.get("payload") or {}
    dry_run = os.getenv("SCANNER_DRY_RUN", "true").lower() in ("1", "true", "yes")
    prowler_raw = executors.run_scanner("prowler", payload, dry_run=dry_run)
    trivy_raw = executors.run_scanner("trivy", payload, dry_run=dry_run)
    prowler_findings = parsers.parse_prowler_json(prowler_raw)
    trivy_findings = parsers.parse_trivy_json(trivy_raw)
    # Create asset (cloud account) and save findings
    asset_id = _get_or_create_asset(session, tenant_id, "cloud_account", payload.get("cloud_connector_id"))
    _insert_findings(session, tenant_id, asset_id, prowler_findings + trivy_findings, scan_id=scan_id, scanner_id=scanner_id)
    return {"status": "ok", "details": f"stored {len(prowler_findings) + len(trivy_findings)} findings"}


def _load_connected_cloud_account(session, tenant_id: str, target_context: CloudTargetContext):
    account = session.execute(
        text(
            """
            SELECT id, account_id, account_name, metadata
            FROM customer_cloud_accounts
            WHERE customer_id = :tenant_id
              AND cloud_provider = :provider
              AND account_id = :account_id
            ORDER BY connected_at DESC NULLS LAST, created_at DESC
            LIMIT 1
            """
        ),
        {"tenant_id": tenant_id, "provider": target_context.provider, "account_id": target_context.account_id},
    ).mappings().first()
    if not account:
        raise RuntimeError(f"No {target_context.provider} cloud account is connected for target {target_context.target_id}")
    return account


def _insert_cloud_posture_findings(
    session,
    tenant_id: str,
    cloud_account_id: str,
    scan_id: str,
    checks: list[dict],
    target_context: CloudTargetContext,
):
    check_ids = [check["check_id"] for check in checks]
    if check_ids:
        session.execute(
            text(
                """
                UPDATE posture_findings
                SET status = 'resolved',
                    remediation_status = COALESCE(remediation_status, 'resolved'),
                    updated_at = now()
                WHERE tenant_id = :tenant_id
                  AND cloud_account_id = :cloud_account_id
                  AND check_id = ANY(:check_ids)
                  AND status IN ('open', 'in_progress')
                """
            ),
            {"tenant_id": tenant_id, "cloud_account_id": cloud_account_id, "check_ids": check_ids},
        )

    for check in checks:
        status = posture_status(check)
        remediation_status = posture_remediation_status(check)
        session.execute(
            text(
                """
                INSERT INTO posture_findings (
                    tenant_id, cloud_account_id, scan_id, check_id, title, description,
                    severity, resource_id, service, category, framework, remediation,
                    status, remediation_status, remediation_plan, soc2_criteria
                )
                VALUES (
                    :tenant_id, :cloud_account_id, :scan_id, :check_id, :title, :description,
                    :severity, :resource_id, :service, :category, :framework, :remediation,
                    :status, :remediation_status, CAST(:remediation_plan AS jsonb), CAST(:soc2_criteria AS jsonb)
                )
                """
            ),
            {
                "tenant_id": tenant_id,
                "cloud_account_id": cloud_account_id,
                "scan_id": scan_id,
                "check_id": check["check_id"],
                "title": check["title"],
                "description": check["description"],
                "severity": check["severity"],
                "resource_id": target_context.asset_external_id,
                "service": check["service"],
                "category": check["category"],
                "framework": posture_framework(target_context),
                "remediation": check["remediation"],
                "status": status,
                "remediation_status": remediation_status,
                "remediation_plan": json.dumps(posture_remediation_plan(check, target_context)),
                "soc2_criteria": json.dumps(["CC6.6", "CC7.1"]),
            },
        )


def _cloud_admin_port_change_plan(adapter, firewall: dict, admin_ssh_cidrs, target_context: CloudTargetContext):
    if admin_ssh_cidrs:
        return adapter.plan_change(
            {},
            {"firewall": firewall, "admin_ssh_cidrs": admin_ssh_cidrs},
        ).raw_plan

    return admin_port_cidrs_required_plan(adapter, firewall, target_context, port=22)


def _create_cloud_fix_group_and_change_request(
    session,
    tenant_id: str,
    scan_id: str,
    cloud_account_id: str,
    server: dict,
    firewall: dict,
    scope: str,
    proposed_diff: dict,
    target_context: CloudTargetContext,
):
    cr_id = str(uuid.uuid4())
    fg_id = str(uuid.uuid4())
    now = datetime.utcnow()
    firewall_id = target_context.relationship_external_id("firewall_policy")
    session.execute(
        text(
            """
            INSERT INTO infrastructure_change_requests (
                id, tenant_id, cloud_account_id, scan_id, provider, action_type,
                status, server_id, firewall_id, scope_hash, pre_state, proposed_diff,
                approval_required, created_at, updated_at
            )
            VALUES (
                :id, :tenant_id, :cloud_account_id, :scan_id, :provider, :action_type,
                'draft', :server_id, :firewall_id, :scope_hash, CAST(:pre_state AS jsonb),
                CAST(:proposed_diff AS jsonb), true, :created_at, :updated_at
            )
            """
        ),
        {
            "id": cr_id,
            "tenant_id": tenant_id,
            "cloud_account_id": cloud_account_id,
            "scan_id": scan_id,
            "provider": target_context.provider,
            "action_type": ADMIN_PORT_RESTRICT_ACTION,
            "server_id": target_context.account_id,
            "firewall_id": firewall_id,
            "scope_hash": scope,
            "pre_state": json.dumps({"server": server, "firewall": firewall}),
            "proposed_diff": json.dumps(proposed_diff),
            "created_at": now,
            "updated_at": now,
        },
    )

    guidance = admin_port_change_guidance(target_context, cr_id, port=22)
    session.execute(
        text(
            """
            INSERT INTO fix_groups (
                id, tenant_id, scan_id, type, description, fixed_in_target,
                priority, sla_due, status, created_at, updated_at, ai_guidance
            )
            VALUES (
                :id, :tenant_id, :scan_id, 'config_change', :description, :fixed_in_target,
                'P1', :sla_due, 'open', :created_at, :updated_at, CAST(:ai_guidance AS jsonb)
            )
            """
        ),
        {
            "id": fg_id,
            "tenant_id": tenant_id,
            "scan_id": scan_id,
            "description": admin_port_change_description(target_context),
            "fixed_in_target": fixed_target_ref(target_context, "firewall_policy"),
            "sla_due": (now + timedelta(days=7)).replace(microsecond=0),
            "created_at": now,
            "updated_at": now,
            "ai_guidance": json.dumps(guidance),
        },
    )
    session.execute(
        text(
            """
            INSERT INTO fix_group_assets (fix_group_id, tenant_id, asset_ref, asset_type)
            VALUES (:fix_group_id, :tenant_id, :asset_ref, :asset_type)
            ON CONFLICT (fix_group_id, asset_ref) DO NOTHING
            """
        ),
        {
            "fix_group_id": fg_id,
            "tenant_id": tenant_id,
            "asset_ref": target_context.asset_external_id,
            "asset_type": target_context.asset_type,
        },
    )
    session.execute(
        text(
            """
            UPDATE infrastructure_change_requests
            SET fix_group_id = :fix_group_id, updated_at = now()
            WHERE id = :id AND tenant_id = :tenant_id
            """
        ),
        {"fix_group_id": fg_id, "id": cr_id, "tenant_id": tenant_id},
    )
    return cr_id, fg_id


def handle_cloud_resource_baseline_scan(session, job: Dict[str, Any], scan_id=None, scanner_id=None):
    """Run provider-targeted cloud baseline controls through the generic scanner ID."""

    payload = dict(job.get("payload") or {})
    requested_scanner = scanner_id or payload.get("scanner_id") or CLOUD_RESOURCE_BASELINE_SCANNER_ID
    scanner_resolution = resolve_scanner_alias(requested_scanner)
    effective_scanner_id = scanner_resolution["scanner"] or CLOUD_RESOURCE_BASELINE_SCANNER_ID
    target_ref = (
        payload.get("target_ref")
        or payload.get("target")
        or job.get("target_ref")
        or scanner_resolution.get("target")
    )
    target_config = get_cloud_target(target_ref) if target_ref else None
    target_context = cloud_target_context(target_ref, target_config=target_config)
    target_ref = target_context.target_id
    target_config = target_context.raw

    provider = canonical_provider_id(target_context.provider)
    if not provider_has_adapter(provider):
        raise RuntimeError(f"cloud-resource-baseline does not have an adapter for provider {provider}")

    payload["scanner_id"] = effective_scanner_id
    payload["requested_scanner_id"] = scanner_resolution["requested_scanner"]
    if target_ref:
        payload["target_ref"] = target_ref
    if target_config:
        payload["cloud_target_config"] = target_config

    result = _run_cloud_resource_baseline_scan(
        session,
        {**job, "job_type": "cloud_resource_baseline_scan", "payload": payload},
        target_context=target_context,
        provider=provider,
        scan_id=scan_id,
        scanner_id=effective_scanner_id,
    )
    result["scanner_id"] = effective_scanner_id
    result["requested_scanner_id"] = scanner_resolution["requested_scanner"]
    result["target_ref"] = target_ref
    return result


def _run_cloud_resource_baseline_scan(
    session,
    job: Dict[str, Any],
    *,
    target_context: CloudTargetContext,
    provider: str,
    scan_id=None,
    scanner_id=None,
):
    tenant_id = job.get("tenant_id")
    payload = job.get("payload") or {}
    scanner_id = scanner_id or payload.get("scanner_id") or CLOUD_RESOURCE_BASELINE_SCANNER_ID

    account = _load_connected_cloud_account(session, tenant_id, target_context)
    state = load_cloud_baseline_state(provider, account, payload, target_context)

    adapter = create_cloud_adapter(provider)
    checks = cloud_resource_baseline_checks(
        adapter,
        state.server,
        state.firewall,
        target_context,
        state.target_metadata,
    )
    asset_id = _get_or_create_asset(
        session,
        tenant_id,
        target_context.asset_type,
        target_context.asset_external_id,
        name=target_context.account_name,
        metadata=state.target_metadata,
    )
    findings = active_cloud_findings_from_checks(
        checks,
        target_context,
        scanner_id=scanner_id,
        server=state.server,
        firewall=state.firewall,
        firewall_policy=adapter.normalize_firewall(state.firewall),
    )
    if findings:
        _insert_findings(session, tenant_id, asset_id, findings, scan_id=scan_id, scanner_id=scanner_id)
    _insert_cloud_posture_findings(session, tenant_id, state.cloud_account_id, scan_id, checks, target_context)

    change_request_id = None
    fix_group_id = None
    if admin_port_open_from_checks(checks, port=22):
        admin_cidrs = payload.get("admin_ssh_cidrs") or state.account_metadata.get("admin_ssh_cidrs")
        proposed_diff = _cloud_admin_port_change_plan(adapter, state.firewall, admin_cidrs, target_context)
        change_request_id, fix_group_id = _create_cloud_fix_group_and_change_request(
            session=session,
            tenant_id=tenant_id,
            scan_id=scan_id,
            cloud_account_id=state.cloud_account_id,
            server=state.server,
            firewall=state.firewall,
            scope=state.scope_hash,
            proposed_diff=proposed_diff,
            target_context=target_context,
        )

    summary = summarize_cloud_baseline(
        checks,
        target_context,
        change_request_id=change_request_id,
        scope=state.scope_hash,
        scanner_id=scanner_id,
    )
    summary["fix_group_id"] = fix_group_id
    session.commit()
    return {
        "status": "ok",
        "details": f"stored {len(findings)} active cloud findings",
        **summary,
    }


def handle_git_scan(session, job: Dict[str, Any], scan_id=None, scanner_id=None):
    logger.info(f"[JOB] Git scan for tenant={job.get('tenant_id')} payload={job.get('payload')}")
    tenant_id = job.get("tenant_id")
    payload = job.get("payload") or {}
    dry_run = os.getenv("SCANNER_DRY_RUN", "true").lower() in ("1", "true", "yes")
    raw = executors.run_git_scanners(payload, dry_run=dry_run)
    gitleaks_findings = parsers.parse_gitleaks_json(raw.get("gitleaks"))
    checkov_findings = parsers.parse_checkov_json(raw.get("checkov") or {})
    asset_id = _get_or_create_asset(session, tenant_id, "source_repo", payload.get("repo_path"))
    _insert_findings(session, tenant_id, asset_id, gitleaks_findings + checkov_findings, scan_id=scan_id, scanner_id=scanner_id)
    return {"status": "ok", "details": f"stored {len(gitleaks_findings) + len(checkov_findings)} findings"}


def handle_app_scan(session, job: Dict[str, Any], scan_id=None, scanner_id=None):
    logger.info(f"[JOB] App scan for tenant={job.get('tenant_id')} payload={job.get('payload')}")
    tenant_id = job.get("tenant_id")
    payload = job.get("payload") or {}
    dry_run = os.getenv("SCANNER_DRY_RUN", "true").lower() in ("1", "true", "yes")
    raw = executors.run_app_scanners(payload, dry_run=dry_run)
    zap_findings = parsers.parse_zap_json(raw.get("zap") or {})
    semgrep_findings = parsers.parse_semgrep_json(raw.get("semgrep") or {})
    asset_id = _get_or_create_asset(session, tenant_id, "app_url", payload.get("target_url"))
    _insert_findings(session, tenant_id, asset_id, zap_findings + semgrep_findings, scan_id=scan_id, scanner_id=scanner_id)
    return {"status": "ok", "details": f"stored {len(zap_findings) + len(semgrep_findings)} findings"}


def handle_ai_summary(session, job: Dict[str, Any], scan_id=None, scanner_id=None):
    logger.info(f"[JOB] AI summary for tenant={job.get('tenant_id')}")
    tenant_id = job.get("tenant_id")
    # No dedicated table for summaries yet; store a info-level finding with summary payload
    summary = {"requests": 0, "tokens_in": 0, "tokens_out": 0}
    # Placeholder evidence until a real summary job is wired
    finding = {
        "source_tool": "ai_daily_summary",
        "severity": "info",
        "category": "ai_summary",
        "title": "AI daily summary",
        "description": "Daily AI usage summary",
        "remediation": "",
        "detected_at": datetime.utcnow().isoformat(),
        "asset_type": "ai",
        "external_id": tenant_id,
        "raw_payload": summary,
        "evidence": summary,
    }
    asset_id = _get_or_create_asset(session, tenant_id, "ai", tenant_id)
    _insert_findings(session, tenant_id, asset_id, [finding], scan_id=scan_id, scanner_id=scanner_id)
    return {"status": "ok", "details": "ai summary stored"}


def handle_golden_image(session, job: Dict[str, Any], scan_id=None, scanner_id=None):
    logger.info(f"[JOB] Golden image build payload={job.get('payload')}")
    tenant_id = job.get("tenant_id")
    payload = job.get("payload") or {}
    # Store an info finding representing the build request
    finding = {
        "source_tool": "golden_image_build",
        "severity": "info",
        "category": "image_build",
        "title": "Golden image build requested",
        "description": f"Images: {payload.get('image_types', [])}",
        "remediation": "",
        "detected_at": datetime.utcnow().isoformat(),
        "asset_type": "image_build",
        "external_id": "golden-image",
        "raw_payload": payload,
        "evidence": payload,
    }
    asset_id = _get_or_create_asset(session, tenant_id, "image_build", "golden-image")
    _insert_findings(session, tenant_id, asset_id, [finding], scan_id=scan_id, scanner_id=scanner_id)
    return {"status": "ok", "details": "golden image build recorded"}
