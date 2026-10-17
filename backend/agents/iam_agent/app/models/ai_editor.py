"""Bounded advisory contracts. These models confer no publication authority."""

import json
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

Text = Annotated[str, Field(min_length=1, max_length=500)]
Identifier = Annotated[
    str, Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
]


def bounded_json(value):
    # Limits parsed content, not total HTTP ingress bytes. Proxy limits are separate.
    count = 0

    def visit(item, depth=0):
        nonlocal count
        count += 1
        if depth > 10 or count > 2000:
            raise ValueError("Editor content is too complex")
        if isinstance(item, dict):
            for child in item.values():
                visit(child, depth + 1)
        elif isinstance(item, list):
            for child in item:
                visit(child, depth + 1)

    visit(value)
    encoded = json.dumps(value, allow_nan=False, ensure_ascii=True)
    if len(encoded.encode()) > 32768:
        raise ValueError("Editor content exceeds 32 KiB")
    return value


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


class DraftCondition(StrictModel):
    type: Literal["role", "group"]
    op: Literal["includes"]
    value: Annotated[str, Field(min_length=1, max_length=100)]


class DraftAction(StrictModel):
    type: Literal["allow", "deny"]


class DraftRule(StrictModel):
    id: Identifier
    name: Text | None = None
    description: Text | None = None
    conditions: Annotated[list[DraftCondition], Field(min_length=1, max_length=8)]
    actions: Annotated[list[DraftAction], Field(min_length=1, max_length=1)]
    priority: Annotated[int, Field(ge=0, le=10000)] = 100


class PolicyDraft(StrictModel):
    id: Identifier
    type: Literal["access"]
    scope: Literal["tenant"] = "tenant"
    rules: Annotated[list[DraftRule], Field(min_length=1, max_length=20)]

    @model_validator(mode="after")
    def unique_rules(self):
        if len({r.id for r in self.rules}) != len(self.rules):
            raise ValueError("Duplicate rule IDs")
        return self


class GeneratedDraft(StrictModel):
    policy_dsl: PolicyDraft
    explanation: Text


class Explanation(StrictModel):
    summary: Text
    limitations: Annotated[list[Text], Field(min_length=1, max_length=10)]


class EditorRequest(StrictModel):
    mode: Literal["policy", "playbook"] = "policy"

    @model_validator(mode="before")
    @classmethod
    def bounded(cls, value):
        return bounded_json(value)


class GenerateRequest(EditorRequest):
    description: Annotated[str, Field(min_length=5, max_length=2000)]
    policy_type: Annotated[str, Field(min_length=1, max_length=32)] = "access"
    scope: Annotated[str, Field(min_length=1, max_length=32)] = "tenant"


class ExplainRequest(EditorRequest):
    graph_data: dict
    name: Text | None = None


class UnsupportedRequest(EditorRequest):
    graph_data: dict | None = None
    description: Annotated[str, Field(min_length=3, max_length=2000)] | None = None
