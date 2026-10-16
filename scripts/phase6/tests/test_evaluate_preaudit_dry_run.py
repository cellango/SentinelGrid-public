from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1] / "evaluate-preaudit-dry-run.py"
)


def run_evaluator(tmp_path: Path, payload: dict) -> tuple[dict, str]:
    result_json = tmp_path / "result.json"
    review_json = tmp_path / "phase7-entry-review.json"
    review_md = tmp_path / "phase7-entry-review.md"
    result_json.write_text(json.dumps(payload, indent=2) + "\n")

    subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--result-json",
            str(result_json),
            "--output-json",
            str(review_json),
            "--output-md",
            str(review_md),
        ],
        check=True,
    )

    return json.loads(review_json.read_text()), review_md.read_text()


def test_failed_step_blocks_phase7_entry(tmp_path: Path) -> None:
    payload = {
        "timestamp_utc": "2026-04-18T18:00:00Z",
        "git_sha": "abc123",
        "git_ref": "phase6",
        "artifact_root": "/tmp/preaudit",
        "result_json": "/tmp/preaudit/result.json",
        "manifest_path": "/tmp/preaudit/evidence-manifest.json",
        "recovery_validation_path": "/tmp/preaudit/recovery-validation.json",
        "overall_status": "failed",
        "steps": [
            {
                "name": "verify_launch_scope_observability",
                "status": "failed",
                "artifact_dir": "/tmp/preaudit/verify-launch-scope-observability",
                "notes": "rerun the observability verifier",
            }
        ],
        "recovery_evidence": [],
        "gate_evidence": [],
    }

    review, markdown = run_evaluator(tmp_path, payload)

    assert review["phase7_entry_ready"] is False
    assert review["recommended_decision"] == "blocked"
    assert any("verify_launch_scope_observability" in item for item in review["blocking_items"])
    assert "Recommended decision: `Blocked`" in markdown


def test_clean_preaudit_is_phase7_eligible(tmp_path: Path) -> None:
    payload = {
        "timestamp_utc": "2026-04-18T19:00:00Z",
        "git_sha": "def456",
        "git_ref": "phase6",
        "artifact_root": "/tmp/preaudit",
        "result_json": "/tmp/preaudit/result.json",
        "manifest_path": "/tmp/preaudit/evidence-manifest.json",
        "recovery_validation_path": "/tmp/preaudit/recovery-validation.json",
        "overall_status": "passed",
        "steps": [
            {
                "name": "verify_launch_scope_observability",
                "status": "passed",
                "artifact_dir": "/tmp/preaudit/verify-launch-scope-observability",
                "notes": "passed",
            },
            {
                "name": "freeze_phase7_evidence_manifest",
                "status": "passed",
                "artifact_dir": "/tmp/preaudit/evidence-manifest.json",
                "notes": "passed",
            },
        ],
        "recovery_evidence": [
            {
                "name": "postgres_restore",
                "status": "passed",
                "within_timebox": True,
                "result_json": "/tmp/preaudit/postgres/result.json",
            }
        ],
        "gate_evidence": [
            {
                "gate": "G-10",
                "status": "passed",
                "items": [{"path": "docs/archive/validation/phase6-slice-6c-production-support-and-incident-rehearsal-closeout-2026-04-18.md", "exists": True}],
            }
        ],
    }

    review, markdown = run_evaluator(tmp_path, payload)

    assert review["phase7_entry_ready"] is True
    assert review["recommended_decision"] == "phase7-eligible"
    assert review["blocking_items"] == []
    assert "Recommended decision: `Eligible`" in markdown
