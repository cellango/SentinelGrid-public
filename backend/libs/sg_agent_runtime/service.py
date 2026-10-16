"""FastAPI service exposing the SentinelGrid agent runtime as an HTTP API."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .agents import BUILTIN_AGENTS, build_builtin_agents
from .agent_loop import AgentLoop
from .compliance_tools import register_compliance_tools
from .soc_tools import register_soc_tools
from .llm_client import AgentLLMClient
from .memory import AgentMemoryStore
from .models import AgentTask, TaskResult
from .soc_models import (
    SOCCaseContext,
    SOCCaseMemory,
    SOCFeedbackRecord,
    SOCFeedbackType,
    SOCOwnerRole,
    SOCRecommendationOutput,
)
from .task_queue import TaskQueue
from .tool_registry import ToolRegistry

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------

class SubmitTaskRequest(BaseModel):
    tenant_id: str
    incident_id: str | None = None
    case_id: str | None = None
    agent_id: str
    task_type: str
    priority: str = "medium"
    payload: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)
    parent_task_id: str | None = None


class ApproveRequest(BaseModel):
    approved_by: str


class RejectRequest(BaseModel):
    rejected_by: str
    reason: str


class TaskResponse(BaseModel):
    id: str
    tenant_id: str
    incident_id: str | None = None
    case_id: str | None = None
    agent_id: str
    task_type: str
    priority: str
    status: str
    payload: dict[str, Any]
    context: dict[str, Any]
    result: dict[str, Any] | None = None
    error: str | None = None
    parent_task_id: str | None = None
    created_at: str
    updated_at: str
    claimed_by: str | None = None
    requires_approval: bool
    approval_status: str | None = None
    approval_reason: str | None = None

    @classmethod
    def from_task(cls, task: AgentTask) -> "TaskResponse":
        return cls(
            id=task.id,
            tenant_id=task.tenant_id,
            incident_id=task.incident_id,
            case_id=task.case_id,
            agent_id=task.agent_id,
            task_type=task.task_type,
            priority=task.priority,
            status=task.status,
            payload=task.payload,
            context=task.context,
            result=task.result,
            error=task.error,
            parent_task_id=task.parent_task_id,
            created_at=task.created_at.isoformat(),
            updated_at=task.updated_at.isoformat(),
            claimed_by=task.claimed_by,
            requires_approval=task.requires_approval,
            approval_status=task.approval_status,
            approval_reason=task.approval_reason,
        )


class AgentStatus(BaseModel):
    agent_id: str
    name: str
    autonomy_level: str
    max_concurrent_tasks: int
    tools: list[str]
    available: bool
    runtime_status: str
    status_reason: str
    runtime_configured: bool
    tool_count: int
    missing_tools: list[str] = Field(default_factory=list)
    feature_flags: dict[str, bool] = Field(default_factory=dict)
    model_required: bool = True


class SOCCaseStateResponse(BaseModel):
    tenant_id: str
    incident_id: str
    case_id: str | None = None
    case_context: SOCCaseContext | None = None
    case_memory: SOCCaseMemory | None = None
    latest_recommendation: SOCRecommendationOutput | None = None
    recommendation_versions: list[SOCRecommendationOutput] = Field(default_factory=list)
    recent_tasks: list[TaskResponse] = Field(default_factory=list)


class SubmitSOCFeedbackRequest(BaseModel):
    tenant_id: str
    recommendation_id: str
    feedback_type: SOCFeedbackType
    actor_id: str
    actor_role: SOCOwnerRole = "HUMAN_OWNER"
    accepted: bool
    action_id: str | None = None
    playbook_id: str | None = None
    playbook_key: str | None = None
    playbook_name: str | None = None
    notes: str | None = None


# ---------------------------------------------------------------------------
# Shared state (populated during lifespan)
# ---------------------------------------------------------------------------

_task_queue: TaskQueue | None = None
_tool_registry: ToolRegistry | None = None
_memory: AgentMemoryStore | None = None
_llm_client: AgentLLMClient | None = None
_agent_loops: dict[str, AgentLoop] = {}
_active_agents = BUILTIN_AGENTS
_feature_flags: dict[str, bool] = {}

SOC_DECLARED_ONLY_AGENT_IDS = {
    "soc_triage_agent",
    "soc_investigation_agent",
    "soc_response_planner_agent",
    "soc_ticket_scribe_agent",
    "triage_agent",
    "investigation_agent",
    "response_agent",
}


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _task_queue, _tool_registry, _memory, _llm_client, _agent_loops, _active_agents, _feature_flags

    redis_url = os.environ.get("REDIS_URL", "redis://redis:6379")

    _task_queue = TaskQueue(redis_url)
    await _task_queue.connect()

    _memory = AgentMemoryStore(redis_url)
    await _memory.connect()

    compliance_enabled = _env_flag("COMPLIANCE_AGENT_ENABLED")
    _feature_flags = {"compliance_agent_enabled": compliance_enabled}
    _active_agents = build_builtin_agents(compliance_agent_enabled=compliance_enabled)

    _tool_registry = ToolRegistry()
    register_soc_tools(_tool_registry)
    if compliance_enabled:
        register_compliance_tools(_tool_registry)
    _llm_client = AgentLLMClient()

    # Start agent loops for runtime-available agents only. Declared agents remain
    # visible through /agents/status with missing tool details.
    import asyncio

    for agent_def in _active_agents.values():
        if not _agent_is_available(agent_def):
            logger.info(
                "Agent declared but not started: %s missing_tools=%s",
                agent_def.agent_id,
                _missing_tools(agent_def),
            )
            continue
        loop = AgentLoop(
            agent_def=agent_def,
            task_queue=_task_queue,
            tool_registry=_tool_registry,
            memory=_memory,
            llm_client=_llm_client,
        )
        _agent_loops[agent_def.agent_id] = loop
        asyncio.create_task(loop.run_forever())

    logger.info(
        "Agent runtime started with %d agents; compliance_agent_enabled=%s",
        len(_agent_loops),
        compliance_enabled,
    )
    yield

    # Shutdown
    for loop in _agent_loops.values():
        loop.stop()
    _agent_loops.clear()

    await _llm_client.close()
    await _memory.close()
    await _task_queue.close()
    logger.info("Agent runtime shut down")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="SentinelGrid Agent Runtime",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health() -> dict[str, Any]:
    """Process-level health check."""
    return {"status": "ok", "service": "agent-runtime", "version": "0.1.0"}


@app.get("/ready")
async def ready() -> JSONResponse:
    """Readiness check for Redis-backed task and memory state."""
    redis_ready = False
    redis_error: str | None = None
    try:
        if _task_queue is not None:
            await _task_queue.redis.ping()
            redis_ready = True
    except Exception as exc:
        redis_error = str(exc)

    statuses = [_build_agent_status(agent).model_dump(mode="json") for agent in _agents().values()]
    ready_status = redis_ready and any(status["available"] for status in statuses)
    payload = {
        "status": "ready" if ready_status else "not_ready",
        "ready": ready_status,
        "redis": {"ready": redis_ready, "error": redis_error},
        "feature_flags": _flags(),
        "active_agent_loops": sorted(_agent_loops),
        "agents": statuses,
    }
    return JSONResponse(status_code=200 if ready_status else 503, content=payload)


def _queue() -> TaskQueue:
    if _task_queue is None:
        raise RuntimeError("Task queue not initialised")
    return _task_queue


def _memory_store() -> AgentMemoryStore:
    if _memory is None:
        raise RuntimeError("Memory store not initialised")
    return _memory


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on", "enabled"}


def _agents() -> dict[str, Any]:
    if _agent_loops or _task_queue is not None:
        return _active_agents
    return build_builtin_agents(compliance_agent_enabled=_env_flag("COMPLIANCE_AGENT_ENABLED"))


def _flags() -> dict[str, bool]:
    if _feature_flags:
        return dict(_feature_flags)
    return {"compliance_agent_enabled": _env_flag("COMPLIANCE_AGENT_ENABLED")}


def _registry() -> ToolRegistry:
    if _tool_registry is not None:
        return _tool_registry
    registry = ToolRegistry()
    register_soc_tools(registry)
    if _env_flag("COMPLIANCE_AGENT_ENABLED"):
        register_compliance_tools(registry)
    return registry


def _missing_tools(agent_def: Any) -> list[str]:
    registered = _registry().names()
    return [tool_name for tool_name in agent_def.tools if tool_name not in registered]


def _agent_is_available(agent_def: Any) -> bool:
    runtime_status, _status_reason = _agent_runtime_state(agent_def)
    return runtime_status == "active"


def _agent_runtime_state(
    agent_def: Any,
    *,
    missing_tools: list[str] | None = None,
) -> tuple[str, str]:
    missing = _missing_tools(agent_def) if missing_tools is None else missing_tools
    if agent_def.agent_id == "compliance_agent" and not _flags()["compliance_agent_enabled"]:
        return "disabled", "feature_flag_disabled"
    if agent_def.agent_id in SOC_DECLARED_ONLY_AGENT_IDS:
        if missing:
            return "declared_only", "missing_or_disabled_tools"
        return "declared_only", "runtime_flow_not_enabled"
    if not agent_def.tools and agent_def.agent_id != "soc_case_agent":
        return "declared_only", "no_tools_registered"
    if missing:
        return "declared_only", "missing_or_disabled_tools"
    return "active", "runtime_loop_enabled"


def _agent_model_required(agent_def: Any) -> bool:
    return not agent_def.agent_id == "soc_case_agent"


def _internal_token() -> str:
    return os.environ.get("INTERNAL_SERVICE_TOKEN", "internal-service-token-change-in-production")


def _require_internal_token(authorization: str | None = Header(None, alias="Authorization")) -> None:
    expected = _internal_token()
    if not expected:
        return
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=403, detail="Missing internal bearer token")
    supplied = authorization.split(" ", 1)[1].strip()
    if supplied != expected:
        raise HTTPException(status_code=403, detail="Invalid internal bearer token")


def _has_task_auth_context(context: dict[str, Any]) -> bool:
    auth_context = context.get("auth") or context.get("auth_context") or {}
    return bool(
        context.get("authorization")
        or context.get("Authorization")
        or context.get("access_token")
        or context.get("token")
        or auth_context.get("authorization")
        or auth_context.get("Authorization")
        or auth_context.get("access_token")
        or auth_context.get("token")
    )


def _requires_compliance_user_auth(req: SubmitTaskRequest) -> bool:
    proposed_actions = req.payload.get("proposed_actions") or []
    write_tools = {
        "create_evidence_collection_task",
        "collect_evidence",
        "create_evidence_package",
        "generate_compliance_report",
    }
    for action in proposed_actions:
        if not isinstance(action, dict):
            continue
        if action.get("requires_approval"):
            return True
        if action.get("tool") in write_tools or action.get("action") in write_tools:
            return True
    return False


def _matches_playbook_feedback(
    playbook: Any,
    request: SubmitSOCFeedbackRequest,
) -> bool:
    playbook_data = (
        playbook.model_dump(mode="json")
        if hasattr(playbook, "model_dump")
        else dict(playbook)
    )
    if request.playbook_id and playbook_data.get("playbook_id") == request.playbook_id:
        return True
    if request.playbook_key and playbook_data.get("playbook_key") == request.playbook_key:
        return True
    if request.playbook_name and playbook_data.get("playbook_name") == request.playbook_name:
        return True
    return False


def _apply_feedback_to_recommendation(
    recommendation: SOCRecommendationOutput | None,
    request: SubmitSOCFeedbackRequest,
) -> SOCRecommendationOutput | None:
    if recommendation is None or recommendation.recommendation_id != request.recommendation_id:
        return recommendation

    updated = recommendation.model_copy(deep=True)
    next_status = "accepted" if request.accepted else "rejected"

    if request.action_id:
        for action in updated.recommended_actions:
            if action.action_id == request.action_id:
                action.status = next_status

    if request.playbook_id or request.playbook_key or request.playbook_name:
        for playbook in updated.recommended_playbooks:
            if _matches_playbook_feedback(playbook, request):
                playbook.status = next_status

    return updated


def _apply_feedback_to_recommendation_versions(
    recommendation_versions: list[SOCRecommendationOutput],
    request: SubmitSOCFeedbackRequest,
) -> list[SOCRecommendationOutput]:
    updated_versions: list[SOCRecommendationOutput] = []
    for recommendation in recommendation_versions:
        updated_versions.append(_apply_feedback_to_recommendation(recommendation, request) or recommendation)
    return updated_versions


def _apply_feedback_to_case_context(
    case_context: SOCCaseContext | None,
    request: SubmitSOCFeedbackRequest,
    feedback: SOCFeedbackRecord,
) -> SOCCaseContext | None:
    if case_context is None:
        return None

    updated = case_context.model_copy(deep=True)
    updated.feedback_history.append(feedback)
    updated.updated_at = feedback.created_at

    if request.playbook_id or request.playbook_key or request.playbook_name:
        next_status = "accepted" if request.accepted else "rejected"
        for playbook in updated.recommended_playbooks:
            if _matches_playbook_feedback(playbook, request):
                playbook.status = next_status

    return updated


async def _build_soc_case_state_response(
    *,
    tenant_id: str,
    incident_id: str,
    case_context: SOCCaseContext | None,
    case_memory: SOCCaseMemory | None,
    include_tasks: bool,
    task_limit: int,
) -> SOCCaseStateResponse:
    recent_tasks: list[TaskResponse] = []
    if include_tasks:
        tasks = await _queue().list_tasks(agent_id="soc_case_agent", tenant_id=tenant_id)
        incident_tasks = [task for task in tasks if task.incident_id == incident_id]
        incident_tasks.sort(key=lambda task: task.updated_at, reverse=True)
        recent_tasks = [TaskResponse.from_task(task) for task in incident_tasks[:task_limit]]

    return SOCCaseStateResponse(
        tenant_id=tenant_id,
        incident_id=incident_id,
        case_id=(case_context.case_id if case_context else case_memory.case_id if case_memory else incident_id),
        case_context=case_context,
        case_memory=case_memory,
        latest_recommendation=case_memory.last_recommendation if case_memory else None,
        recommendation_versions=list(case_memory.recommendation_versions) if case_memory else [],
        recent_tasks=recent_tasks,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.post(
    "/agents/tasks",
    response_model=TaskResponse,
    status_code=201,
    dependencies=[Depends(_require_internal_token)],
)
async def submit_task(req: SubmitTaskRequest) -> TaskResponse:
    """Submit a new task to an agent."""
    if req.agent_id not in _agents():
        raise HTTPException(status_code=400, detail=f"Unknown agent: {req.agent_id}")
    agent_def = _agents()[req.agent_id]
    if not _agent_is_available(agent_def):
        runtime_status, status_reason = _agent_runtime_state(agent_def)
        raise HTTPException(
            status_code=409,
            detail={
                "message": f"Agent is not active: {req.agent_id}",
                "runtime_status": runtime_status,
                "status_reason": status_reason,
                "missing_tools": _missing_tools(agent_def),
                "feature_flags": _flags(),
            },
        )
    if (
        req.agent_id == "compliance_agent"
        and _requires_compliance_user_auth(req)
        and not _has_task_auth_context(req.context)
    ):
        raise HTTPException(
            status_code=400,
            detail="Compliance Agent write-action tasks require user auth context",
        )

    task = AgentTask(
        tenant_id=req.tenant_id,
        incident_id=req.incident_id,
        case_id=req.case_id,
        agent_id=req.agent_id,
        task_type=req.task_type,
        priority=req.priority,
        payload=req.payload,
        context=req.context,
        parent_task_id=req.parent_task_id,
    )
    await _queue().submit(task)
    return TaskResponse.from_task(task)


@app.get(
    "/agents/tasks/{task_id}",
    response_model=TaskResponse,
    dependencies=[Depends(_require_internal_token)],
)
async def get_task(task_id: str) -> TaskResponse:
    """Get a task by ID."""
    task = await _queue().get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResponse.from_task(task)


@app.get(
    "/agents/tasks",
    response_model=list[TaskResponse],
    dependencies=[Depends(_require_internal_token)],
)
async def list_tasks(
    tenant_id: str | None = Query(None),
    agent_id: str | None = Query(None),
    status: str | None = Query(None),
) -> list[TaskResponse]:
    """List tasks with optional filters."""
    tasks = await _queue().list_tasks(agent_id=agent_id, tenant_id=tenant_id, status=status)
    return [TaskResponse.from_task(t) for t in tasks]


@app.post(
    "/agents/tasks/{task_id}/approve",
    response_model=TaskResponse,
    dependencies=[Depends(_require_internal_token)],
)
async def approve_task(task_id: str, req: ApproveRequest) -> TaskResponse:
    """Approve a task awaiting human approval."""
    try:
        task = await _queue().approve(task_id, approved_by=req.approved_by)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return TaskResponse.from_task(task)


@app.post(
    "/agents/tasks/{task_id}/reject",
    response_model=TaskResponse,
    dependencies=[Depends(_require_internal_token)],
)
async def reject_task(task_id: str, req: RejectRequest) -> TaskResponse:
    """Reject a task awaiting human approval."""
    try:
        await _queue().reject(task_id, rejected_by=req.rejected_by, reason=req.reason)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    task = await _queue().get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResponse.from_task(task)


@app.get(
    "/agents/approvals",
    response_model=list[TaskResponse],
    dependencies=[Depends(_require_internal_token)],
)
async def pending_approvals(tenant_id: str = Query(...)) -> list[TaskResponse]:
    """List tasks awaiting human approval for a tenant."""
    tasks = await _queue().get_pending_approvals(tenant_id)
    return [TaskResponse.from_task(t) for t in tasks]


def _build_agent_status(agent_def: Any) -> AgentStatus:
    missing_tools = _missing_tools(agent_def)
    runtime_status, status_reason = _agent_runtime_state(
        agent_def,
        missing_tools=missing_tools,
    )
    registered_tool_count = len(agent_def.tools) - len(missing_tools)
    return AgentStatus(
        agent_id=agent_def.agent_id,
        name=agent_def.name,
        autonomy_level=agent_def.autonomy_level,
        max_concurrent_tasks=agent_def.max_concurrent_tasks,
        tools=agent_def.tools,
        available=runtime_status == "active",
        runtime_status=runtime_status,
        status_reason=status_reason,
        runtime_configured=True,
        tool_count=registered_tool_count,
        missing_tools=missing_tools,
        feature_flags=_flags(),
        model_required=_agent_model_required(agent_def),
    )


@app.get(
    "/agents/status",
    response_model=list[AgentStatus],
    dependencies=[Depends(_require_internal_token)],
)
async def agent_status() -> list[AgentStatus]:
    """Return health/status of all registered agents."""
    return [_build_agent_status(agent_def) for agent_def in _agents().values()]


@app.get(
    "/agents/cases/{incident_id}",
    response_model=SOCCaseStateResponse,
    dependencies=[Depends(_require_internal_token)],
)
async def get_soc_case_state(
    incident_id: str,
    tenant_id: str = Query(...),
    include_tasks: bool = Query(True),
    task_limit: int = Query(10, ge=1, le=50),
) -> SOCCaseStateResponse:
    """Return the latest incident-scoped SOC case state."""
    case_context = await _memory_store().recall_case_context(tenant_id, incident_id)
    case_memory = await _memory_store().recall_case_memory(tenant_id, incident_id)
    if case_context is None and case_memory is None:
        raise HTTPException(status_code=404, detail="SOC case state not found")

    return await _build_soc_case_state_response(
        tenant_id=tenant_id,
        incident_id=incident_id,
        case_context=case_context,
        case_memory=case_memory,
        include_tasks=include_tasks,
        task_limit=task_limit,
    )


@app.post(
    "/agents/cases/{incident_id}/feedback",
    response_model=SOCCaseStateResponse,
    dependencies=[Depends(_require_internal_token)],
)
async def submit_soc_case_feedback(
    incident_id: str,
    req: SubmitSOCFeedbackRequest,
    include_tasks: bool = Query(True),
    task_limit: int = Query(10, ge=1, le=50),
) -> SOCCaseStateResponse:
    """Persist analyst feedback for the latest SOC recommendation cycle."""
    case_context = await _memory_store().recall_case_context(req.tenant_id, incident_id)
    case_memory = await _memory_store().recall_case_memory(req.tenant_id, incident_id)
    if case_context is None and case_memory is None:
        raise HTTPException(status_code=404, detail="SOC case state not found")

    feedback = SOCFeedbackRecord(
        recommendation_id=req.recommendation_id,
        incident_id=incident_id,
        tenant_id=req.tenant_id,
        feedback_type=req.feedback_type,
        actor_id=req.actor_id,
        actor_role=req.actor_role,
        accepted=req.accepted,
        action_id=req.action_id,
        playbook_id=req.playbook_id,
        playbook_key=req.playbook_key,
        playbook_name=req.playbook_name,
        notes=req.notes,
    )

    updated_context = _apply_feedback_to_case_context(case_context, req, feedback)
    updated_memory = case_memory.model_copy(deep=True) if case_memory is not None else None
    if updated_memory is not None:
        updated_memory.feedback_history.append(feedback)
        updated_memory.last_recommendation = _apply_feedback_to_recommendation(
            updated_memory.last_recommendation,
            req,
        )
        updated_memory.recommendation_versions = _apply_feedback_to_recommendation_versions(
            updated_memory.recommendation_versions,
            req,
        )
        updated_memory.last_refreshed_at = feedback.created_at

    if updated_context is not None:
        await _memory_store().store_case_context(updated_context)
    if updated_memory is not None:
        await _memory_store().store_case_memory(updated_memory)

    return await _build_soc_case_state_response(
        tenant_id=req.tenant_id,
        incident_id=incident_id,
        case_context=updated_context or case_context,
        case_memory=updated_memory or case_memory,
        include_tasks=include_tasks,
        task_limit=task_limit,
    )
