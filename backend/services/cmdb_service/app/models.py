"""SQLAlchemy models for CMDB service."""

from sqlalchemy import Column, String, Text, JSON, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()


class Asset(Base):
    """CMDB asset inventory (hardware, software, network)."""
    __tablename__ = "assets"
    __table_args__ = {"schema": "public"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
    asset_id = Column(Text, nullable=False, default=lambda: str(uuid.uuid4()))
    asset_type = Column(Text, nullable=False)
    name = Column(Text)
    hostname = Column(Text)
    ip_address = Column(Text)
    mac_address = Column(Text)
    manufacturer = Column(Text)
    model = Column(Text)
    serial_number = Column(Text)
    hardware_specs = Column(JSON)
    operating_system = Column(Text)
    os_version = Column(Text)
    installed_software = Column(JSON)
    installed_patches = Column(JSON)
    network_segment = Column(Text)
    vlan = Column(Text)
    firewall_rules = Column(JSON)
    owner = Column(Text)
    location = Column(Text)
    department = Column(Text)
    vulnerabilities = Column(JSON)
    compliance_status = Column(Text)
    last_scan_date = Column(DateTime(timezone=True))
    source = Column(Text)
    user_id = Column(Text)
    external_id = Column(Text)
    metadata_json = Column("metadata", JSON, default=dict)
    last_seen_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
