"""Playbook data models."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
import json

from pydantic import BaseModel, Field


class WorkflowStructure(BaseModel):
    """React Flow workflow structure."""
    nodes: List[Dict[str, Any]] = Field(default_factory=list)
    edges: List[Dict[str, Any]] = Field(default_factory=list)
    viewport: Optional[Dict[str, Any]] = None


class RetryPolicy(BaseModel):
    """Retry policy configuration."""
    max_retries: int = 3
    retry_delay_seconds: int = 60
    backoff_multiplier: float = 2.0


class PlaybookBase(BaseModel):
    """Base playbook model."""
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    key: Optional[str] = None  # Internal identifier (per-tenant)
    version: str = "1.0.0"
    workflow: WorkflowStructure
    timeout_seconds: int = 3600
    retry_policy: Optional[RetryPolicy] = None
    on_failure: str = "fail"
    is_template: bool = False
    requires_approval: bool = False
    tags: List[str] = Field(default_factory=list)
    
    # OOTB Playbook fields
    playbook_key: Optional[str] = None  # Unique identifier for built-in playbooks
    is_builtin: bool = False  # True if SentinelGrid built-in
    severity_default: Optional[str] = None  # 'low', 'medium', 'high', 'critical'
    applicable_sources: List[str] = Field(default_factory=list)  # Data sources
    triggers: List[str] = Field(default_factory=list)  # Trigger conditions
    prerequisites: List[str] = Field(default_factory=list)  # Prerequisites
    artifacts_required: List[str] = Field(default_factory=list)  # Required artifacts
    phases: Optional[Any] = None  # NIST IR phases structure (allow dict or list)
    cis_controls: List[str] = Field(default_factory=list)  # CIS Controls
    
    # Framework mappings
    nist_controls: List[str] = Field(default_factory=list)  # NIST SP 800-53 control IDs (e.g., ["IR-4", "SI-3"])
    soc2_criteria: List[str] = Field(default_factory=list)  # SOC 2 Common Criteria (e.g., ["CC6.1", "CC7.1"])
    mitre_tactics: List[str] = Field(default_factory=list)  # MITRE tactics (e.g., ["TA0001", "TA0002"])
    mitre_techniques: List[str] = Field(default_factory=list)  # MITRE techniques (e.g., ["T1078", "T1566"])
    
    # Trigger configuration
    trigger_conditions: Optional[Dict[str, Any]] = None
    auto_trigger_enabled: bool = False
    trigger_priority: int = 0


class PlaybookCreate(PlaybookBase):
    """Playbook creation model."""
    pass


class PlaybookUpdate(BaseModel):
    """Playbook update model."""
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    version: Optional[str] = None
    workflow: Optional[WorkflowStructure] = None
    timeout_seconds: Optional[int] = None
    retry_policy: Optional[RetryPolicy] = None
    on_failure: Optional[str] = None
    is_template: Optional[bool] = None
    requires_approval: Optional[bool] = None
    tags: Optional[List[str]] = None
    severity_default: Optional[str] = None
    applicable_sources: Optional[List[str]] = None
    triggers: Optional[List[str]] = None
    prerequisites: Optional[List[str]] = None
    artifacts_required: Optional[List[str]] = None
    phases: Optional[Any] = None
    cis_controls: Optional[List[str]] = None
    nist_controls: Optional[List[str]] = None
    soc2_criteria: Optional[List[str]] = None
    mitre_tactics: Optional[List[str]] = None
    mitre_techniques: Optional[List[str]] = None
    trigger_conditions: Optional[Dict[str, Any]] = None
    auto_trigger_enabled: Optional[bool] = None
    trigger_priority: Optional[int] = None


class Playbook(PlaybookBase):
    """Playbook model with database fields."""
    id: UUID
    tenant_id: UUID
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    n8n_workflow_id: Optional[str] = None
    n8n_webhook_url: Optional[str] = None

    class Config:
        from_attributes = True


class PlaybookExecutionCreate(BaseModel):
    """Playbook execution creation model."""
    trigger_type: str  # 'alert', 'incident', 'manual', 'scheduled'
    trigger_id: Optional[UUID] = None
    parameters: Optional[Dict[str, Any]] = None


class PlaybookExecution(BaseModel):
    """Playbook execution model."""
    id: UUID
    playbook_id: UUID
    tenant_id: UUID
    trigger_type: Optional[str] = None
    trigger_id: Optional[UUID] = None
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    n8n_execution_id: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    logs: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime

    class Config:
        from_attributes = True


class ObservableDefinition(BaseModel):
    """Observable definition model."""
    id: UUID
    playbook_id: UUID
    node_id: str
    data_type: str
    extraction_path: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    mark_as_ioc: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class AnalyzerDefinition(BaseModel):
    """Analyzer definition model."""
    id: UUID
    playbook_id: UUID
    node_id: str
    analyzer_id: str
    observable_node_id: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    class Config:
        from_attributes = True


class PlaybookCopy(BaseModel):
    """Playbook copy request model."""
    new_name: str
    new_key: Optional[str] = None
    new_version: Optional[str] = None
    copy_executions: bool = False


class PlaybookValidationResult(BaseModel):
    """Playbook validation result."""
    valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
