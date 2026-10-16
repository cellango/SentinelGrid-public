"""Main framework mapping service."""

import logging
from typing import Dict, Any
from app.services.nist_mapper import NISTMapper
from app.services.mitre_mapper import MITREMapper
from app.services.soc2_mapper import SOC2Mapper

logger = logging.getLogger(__name__)


class FrameworkMapper:
    """Main service for mapping incidents to NIST and MITRE frameworks."""
    
    def __init__(self):
        self.nist_mapper = NISTMapper()
        self.mitre_mapper = MITREMapper()
        self.soc2_mapper = SOC2Mapper()
    
    async def map_incident(
        self,
        incident_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Map incident to both NIST and MITRE frameworks.
        
        Args:
            incident_data: Incident/ticket data dictionary
        
        Returns:
            Dictionary with NIST and MITRE mappings
        """
        # Map to NIST controls
        nist_controls = await self.nist_mapper.map_incident_to_controls(incident_data)
        
        # Map to MITRE
        mitre_mapping = await self.mitre_mapper.map_incident_to_mitre(incident_data)

        # Map to SOC 2 Common Criteria
        soc2_criteria = await self.soc2_mapper.map_incident_to_criteria(incident_data)
        
        return {
            "nist_controls": nist_controls,
            "mitre_tactics": mitre_mapping.get("tactics", []),
            "mitre_techniques": mitre_mapping.get("techniques", []),
            "soc2_criteria": soc2_criteria,
        }
