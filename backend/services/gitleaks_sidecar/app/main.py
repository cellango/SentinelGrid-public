import subprocess
from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Gitleaks Sidecar", version="0.1.0")


class ScanRequest(BaseModel):
    repo_path: str
    extra_args: List[str] = []


@app.post("/scan")
def scan(req: ScanRequest):
    repo_path = Path(req.repo_path)
    if not repo_path.exists():
        raise HTTPException(status_code=400, detail="repo_path does not exist")
    report_path = "/tmp/gitleaks_report.json"
    cmd = [
        "gitleaks",
        "detect",
        "-s",
        str(repo_path),
        "--report-format",
        "json",
        "--report-path",
        report_path,
        "--no-banner",
        "--log-level",
        "error",
    ] + req.extra_args
    result = subprocess.run(cmd, capture_output=True, text=True)
    # Gitleaks exits 1 when leaks are found; treat both 0/1 as success, anything else as error
    if result.returncode not in (0, 1):
        raise HTTPException(
            status_code=500,
            detail={
                "error": result.stderr.strip() or f"exit {result.returncode}",
                "stdout": result.stdout[:2000],
            },
        )
    raw_json = ""
    try:
        with open(report_path, "r", encoding="utf-8") as f:
            raw_json = f.read()
    except FileNotFoundError:
        raw_json = ""
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    try:
        return {"raw": raw_json, "stderr": result.stderr.strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
