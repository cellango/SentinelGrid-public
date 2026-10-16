"""Database models for SOAR Agent."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import JSON, Column, ForeignKey, Index, Integer, String, Text, Boolean, TIMESTAMP, ARRAY
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class PlaybookDB(Base):
    """Playbook database model."""
    __tablename__ = "playbooks"

    id = Column(PGUUID(as_uuid=True), primary_key=True)
    tenant_id = Column(PGUUID(as_uuid=True), nullable=False)
    key = Column(String(255), nullable=False)  # Required by schema, use playbook_key value for built-ins
    name = Column(String(255), nullable=False)
    description = Column(Text)
    target_type = Column(String(50), nullable=False, default="incident")  # Required by schema: 'alert' | 'incident'
    category = Column(String(50))
    category_filter = Column(JSON)  # JSONB filter for categories
    severity_filter = Column(JSON)  # JSONB filter for severity
    workflow_ref = Column(Text, nullable=False, default="")  # Required by schema: workflow engine reference
    version = Column(String(50), nullable=False, default="1.0.0")
    is_enabled = Column(Boolean, default=True)  # Required by schema
    
    # React Flow workflow structure
    workflow = Column(JSON, nullable=False, default={"nodes": [], "edges": []})
    
    # Execution config
    timeout_seconds = Column(Integer, default=3600)
    retry_policy = Column(JSON)
    on_failure = Column(String(50), default="fail")
    
    # Metadata
    is_template = Column(Boolean, default=False)
    requires_approval = Column(Boolean, default=False)
    tags = Column(ARRAY(Text), default=[])
    
    # OOTB Playbook fields
    playbook_key = Column(String(255))  # Unique identifier for built-in playbooks
    is_builtin = Column(Boolean, default=False)  # True if SentinelGrid built-in
    severity_default = Column(String(50))  # 'low', 'medium', 'high', 'critical'
    applicable_sources = Column(ARRAY(Text), default=[])  # Data sources this applies to
    triggers = Column(ARRAY(Text), default=[])  # Trigger conditions
    prerequisites = Column(ARRAY(Text), default=[])  # Prerequisites
    artifacts_required = Column(ARRAY(Text), default=[])  # Required artifacts
    phases = Column(JSON)  # NIST IR phases structure
    cis_controls = Column(ARRAY(Text), default=[])  # CIS Controls
    
    # Framework mappings
    nist_controls = Column(ARRAY(Text), default=[])  # NIST SP 800-53 control IDs
    soc2_criteria = Column(ARRAY(Text), default=[])  # SOC 2 Common Criteria IDs
    mitre_tactics = Column(ARRAY(Text), default=[])  # MITRE tactics
    mitre_techniques = Column(ARRAY(Text), default=[])  # MITRE techniques
    
    # Trigger configuration
    trigger_conditions = Column(JSON)
    auto_trigger_enabled = Column(Boolean, default=False)
    trigger_priority = Column(Integer, default=0)
    
    # n8n integration
    n8n_workflow_id = Column(String(255))
    n8n_webhook_url = Column(Text)
    
    created_by = Column(PGUUID(as_uuid=True))
    created_at = Column(TIMESTAMP, default=func.now())
    updated_at = Column(TIMESTAMP, default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_playbooks_tenant_category", "tenant_id", "category"),
        Index("idx_playbooks_n8n_workflow_id", "n8n_workflow_id"),
        Index("idx_playbooks_is_template", "is_template"),
        Index("idx_playbooks_is_builtin", "is_builtin"),
        Index("idx_playbooks_playbook_key", "playbook_key"),
    )


class PlaybookExecutionDB(Base):
    """Playbook execution database model."""
    __tablename__ = "playbook_executions"

    id = Column(PGUUID(as_uuid=True), primary_key=True)
    playbook_id = Column(PGUUID(as_uuid=True), ForeignKey("playbooks.id", ondelete="CASCADE"), nullable=False)
    tenant_id = Column(PGUUID(as_uuid=True), nullable=False)
    
    # Execution context
    trigger_type = Column(String(50))
    trigger_id = Column(PGUUID(as_uuid=True))
    
    # Status
    status = Column(String(50), default="pending")
    started_at = Column(TIMESTAMP)
    completed_at = Column(TIMESTAMP)
    
    # n8n integration
    n8n_execution_id = Column(String(255))
    
    # Results
    result = Column(JSON)
    error_message = Column(Text)
    logs = Column(JSON, default=[])
    
    created_at = Column(TIMESTAMP, default=func.now())

    __table_args__ = (
        Index("idx_playbook_executions_playbook", "playbook_id"),
        Index("idx_playbook_executions_status", "status"),
        Index("idx_playbook_executions_tenant", "tenant_id"),
        Index("idx_playbook_executions_trigger", "trigger_type", "trigger_id"),
    )


class PlaybookObservableDB(Base):
    """Playbook observable definition database model."""
    __tablename__ = "playbook_observables"

    id = Column(PGUUID(as_uuid=True), primary_key=True)
    playbook_id = Column(PGUUID(as_uuid=True), ForeignKey("playbooks.id", ondelete="CASCADE"), nullable=False)
    node_id = Column(String(255), nullable=False)
    
    data_type = Column(String(50), nullable=False)
    extraction_path = Column(Text)
    tags = Column(ARRAY(Text), default=[])
    mark_as_ioc = Column(Boolean, default=False)
    
    created_at = Column(TIMESTAMP, default=func.now())

    __table_args__ = (
        Index("idx_playbook_observables_playbook", "playbook_id"),
    )


class PlaybookAnalyzerDB(Base):
    """Playbook analyzer definition database model."""
    __tablename__ = "playbook_analyzers"

    id = Column(PGUUID(as_uuid=True), primary_key=True)
    playbook_id = Column(PGUUID(as_uuid=True), ForeignKey("playbooks.id", ondelete="CASCADE"), nullable=False)
    node_id = Column(String(255), nullable=False)
    
    analyzer_id = Column(String(255), nullable=False)
    observable_node_id = Column(String(255), nullable=False)
    parameters = Column(JSON, default={})
    
    created_at = Column(TIMESTAMP, default=func.now())

    __table_args__ = (
        Index("idx_playbook_analyzers_playbook", "playbook_id"),
    )
