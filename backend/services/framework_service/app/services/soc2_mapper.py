"""SOC 2 Trust Services Criteria mapping service."""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class SOC2Mapper:
    """Maps incidents/alerts to SOC 2 criteria (Common Criteria CC1–CC9)."""

    def __init__(self):
        # Minimal catalog; expand as needed. Keys are Common Criteria IDs.
        self._catalog = {
            "CC1.1": "Control Environment",
            "CC2.1": "Communication and Information",
            "CC3.1": "Risk Assessment",
            "CC4.1": "Monitoring Activities",
            "CC5.1": "Control Activities",
            "CC6.1": "Logical and Physical Access Controls",
            "CC7.1": "System Operations",
            "CC8.1": "Change Management",
            "CC9.1": "Risk Mitigation",
        }

    async def map_incident_to_criteria(
        self,
        incident_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Map incident/ticket data to SOC 2 Common Criteria.

        Args:
            incident_data: Incident/ticket data dictionary

        Returns:
            List of SOC 2 criteria mappings
        """
        category = (incident_data.get("category") or "").lower()
        severity = (incident_data.get("severity") or "").lower()
        mapped: List[Dict[str, Any]] = []

        # Always include monitoring for incidents
        mapped.append(self._build("CC4.1", "Monitoring Activities", "Monitoring and detection", "high"))

        if "login" in category or "auth" in category:
            mapped.extend([
                self._build("CC6.1", "Logical and Physical Access Controls", "Authentication/authorization issue", "high"),
                self._build("CC5.1", "Control Activities", "Access control enforcement", "medium"),
            ])

        if "malware" in category or "endpoint" in category:
            mapped.extend([
                self._build("CC6.1", "Logical and Physical Access Controls", "Endpoint protection controls", "high"),
                self._build("CC7.1", "System Operations", "Endpoint monitoring/response", "high"),
            ])

        if "phishing" in category or "awareness" in category:
            mapped.extend([
                self._build("CC2.1", "Communication and Information", "Security awareness and comms", "medium"),
                self._build("CC6.1", "Logical and Physical Access Controls", "Account takeover protection", "medium"),
            ])

        if "vulnerability" in category or incident_data.get("cve_ids"):
            mapped.extend([
                self._build("CC7.1", "System Operations", "Vulnerability detection/response", "high"),
                self._build("CC8.1", "Change Management", "Patch/change process", "high"),
                self._build("CC9.1", "Risk Mitigation", "Remediation risk handling", "medium"),
            ])

        if severity in ("critical", "high"):
            mapped.append(self._build("CC3.1", "Risk Assessment", "High-severity event risk handling", "high"))

        # Deduplicate by criterion
        seen = set()
        unique = []
        for item in mapped:
            cid = item["criterion_id"]
            if cid in seen:
                continue
            seen.add(cid)
            unique.append(item)

        return unique

    def get_criterion(self, criterion_id: str) -> Dict[str, str]:
        """Return catalog entry for a criterion id."""
        title = self._catalog.get(criterion_id)
        if not title:
            return {}
        return {"criterion_id": criterion_id, "title": title}

    def _build(self, cid: str, title: str, relevance: str, severity: str) -> Dict[str, Any]:
        return {
            "criterion_id": cid,
            "title": title,
            "relevance": relevance,
            "severity": severity,
        }
