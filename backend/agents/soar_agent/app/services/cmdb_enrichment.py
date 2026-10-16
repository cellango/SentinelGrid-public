"""CMDB enrichment module - Assets, inventory, software."""

import logging
from typing import Dict, Any, List, Optional
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


class CMDBEnrichmentModule:
    """Enriches tickets with CMDB asset data."""
    
    def __init__(self):
        self.cmdb_service_url = settings.CMDB_SERVICE_URL
        self.internal_token = settings.INTERNAL_SERVICE_TOKEN
    
    async def enrich(self, ticket_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich ticket with CMDB data.
        
        Args:
            ticket_data: Ticket data dictionary
        
        Returns:
            CMDB enrichment data
        """
        # Extract asset identifiers from ticket
        asset_identifiers = self._extract_asset_identifiers(ticket_data)
        
        if not asset_identifiers:
            return {
                "assets": [],
                "software_inventory": [],
                "hardware_inventory": [],
                "network_info": []
            }
        
        enrichment_data = {
            "assets": [],
            "software_inventory": [],
            "hardware_inventory": [],
            "network_info": []
        }
        
        for asset_id in asset_identifiers:
            try:
                # Fetch asset from CMDB Service
                asset = await self._get_asset(asset_id, ticket_data.get("tenant_id"))
                
                if asset:
                    enrichment_data["assets"].append({
                        "asset_id": asset.get("asset_id"),
                        "name": asset.get("name"),
                        "hostname": asset.get("hostname"),
                        "ip_address": asset.get("ip_address"),
                        "asset_type": asset.get("asset_type"),
                        "operating_system": asset.get("operating_system"),
                        "os_version": asset.get("os_version"),
                        "owner": asset.get("owner"),
                        "location": asset.get("location"),
                        "department": asset.get("department"),
                        "compliance_status": asset.get("compliance_status")
                    })
                    
                    # Add software inventory
                    if asset.get("installed_software"):
                        enrichment_data["software_inventory"].extend(asset["installed_software"])
                    
                    # Add hardware specs
                    if asset.get("hardware_specs"):
                        enrichment_data["hardware_inventory"].append({
                            "asset_id": asset.get("asset_id"),
                            "manufacturer": asset.get("manufacturer"),
                            "model": asset.get("model"),
                            "serial_number": asset.get("serial_number"),
                            "specs": asset.get("hardware_specs")
                        })
                    
                    # Add network information
                    enrichment_data["network_info"].append({
                        "asset_id": asset.get("asset_id"),
                        "ip_address": asset.get("ip_address"),
                        "mac_address": asset.get("mac_address"),
                        "network_segment": asset.get("network_segment"),
                        "vlan": asset.get("vlan"),
                        "firewall_rules": asset.get("firewall_rules")
                    })
            
            except Exception as e:
                logger.error(f"Error enriching CMDB data for asset {asset_id}: {e}")
                continue
        
        return enrichment_data
    
    def _extract_asset_identifiers(self, ticket_data: Dict[str, Any]) -> List[str]:
        """Extract asset identifiers from ticket data."""
        identifiers = []
        
        # Check ticket fields
        if ticket_data.get("asset_id"):
            identifiers.append(ticket_data["asset_id"])
        
        # Check linked alerts
        if ticket_data.get("alerts"):
            for alert in ticket_data["alerts"]:
                if alert.get("asset_id"):
                    identifiers.append(alert["asset_id"])
        
        # Check CMDB data if already present
        if ticket_data.get("cmdb_data", {}).get("assets"):
            for asset in ticket_data["cmdb_data"]["assets"]:
                if asset.get("asset_id"):
                    identifiers.append(asset["asset_id"])
        
        # Remove duplicates
        return list(set(identifiers))
    
    async def _get_asset(self, asset_id: str, tenant_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Fetch asset from CMDB Service."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                headers = {
                    "Authorization": f"Bearer {self.internal_token}",
                    "Content-Type": "application/json"
                }
                url = f"{self.cmdb_service_url}/api/v1/assets/{asset_id}"
                params = {"tenant_id": tenant_id} if tenant_id else {}
                response = await client.get(url, headers=headers, params=params)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.warning(f"Could not fetch asset {asset_id}: {e}")
            return None

