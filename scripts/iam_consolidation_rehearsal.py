"""Offline synthetic transfer planner. No SQL, evaluator, credentials or cutover.

This deliberately accepts only an explicitly synthetic envelope. It preserves
opaque row content and rejects unmapped tables; it is not a production exporter.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1]
PROFILES = ("application-database-profile.json", "iam-database-profile.json")
TABLES = {
    "catalog.public.policies": "iam.effective_policies",
    "catalog.public.policy_rules": "iam.effective_policy_rules",
    "iam.public.entitlements": "iam.subject_grants",
    "catalog.public.policy_templates": "catalog.template_candidates",
    "catalog.public.entitlements": "catalog.permission_definitions",
}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def profile_fingerprints(root=ROOT):
    result = {}
    for name in PROFILES:
        profile = json.loads((root / "publication" / name).read_text())
        for item in profile["migrations"]:
            path = root / item["path"]
            if hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
                raise ValueError("Migration source drift: " + item["path"])
        result[name] = digest(profile)
    return result


def uuid(value):
    if not isinstance(value, str) or str(UUID(value)) != value:
        raise ValueError("Canonical tenant/entity UUID required")
    return value


def plan(snapshot, fingerprints):
    if set(snapshot) != {"synthetic", "profiles", "tables"} or snapshot["synthetic"] is not True:
        raise ValueError("Only explicit synthetic envelopes are supported")
    if snapshot["profiles"] != fingerprints:
        raise ValueError("Unknown or changed source profile; reconcile histories first")
    tables = snapshot["tables"]
    if set(tables) != set(TABLES):
        raise ValueError("Missing or unmapped source table")
    output, seen, policies = {}, {}, {}
    for source, destination in TABLES.items():
        rows = tables[source]
        if not isinstance(rows, list):
            raise ValueError("Rows must be a list")
        seen[source] = set()
        for row in rows:
            identifier = uuid(row["id"])
            if identifier in seen[source]:
                raise ValueError("Duplicate source identity")
            seen[source].add(identifier)
            if source != "catalog.public.policy_rules":
                if row.get("tenant_id") is None and source == "catalog.public.policy_templates":
                    pass  # Existing global template candidates are not authority.
                else:
                    uuid(row["tenant_id"])
            if source == "catalog.public.policies":
                if row.get("is_template") is not False:
                    raise ValueError("Mixed policy/template semantics require explicit review")
                if row.get("policy_type") not in {"signon", "access", "approval", "sod", "authorization"}:
                    raise ValueError("Unreviewed policy type")
                if not isinstance(row.get("policy_data"), dict):
                    raise ValueError("Policy payload must be preserved as an object")
                policies[identifier] = row["tenant_id"]
            if source == "iam.public.entitlements":
                for field in ("resource_type", "resource_id", "action", "granted_to_type"):
                    if not isinstance(row.get(field), str) or not row[field]:
                        raise ValueError("Not a subject grant")
                uuid(row["granted_to_id"])
                if row["granted_to_type"] not in {"user", "role", "group"}:
                    raise ValueError("Unknown subject type")
                if row.get("status") not in {"active", "expired", "revoked", "pending_review", "suspended"}:
                    raise ValueError("Unknown grant status")
        output[destination] = sorted(deepcopy(rows), key=lambda row: row["id"])
    for rule in tables["catalog.public.policy_rules"]:
        parent = policies.get(rule.get("policy_id"))
        if parent is None or ("tenant_id" in rule and rule["tenant_id"] != parent):
            raise ValueError("Orphan or cross-tenant rule")
    grants = tables["iam.public.entitlements"]
    keys = [tuple(row[k] for k in ("tenant_id", "resource_type", "resource_id", "action", "granted_to_type", "granted_to_id")) for row in grants]
    if len(keys) != len(set(keys)):
        raise ValueError("Conflicting logical grants")
    return {"mode": "synthetic_plan_only", "executable": False,
            "profiles": deepcopy(fingerprints), "tables": output,
            "reconciliation": {TABLES[s]: {"count": len(output[TABLES[s]]), "sha256": digest(output[TABLES[s]])} for s in TABLES},
            "blockers": ["native Flyway/model rehearsal", "all writers and principal/audit relations",
                         "template immutable version publication", "nonowner RLS qualification",
                         "cross-store admission ordering", "restore incarnation custody"]}


def verify_result(result, source, fingerprints):
    if result != plan(source, fingerprints):
        raise ValueError("Transfer plan differs from source; do not cut over")


if __name__ == "__main__":
    print(json.dumps({"mode": "source_profile_validation_only", "profiles": profile_fingerprints()}, indent=2))
