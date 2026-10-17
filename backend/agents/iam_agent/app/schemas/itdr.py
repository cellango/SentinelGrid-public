"""Bounded, untrusted threat assertions; none of these fields grants authority."""

import json
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator
from app.services.itdr_response_map import ThreatType


class ThreatSignal(BaseModel):
    model_config = ConfigDict(extra="forbid")
    threat_type: ThreatType
    user_id: UUID
    tenant_id: UUID | None = None
    realm: str | None = Field(default=None, min_length=1, max_length=100)
    context: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("context")
    @classmethod
    def bounded_context(cls, value):
        if len(json.dumps(value, allow_nan=False).encode()) > 2048:
            raise ValueError("Threat context exceeds 2048 bytes")
        pending = [(value, 0)]
        nodes = 0
        while pending:
            item, depth = pending.pop()
            nodes += 1
            if depth > 6 or nodes > 256:
                raise ValueError("Threat context is too complex")
            if isinstance(item, dict):
                pending.extend((child, depth + 1) for child in item.values())
            elif isinstance(item, list):
                pending.extend((child, depth + 1) for child in item)
        return value


class ThreatSignalBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    signals: list[ThreatSignal] = Field(min_length=1, max_length=10)


class ActionOutcome(BaseModel):
    action: str
    status: Literal["recorded", "blocked"]
    reason: str


class EnforcementResponse(BaseModel):
    proposal_id: UUID
    tenant_id: UUID
    user_id: UUID
    threat_type: ThreatType
    severity: str
    status: Literal["proposal_recorded"] = "proposal_recorded"
    auto_response_enabled: Literal[False] = False
    advisory_actions: list[ActionOutcome]
    enforcement_actions: list[ActionOutcome]
    soar_incident_id: None = None
    actions_recorded: list[str]
    actions_executed: list[str] = Field(default_factory=list)
    actions_skipped: list[str]
    errors: list[str] = Field(default_factory=list)
