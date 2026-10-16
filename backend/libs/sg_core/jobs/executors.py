"""
Executors for scanner tools.

Currently uses dry-run fixtures for Prowler/Trivy. Replace the dry-run branch with
actual container invocation when scanners are available.
"""

import os
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List

FIXTURES = Path(__file__).resolve().parents[2] / "tests" / "jobs" / "fixtures"

def _run_command(cmd: List[str], env=None) -> Dict[str, Any]:
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if result.returncode != 0:
        return {"error": result.stderr.strip() or f"exit {result.returncode}"}
    return json.loads(result.stdout) if result.stdout else {}


def _run_docker(image: str, args: List[str]) -> Dict[str, Any]:
    cmd = ["docker", "run", "--rm"] + args + [image]
    return _run_command(cmd)


def _load_fixture(name: str) -> Dict[str, Any]:
    with open(FIXTURES / name, "r", encoding="utf-8") as f:
        return json.load(f)


def run_prowler(payload: Dict[str, Any], dry_run: bool = True) -> Dict[str, Any]:
    if dry_run:
        data = _load_fixture("prowler_sample.json")
        # inject account if provided
        acct = payload.get("cloud_connector_id")
        if acct:
            for f in data.get("findings", []):
                f["AccountId"] = acct
        return data
    use_docker = os.getenv("SCANNER_USE_DOCKER", "false").lower() in ("1", "true", "yes")
    if use_docker:
        image = os.getenv("CLOUD_SCANNER_IMAGE", "toniblyx/prowler:latest")
        args = ["-M", "json", "-f", "aws"]
        role = payload.get("cloud_connector_arn")
        if role:
            args += ["--role", role]
        # Assume AWS creds/role available in env/volume as appropriate
        return _run_docker(image, args)
    cmd = ["prowler", "-M", "json", "-f", "aws"]
    role = payload.get("cloud_connector_arn")
    if role:
        cmd += ["--role", role]
    return _run_command(cmd)


def run_trivy(payload: Dict[str, Any], dry_run: bool = True) -> Dict[str, Any]:
    if dry_run:
        data = _load_fixture("trivy_sample.json")
        img = payload.get("image_ref")
        if img:
            for r in data.get("Results", []):
                r["Target"] = img
        return data
    use_docker = os.getenv("SCANNER_USE_DOCKER", "false").lower() in ("1", "true", "yes")
    image_ref = payload.get("image_ref", "")
    if use_docker:
        image = os.getenv("CLOUD_SCANNER_IMAGE", "aquasec/trivy:latest")
        args = ["image", "--format", "json", image_ref]
        return _run_docker(image, args)
    cmd = ["trivy", "image", "--format", "json", image_ref]
    return _run_command(cmd)


def run_scanner(tool_id: str, payload: Dict[str, Any], dry_run: bool = True) -> Dict[str, Any]:
    if tool_id == "prowler":
        return run_prowler(payload, dry_run=dry_run)
    if tool_id == "trivy":
        return run_trivy(payload, dry_run=dry_run)
    raise ValueError(f"Unsupported tool_id: {tool_id}")


def run_gitleaks(payload: Dict[str, Any], dry_run: bool = True) -> Any:
    if dry_run:
        return _load_fixture("gitleaks_sample.json")
    repo_path = payload.get("repo_path", "")
    sidecar = os.getenv("GITLEAKS_SIDECAR_URL")
    if sidecar:
        import httpx

        try:
            resp = httpx.post(f"{sidecar}/scan", json={"repo_path": repo_path})
            resp.raise_for_status()
            payload = resp.json()
            raw = payload.get("raw", "")
            # Gitleaks returns JSON string in raw; parse if present
            return json.loads(raw) if raw else {}
        except Exception as e:
            return {"error": str(e)}
    use_docker = os.getenv("SCANNER_USE_DOCKER", "false").lower() in ("1", "true", "yes")
    if use_docker:
        image = os.getenv("GIT_SCANNER_IMAGE", "zricethezav/gitleaks:latest")
        cmd = ["docker", "run", "--rm", "-v", f"{repo_path}:/repo", image, "detect", "-s", "/repo", "-f", "json"]
        return _run_command(cmd)
    cmd = ["gitleaks", "detect", "-s", repo_path, "-f", "json"]
    return _run_command(cmd)


def run_checkov(payload: Dict[str, Any], dry_run: bool = True) -> Dict[str, Any]:
    if dry_run:
        return _load_fixture("checkov_sample.json")
    use_docker = os.getenv("SCANNER_USE_DOCKER", "false").lower() in ("1", "true", "yes")
    repo_path = payload.get("repo_path", "")
    if use_docker:
        image = os.getenv("GIT_SCANNER_IMAGE", "bridgecrew/checkov:latest")
        cmd = ["docker", "run", "--rm", "-v", f"{repo_path}:/repo", image, "-d", "/repo", "--output", "json"]
        return _run_command(cmd)
    cmd = ["checkov", "-d", repo_path, "--output", "json"]
    return _run_command(cmd)


def run_git_scanners(payload: Dict[str, Any], dry_run: bool = True) -> Dict[str, Any]:
    result = {
        "gitleaks": run_gitleaks(payload, dry_run=dry_run),
    }
    # Run checkov only when docker/local binary is usable
    use_docker = os.getenv("SCANNER_USE_DOCKER", "false").lower() in ("1", "true", "yes")
    if not os.getenv("GITLEAKS_SIDECAR_URL"):  # only include checkov in non-sidecar mode
        result["checkov"] = run_checkov(payload, dry_run=dry_run)
    return result


def run_zap(payload: Dict[str, Any], dry_run: bool = True) -> Dict[str, Any]:
    if dry_run:
        return _load_fixture("zap_sample.json")
    use_docker = os.getenv("SCANNER_USE_DOCKER", "false").lower() in ("1", "true", "yes")
    target = payload.get("target_url", "")
    if use_docker:
        image = os.getenv("APP_SCANNER_IMAGE", "ghcr.io/zaproxy/zaproxy:stable")
        # zap-baseline.py writes JSON to /zap/wrk; assume default
        return _run_command(["docker", "run", "--rm", image, "zap-baseline.py", "-t", target, "-J", "/zap/wrk/zap.json"])
    cmd = ["zap-baseline.py", "-t", target, "-J", "zap.json"]
    return _run_command(cmd)


def run_semgrep(payload: Dict[str, Any], dry_run: bool = True) -> Dict[str, Any]:
    if dry_run:
        return _load_fixture("semgrep_sample.json")
    use_docker = os.getenv("SCANNER_USE_DOCKER", "false").lower() in ("1", "true", "yes")
    repo_path = payload.get("repo_path", "")
    if use_docker:
        image = os.getenv("SEMGREP_SCANNER_IMAGE", "returntocorp/semgrep:latest")
        return _run_command(["docker", "run", "--rm", "-v", f"{repo_path}:/repo", image, "scan", "--config", "p/owasp-top-ten", "--json", "--quiet", "/repo"])
    cmd = ["semgrep", "scan", "--config", "p/owasp-top-ten", "--json", "--quiet", repo_path]
    return _run_command(cmd)


def run_app_scanners(payload: Dict[str, Any], dry_run: bool = True) -> Dict[str, Any]:
    return {
        "zap": run_zap(payload, dry_run=dry_run),
        "semgrep": run_semgrep(payload, dry_run=dry_run),
    }
