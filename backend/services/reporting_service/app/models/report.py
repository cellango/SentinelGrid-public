"""Report data models."""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from uuid import UUID, uuid4
from sqlalchemy import Column, String, Text, DateTime, JSON, ForeignKey, Integer, Enum as SQLEnum
from sqlalchemy.orm import relationship
import sys
import os

# Add libs directory to path
libs_path = os.path.join(os.path.dirname(__file__), "../../../libs")
if os.path.exists(libs_path):
    sys.path.insert(0, libs_path)
else:
    sys.path.insert(0, "/app/libs")

from sg_core.db import Base


class ReportStatus(str, Enum):
    """Report generation status."""
    PENDING = "PENDING"
    GENERATING = "GENERATING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ReportFormat(str, Enum):
    """Report output format."""
    PDF = "PDF"
    CSV = "CSV"
    JSON = "JSON"
    HTML = "HTML"


class Report(Base):
    """Report model - stores generated reports."""
    __tablename__ = "reports"
    __table_args__ = {"schema": "reporting"}
    
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    tenant_id = Column(String, nullable=False, index=True)
    template_id = Column(String, ForeignKey("reporting.report_templates.id"), nullable=True)
    name = Column(String, nullable=False)
    format = Column(SQLEnum(ReportFormat), nullable=False, default=ReportFormat.PDF)
    status = Column(SQLEnum(ReportStatus), nullable=False, default=ReportStatus.PENDING)
    
    # Report metadata
    generated_at = Column(DateTime, default=datetime.utcnow)
    generated_by = Column(String, nullable=True)  # User ID
    date_range_start = Column(DateTime, nullable=True)
    date_range_end = Column(DateTime, nullable=True)
    
    # Storage
    file_path = Column(String, nullable=True)  # Path to generated file
    file_size_bytes = Column(Integer, nullable=True)
    download_url = Column(String, nullable=True)
    
    # Report data
    sections = Column(JSON, nullable=True)  # Which sections were included
    report_metadata = Column("metadata", JSON, nullable=True)  # Additional metadata (column name metadata)
    
    # Error handling
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    template = relationship("ReportTemplate", back_populates="reports")


class ReportTemplate(Base):
    """Report template model - defines report structure."""
    __tablename__ = "report_templates"
    __table_args__ = {"schema": "reporting"}
    
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    tenant_id = Column(String, nullable=True, index=True)  # NULL = system template
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    type = Column(String, nullable=False)  # executive, compliance, incident, custom
    
    # Template configuration
    sections = Column(JSON, nullable=False)  # List of TemplateSection
    data_queries = Column(JSON, nullable=True)  # List of DataQuery
    schedule = Column(JSON, nullable=True)  # ScheduleConfig
    
    # Permissions
    required_roles = Column(JSON, nullable=True)  # List of roles that can use this template
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    reports = relationship("Report", back_populates="template")


class ReportShare(Base):
    """Report share model - manages shareable links."""
    __tablename__ = "report_shares"
    __table_args__ = {"schema": "reporting"}
    
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    report_id = Column(String, ForeignKey("reporting.reports.id"), nullable=False, index=True)
    tenant_id = Column(String, nullable=False, index=True)
    
    # Share token (used in URL)
    share_token = Column(String, unique=True, nullable=False, index=True)
    
    # Expiration
    expires_at = Column(DateTime, nullable=True)
    
    # Password protection
    password_hash = Column(String, nullable=True)  # Hashed password if protected
    
    # Access tracking
    access_count = Column(Integer, default=0)
    last_accessed_at = Column(DateTime, nullable=True)
    
    # Metadata
    created_by = Column(String, nullable=True)  # User ID
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    report = relationship("Report")
