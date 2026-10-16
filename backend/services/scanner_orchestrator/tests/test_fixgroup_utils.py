import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../libs")))
from app.api_scans import _extract_cve, _extract_fixed_target, _priority_from_severity


def test_extract_cve_prefers_payload_id():
    raw = {"VulnerabilityID": "cve-2024-1234"}
    assert _extract_cve(raw, "ignored") == "CVE-2024-1234"


def test_extract_cve_falls_back_to_title():
    assert _extract_cve({}, "CVE-2023-9999 in openssl").startswith("CVE-2023-9999")


def test_extract_fixed_target_prefers_fixed_version_field():
    raw = {"FixedVersion": "1.2.3"}
    assert _extract_fixed_target(raw, None) == "1.2.3"


def test_extract_fixed_target_uses_remediation_hint():
    remediation = "Upgrade to 4.5.6"
    assert _extract_fixed_target({}, remediation) == remediation


def test_priority_from_severity_map():
    assert _priority_from_severity("critical") == "P0"
    assert _priority_from_severity("high") == "P1"
    assert _priority_from_severity("medium") == "P2"
    assert _priority_from_severity("unknown") == "P2"
