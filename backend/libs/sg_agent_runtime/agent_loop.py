"""Core agent execution loop for the SentinelGrid agent runtime.

Each ``AgentLoop`` instance is bound to a single ``AgentDefinition`` and
continuously claims tasks from its Redis queue, processes them through an
LLM tool-use loop, and writes results back.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
import time
import traceback
import uuid
from typing import Any

from .llm_client import AgentLLMClient
from .memory import AgentMemoryStore
from .models import AgentDefinition, AgentTask, TaskResult
from .soc_case_task_handler import SOCCaseTaskHandler
from .task_queue import TaskQueue
from .tool_registry import ToolRegistry

logger = logging.getLogger(__name__)

MAX_TOOL_ITERATIONS = 25  # Safety cap to prevent infinite loops
SENSITIVE_PROMPT_KEYS = {
    "authorization",
    "access_token",
    "token",
    "refresh_token",
    "jwt",
    "api_key",
    "secret",
}


class AgentLoop:
    """Claims and executes tasks for a single agent definition."""

    def __init__(
        self,
        agent_def: AgentDefinition,
        task_queue: TaskQueue,
        tool_registry: ToolRegistry,
        memory: AgentMemoryStore,
        llm_client: AgentLLMClient,
    ) -> None:
        self.agent_def = agent_def
        self.task_queue = task_queue
        self.tool_registry = tool_registry
        self.memory = memory
        self.llm_client = llm_client
        self._running = False
        self._instance_id = f"{agent_def.agent_id}:{uuid.uuid4().hex[:8]}"

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    async def run_forever(self) -> None:
        """Main loop: claim tasks, execute, repeat."""
        self._running = True
        logger.info("Agent loop started: %s (%s)", self.agent_def.name, self._instance_id)

        while self._running:
            try:
                task = await self.task_queue.claim(self.agent_def.agent_id)
                if task:
                    await self.execute_task(task)
                else:
                    await asyncio.sleep(1)
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Unhandled error in agent loop %s", self._instance_id)
                await asyncio.sleep(2)

        logger.info("Agent loop stopped: %s", self._instance_id)

    def stop(self) -> None:
        self._running = False

    # ------------------------------------------------------------------
    # Task execution
    # ------------------------------------------------------------------

    async def execute_task(self, task: AgentTask) -> TaskResult:
        """Execute a single task through the LLM tool-use loop."""
        start = time.monotonic()
        total_tokens = 0
        actions_taken: list[dict[str, Any]] = []
        approval_requests: list[dict[str, Any]] = []
        delegated_tasks: list[str] = []

        try:
            # 1. Update status to running
            task.status = "running"
            task.claimed_by = self._instance_id

            if SOCCaseTaskHandler.supports(task):
                handler = SOCCaseTaskHandler(memory=self.memory)
                result = await handler.handle(task)
                await self.task_queue.complete(task.id, result)
                await self._save_learnings(task, result)
                return result

            # 2. Build initial messages
            messages = self._build_messages(task)

            # 3. Get tools in LLM format
            llm_tools = self.tool_registry.to_llm_tools(self.agent_def.tools)

            # 4. Load relevant memories
            memories = await self.memory.search(
                self.agent_def.agent_id, task.tenant_id, prefix=""
            )
            if memories:
                mem_text = "\n".join(
                    f"- {m.key}: {json.dumps(m.value)}" for m in memories[:20]
                )
                messages.append(
                    {"role": "user", "content": f"[Agent memory]\n{mem_text}"}
                )

            # 5. Tool-use loop
            for iteration in range(MAX_TOOL_ITERATIONS):
                response = await self.llm_client.chat(
                    messages=messages,
                    tools=llm_tools if llm_tools else None,
                    temperature=0.1,
                )
                total_tokens += response["tokens"]["input"] + response["tokens"]["output"]

                # No tool calls — LLM produced a final answer
                if not response["tool_calls"]:
                    result = TaskResult(
                        task_id=task.id,
                        status="completed",
                        result={
                            "answer": response["content"],
                            "actions_taken": actions_taken,
                        },
                        actions_taken=actions_taken,
                        approval_requests=approval_requests,
                        delegated_tasks=delegated_tasks,
                        tokens_used=total_tokens,
                        duration_seconds=time.monotonic() - start,
                    )
                    await self.task_queue.complete(task.id, result)

                    # Save learnings to memory
                    await self._save_learnings(task, result)
                    return result

                # Process tool calls
                # Add assistant message with tool calls to history
                assistant_msg: dict[str, Any] = {"role": "assistant", "content": response["content"] or ""}
                assistant_msg["tool_calls"] = [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {"name": tc["name"], "arguments": json.dumps(tc["arguments"])},
                    }
                    for tc in response["tool_calls"]
                ]
                messages.append(assistant_msg)

                for tc in response["tool_calls"]:
                    tool_name = tc["name"]
                    tool_args = tc["arguments"]
                    tool_call_id = tc["id"]

                    # Check if this is a delegation request
                    if tool_name == "delegate":
                        child_result = await self._delegate(
                            target_agent=tool_args.get("agent_id", ""),
                            sub_task=tool_args,
                            parent_task=task,
                        )
                        delegated_tasks.append(child_result.task_id)
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_call_id,
                                "content": json.dumps(child_result.result),
                            }
                        )
                        continue

                    # Check approval requirements
                    needs_approval = await self._check_approval(
                        {"tool": tool_name, "arguments": tool_args}, task
                    )
                    if needs_approval:
                        await self.task_queue.request_approval(
                            task.id,
                            action={"tool": tool_name, "arguments": tool_args},
                            reason=f"Tool '{tool_name}' requires approval (agent autonomy: {self.agent_def.autonomy_level})",
                        )
                        approval_requests.append({"tool": tool_name, "arguments": tool_args})

                        # Wait for approval (poll with backoff)
                        approved = await self._wait_for_approval(task.id)
                        if not approved:
                            result = TaskResult(
                                task_id=task.id,
                                status="failed",
                                result={"reason": "Approval rejected"},
                                actions_taken=actions_taken,
                                approval_requests=approval_requests,
                                delegated_tasks=delegated_tasks,
                                tokens_used=total_tokens,
                                duration_seconds=time.monotonic() - start,
                            )
                            return result

                    # Execute the tool
                    tool_result = await self._call_tool(tool_name, tool_args, task)
                    actions_taken.append(
                        {"tool": tool_name, "arguments": tool_args, "result": tool_result}
                    )
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call_id,
                            "content": json.dumps(tool_result),
                        }
                    )

            # Exceeded max iterations
            result = TaskResult(
                task_id=task.id,
                status="completed",
                result={
                    "answer": "Task completed (max iterations reached)",
                    "actions_taken": actions_taken,
                },
                actions_taken=actions_taken,
                approval_requests=approval_requests,
                delegated_tasks=delegated_tasks,
                tokens_used=total_tokens,
                duration_seconds=time.monotonic() - start,
            )
            await self.task_queue.complete(task.id, result)
            return result

        except Exception as exc:
            error_msg = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
            logger.error("Task %s failed: %s", task.id, error_msg)
            await self.task_queue.fail(task.id, str(exc))
            return TaskResult(
                task_id=task.id,
                status="failed",
                result={"error": str(exc)},
                actions_taken=actions_taken,
                approval_requests=approval_requests,
                delegated_tasks=delegated_tasks,
                tokens_used=total_tokens,
                duration_seconds=time.monotonic() - start,
            )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_messages(self, task: AgentTask) -> list[dict[str, Any]]:
        """Build the initial message list from agent definition and task."""
        system = self.agent_def.system_prompt
        task_payload = json.dumps(task.payload, default=str)
        task_context = json.dumps(_redact_for_prompt(task.context), default=str) if task.context else "{}"

        return [
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": (
                    f"Task ID: {task.id}\n"
                    f"Task type: {task.task_type}\n"
                    f"Priority: {task.priority}\n"
                    f"Tenant: {task.tenant_id}\n\n"
                    f"Payload:\n{task_payload}\n\n"
                    f"Context:\n{task_context}"
                ),
            },
        ]

    async def _call_tool(
        self, tool_name: str, params: dict[str, Any], task: AgentTask
    ) -> dict[str, Any]:
        """Invoke a registered tool handler."""
        try:
            _def, handler = self.tool_registry.get(tool_name)
            safe_params = {
                key: value
                for key, value in params.items()
                if isinstance(key, str) and not key.startswith("_")
            }
            if "_agent_task" in inspect.signature(handler).parameters:
                safe_params["_agent_task"] = task
            result = await handler(**safe_params)
            return result if isinstance(result, dict) else {"result": result}
        except KeyError:
            return {"error": f"Unknown tool: {tool_name}"}
        except Exception as exc:
            logger.exception("Tool %s failed", tool_name)
            return {"error": f"{type(exc).__name__}: {exc}"}

    async def _delegate(
        self,
        target_agent: str,
        sub_task: dict[str, Any],
        parent_task: AgentTask,
    ) -> TaskResult:
        """Delegate work to another agent and wait for the result."""
        child = AgentTask(
            tenant_id=parent_task.tenant_id,
            agent_id=target_agent,
            task_type=sub_task.get("task_type", "delegated"),
            priority=parent_task.priority,
            payload=sub_task.get("payload", {}),
            context={**parent_task.context, "delegated_from": parent_task.id},
            parent_task_id=parent_task.id,
        )
        await self.task_queue.submit(child)
        logger.info(
            "Delegated task %s -> %s (child %s)", parent_task.id, target_agent, child.id
        )

        # Poll until child completes (with timeout)
        for _ in range(300):  # ~5 minutes at 1s intervals
            child_state = await self.task_queue.get_task(child.id)
            if child_state and child_state.status in ("completed", "failed"):
                return TaskResult(
                    task_id=child.id,
                    status=child_state.status,
                    result=child_state.result or {},
                )
            await asyncio.sleep(1)

        return TaskResult(
            task_id=child.id,
            status="failed",
            result={"error": "Delegation timed out"},
        )

    async def _check_approval(
        self, action: dict[str, Any], task: AgentTask
    ) -> bool:
        """Determine whether *action* requires human approval."""
        # Agents with full autonomy never need approval
        if self.agent_def.autonomy_level == "full":
            return False

        # Agents that always need approval
        if self.agent_def.autonomy_level == "approval_required":
            return True

        # "supervised" — check the tool's risk level
        tool_name = action.get("tool", "")
        try:
            tool_def, _ = self.tool_registry.get(tool_name)
            if tool_def.requires_approval:
                return True
            if tool_def.risk_level in ("high", "critical"):
                return True
        except KeyError:
            pass

        return False

    async def _wait_for_approval(self, task_id: str, timeout: int = 600) -> bool:
        """Poll until the task is approved or rejected (or timeout)."""
        for _ in range(timeout):
            task = await self.task_queue.get_task(task_id)
            if task is None:
                return False
            if task.approval_status == "approved":
                return True
            if task.approval_status == "rejected":
                return False
            if task.status not in ("awaiting_approval", "running"):
                return False
            await asyncio.sleep(1)
        return False

    async def _save_learnings(self, task: AgentTask, result: TaskResult) -> None:
        """Persist useful context from the task execution as agent memory."""
        try:
            if result.status == "completed" and result.result:
                key = f"task:{task.task_type}:{task.id[:8]}"
                await self.memory.store(
                    agent_id=self.agent_def.agent_id,
                    tenant_id=task.tenant_id,
                    key=key,
                    value={
                        "task_type": task.task_type,
                        "summary": str(result.result.get("answer", ""))[:500],
                        "actions": len(result.actions_taken),
                    },
                    ttl_seconds=86400,  # 24 hours
                )
        except Exception:
            logger.debug("Failed to save learnings for task %s", task.id, exc_info=True)


def _redact_for_prompt(value: Any) -> Any:
    """Redact credential-bearing context before building LLM-visible prompts."""
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            if str(key).strip().lower() in SENSITIVE_PROMPT_KEYS:
                redacted[key] = "[redacted]"
            else:
                redacted[key] = _redact_for_prompt(item)
        return redacted
    if isinstance(value, list):
        return [_redact_for_prompt(item) for item in value]
    return value
