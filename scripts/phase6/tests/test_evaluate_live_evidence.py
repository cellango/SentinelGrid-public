from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1] / "evaluate-live-evidence.py"
)


def run_evaluator(tmp_path: Path, payload: dict) -> tuple[dict, str]:
    result_json = tmp_path / "result.json"
    gate_review_json = tmp_path / "gate-review.json"
    gate_review_md = tmp_path / "gate-review.md"
    result_json.write_text(json.dumps(payload, indent=2) + "\n")

    subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--result-json",
            str(result_json),
            "--output-json",
            str(gate_review_json),
            "--output-md",
            str(gate_review_md),
        ],
        check=True,
    )

    return json.loads(gate_review_json.read_text()), gate_review_md.read_text()


def test_plan_mode_stays_no_go(tmp_path: Path) -> None:
    payload = {
        "timestamp_utc": "2026-04-16T15:18:11Z",
        "git_sha": "abc123",
        "git_ref": "main",
        "mode": "plan",
        "audit_profile": "full",
        "audit_env": "audit",
        "restore_component": "all",
        "rollback": {
            "release": "api-gateway",
            "revision": "1",
            "namespace": "sg-core",
            "ready_url": "",
        },
        "artifact_root": "/tmp/phase6-plan",
        "overall_status": "partial",
        "steps": [
            {
                "name": "prepare_live_rls_inputs",
                "status": "skipped",
                "artifact_dir": "/tmp/phase6-plan/prep",
                "notes": "Live RLS inputs were skipped.",
            },
            {
                "name": "run_live_multi_tenant_audit",
                "status": "planned",
                "artifact_dir": "",
                "notes": "Audit not executed.",
            },
            {
                "name": "restore_drill",
                "status": "planned",
                "artifact_dir": "/tmp/phase6-plan/restore",
                "notes": "Restore drill not executed.",
            },
            {
                "name": "rollback_drill",
                "status": "planned",
                "artifact_dir": "/tmp/phase6-plan/rollback",
                "notes": "Rollback drill not executed.",
            },
        ],
    }

    review, markdown = run_evaluator(tmp_path, payload)

    assert review["recommended_decision"] == "no-go"
    assert review["ready_for_signoff"] is False
    assert any("plan mode" in item for item in review["blocking_items"])
    assert "Suggested Live Rerun Command" in markdown
    assert "--mode live" in review["live_rerun_command"]


def test_live_success_becomes_ready_for_signoff(tmp_path: Path) -> None:
    payload = {
        "timestamp_utc": "2026-04-16T20:00:00Z",
        "git_sha": "def456",
        "git_ref": "release-candidate",
        "mode": "live",
        "audit_profile": "full",
        "audit_env": "audit",
        "restore_component": "all",
        "rollback": {
            "release": "api-gateway",
            "revision": "12",
            "namespace": "sg-core",
            "ready_url": "https://api.example.com/ready",
        },
        "artifact_root": "/tmp/phase6-live",
        "overall_status": "passed",
        "steps": [
            {
                "name": "prepare_live_rls_inputs",
                "status": "passed",
                "artifact_dir": "/tmp/phase6-live/prep",
                "notes": "Inputs prepared.",
            },
            {
                "name": "run_live_multi_tenant_audit",
                "status": "passed",
                "artifact_dir": "/tmp/phase6-live/audit",
                "notes": "Audit completed.",
            },
            {
                "name": "restore_drill",
                "status": "passed",
                "artifact_dir": "/tmp/phase6-live/restore",
                "notes": "Restore drill completed.",
            },
            {
                "name": "rollback_drill",
                "status": "passed",
                "artifact_dir": "/tmp/phase6-live/rollback",
                "notes": "Rollback drill completed.",
            },
        ],
    }

    review, markdown = run_evaluator(tmp_path, payload)

    assert review["recommended_decision"] == "go"
    assert review["ready_for_signoff"] is True
    assert review["blocking_items"] == []
    assert "Recommended decision: `Go`" in markdown
