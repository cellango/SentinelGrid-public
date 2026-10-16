from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"


def _iter_live_python_files():
    for path in BACKEND_ROOT.rglob("*.py"):
        parts = set(path.parts)
        if "tests" in parts or "scripts" in parts or "__pycache__" in parts:
            continue
        yield path


def test_no_live_verify_false_in_backend_code():
    offenders: list[str] = []
    for path in _iter_live_python_files():
        content = path.read_text()
        if "verify=False" in content:
            offenders.append(str(path.relative_to(REPO_ROOT)))
    assert offenders == [], f"verify=False must not appear in live backend code: {offenders}"


def test_no_wildcard_cors_in_service_entrypoints():
    offenders: list[str] = []
    for path in BACKEND_ROOT.rglob("main.py"):
        if "tests" in path.parts:
            continue
        content = path.read_text()
        if 'allow_origins=["*"]' in content:
            offenders.append(str(path.relative_to(REPO_ROOT)))
        if 'allow_origins=os.getenv("CORS_ORIGINS", "*")' in content:
            offenders.append(str(path.relative_to(REPO_ROOT)))
    assert offenders == [], f"CORS allowlists must be explicit in service entrypoints: {offenders}"
