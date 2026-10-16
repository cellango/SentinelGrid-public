"""Pydantic schemas for CMDB service responses."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class AssetResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: UUID
    tenant_id: UUID
    asset_id: str
    asset_type: str
    name: Optional[str] = None
    hostname: Optional[str] = None
    ip_address: Optional[str] = None
    mac_address: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    hardware_specs: Optional[Dict[str, Any]] = None
    operating_system: Optional[str] = None
    os_version: Optional[str] = None
    installed_software: Optional[List[Dict[str, Any]]] = None
    installed_patches: Optional[List[str]] = None
    network_segment: Optional[str] = None
    vlan: Optional[str] = None
    firewall_rules: Optional[Dict[str, Any]] = None
    owner: Optional[str] = None
    location: Optional[str] = None
    department: Optional[str] = None
    vulnerabilities: Optional[Dict[str, Any]] = None
    compliance_status: Optional[str] = None
    last_scan_date: Optional[datetime] = None
    source: Optional[str] = None
    user_id: Optional[str] = None
    external_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(None, alias="metadata_json")
    last_seen_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
