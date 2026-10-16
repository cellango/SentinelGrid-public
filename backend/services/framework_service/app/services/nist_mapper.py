"""NIST SP 800-53 control mapping service."""

import logging
from typing import Dict, Any, List, Optional
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


class NISTMapper:
    """Maps incidents/alerts to NIST SP 800-53 controls."""
    
    def __init__(self):
        self.model_gateway_url = settings.MODEL_GATEWAY_URL
        self.internal_token = settings.INTERNAL_SERVICE_TOKEN
        self._nist_controls_cache = None
    
    async def map_incident_to_controls(
        self,
        incident_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Map incident to NIST SP 800-53 controls.
        
        Args:
            incident_data: Incident/ticket data dictionary
        
        Returns:
            List of NIST control mappings
        """
        # Load NIST controls if not cached
        if not self._nist_controls_cache:
            await self._load_nist_controls()
        
        # Determine incident category and severity
        category = incident_data.get("category", "").lower()
        severity = incident_data.get("severity", "").lower()
        
        # Map based on category
        mapped_controls = []
        
        # Incident Response controls (always relevant)
        mapped_controls.append({
            "control_id": "IR-4",
            "title": "Incident Response Planning",
            "relevance": "Core incident response control",
            "severity": "high"
        })
        
        # Category-specific mappings
        if "login" in category or "authentication" in category:
            mapped_controls.extend([
                {
                    "control_id": "AC-2",
                    "title": "Account Management",
                    "relevance": "Account-related security incident",
                    "severity": "high"
                },
                {
                    "control_id": "AC-7",
                    "title": "Unsuccessful Logon Attempts",
                    "relevance": "Failed login attempts detected",
                    "severity": "medium"
                }
            ])
        
        if "malware" in category:
            mapped_controls.extend([
                {
                    "control_id": "SI-3",
                    "title": "Malicious Code Protection",
                    "relevance": "Malware detection and response",
                    "severity": "high"
                },
                {
                    "control_id": "IR-5",
                    "title": "Incident Monitoring",
                    "relevance": "Malware incident monitoring",
                    "severity": "high"
                }
            ])
        
        if "phishing" in category:
            mapped_controls.extend([
                {
                    "control_id": "AT-2",
                    "title": "Security Awareness Training",
                    "relevance": "Phishing awareness and training",
                    "severity": "medium"
                },
                {
                    "control_id": "IR-4",
                    "title": "Incident Response Planning",
                    "relevance": "Phishing incident response",
                    "severity": "high"
                }
            ])
        
        if "vulnerability" in category or incident_data.get("cve_ids"):
            mapped_controls.extend([
                {
                    "control_id": "RA-5",
                    "title": "Vulnerability Scanning",
                    "relevance": "Vulnerability identification and remediation",
                    "severity": "high"
                },
                {
                    "control_id": "SI-2",
                    "title": "Flaw Remediation",
                    "relevance": "Vulnerability remediation",
                    "severity": "high"
                }
            ])
        
        # Use AI for additional mapping if available
        ai_mappings = await self._ai_map_controls(incident_data)
        if ai_mappings:
            mapped_controls.extend(ai_mappings)
        
        # Remove duplicates
        seen = set()
        unique_controls = []
        for control in mapped_controls:
            control_id = control["control_id"]
            if control_id not in seen:
                seen.add(control_id)
                unique_controls.append(control)
        
        return unique_controls
    
    async def _load_nist_controls(self):
        """Load NIST controls from knowledge base."""
        try:
            # Try to load from Model Gateway knowledge base
            async with httpx.AsyncClient(timeout=10.0) as client:
                headers = {
                    "Authorization": f"Bearer {self.internal_token}",
                    "Content-Type": "application/json"
                }
                url = f"{self.model_gateway_url}/api/v1/knowledge-base/nist-controls"
                response = await client.get(url, headers=headers)
                if response.status_code == 200:
                    self._nist_controls_cache = response.json()
                    return
            
            # Fallback: Use hardcoded common controls
            self._nist_controls_cache = {
                "IR-4": {"title": "Incident Response Planning"},
                "IR-5": {"title": "Incident Monitoring"},
                "AC-2": {"title": "Account Management"},
                "AC-7": {"title": "Unsuccessful Logon Attempts"},
                "SI-3": {"title": "Malicious Code Protection"},
                "SI-2": {"title": "Flaw Remediation"},
                "RA-5": {"title": "Vulnerability Scanning"},
                "AT-2": {"title": "Security Awareness Training"}
            }
        except Exception as e:
            logger.warning(f"Could not load NIST controls: {e}")
            # Use fallback
            self._nist_controls_cache = {}
    
    async def _ai_map_controls(self, incident_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Use AI to map additional NIST controls (placeholder)."""
        # Placeholder - would integrate with Model Gateway for AI-assisted mapping
        return []

