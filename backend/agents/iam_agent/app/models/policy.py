"""Policy management models."""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class PolicyCreateRequest(BaseModel):
    """Request to create a new authorization policy."""
    name: str
    type: str  # role, time, ip, group, client, user, js, aggregate
    logic: Optional[str] = "POSITIVE"  # POSITIVE or NEGATIVE
    decisionStrategy: Optional[str] = None  # UNANIMOUS, AFFIRMATIVE, CONSENSUS
    roles: Optional[List[Dict[str, Any]]] = None
    users: Optional[List[str]] = None
    groups: Optional[List[Dict[str, Any]]] = None
    clients: Optional[List[str]] = None
    ipAddress: Optional[str] = None
    dayMonth: Optional[str] = None
    dayMonthEnd: Optional[str] = None
    hour: Optional[str] = None
    minute: Optional[str] = None
    hourEnd: Optional[str] = None
    minuteEnd: Optional[str] = None
    notBefore: Optional[str] = None
    notOnOrAfter: Optional[str] = None
    code: Optional[str] = None
    policies: Optional[List[Dict[str, str]]] = None  # For aggregate policies
    clientId: Optional[str] = None


class PolicyUpdateRequest(BaseModel):
    """Request to update an authorization policy."""
    name: Optional[str] = None
    type: Optional[str] = None
    logic: Optional[str] = None
    decisionStrategy: Optional[str] = None
    roles: Optional[List[Dict[str, Any]]] = None
    users: Optional[List[str]] = None
    groups: Optional[List[Dict[str, Any]]] = None
    clients: Optional[List[str]] = None
    ipAddress: Optional[str] = None
    dayMonth: Optional[str] = None
    dayMonthEnd: Optional[str] = None
    hour: Optional[str] = None
    minute: Optional[str] = None
    hourEnd: Optional[str] = None
    minuteEnd: Optional[str] = None
    notBefore: Optional[str] = None
    notOnOrAfter: Optional[str] = None
    code: Optional[str] = None
    policies: Optional[List[Dict[str, str]]] = None


class PolicyResponse(BaseModel):
    """Response with authorization policy data."""
    id: str
    name: str
    type: str
    logic: Optional[str] = None
    decisionStrategy: Optional[str] = None
    roles: Optional[List[Dict[str, Any]]] = None
    users: Optional[List[str]] = None
    groups: Optional[List[Dict[str, Any]]] = None
    clients: Optional[List[str]] = None
    ipAddress: Optional[str] = None
    dayMonth: Optional[str] = None
    dayMonthEnd: Optional[str] = None
    hour: Optional[str] = None
    minute: Optional[str] = None
    hourEnd: Optional[str] = None
    minuteEnd: Optional[str] = None
    notBefore: Optional[str] = None
    notOnOrAfter: Optional[str] = None
    code: Optional[str] = None
    policies: Optional[List[Dict[str, str]]] = None


class PolicyTestRequest(BaseModel):
    """Request to test a policy evaluation."""
    userId: Optional[str] = None
    username: Optional[str] = None
    resourceId: Optional[str] = None
    action: Optional[str] = None
    roles: Optional[List[str]] = None
    clientId: Optional[str] = None


class PolicyTestResponse(BaseModel):
    """Response from policy evaluation test."""
    decision: str  # PERMIT or DENY
    status: str
    results: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None

