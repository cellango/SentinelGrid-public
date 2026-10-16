import types
import os
import sys
from datetime import datetime, timedelta, timezone

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.posture_scoring import PostureScoringService


class FakeRow:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def test_compute_scores_applies_severity_and_criticality(monkeypatch):
    scorer = PostureScoringService()

    # Stub severity weights and domain mapping
    monkeypatch.setattr(scorer, "_load_severity_weights", lambda db: {"critical": 40})
    monkeypatch.setattr(scorer, "_derive_domain", lambda db, svc, cat: "cloud")

    # Stub asset context to return criticality multiplier and metadata
    monkeypatch.setattr(
        scorer,
        "_asset_context",
        lambda db, row: {
            "criticality": "critical",
            "data_classification": "restricted",
            "multiplier": 1.3,
        },
    )

    row = FakeRow(
        id="f1",
        severity="critical",
        service="s3",
        category="storage",
        title="Private bucket",  # avoid exposure boost so we only test severity * multiplier
        detected_at=datetime.now(timezone.utc),
        resource_id=None,
        cloud_account_id=None,
    )

    scores = scorer._compute_scores(None, [row])
    # Risk includes severity weight * multiplier (40 * 1.3 = 52)
    assert scores["domain_scores"]["cloud"]["risk"] == 52
    assert scores["top_risks"][0]["criticality"] == "critical"
    assert scores["top_risks"][0]["data_classification"] == "restricted"


def test_coverage_flags_counts(tmp_path):
    from sqlalchemy import create_engine, text

    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE customer_cloud_accounts (id TEXT, tenant_id TEXT, criticality TEXT, data_classification TEXT)"))
        conn.execute(text("CREATE TABLE posture_findings (cloud_account_id TEXT, tenant_id TEXT, detected_at TEXT)"))
        conn.execute(text("CREATE TABLE git_repositories (id TEXT, tenant_id TEXT, criticality TEXT, data_classification TEXT)"))
        conn.execute(text("CREATE TABLE scans (tenant_id TEXT, scanner_id TEXT, target_ref TEXT, finished_at TEXT)"))
        conn.execute(text("CREATE TABLE customer_endpoint_agents (id TEXT, customer_id TEXT, status TEXT, last_seen_at TEXT, criticality TEXT, data_classification TEXT)"))

        now = datetime.now(timezone.utc)
        seven_days_ago = now - timedelta(days=1)

        # Cloud: 2 accounts, 1 scanned
        conn.execute(text("INSERT INTO customer_cloud_accounts VALUES ('c1','t1',NULL,NULL)"))
        conn.execute(text("INSERT INTO customer_cloud_accounts VALUES ('c2','t1',NULL,NULL)"))
        conn.execute(text("INSERT INTO posture_findings VALUES ('c1','t1', :ts)"), {"ts": seven_days_ago.isoformat()})

        # App: 2 repos, 1 scanned recently
        conn.execute(text("INSERT INTO git_repositories VALUES ('r1','t1',NULL,NULL)"))
        conn.execute(text("INSERT INTO git_repositories VALUES ('r2','t1',NULL,NULL)"))
        conn.execute(text("INSERT INTO scans VALUES ('t1','semgrep','r1', :ts)"), {"ts": seven_days_ago.isoformat()})

        # Endpoint: 2 agents, 1 active
        conn.execute(text("INSERT INTO customer_endpoint_agents VALUES ('e1','t1','active', :ts, NULL, NULL)"), {"ts": seven_days_ago.isoformat()})
        conn.execute(text("INSERT INTO customer_endpoint_agents VALUES ('e2','t1','inactive', :ts, NULL, NULL)"), {"ts": seven_days_ago.isoformat()})

        scorer = PostureScoringService()
        coverage, details = scorer._coverage_flags(conn, "t1")

        assert coverage["cloud"] == pytest.approx(0.5)
        assert coverage["app"] == pytest.approx(0.5)
        assert coverage["endpoint"] == pytest.approx(0.5)
        assert details["cloud"]["total"] == 2
        assert details["app"]["scanned"] == 1
        assert details["endpoint"]["scanned"] == 1
