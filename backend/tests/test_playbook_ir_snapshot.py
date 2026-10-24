"""Synthetic snapshot qualification; no persistence or workflow execution."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
from uuid import UUID

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "libs"))
from sg_agent_runtime.playbook_catalog import load_playbook_catalog
from sg_agent_runtime.playbook_ir_loader import load_crosswalk_entries, load_executor_aliases
from sg_agent_runtime import playbook_ir_snapshot as module

TENANT = UUID("10000000-0000-0000-0000-000000000001")
VERSION = UUID("20000000-0000-0000-0000-000000000001")
OTHER = UUID("30000000-0000-0000-0000-000000000001")


@pytest.fixture
def inputs():
    return dict(tenant_id=TENANT, version_id=VERSION, compiler_build="synthetic-build-v1",
        playbook_key="ACCOUNT-COMPROMISE", catalog_playbooks=deepcopy(load_playbook_catalog()),
        ootb_playbooks=yaml.safe_load((Path(__file__).parent / "fixtures/account_compromise.synthetic.yaml").read_text())["playbooks"],
        crosswalk_entries=deepcopy(load_crosswalk_entries()), executor_aliases=deepcopy(load_executor_aliases()))


def test_round_trip_retains_complete_content_without_recompilation(inputs, monkeypatch):
    snapshot = module.capture_playbook_snapshot(**inputs)
    body = json.loads(snapshot.payload)
    assert body["source_inputs"]["ootb_playbooks"] == inputs["ootb_playbooks"]
    assert body["source_inputs"]["response_packs"]
    monkeypatch.setattr(module, "compile_playbook_irs", lambda **kwargs: pytest.fail("recompilation forbidden"))
    ir = module.read_pinned_playbook(snapshot.model_dump_json(), expected_tenant_id=TENANT, expected_version_id=VERSION, expected_payload_sha256=snapshot.payload_sha256)
    assert ir.playbook_key == "ACCOUNT-COMPROMISE"
    assert len(ir.actions) == 9
    assert ir.version == "synthetic-qualification-1"
    assert all(action.executor_binding_id is None for action in ir.actions)


def test_snapshot_is_stable_and_detached_from_mutable_sources_and_reads(inputs):
    snapshot = module.capture_playbook_snapshot(**inputs)
    assert snapshot == module.capture_playbook_snapshot(**inputs)
    before = snapshot.payload
    inputs["ootb_playbooks"][0]["phases"][0]["steps"][0]["label"] = "new content"
    changed = module.capture_playbook_snapshot(**inputs)
    assert changed.payload_sha256 != snapshot.payload_sha256
    assert snapshot.payload == before
    ir = module.read_pinned_playbook(snapshot.model_dump_json(), expected_tenant_id=TENANT, expected_version_id=VERSION, expected_payload_sha256=snapshot.payload_sha256)
    ir.actions.clear()
    assert len(module.read_pinned_playbook(snapshot.model_dump_json(), expected_tenant_id=TENANT, expected_version_id=VERSION, expected_payload_sha256=snapshot.payload_sha256).actions) == 9
    with pytest.raises(ValueError):
        snapshot.payload = changed.payload


@pytest.mark.parametrize("field", ["tenant_id", "version_id", "compiler_build"])
def test_scope_and_build_are_part_of_digest(inputs, field):
    before = module.capture_playbook_snapshot(**inputs)
    inputs[field] = "synthetic-build-v2" if field == "compiler_build" else OTHER
    assert module.capture_playbook_snapshot(**inputs).payload_sha256 != before.payload_sha256


@pytest.mark.parametrize("tenant,version", [(OTHER, VERSION), (TENANT, OTHER)])
def test_cross_tenant_and_wrong_version_reads_denied(inputs, tenant, version):
    snapshot = module.capture_playbook_snapshot(**inputs)
    with pytest.raises(ValueError, match="scope/version"):
        module.read_pinned_playbook(snapshot.model_dump_json(), expected_tenant_id=tenant, expected_version_id=version, expected_payload_sha256=snapshot.payload_sha256)


@pytest.mark.parametrize("value", [UUID(int=0), "tenant-slug", str(TENANT)])
def test_only_non_nil_typed_scope_accepted(inputs, value):
    inputs["tenant_id"] = value
    with pytest.raises(ValueError): module.capture_playbook_snapshot(**inputs)


@pytest.mark.parametrize("change", ["missing", "duplicate", "invalid", "unknown_key"])
def test_unqualified_source_cannot_be_pinned(inputs, change):
    if change == "missing": inputs["ootb_playbooks"] = []
    elif change == "duplicate": inputs["ootb_playbooks"] *= 2
    elif change == "invalid": inputs["ootb_playbooks"][0]["phases"][0]["steps"][0]["type"] = "loop"
    else: inputs["playbook_key"] = "unknown"
    with pytest.raises(ValueError): module.capture_playbook_snapshot(**inputs)


def test_digest_tampering_and_unknown_envelope_rejected(inputs):
    snapshot = module.capture_playbook_snapshot(**inputs)
    serialized = snapshot.model_dump()
    serialized["payload"] += " "
    with pytest.raises(ValueError): module.PlaybookIRSnapshot.model_validate(serialized)
    serialized["payload_sha256"] = hashlib.sha256(serialized["payload"].encode()).hexdigest()
    with pytest.raises(ValueError): module.PlaybookIRSnapshot.model_validate(serialized)
    serialized = snapshot.model_dump(); serialized["schema_version"] = "unknown"
    with pytest.raises(ValueError): module.PlaybookIRSnapshot.model_validate(serialized)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), "x" * 262144])
def test_nonfinite_or_oversize_input_rejected(inputs, value):
    inputs["ootb_playbooks"][0]["extra_source_value"] = value
    with pytest.raises(ValueError): module.capture_playbook_snapshot(**inputs)


def test_mapping_key_order_does_not_change_digest(inputs):
    first = module.capture_playbook_snapshot(**inputs)
    inputs["executor_aliases"] = dict(reversed(list(inputs["executor_aliases"].items())))
    assert module.capture_playbook_snapshot(**inputs) == first


def test_trusted_digest_rejects_replacement_under_same_version(inputs):
    original = module.capture_playbook_snapshot(**inputs)
    inputs["ootb_playbooks"][0]["name"] = "Replacement content"
    replacement = module.capture_playbook_snapshot(**inputs)
    with pytest.raises(ValueError, match="digest mismatch"):
        module.read_pinned_playbook(replacement.model_dump_json(), expected_tenant_id=TENANT,
            expected_version_id=VERSION, expected_payload_sha256=original.payload_sha256)


def test_complete_envelope_and_json_keys_required(inputs):
    snapshot = module.capture_playbook_snapshot(**inputs)
    body = json.loads(snapshot.payload)
    del body["source_inputs"]
    payload = module._canonical(body)
    with pytest.raises(ValueError):
        module.PlaybookIRSnapshot(payload=payload, payload_sha256=hashlib.sha256(payload.encode()).hexdigest())
    inputs["ootb_playbooks"][0][1] = "ambiguous key"
    with pytest.raises(ValueError): module.capture_playbook_snapshot(**inputs)
