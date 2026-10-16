import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIBS = ROOT / "libs"
if str(LIBS) not in sys.path:
    sys.path.insert(0, str(LIBS))

from sg_core.jobs import parsers


FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str):
    with open(FIXTURES / name, "r", encoding="utf-8") as f:
        return json.load(f)


def test_parse_prowler_json():
    raw = load_fixture("prowler_sample.json")
    findings = parsers.parse_prowler_json(raw)
    assert len(findings) == 1
    f = findings[0]
    assert f["severity"] == "high"
    assert f["category"] == "cloud_misconfiguration"
    assert f["external_id"] == "123456789012"


def test_parse_trivy_json():
    raw = load_fixture("trivy_sample.json")
    findings = parsers.parse_trivy_json(raw)
    assert len(findings) == 1
    f = findings[0]
    assert f["severity"] == "critical"
    assert f["category"] == "vuln"
    assert "CVE-" in f["title"]


def test_parse_gitleaks_json():
    raw = load_fixture("gitleaks_sample.json")
    findings = parsers.parse_gitleaks_json(raw)
    assert len(findings) == 1
    f = findings[0]
    assert f["category"] == "secret_exposure"
    assert f["severity"] == "high"


def test_parse_checkov_json():
    raw = load_fixture("checkov_sample.json")
    findings = parsers.parse_checkov_json(raw)
    assert len(findings) == 1
    f = findings[0]
    assert f["category"] == "iac_misconfiguration"
    assert f["severity"] == "high"


def test_parse_zap_json():
    raw = load_fixture("zap_sample.json")
    findings = parsers.parse_zap_json(raw)
    assert len(findings) == 1
    f = findings[0]
    assert f["category"] == "dast"
    assert f["severity"] == "high"


def test_parse_semgrep_json():
    raw = load_fixture("semgrep_sample.json")
    findings = parsers.parse_semgrep_json(raw)
    assert len(findings) == 1
    f = findings[0]
    assert f["category"] == "sast"
    assert f["severity"] == "warning"
