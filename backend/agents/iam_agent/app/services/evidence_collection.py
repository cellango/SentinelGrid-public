"""
Evidence Collection Service
Collects and manages evidence for compliance assessments
"""

import hashlib
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone
from enum import Enum

from app.services.keycloak_client import KeycloakClient

logger = logging.getLogger(__name__)


NIST_TO_SOC2_CONTROL_LINKS = {
    "AC-2": ["CC6.2", "CC6.3"],
    "AC-3": ["CC6.1", "CC6.7"],
    "AC-6": ["CC6.7", "CC6.8"],
    "IA-2": ["CC6.1", "CC6.6"],
    "AU-2": ["CC7.2", "CC8.1"],
    "AU-3": ["CC7.2", "CC8.1"],
    "AU-6": ["CC7.2", "CC8.1"],
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _manual_evidence_required(message: str, **metadata: Any) -> dict[str, Any]:
    return {
        "status": "manual_evidence_required",
        "audit_ready": False,
        "message": message,
        **metadata,
    }


def _needs_connector(message: str, **metadata: Any) -> dict[str, Any]:
    return {
        "status": "needs_connector",
        "audit_ready": False,
        "message": message,
        **metadata,
    }


class EvidenceType(str, Enum):
    """Types of compliance evidence."""
    CONFIGURATION = "configuration"
    AUDIT_LOG = "audit_log"
    POLICY_DOCUMENT = "policy_document"
    TEST_RESULT = "test_result"
    SCREENSHOT = "screenshot"
    EXPORT = "export"
    API_RESPONSE = "api_response"


class EvidenceCollectionService:
    """Service for collecting and managing compliance evidence."""
    
    def __init__(self, keycloak_client: KeycloakClient):
        self.keycloak_client = keycloak_client
    
    def collect_control_evidence(
        self,
        control_id: str,
        evidence_types: List[EvidenceType],
        tenant_id: Optional[str] = None,
        repository_client: Any | None = None,
        actor_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Collect evidence for a specific control.
        """
        evidence = {}
        collected_at = _utc_now()
        
        for evidence_type in evidence_types:
            try:
                if evidence_type == EvidenceType.CONFIGURATION:
                    evidence["configuration"] = self._collect_configuration_evidence(control_id, tenant_id)
                
                elif evidence_type == EvidenceType.AUDIT_LOG:
                    evidence["audit_log"] = self._collect_audit_log_evidence(control_id, tenant_id)
                
                elif evidence_type == EvidenceType.POLICY_DOCUMENT:
                    evidence["policy_document"] = self._collect_policy_evidence(control_id, tenant_id)
                
                elif evidence_type == EvidenceType.TEST_RESULT:
                    evidence["test_result"] = self._collect_test_evidence(control_id, tenant_id)
                
                elif evidence_type == EvidenceType.API_RESPONSE:
                    evidence["api_response"] = self._collect_api_evidence(control_id, tenant_id)
                
            except Exception as e:
                logger.error(f"Error collecting {evidence_type} evidence for {control_id}: {e}")
                evidence[evidence_type.value] = {
                    "error": str(e),
                    "status": "failed"
                }

        repository_result = self._persist_repository_evidence(
            control_id=control_id,
            tenant_id=tenant_id,
            evidence=evidence,
            collected_at=collected_at,
            repository_client=repository_client,
            actor_id=actor_id,
        )
        
        return {
            "control_id": control_id,
            "tenant_id": tenant_id,
            "evidence": evidence,
            "repository": repository_result,
            "collected_at": collected_at.isoformat()
        }
    
    def collect_account_management_evidence(
        self,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Collect evidence for AC-2 (Account Management).
        """
        evidence = {}
        
        try:
            # Get user management configuration
            users = self.keycloak_client.list_users()
            
            evidence["account_lifecycle_management"] = {
                "status": "collected",
                "audit_ready": False,
                "source": "keycloak_admin_api",
                "total_users": len(users),
                "enabled_users": sum(1 for u in users if u.get("enabled", True)),
                "disabled_users": sum(1 for u in users if not u.get("enabled", True)),
                "summary": "Keycloak user lifecycle counts collected from the IAM tenant realm."
            }
            
            evidence["account_reviews"] = _manual_evidence_required(
                "Access review campaign evidence is not available from the IAM collector yet.",
                required_source="governance_access_review_campaigns",
                next_step="Create or attach an access review campaign export.",
            )
            
        except Exception as e:
            logger.error(f"Error collecting account management evidence: {e}")
            evidence["error"] = str(e)
        
        return evidence
    
    def collect_access_enforcement_evidence(
        self,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Collect evidence for AC-3 (Access Enforcement).
        """
        evidence = {}
        
        try:
            # Get authorization policies
            policies = self.keycloak_client.get_authorization_policies()
            
            evidence["authorization_policies"] = {
                "status": "collected",
                "audit_ready": False,
                "source": "keycloak_authorization_policies",
                "policy_count": len(policies),
                "policies": [
                    {
                        "id": p.get("id"),
                        "name": p.get("name"),
                        "type": p.get("type"),
                        "enabled": p.get("logic") != "NEGATIVE"
                    }
                    for p in policies[:10]  # Limit to first 10
                ],
                "has_enforcement": len(policies) > 0
            }
            
            evidence["access_enforcement"] = _manual_evidence_required(
                "Policy enforcement and evaluation activity require a policy decision or authorization log export.",
                required_source="authorization_decision_logs",
                next_step="Attach policy decision logs or enable the authorization decision connector.",
            )
            
        except Exception as e:
            logger.error(f"Error collecting access enforcement evidence: {e}")
            evidence["error"] = str(e)
        
        return evidence
    
    def collect_least_privilege_evidence(
        self,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Collect evidence for AC-6 (Least Privilege).
        """
        evidence = {}
        
        try:
            users = self.keycloak_client.list_users()
            
            # Analyze privilege distribution
            role_counts = []
            for user in users[:100]:  # Sample first 100
                user_id = user.get("id")
                if user_id:
                    try:
                        roles = self.keycloak_client.get_user_roles(user_id)
                        role_counts.append(len(roles))
                    except:
                        pass
            
            if role_counts:
                avg_roles = sum(role_counts) / len(role_counts)
                max_roles = max(role_counts)
                
                evidence["privilege_analysis"] = {
                    "status": "collected",
                    "audit_ready": False,
                    "source": "keycloak_user_role_assignments",
                    "average_roles_per_user": round(avg_roles, 2),
                    "max_roles_per_user": max_roles,
                    "users_with_excessive_privileges": sum(1 for count in role_counts if count > 5),
                    "summary": "Role distribution sampled from Keycloak user role assignments."
                }

            evidence["role_mining"] = _manual_evidence_required(
                "Role mining and access optimization evidence is not collected automatically yet.",
                required_source="role_mining_report",
                next_step="Attach a role mining report or run an access optimization campaign.",
            )
            
        except Exception as e:
            logger.error(f"Error collecting least privilege evidence: {e}")
            evidence["error"] = str(e)
        
        return evidence
    
    def collect_authentication_evidence(
        self,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Collect evidence for IA-2 (Identification and Authentication).
        """
        evidence = {}
        
        try:
            evidence["user_authentication"] = _needs_connector(
                "Realm authentication flow settings are not collected by the IAM evidence connector yet.",
                required_connector="keycloak_realm_authentication_flows",
                next_step="Enable authentication-flow collection before treating this control as evidenced.",
            )
            
            evidence["multi_factor_authentication"] = _manual_evidence_required(
                "MFA requirement evidence requires a real policy export or tenant attestation.",
                required_source="mfa_policy_export",
                next_step="Attach the MFA policy export or enable MFA policy collection.",
            )
            
        except Exception as e:
            logger.error(f"Error collecting authentication evidence: {e}")
            evidence["error"] = str(e)
        
        return evidence
    
    def collect_audit_evidence(
        self,
        tenant_id: Optional[str] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Collect evidence for AU controls (Audit and Accountability).
        """
        evidence = {}
        
        try:
            evidence["audit_logging"] = _needs_connector(
                "Audit logging configuration and retention evidence requires the audit-service connector.",
                required_connector="audit_service",
                next_step="Enable audit-service evidence collection or attach a log retention export.",
            )
            
            evidence["audit_review"] = _manual_evidence_required(
                "Audit review cadence is not automatically available from IAM.",
                required_source="audit_review_attestation",
                next_step="Attach audit review evidence or an owner attestation.",
            )
            
        except Exception as e:
            logger.error(f"Error collecting audit evidence: {e}")
            evidence["error"] = str(e)
        
        return evidence
    
    def _collect_configuration_evidence(
        self,
        control_id: str,
        tenant_id: Optional[str]
    ) -> Dict[str, Any]:
        """Collect configuration-based evidence."""
        # Map controls to evidence collection methods
        evidence_collectors = {
            "AC-2": self.collect_account_management_evidence,
            "AC-3": self.collect_access_enforcement_evidence,
            "AC-6": self.collect_least_privilege_evidence,
            "IA-2": self.collect_authentication_evidence,
            "AU-2": self.collect_audit_evidence,
            "AU-3": self.collect_audit_evidence,
            "AU-6": self.collect_audit_evidence
        }
        
        collector = evidence_collectors.get(control_id)
        if collector:
            return collector(tenant_id)
        else:
            return {
                **_manual_evidence_required(
                    f"Evidence collection for {control_id} is not implemented in the IAM collector.",
                    required_source="manual_evidence_upload",
                    next_step="Attach manual evidence or configure a dedicated connector.",
                )
            }
    
    def _collect_audit_log_evidence(
        self,
        control_id: str,
        tenant_id: Optional[str]
    ) -> Dict[str, Any]:
        """Collect audit log evidence."""
        return _needs_connector(
            "Audit log samples require a connected audit log source; no sample logs were collected.",
            required_connector="audit_log_export",
            next_step="Connect the audit log source or attach a manual audit log export.",
        )
    
    def _collect_policy_evidence(
        self,
        control_id: str,
        tenant_id: Optional[str]
    ) -> Dict[str, Any]:
        """Collect policy document evidence."""
        policies = self.keycloak_client.get_authorization_policies()
        
        return {
            "status": "collected",
            "audit_ready": False,
            "source": "keycloak_authorization_policies",
            "policy_count": len(policies),
            "policies": [
                {
                    "id": p.get("id"),
                    "name": p.get("name"),
                    "type": p.get("type")
                }
                for p in policies[:5]
            ]
        }
    
    def _collect_test_evidence(
        self,
        control_id: str,
        tenant_id: Optional[str]
    ) -> Dict[str, Any]:
        """Collect test result evidence."""
        return _manual_evidence_required(
            "Automated control test results are not available for this IAM control yet.",
            required_source="control_test_result",
            next_step="Run or attach control test results before claiming test evidence.",
        )
    
    def _collect_api_evidence(
        self,
        control_id: str,
        tenant_id: Optional[str]
    ) -> Dict[str, Any]:
        """Collect API response evidence."""
        return _needs_connector(
            "API verification evidence is not implemented for this IAM control yet.",
            required_connector="iam_control_verification_api",
            next_step="Enable API verification or attach a manual API response export.",
        )

    def _persist_repository_evidence(
        self,
        control_id: str,
        tenant_id: Optional[str],
        evidence: dict[str, Any],
        collected_at: datetime,
        repository_client: Any | None,
        actor_id: Optional[str],
    ) -> dict[str, Any]:
        if not repository_client or not tenant_id:
            return {
                "status": "not_configured",
                "evidence_items": [],
                "collection_tasks": [],
                "errors": [],
            }

        result: dict[str, Any] = {
            "status": "completed",
            "evidence_items": [],
            "collection_tasks": [],
            "errors": [],
        }

        for evidence_type, evidence_value in evidence.items():
            for evidence_key, payload in self._iter_evidence_units(evidence_type, evidence_value):
                try:
                    if self._requires_collection_task(payload):
                        task = repository_client.create_collection_task(
                            self._collection_task_payload(
                                tenant_id=tenant_id,
                                control_id=control_id,
                                evidence_type=evidence_type,
                                evidence_key=evidence_key,
                                payload=payload,
                                actor_id=actor_id,
                            )
                        )
                        result["collection_tasks"].append(task)
                    else:
                        item = repository_client.create_evidence_item(
                            self._evidence_item_payload(
                                tenant_id=tenant_id,
                                control_id=control_id,
                                evidence_type=evidence_type,
                                evidence_key=evidence_key,
                                payload=payload,
                                collected_at=collected_at,
                                actor_id=actor_id,
                            )
                        )
                        result["evidence_items"].append(item)
                except Exception as exc:
                    logger.warning(
                        "Failed to persist IAM compliance evidence",
                        extra={
                            "control_id": control_id,
                            "evidence_type": evidence_type,
                            "evidence_key": evidence_key,
                            "tenant_id": tenant_id,
                        },
                    )
                    result["errors"].append(
                        {
                            "evidence_type": evidence_type,
                            "evidence_key": evidence_key,
                            "error": str(exc),
                        }
                    )

        if result["errors"]:
            result["status"] = "partial" if (result["evidence_items"] or result["collection_tasks"]) else "failed"
        return result

    def _iter_evidence_units(self, evidence_type: str, value: Any):
        if isinstance(value, dict) and "status" not in value and any(isinstance(item, dict) for item in value.values()):
            for key, item in value.items():
                yield key, item
            return
        yield evidence_type, value

    def _requires_collection_task(self, payload: Any) -> bool:
        if not isinstance(payload, dict):
            return False
        status = str(payload.get("status") or payload.get("evidence_status") or "").lower()
        if status in {"failed", "not_implemented", "needs_connector", "manual_evidence_required"}:
            return True
        if payload.get("error"):
            return True
        return False

    def _evidence_item_payload(
        self,
        tenant_id: str,
        control_id: str,
        evidence_type: str,
        evidence_key: str,
        payload: Any,
        collected_at: datetime,
        actor_id: Optional[str],
    ) -> dict[str, Any]:
        content_hash = _sha256(payload)
        idempotency_key = self._idempotency_key(
            tenant_id,
            control_id,
            evidence_type,
            evidence_key,
            content_hash,
        )
        valid_until = collected_at + timedelta(days=90)
        title = f"IAM {control_id} {evidence_key.replace('_', ' ')} evidence"
        summary = self._summary_for_payload(evidence_key, payload)
        return {
            "tenant_id": tenant_id,
            "evidence_type": evidence_type,
            "title": title,
            "description": summary,
            "source_system": "iam_agent",
            "source_resource_id": f"iam:{control_id}:{evidence_type}:{evidence_key}",
            "collector": "iam_agent",
            "collection_method": self._collection_method_for_payload(payload),
            "collected_at": collected_at.isoformat(),
            "valid_from": collected_at.isoformat(),
            "valid_until": valid_until.isoformat(),
            "hash_sha256": content_hash,
            "storage_uri": f"urn:sentinelgrid:evidence:iam:{tenant_id}:{control_id}:{evidence_type}:{evidence_key}:{content_hash[:12]}",
            "summary": summary,
            "sensitivity": "internal",
            "review_status": "pending",
            "created_by": actor_id or "iam_agent",
            "control_links": self._control_links_for(control_id),
            "metadata": {
                "nist_control_id": control_id,
                "evidence_type": evidence_type,
                "evidence_key": evidence_key,
                "raw_evidence": payload,
                "audit_ready": False,
                "review_required": True,
                "mapped_frameworks": ["soc2"] if control_id in NIST_TO_SOC2_CONTROL_LINKS else [],
            },
            "provenance": {
                "source": "iam_agent",
                "collector": "iam_agent",
                "source_control_id": control_id,
                "source_evidence_type": evidence_type,
            },
            "integrity_metadata": {
                "hash_algorithm": "sha256",
                "canonicalization": "json_sort_keys_compact",
            },
            "idempotency_key": idempotency_key,
        }

    def _collection_task_payload(
        self,
        tenant_id: str,
        control_id: str,
        evidence_type: str,
        evidence_key: str,
        payload: Any,
        actor_id: Optional[str],
    ) -> dict[str, Any]:
        task_status = self._task_status_for_payload(payload)
        idempotency_key = self._idempotency_key(
            tenant_id,
            control_id,
            evidence_type,
            evidence_key,
            task_status,
        )
        message = payload.get("message") if isinstance(payload, dict) else None
        return {
            "tenant_id": tenant_id,
            "task_name": f"Collect IAM {control_id} {evidence_key.replace('_', ' ')} evidence",
            "task_type": evidence_type,
            "status": task_status,
            "source_system": "iam_agent",
            "source_resource_id": f"iam:{control_id}:{evidence_type}:{evidence_key}",
            "collector": "iam_agent",
            "collection_method": "manual_attestation" if task_status == "manual_evidence_required" else "connector",
            "requested_by": actor_id or "iam_agent",
            "error_message": message,
            "metadata": {
                "nist_control_id": control_id,
                "evidence_type": evidence_type,
                "evidence_key": evidence_key,
                "raw_evidence": payload,
                "control_links": self._control_links_for(control_id),
                "audit_ready": False,
            },
            "idempotency_key": idempotency_key,
        }

    def _task_status_for_payload(self, payload: Any) -> str:
        if isinstance(payload, dict):
            status = str(payload.get("status") or "").lower()
            if status in {"needs_connector", "manual_evidence_required"}:
                return status
        return "manual_evidence_required"

    def _collection_method_for_payload(self, payload: Any) -> str:
        if isinstance(payload, dict):
            source = str(payload.get("source") or "").lower()
            if "keycloak" in source:
                return "keycloak_admin_api"
        return "api"

    def _summary_for_payload(self, evidence_key: str, payload: Any) -> str:
        if isinstance(payload, dict):
            if payload.get("summary"):
                return str(payload["summary"])
            if payload.get("message"):
                return str(payload["message"])
            compact = {key: value for key, value in payload.items() if key not in {"policies", "raw_evidence"}}
            return f"{evidence_key.replace('_', ' ').title()} evidence collected: {_canonical_json(compact)[:500]}"
        return f"{evidence_key.replace('_', ' ').title()} evidence collected."

    def _control_links_for(self, control_id: str) -> list[dict[str, Any]]:
        return [
            {
                "framework_id": "soc2",
                "control_id": soc2_control_id,
                "link_type": "supports",
                "rationale": f"IAM NIST {control_id} evidence maps to SOC 2 {soc2_control_id}.",
                "metadata": {
                    "source_nist_control_id": control_id,
                    "mapping_source": "iam_static_nist_to_soc2",
                },
            }
            for soc2_control_id in NIST_TO_SOC2_CONTROL_LINKS.get(control_id, [])
        ]

    def _idempotency_key(self, tenant_id: str, control_id: str, evidence_type: str, evidence_key: str, suffix: str) -> str:
        normalized = ":".join(
            [
                "iam",
                tenant_id,
                control_id.lower(),
                evidence_type.lower(),
                evidence_key.lower(),
                suffix,
            ]
        )
        if len(normalized) <= 255:
            return normalized
        return f"iam:{tenant_id}:{hashlib.sha256(normalized.encode('utf-8')).hexdigest()}"
