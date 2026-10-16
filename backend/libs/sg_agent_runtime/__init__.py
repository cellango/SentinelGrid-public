"""
SentinelGrid Agent Runtime

Async agent execution framework with Redis-backed task queues,
tool registries, memory stores, and LLM-driven agent loops.
"""

from importlib import import_module

__version__ = "0.1.0"

from .models import (
    AgentDefinition,
    AgentMemory,
    AgentTask,
    TaskResult,
    ToolDefinition,
)
from .soc_models import (
    SOCActionRecommendation,
    SOCCaseContext,
    SOCCaseMemory,
    SOCFeedbackRecord,
    SOCIncidentTriggerEvent,
    SOCPlaybookRecommendation,
    SOCRecommendationHistoryEntry,
    SOCRecommendationOutput,
    SOCRecordRef,
)
from .playbook_ir_models import (
    PlaybookCrosswalkEntry,
    PlaybookEntryCriterion,
    PlaybookEvidenceRequirement,
    PlaybookIR,
    PlaybookIRValidationIssue,
)
from .playbook_ir_loader import (
    load_compiled_playbook_irs,
    load_planner_playbooks,
)
from .agents import (
    BUILTIN_AGENTS,
    SOC_CASE_AGENT,
    SOC_INVESTIGATION_AGENT,
    SOC_RESPONSE_PLANNER_AGENT,
    SOC_TICKET_SCRIBE_AGENT,
    SOC_TRIAGE_AGENT,
    TRIAGE_AGENT,
    INVESTIGATION_AGENT,
    RESPONSE_AGENT,
    COMPLIANCE_AGENT,
    build_builtin_agents,
)
from .compliance_tools import (
    COMPLIANCE_TOOL_NAMES,
    ComplianceToolClient,
    build_compliance_tool_definitions,
    register_compliance_tools,
)
from .soc_tools import (
    SOC_READ_TOOL_NAMES,
    SOCToolClient,
    build_soc_tool_definitions,
    register_soc_tools,
)
from .compliance_workflow import (
    ComplianceAgentRecommendationRepository,
    ComplianceAgentRuntimeClient,
    ComplianceAgentWorkflowService,
)

__all__ = [
    "AgentDefinition",
    "AgentMemory",
    "AgentTask",
    "TaskResult",
    "ToolDefinition",
    "SOCActionRecommendation",
    "SOCCaseContext",
    "SOCCaseMemory",
    "SOCFeedbackRecord",
    "SOCIncidentTriggerEvent",
    "SOCPlaybookRecommendation",
    "SOCRecommendationHistoryEntry",
    "SOCRecommendationOutput",
    "SOCRecordRef",
    "PlaybookCrosswalkEntry",
    "PlaybookEntryCriterion",
    "PlaybookEvidenceRequirement",
    "PlaybookIR",
    "PlaybookIRValidationIssue",
    "load_compiled_playbook_irs",
    "load_planner_playbooks",
    "TaskQueue",
    "AgentLoop",
    "ToolRegistry",
    "AgentMemoryStore",
    "AgentLLMClient",
    "BUILTIN_AGENTS",
    "SOC_CASE_AGENT",
    "SOC_INVESTIGATION_AGENT",
    "SOC_RESPONSE_PLANNER_AGENT",
    "SOC_TICKET_SCRIBE_AGENT",
    "SOC_TRIAGE_AGENT",
    "TRIAGE_AGENT",
    "INVESTIGATION_AGENT",
    "RESPONSE_AGENT",
    "COMPLIANCE_AGENT",
    "COMPLIANCE_TOOL_NAMES",
    "ComplianceToolClient",
    "SOC_READ_TOOL_NAMES",
    "SOCToolClient",
    "build_builtin_agents",
    "build_compliance_tool_definitions",
    "build_soc_tool_definitions",
    "register_compliance_tools",
    "register_soc_tools",
    "ComplianceAgentRecommendationRepository",
    "ComplianceAgentRuntimeClient",
    "ComplianceAgentWorkflowService",
]

_LAZY_IMPORTS = {
    "TaskQueue": (".task_queue", "TaskQueue"),
    "AgentLoop": (".agent_loop", "AgentLoop"),
    "ToolRegistry": (".tool_registry", "ToolRegistry"),
    "AgentMemoryStore": (".memory", "AgentMemoryStore"),
    "AgentLLMClient": (".llm_client", "AgentLLMClient"),
}


def __getattr__(name: str):
    if name in _LAZY_IMPORTS:
        module_name, attr_name = _LAZY_IMPORTS[name]
        module = import_module(module_name, __name__)
        value = getattr(module, attr_name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
