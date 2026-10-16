"""IAM Policy models."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from uuid import UUID


# Policy DSL Types
PolicyType = Literal["signon", "access", "approval", "sod", "authorization"]
PolicyScope = Literal["tenant", "app", "entitlement"]
EvaluationResult = Literal["allow", "deny", "step_up", "require_approval", "auto_approve"]
ConflictType = Literal["overlapping", "contradictory", "circular"]
Severity = Literal["low", "medium", "high", "critical"]


# Condition Types
class Condition(BaseModel):
    """Policy condition."""
    type: str  # 'role', 'group', 'location', 'ip', 'device', 'time', 'risk_level', 'department', etc.
    op: str  # 'equals', 'includes', 'in', 'not_in', 'greater_than', 'less_than', 'contains', etc.
    value: Any  # Value to compare against
    field: Optional[str] = None  # Field name if type is 'attribute'


# Action Types
class Action(BaseModel):
    """Policy action."""
    type: str  # 'require_mfa', 'require_webauthn', 'deny', 'allow', 'log', 'notify', 'require_approval', etc.
    value: Optional[Any] = None  # Action value/parameter
    params: Optional[Dict[str, Any]] = None  # Additional parameters


# Policy Rule
class PolicyRule(BaseModel):
    """A rule within a policy."""
    id: str
    name: Optional[str] = None
    description: Optional[str] = None
    conditions: List[Condition]
    actions: List[Action]
    priority: int = 100


# Policy DSL
class PolicyDSL(BaseModel):
    """Policy DSL structure."""
    id: str
    type: PolicyType
    scope: PolicyScope = "tenant"
    scope_id: Optional[str] = None
    rules: List[PolicyRule]
    metadata: Optional[Dict[str, Any]] = None


# Policy Template Models
class PolicyTemplateBase(BaseModel):
    name: str
    display_name: str
    description: Optional[str] = None
    policy_type: PolicyType
    template_data: Dict[str, Any]  # Policy DSL JSON
    category: Optional[str] = None


class PolicyTemplateCreate(PolicyTemplateBase):
    is_system: bool = False


class PolicyTemplate(PolicyTemplateBase):
    id: UUID
    is_system: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Policy Models
class PolicyBase(BaseModel):
    name: str
    display_name: str
    description: Optional[str] = None
    policy_type: PolicyType
    scope: PolicyScope = "tenant"
    scope_id: Optional[UUID] = None
    policy_data: Dict[str, Any]  # Policy DSL JSON
    is_active: bool = True
    priority: int = 100


class PolicyCreate(PolicyBase):
    pass


class PolicyUpdate(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None
    policy_data: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    priority: Optional[int] = None


class Policy(PolicyBase):
    id: UUID
    tenant_id: UUID
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Policy Evaluation Models
class EvaluationContext(BaseModel):
    """Context for policy evaluation."""
    user_id: Optional[str] = None
    username: Optional[str] = None
    email: Optional[str] = None
    roles: Optional[List[str]] = None
    groups: Optional[List[str]] = None
    department: Optional[str] = None
    resource: Optional[str] = None  # App, entitlement, etc.
    resource_type: Optional[str] = None
    entitlement_ids: List[str] = Field(default_factory=list)
    action: Optional[str] = None  # 'signon', 'access', 'request'
    ip_address: Optional[str] = None
    country: Optional[str] = None
    device_id: Optional[str] = None
    device_known: Optional[bool] = None
    time_of_day: Optional[str] = None
    day_of_week: Optional[str] = None
    risk_score: Optional[float] = None
    risk_level: Optional[str] = None
    custom: Optional[Dict[str, Any]] = None  # Additional context


class PolicyEvaluationResult(BaseModel):
    """Result of policy evaluation."""
    result: EvaluationResult
    policy_id: UUID
    matched_rules: List[str]  # Rule IDs that matched
    actions: List[Action]  # Actions to take
    explanation: Optional[str] = None  # Human-readable explanation


# Policy Conflict Models
class PolicyConflictBase(BaseModel):
    conflict_type: ConflictType
    description: Optional[str] = None
    severity: Severity = "medium"


class PolicyConflict(PolicyConflictBase):
    id: UUID
    tenant_id: UUID
    policy_id_1: UUID
    policy_id_2: UUID
    detected_at: datetime
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None

    class Config:
        from_attributes = True


# Policy Analysis Models
class PolicyAnalysis(BaseModel):
    """Analysis of a policy."""
    policy_id: UUID
    total_rules: int
    active_rules: int
    complexity_score: float  # 0-1, higher = more complex
    potential_conflicts: List[PolicyConflict]
    recommendations: List[str]  # AI-generated recommendations


# Policy Editor Models
class PolicyNode(BaseModel):
    """Node in the policy editor graph."""
    id: str
    type: str  # 'condition', 'action', 'gateway'
    label: str
    data: Dict[str, Any]
    position: Dict[str, float]  # {x, y}


class PolicyEdge(BaseModel):
    """Edge in the policy editor graph."""
    id: str
    source: str  # Node ID
    target: str  # Node ID
    label: Optional[str] = None
    condition: Optional[str] = None  # Edge condition (e.g., "true", "false", "high_risk")


class PolicyGraph(BaseModel):
    """Graph representation of a policy."""
    nodes: List[PolicyNode]
    edges: List[PolicyEdge]


# AI Helper Models
class PolicyExplanation(BaseModel):
    """AI-generated explanation of a policy."""
    summary: str
    rules_explained: List[Dict[str, str]]  # [{rule_id, explanation}]
    potential_issues: List[str]
    recommendations: List[str]


class PolicyGenerationRequest(BaseModel):
    """Request to generate a policy from natural language."""
    description: str
    policy_type: PolicyType
    scope: Optional[PolicyScope] = "tenant"
    context: Optional[Dict[str, Any]] = None


class PolicyGenerationResult(BaseModel):
    """Generated policy from AI."""
    policy_dsl: Dict[str, Any]  # Policy DSL JSON
    explanation: str
    confidence: float  # 0-1
