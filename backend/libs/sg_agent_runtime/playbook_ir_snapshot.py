"""Content-addressed recommendation IR snapshots; no storage or execution authority."""
from dataclasses import asdict
import hashlib
import json
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator

from .playbook_ir_compiler import compile_playbook_irs
from .playbook_ir_models import PlaybookIR
from .response_pack_matcher import RESPONSE_PACKS

SCHEMA = "playbook-ir-snapshot-v1"
MAX_PAYLOAD_BYTES = 262144


def _canonical(value):
    # Reject coercion of object keys; a digest must describe unambiguous JSON.
    def check(item):
        if isinstance(item, dict):
            if any(not isinstance(key, str) for key in item):
                raise ValueError("Snapshot object keys must be strings")
            for child in item.values():
                check(child)
        elif isinstance(item, (list, tuple)):
            for child in item:
                check(child)
    check(value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _uuid(value):
    if not isinstance(value, UUID) or value.int == 0:
        raise ValueError("A non-nil UUID is required")
    return str(value)


class PlaybookIRSnapshot(BaseModel):
    """Frozen strings avoid mutable nested model/list references in a pinned record."""
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    schema_version: Literal["playbook-ir-snapshot-v1"] = SCHEMA
    payload: str
    payload_sha256: str

    @model_validator(mode="after")
    def verify_payload(self):
        data = self.payload.encode("utf-8")
        if not 2 <= len(data) <= MAX_PAYLOAD_BYTES:
            raise ValueError("Snapshot payload exceeds the bounded content size")
        if hashlib.sha256(data).hexdigest() != self.payload_sha256:
            raise ValueError("Snapshot content digest mismatch")
        body = json.loads(self.payload)
        if _canonical(body) != self.payload:
            raise ValueError("Snapshot must contain canonical JSON")
        if not isinstance(body, dict) or set(body) != {
            "schema_version", "tenant_id", "version_id", "compiler_build",
            "source_inputs", "compiled_ir",
        }:
            raise ValueError("Invalid snapshot envelope")
        if body["schema_version"] != SCHEMA:
            raise ValueError("Unsupported snapshot schema")
        for field in ("tenant_id", "version_id"):
            if _uuid(UUID(body[field])) != body[field]:
                raise ValueError("Snapshot UUID must be canonical")
        if not isinstance(body["compiler_build"], str) or not body["compiler_build"].strip():
            raise ValueError("Compiler build must be explicit")
        if not isinstance(body["source_inputs"], dict) or set(body["source_inputs"]) != {
            "catalog_playbooks", "ootb_playbooks", "crosswalk_entries", "executor_aliases", "response_packs",
        }:
            raise ValueError("Complete normalized compiler inputs are required")
        PlaybookIR.model_validate(body["compiled_ir"])
        return self


def capture_playbook_snapshot(*, tenant_id, version_id, compiler_build, playbook_key,
                              catalog_playbooks, ootb_playbooks, crosswalk_entries,
                              executor_aliases):
    """Compile once and retain complete normalized inputs and output for one key.

    Call only with server-verified scope at a future trusted publication boundary.
    UUID validation is not authentication. This helper does not publish a version.
    """
    tenant = _uuid(tenant_id)
    version = _uuid(version_id)
    matching = [row for row in crosswalk_entries if row.canonical_playbook_key == playbook_key]
    if len(matching) != 1:
        raise ValueError("Exactly one canonical crosswalk entry is required")
    selected = matching[0]
    for rows, identity in ((catalog_playbooks, selected.catalog_id), (ootb_playbooks, selected.ootb_source_id)):
        if sum(row.get("id") == identity for row in rows) != 1:
            raise ValueError("Exactly one catalog and source definition are required")
    compiled = compile_playbook_irs(catalog_playbooks=catalog_playbooks,
        ootb_playbooks=ootb_playbooks, crosswalk_entries=matching, executor_aliases=executor_aliases)[0]
    if compiled.status != "ready":
        raise ValueError("Only ready recommendation IR may be captured")
    body = {
        "schema_version": SCHEMA, "tenant_id": tenant, "version_id": version,
        "compiler_build": compiler_build,
        "source_inputs": {"catalog_playbooks": catalog_playbooks, "ootb_playbooks": ootb_playbooks,
            "crosswalk_entries": [row.model_dump(mode="json") for row in crosswalk_entries],
            "executor_aliases": executor_aliases, "response_packs": [asdict(pack) for pack in RESPONSE_PACKS]},
        "compiled_ir": compiled.model_dump(mode="json"),
    }
    payload = _canonical(body)
    return PlaybookIRSnapshot(payload=payload, payload_sha256=hashlib.sha256(payload.encode("utf-8")).hexdigest())


def read_pinned_playbook(serialized_snapshot, *, expected_tenant_id, expected_version_id, expected_payload_sha256):
    """Read retained IR without loaders, compilation, model calls or provider I/O.

    Expected scope must come from trusted server context. Integrity is not origin
    authentication: an attacker can hash their own payload. Durable ownership,
    publication approval and authorization remain separate mandatory boundaries.
    """
    snapshot = PlaybookIRSnapshot.model_validate_json(serialized_snapshot)
    if snapshot.payload_sha256 != expected_payload_sha256:
        raise ValueError("Pinned playbook digest mismatch")
    body = json.loads(snapshot.payload)
    if body["tenant_id"] != _uuid(expected_tenant_id) or body["version_id"] != _uuid(expected_version_id):
        raise ValueError("Pinned playbook scope/version mismatch")
    return PlaybookIR.model_validate(body["compiled_ir"])
