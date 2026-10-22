"""Versioned proposal bytes; identity and approval never come from model arguments."""

import hashlib
import json
import math
from uuid import UUID
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
import rfc8785

VERSION = "sentinelgrid-action-proposal-v1"
LIMIT = 32768


def canonical_uuid(value):
    if not isinstance(value, str) or str(UUID(value)) != value or UUID(value).int == 0:
        raise ValueError("Canonical non-nil UUID required")
    return value


def strict_json(data, *, limit=LIMIT):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate JSON field")
            result[key] = value
        return result

    def constant(_):
        raise ValueError("Non-finite JSON value")

    if len(data) > limit:
        raise ValueError("Proposal exceeds bounds")
    return json.loads(data, object_pairs_hook=pairs, parse_constant=constant)


def canonical(data):
    def bounded(value, depth=0):
        if depth > 12:
            raise ValueError("Proposal nesting exceeds bounds")
        if isinstance(value, (dict, list)):
            if len(value) > 256:
                raise ValueError("Proposal collection exceeds bounds")
            for child in value.values() if isinstance(value, dict) else value:
                bounded(child, depth + 1)
        elif isinstance(value, float) and not math.isfinite(value):
            raise ValueError("Non-finite proposal")

    bounded(data)
    try:
        result = rfc8785.dumps(data)
    except (rfc8785.CanonicalizationError, UnicodeError, TypeError):
        raise ValueError("Invalid canonical proposal") from None
    if len(result) > LIMIT:
        raise ValueError("Canonical proposal exceeds bounds")
    return result


def digest(data):
    return hashlib.sha256(canonical(data)).hexdigest()


class Target(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    kind: str = Field(pattern=r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$", max_length=80)
    resource_id: str
    _uuid = field_validator("resource_id")(canonical_uuid)


class ProposalInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    tool_id: str = Field(pattern=r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$", max_length=128)
    tool_version: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$")
    targets: list[Target] = Field(min_length=1, max_length=16)
    parameters: dict = Field(default_factory=dict)
    expected_effect: str = Field(min_length=1, max_length=2048)
    risk: str = Field(pattern=r"^(low|medium|high|critical)$")
    preconditions: dict = Field(default_factory=dict)
    compensation: dict = Field(default_factory=dict)
    verification: dict = Field(min_length=1)
    expires_at: int = Field(gt=0)

    @field_validator("targets")
    @classmethod
    def unique_targets(cls, targets):
        keys = [(t.kind, t.resource_id) for t in targets]
        if len(keys) != len(set(keys)):
            raise ValueError("Duplicate action target")
        return targets


def proposal_payload(
    body,
    *,
    tenant_id,
    case_id,
    case_revision,
    plan_revision,
    policy_version,
    action_id,
    proposal_id,
    actor_id,
):
    # The service supplies every bound authority/revision field; request bodies
    # cannot set tenant, actor, approvals, case/plan revision or policy version.
    value = body.model_dump()
    value["targets"] = sorted(
        value["targets"], key=lambda t: (t["kind"], t["resource_id"])
    )
    value.update(
        schema=VERSION,
        tenant_id=canonical_uuid(tenant_id),
        case_id=canonical_uuid(case_id),
        case_revision=case_revision,
        plan_revision=plan_revision,
        policy_version=policy_version,
        action_id=canonical_uuid(action_id),
        proposal_id=canonical_uuid(proposal_id),
        proposal_revision=1,
        proposed_by=canonical_uuid(actor_id),
    )
    canonical(value)
    return value


class ApprovalInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    proposal_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    decision: str = Field(pattern=r"^(approve|reject|revoke)$")
    reason: str = Field(min_length=1, max_length=2048)


class ProposalDocument(ProposalInput):
    schema_version: Literal[VERSION] = Field(alias="schema")
    tenant_id: str
    case_id: str
    case_revision: int = Field(gt=0)
    plan_revision: int = Field(gt=0)
    policy_version: Literal["action-policy-v1"]
    action_id: str
    proposal_id: str
    proposal_revision: int = Field(gt=0)
    proposed_by: str
    _bound_ids = field_validator(
        "tenant_id", "case_id", "action_id", "proposal_id", "proposed_by"
    )(canonical_uuid)


class ProposalRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    tenant_id: str
    case_id: str
    action_id: str
    proposal_id: str
    proposal_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    proposal_revision: int = Field(gt=0)
    status: Literal[
        "pending_approval",
        "approved",
        "rejected",
        "revoked",
        "expired",
        "stale",
        "approval_expired",
        "approval_authority_revoked",
    ]
    execution_available: Literal[False]
    proposal: ProposalDocument | None = None
    _ids = field_validator("tenant_id", "case_id", "action_id", "proposal_id")(
        canonical_uuid
    )

    @field_validator("execution_available", mode="before")
    @classmethod
    def execution_is_unavailable(cls, value):
        if value is not False:
            raise ValueError("Case records cannot admit execution")
        return value
