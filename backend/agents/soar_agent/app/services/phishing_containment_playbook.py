"""Phishing containment playbook implementation."""

import sys
import os
import logging
from typing import Dict, Any, List
from uuid import UUID
import httpx

# Add libs to path
libs_path = os.path.join(os.path.dirname(__file__), "../../../../libs")
if os.path.exists(libs_path):
    sys.path.insert(0, libs_path)

from app.core.config import settings

logger = logging.getLogger(__name__)


class PhishingContainmentPlaybook:
    """Playbook for containing phishing incidents."""
    
    def __init__(self):
        """Initialize containment playbook."""
        self.n8n_url = settings.N8N_URL
        self.email_ingestion_url = settings.EMAIL_INGESTION_SERVICE_URL or "http://email_ingestion_service:8000"
        self.ticketing_url = settings.TICKETING_SERVICE_URL or "http://ticketing_agent:8000"
        self.action_agent_url = settings.ACTION_AGENT_URL or "http://action_agent:8000"
        self.internal_service_token = settings.INTERNAL_SERVICE_TOKEN
    
    async def execute(
        self,
        tenant_id: UUID,
        phishing_report_id: UUID,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute phishing containment playbook.
        
        Steps:
        1. Extract observables from phishing report
        2. Search for similar emails
        3. Quarantine/delete similar emails
        4. Block malicious domains/IPs
        5. Create incident ticket
        6. Notify affected users
        7. Update report status
        
        Args:
            tenant_id: Tenant ID
            phishing_report_id: Phishing report ID
            context: Additional context (options, overrides)
            
        Returns:
            Execution results
        """
        results = {
            "playbook_id": "phishing_containment",
            "phishing_report_id": str(phishing_report_id),
            "steps": {},
            "status": "in_progress",
        }
        
        try:
            # Step 1: Extract observables
            observables = await self._extract_observables(tenant_id, phishing_report_id)
            results["steps"]["extract_observables"] = {
                "status": "completed",
                "observables_count": len(observables),
            }
            
            # Step 2: Search for similar emails
            if context.get("search_emails", True):
                similar_emails = await self._search_similar_emails(
                    tenant_id,
                    phishing_report_id,
                    observables
                )
                results["steps"]["search_emails"] = {
                    "status": "completed",
                    "emails_found": len(similar_emails),
                    "email_ids": [e["id"] for e in similar_emails],
                }
            else:
                similar_emails = []
                results["steps"]["search_emails"] = {"status": "skipped"}
            
            # Step 3: Quarantine/delete emails
            if context.get("quarantine_emails", True) and similar_emails:
                deletion_result = await self._quarantine_emails(
                    tenant_id,
                    [e["id"] for e in similar_emails],
                    context.get("email_provider", "microsoft_graph"),
                    phishing_report_id
                )
                results["steps"]["quarantine_emails"] = {
                    "status": "completed",
                    "result": deletion_result,
                }
            else:
                results["steps"]["quarantine_emails"] = {"status": "skipped"}
            
            # Step 4: Block domains/IPs
            if context.get("block_domains", True):
                block_result = await self._block_observables(
                    tenant_id,
                    observables
                )
                results["steps"]["block_observables"] = {
                    "status": "completed",
                    "result": block_result,
                }
            else:
                results["steps"]["block_observables"] = {"status": "skipped"}
            
            # Step 5: Create ticket
            if context.get("create_ticket", True):
                ticket_result = await self._create_ticket(
                    tenant_id,
                    phishing_report_id,
                    observables,
                    similar_emails
                )
                results["steps"]["create_ticket"] = {
                    "status": "completed",
                    "ticket_id": ticket_result.get("ticket_id"),
                }
            else:
                results["steps"]["create_ticket"] = {"status": "skipped"}
            
            # Step 6: Notify users
            if context.get("notify_users", True):
                notification_result = await self._notify_users(
                    tenant_id,
                    phishing_report_id,
                    similar_emails
                )
                results["steps"]["notify_users"] = {
                    "status": "completed",
                    "users_notified": notification_result.get("count", 0),
                }
            else:
                results["steps"]["notify_users"] = {"status": "skipped"}
            
            results["status"] = "completed"
            
        except Exception as e:
            logger.error(f"Error executing containment playbook: {e}")
            results["status"] = "failed"
            results["error"] = str(e)
        
        return results
    
    async def _extract_observables(
        self,
        tenant_id: UUID,
        phishing_report_id: UUID
    ) -> List[Dict[str, Any]]:
        """Extract observables from phishing report."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.email_ingestion_url}/api/v1/phishing/reports/{phishing_report_id}/observables",
                    params={"tenant_id": str(tenant_id)},
                    headers={
                        "Authorization": f"Bearer {self.internal_service_token}",
                    },
                    timeout=10.0,
                )
                
                if response.status_code == 200:
                    observables = response.json()
                    return [
                        {
                            "type": o["observable_type"],
                            "value": o["observable_value"],
                            "is_malicious": o.get("is_malicious", False),
                        }
                        for o in observables
                    ]
        except Exception as e:
            logger.error(f"Error extracting observables: {e}")
        
        return []
    
    async def _search_similar_emails(
        self,
        tenant_id: UUID,
        phishing_report_id: UUID,
        observables: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Search for similar emails."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.email_ingestion_url}/api/v1/phishing/reports/{phishing_report_id}/search-similar",
                    json={
                        "provider": "microsoft_graph",  # TODO: Get from tenant config
                    },
                    params={"tenant_id": str(tenant_id)},
                    headers={
                        "Authorization": f"Bearer {self.internal_service_token}",
                    },
                    timeout=60.0,
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result.get("results", [])
        except Exception as e:
            logger.error(f"Error searching similar emails: {e}")
        
        return []
    
    async def _quarantine_emails(
        self,
        tenant_id: UUID,
        email_ids: List[str],
        provider: str,
        phishing_report_id: UUID = None
    ) -> Dict[str, Any]:
        """Quarantine similar emails."""
        try:
            # If no report ID, we need to create a temporary endpoint or use a different approach
            # For now, we'll call the deletion service directly
            async with httpx.AsyncClient() as client:
                # Use a generic endpoint or pass report_id if available
                endpoint = f"{self.email_ingestion_url}/api/v1/phishing/reports/{phishing_report_id}/delete-similar" if phishing_report_id else f"{self.email_ingestion_url}/api/v1/phishing/delete-emails"
                
                response = await client.post(
                    endpoint,
                    json={
                        "email_ids": email_ids,
                        "provider": provider,
                        "action": "quarantine",
                    },
                    params={"tenant_id": str(tenant_id)},
                    headers={
                        "Authorization": f"Bearer {self.internal_service_token}",
                    },
                    timeout=60.0,
                )
                
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.error(f"Error quarantining emails: {e}")
        
        return {"success_count": 0, "failure_count": len(email_ids)}
    
    async def _block_observables(
        self,
        tenant_id: UUID,
        observables: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Block malicious domains/IPs."""
        try:
            # Extract domains and IPs
            domains = [o["value"] for o in observables if o["type"] == "domain" and o.get("is_malicious")]
            ips = [o["value"] for o in observables if o["type"] == "ip" and o.get("is_malicious")]
            
            if not domains and not ips:
                return {"blocked": [], "status": "no_observables_to_block"}
            
            # Call action agent to block
            async with httpx.AsyncClient() as client:
                block_results = []
                
                # Block domains
                for domain in domains:
                    try:
                        response = await client.post(
                            f"{self.action_agent_url}/api/v1/actions/execute",
                            json={
                                "action_type": "network_block_domain",
                                "action_params": {"domain": domain},
                                "tenant_id": str(tenant_id),
                                "requires_approval": False,
                            },
                            headers={
                                "Authorization": f"Bearer {settings.INTERNAL_SERVICE_TOKEN}",
                            },
                            timeout=30.0,
                        )
                        
                        if response.status_code == 200:
                            block_results.append({"type": "domain", "value": domain, "status": "blocked"})
                    except Exception as e:
                        logger.error(f"Error blocking domain {domain}: {e}")
                        block_results.append({"type": "domain", "value": domain, "status": "failed", "error": str(e)})
                
                # Block IPs
                for ip in ips:
                    try:
                        response = await client.post(
                            f"{self.action_agent_url}/api/v1/actions/execute",
                            json={
                                "action_type": "network_block_ip",
                                "action_params": {"ip_address": ip},
                                "tenant_id": str(tenant_id),
                                "requires_approval": False,
                            },
                            headers={
                                "Authorization": f"Bearer {settings.INTERNAL_SERVICE_TOKEN}",
                            },
                            timeout=30.0,
                        )
                        
                        if response.status_code == 200:
                            block_results.append({"type": "ip", "value": ip, "status": "blocked"})
                    except Exception as e:
                        logger.error(f"Error blocking IP {ip}: {e}")
                        block_results.append({"type": "ip", "value": ip, "status": "failed", "error": str(e)})
                
                return {
                    "blocked": block_results,
                    "domains_blocked": len([r for r in block_results if r["type"] == "domain" and r["status"] == "blocked"]),
                    "ips_blocked": len([r for r in block_results if r["type"] == "ip" and r["status"] == "blocked"]),
                }
        except Exception as e:
            logger.error(f"Error blocking observables: {e}")
            return {"blocked": [], "status": "error", "error": str(e)}
    
    async def _create_ticket(
        self,
        tenant_id: UUID,
        phishing_report_id: UUID,
        observables: List[Dict[str, Any]],
        similar_emails: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Create incident ticket."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.ticketing_url}/api/v1/tickets",
                    json={
                        "title": f"Phishing Incident - Report {phishing_report_id}",
                        "description": f"Phishing email detected. {len(similar_emails)} similar emails found.",
                        "status": "open",
                        "severity": "high",
                        "category": "phishing",
                        "source": "phishing_containment_playbook",
                    },
                    params={"tenant_id": str(tenant_id)},
                    headers={
                        "Authorization": f"Bearer {self.internal_service_token}",
                    },
                    timeout=30.0,
                )
                
                if response.status_code == 200:
                    ticket = response.json()
                    return {"ticket_id": ticket.get("id"), "status": "created"}
        except Exception as e:
            logger.error(f"Error creating ticket: {e}")
        
        return {"ticket_id": None, "status": "failed"}
    
    async def _notify_users(
        self,
        tenant_id: UUID,
        phishing_report_id: UUID,
        similar_emails: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Notify affected users."""
        # TODO: Implement user notification
        # This would:
        # 1. Extract user emails from similar_emails
        # 2. Send notification emails
        # 3. Log notifications
        
        return {"count": 0, "status": "pending_implementation"}
