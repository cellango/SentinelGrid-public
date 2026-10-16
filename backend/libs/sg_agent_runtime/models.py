"""Pydantic models for the SentinelGrid agent runtime."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------

class AgentTask(BaseModel):
    """A unit of work dispatched to an agent."""

    id: str = Field(default_factory=_new_id)
    tenant_id: str
    incident_id: str | None = None
    case_id: str | None = None
    agent_id: str  # which agent should handle this
    task_type: str  # e.g. "triage_alert", "investigate_incident", "execute_playbook"
    priority: str = "medium"  # critical, high, medium, low
    status: str = "pending"  # pending, claimed, running, awaiting_approval, completed, failed
    payload: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)  # enrichment context
    result: dict[str, Any] | None = None
    error: str | None = None
    parent_task_id: str | None = None  # for delegation chains
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
    claimed_by: str | None = None  # agent instance id
    requires_approval: bool = False
    approval_status: str | None = None  # pending, approved, rejected
    approval_reason: str | None = None


# ---------------------------------------------------------------------------
# Memory
# ---------------------------------------------------------------------------

class AgentMemory(BaseModel):
    """A key-value memory entry scoped to an agent and tenant."""

    agent_id: str
    tenant_id: str
    incident_id: str | None = None
    case_id: str | None = None
    key: str
    value: dict[str, Any]
    ttl_seconds: int | None = None
    created_at: datetime = Field(default_factory=_utcnow)


# ---------------------------------------------------------------------------
# Definitions
# ---------------------------------------------------------------------------

class AgentDefinition(BaseModel):
    """Declarative definition of an agent's identity and capabilities."""

    agent_id: str
    name: str
    description: str
    system_prompt: str
    tools: list[str] = Field(default_factory=list)  # tool names this agent can use
    autonomy_level: str = "supervised"  # "full", "supervised", "approval_required"
    max_concurrent_tasks: int = 5


class ToolDefinition(BaseModel):
    """Declarative definition of a tool that agents can invoke."""

    name: str
    description: str
    parameters: dict[str, Any] = Field(default_factory=dict)  # JSON Schema
    requires_approval: bool = False
    risk_level: str = "low"  # low, medium, high, critical


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------

class TaskResult(BaseModel):
    """Outcome of a completed agent task."""

    task_id: str
    status: str  # completed, failed
    result: dict[str, Any] = Field(default_factory=dict)
    actions_taken: list[dict[str, Any]] = Field(default_factory=list)
    approval_requests: list[dict[str, Any]] = Field(default_factory=list)
    delegated_tasks: list[str] = Field(default_factory=list)
    tokens_used: int = 0
    duration_seconds: float = 0.0
