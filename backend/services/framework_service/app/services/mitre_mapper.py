"""MITRE ATT&CK framework mapping service."""

import logging
from typing import Dict, Any, List, Optional
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


class MITREMapper:
    """Maps incidents/alerts to MITRE ATT&CK tactics and techniques."""
    
    def __init__(self):
        self.model_gateway_url = settings.MODEL_GATEWAY_URL
        self.internal_token = settings.INTERNAL_SERVICE_TOKEN
        self._mitre_techniques_cache = None
    
    async def map_incident_to_mitre(
        self,
        incident_data: Dict[str, Any]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Map incident to MITRE ATT&CK framework.
        
        Args:
            incident_data: Incident/ticket data dictionary
        
        Returns:
            Dictionary with tactics and techniques
        """
        # Load MITRE techniques if not cached
        if not self._mitre_techniques_cache:
            await self._load_mitre_techniques()
        
        # Determine incident category
        category = incident_data.get("category", "").lower()
        
        tactics = []
        techniques = []
        
        # Category-specific mappings
        if "login" in category or "authentication" in category:
            tactics.append({
                "tactic_id": "TA0001",
                "name": "Initial Access",
                "description": "The adversary is trying to get into your network."
            })
            techniques.append({
                "technique_id": "T1078",
                "name": "Valid Accounts",
                "description": "Adversaries may steal credentials or use valid accounts to gain access."
            })
            techniques.append({
                "technique_id": "T1110",
                "name": "Brute Force",
                "description": "Adversaries may use brute force techniques to gain access to accounts."
            })
        
        if "malware" in category:
            tactics.append({
                "tactic_id": "TA0002",
                "name": "Execution",
                "description": "The adversary is trying to run malicious code."
            })
            techniques.append({
                "technique_id": "T1059",
                "name": "Command and Scripting Interpreter",
                "description": "Adversaries may abuse command and script interpreters to execute commands."
            })
        
        if "phishing" in category:
            tactics.append({
                "tactic_id": "TA0001",
                "name": "Initial Access",
                "description": "The adversary is trying to get into your network."
            })
            techniques.append({
                "technique_id": "T1566",
                "name": "Phishing",
                "description": "Adversaries may send phishing messages to gain access to victim systems."
            })
        
        if "vulnerability" in category or incident_data.get("cve_ids"):
            tactics.append({
                "tactic_id": "TA0001",
                "name": "Initial Access",
                "description": "The adversary is trying to get into your network."
            })
            techniques.append({
                "technique_id": "T1190",
                "name": "Exploit Public-Facing Application",
                "description": "Adversaries may exploit software vulnerabilities in public-facing applications."
            })
        
        # Use AI for additional mapping if available
        ai_mappings = await self._ai_map_mitre(incident_data)
        if ai_mappings:
            tactics.extend(ai_mappings.get("tactics", []))
            techniques.extend(ai_mappings.get("techniques", []))
        
        # Remove duplicates
        seen_tactics = set()
        unique_tactics = []
        for tactic in tactics:
            tactic_id = tactic["tactic_id"]
            if tactic_id not in seen_tactics:
                seen_tactics.add(tactic_id)
                unique_tactics.append(tactic)
        
        seen_techniques = set()
        unique_techniques = []
        for technique in techniques:
            technique_id = technique["technique_id"]
            if technique_id not in seen_techniques:
                seen_techniques.add(technique_id)
                unique_techniques.append(technique)
        
        return {
            "tactics": unique_tactics,
            "techniques": unique_techniques
        }
    
    async def _load_mitre_techniques(self):
        """Load MITRE techniques from knowledge base."""
        try:
            # Try to load from Model Gateway knowledge base
            async with httpx.AsyncClient(timeout=10.0) as client:
                headers = {
                    "Authorization": f"Bearer {self.internal_token}",
                    "Content-Type": "application/json"
                }
                url = f"{self.model_gateway_url}/api/v1/knowledge-base/mitre-techniques"
                response = await client.get(url, headers=headers)
                if response.status_code == 200:
                    self._mitre_techniques_cache = response.json()
                    return
            
            # Fallback: Use hardcoded common techniques
            self._mitre_techniques_cache = {
                "T1078": {"name": "Valid Accounts", "tactic": "TA0001"},
                "T1110": {"name": "Brute Force", "tactic": "TA0001"},
                "T1059": {"name": "Command and Scripting Interpreter", "tactic": "TA0002"},
                "T1566": {"name": "Phishing", "tactic": "TA0001"},
                "T1190": {"name": "Exploit Public-Facing Application", "tactic": "TA0001"}
            }
        except Exception as e:
            logger.warning(f"Could not load MITRE techniques: {e}")
            self._mitre_techniques_cache = {}
    
    async def _ai_map_mitre(self, incident_data: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """Use AI to map additional MITRE tactics/techniques (placeholder)."""
        # Placeholder - would integrate with Model Gateway for AI-assisted mapping
        return {"tactics": [], "techniques": []}

