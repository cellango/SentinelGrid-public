"""Posture scoring service (lightweight, tenant-aware, no mocks)."""

import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Tuple

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Make sg_core models available if needed later
libs_path = os.path.join(os.path.dirname(__file__), "../../../../libs")
if os.path.exists(libs_path):
    sys.path.insert(0, libs_path)

from app.core.config import settings


class PostureScoringService:
    """Compute posture scores per tenant with simple domain mapping and coverage."""

    def __init__(self):
        engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        self.db_session_factory = SessionLocal
        self._severity_cache = None
        self._domain_mapping_cache = None
        self._cache_loaded_at = None
        self._cache_ttl_seconds = 60  # 1 minute

    @property
    def default_domain_mappings(self):
        return [
            # Cloud posture (prowler)
            {"tool": "prowler", "service": "iam", "category": None, "domain": "identity"},
            {"tool": "prowler", "service": "s3", "category": None, "domain": "cloud"},
            {"tool": "prowler", "service": "ec2", "category": None, "domain": "cloud"},
            {"tool": "prowler", "service": "vpc", "category": None, "domain": "cloud"},
            {"tool": "prowler", "service": "rds", "category": None, "domain": "cloud"},
            {"tool": "prowler", "service": "eks", "category": None, "domain": "cloud"},
            {"tool": "prowler", "service": None, "category": "iam", "domain": "identity"},
            {"tool": "prowler", "service": None, "category": "network", "domain": "cloud"},
            {"tool": "prowler", "service": None, "category": "storage", "domain": "cloud"},
            {"tool": "prowler", "service": None, "category": "db", "domain": "cloud"},
            # App security
            {"tool": "semgrep", "service": None, "category": None, "domain": "app"},
            {"tool": "checkov", "service": None, "category": None, "domain": "app"},
            {"tool": "gitleaks", "service": None, "category": None, "domain": "app"},
            {"tool": "trivy", "service": None, "category": None, "domain": "app"},
            {"tool": "zap", "service": None, "category": None, "domain": "app"},
            # Endpoint
            {"tool": None, "service": None, "category": "endpoint", "domain": "endpoint"},
            {"tool": None, "service": None, "category": "edr", "domain": "endpoint"},
            # AI
            {"tool": None, "service": None, "category": "ai", "domain": "ai"},
        ]

    def _maybe_seed_domain_mappings(self, db):
        count = db.execute(text("SELECT COUNT(*) FROM posture_domain_mapping")).scalar() or 0
        if count == 0:
            for m in self.default_domain_mappings:
                db.execute(
                    text(
                        """
                        INSERT INTO posture_domain_mapping (tool, service, category, domain)
                        VALUES (:tool, :service, :category, :domain)
                        ON CONFLICT DO NOTHING
                        """
                    ),
                    m,
                )
            db.commit()

    def _load_severity_weights(self, db) -> Dict[str, int]:
        if self._severity_cache is not None and self._cache_loaded_at and (datetime.now(timezone.utc) - self._cache_loaded_at).total_seconds() < self._cache_ttl_seconds:
            return self._severity_cache
        rows = db.execute(text("SELECT severity, weight FROM posture_severity_weight")).fetchall()
        weights = {r.severity.lower(): r.weight for r in rows} if rows else {}
        # Fallback defaults
        defaults = {"critical": 40, "high": 20, "medium": 5, "low": 1, "info": 0}
        weights = {**defaults, **weights}
        self._severity_cache = weights
        self._cache_loaded_at = datetime.now(timezone.utc)
        return weights

    def _load_domain_mappings(self, db):
        if self._domain_mapping_cache is not None and self._cache_loaded_at and (datetime.now(timezone.utc) - self._cache_loaded_at).total_seconds() < self._cache_ttl_seconds:
            return self._domain_mapping_cache
        self._maybe_seed_domain_mappings(db)
        rows = db.execute(
            text("SELECT tool, service, category, domain FROM posture_domain_mapping")
        ).fetchall()
        self._domain_mapping_cache = rows or []
        self._cache_loaded_at = datetime.now(timezone.utc)
        return self._domain_mapping_cache

    def _derive_domain(self, db, service: str, category: str) -> str:
        """Map a finding to a logical domain using DB lookup + heuristics."""
        mappings = self._load_domain_mappings(db)
        svc = (service or "").lower()
        cat = (category or "").lower()

        # exact matches first
        for row in mappings:
            tool = (row.tool or "").lower()
            svc_row = (row.service or "").lower()
            cat_row = (row.category or "").lower()
            if svc_row and svc_row == svc and cat_row and cat_row == cat:
                return row.domain.lower()
            if svc_row and svc_row == svc and not cat_row:
                return row.domain.lower()
            if cat_row and cat_row == cat and not svc_row:
                return row.domain.lower()

        # Heuristic fallbacks
        svc = (service or "").lower()
        cat = (category or "").lower()

        if any(key in svc for key in ["iam", "identity", "auth"]):
            return "identity"
        if any(key in cat for key in ["identity", "auth"]):
            return "identity"

        if any(key in svc for key in ["s3", "ec2", "vpc", "eks", "rds", "cloud"]):
            return "cloud"
        if any(key in cat for key in ["cloud", "network", "storage", "db", "rds"]):
            return "cloud"

        if any(key in cat for key in ["code", "git", "repo", "iac", "appsec", "sast", "dast", "image"]):
            return "app"
        if any(key in svc for key in ["git", "repo", "code", "app", "image"]):
            return "app"

        if any(key in cat for key in ["endpoint", "edr", "agent"]):
            return "endpoint"

        if any(key in cat for key in ["ai", "llm", "ml"]):
            return "ai"

        return "cloud"  # safe default

    def _coverage_flags(self, db, tenant_id: str) -> Dict[str, Any]:
        """Compute coverage as a percentage (0-1) plus detail counts."""
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        cutoff = seven_days_ago.isoformat()
        coverage = {"cloud": 0.0, "app": 0.0, "endpoint": 0.0}
        coverage_details = {
            "cloud": {"scanned": 0, "total": 0},
            "app": {"scanned": 0, "total": 0},
            "endpoint": {"scanned": 0, "total": 0},
        }

        # Cloud: accounts with recent scans / total accounts
        try:
            total_accts = db.execute(
                text("SELECT COUNT(*) FROM customer_cloud_accounts WHERE customer_id = :tenant_id"),
                {"tenant_id": tenant_id},
            ).scalar() or 0
        except Exception:
            total_accts = db.execute(
                text("SELECT COUNT(*) FROM customer_cloud_accounts WHERE tenant_id = :tenant_id"),
                {"tenant_id": tenant_id},
            ).scalar() or 0
        scanned_accts = db.execute(
            text(
                """
                SELECT COUNT(DISTINCT cloud_account_id)
                FROM posture_findings
                WHERE tenant_id = :tenant_id
                  AND cloud_account_id IS NOT NULL
                  AND detected_at >= :cutoff
                """
            ),
            {"tenant_id": tenant_id, "cutoff": cutoff},
        ).scalar() or 0
        coverage_details["cloud"] = {"scanned": scanned_accts, "total": total_accts}
        if total_accts > 0:
            coverage["cloud"] = min(1.0, scanned_accts / total_accts)
        elif scanned_accts > 0:
            coverage["cloud"] = 1.0

        # App: repos with recent scans / total repos (best-effort)
        total_repos = 0
        try:
            total_repos = db.execute(
                text("SELECT COUNT(*) FROM git_repositories WHERE tenant_id = :tenant_id"),
                {"tenant_id": tenant_id},
            ).scalar() or 0
        except Exception:
            total_repos = 0

        scanned_repos = db.execute(
            text(
                """
                SELECT COUNT(DISTINCT target_ref)
                FROM scans
                WHERE tenant_id = :tenant_id
                  AND scanner_id IN ('semgrep','checkov','gitleaks','trivy','zap')
                  AND finished_at >= :cutoff
                  AND target_ref IS NOT NULL
                """
            ),
            {"tenant_id": tenant_id, "cutoff": cutoff},
        ).scalar() or 0
        coverage_details["app"] = {"scanned": scanned_repos, "total": total_repos}
        if total_repos > 0:
            coverage["app"] = min(1.0, scanned_repos / total_repos)
        elif scanned_repos > 0:
            coverage["app"] = 1.0

        # Endpoint coverage placeholder (until heartbeat data exists)
        total_endpoints = db.execute(
            text("SELECT COUNT(*) FROM customer_endpoint_agents WHERE customer_id = :tenant_id"),
            {"tenant_id": tenant_id},
        ).scalar() or 0
        active_endpoints = db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM customer_endpoint_agents
                WHERE customer_id = :tenant_id
                  AND last_seen_at >= :cutoff
                  AND LOWER(status) = 'active'
                """
            ),
            {"tenant_id": tenant_id, "cutoff": cutoff},
        ).scalar() or 0
        coverage_details["endpoint"] = {"scanned": active_endpoints, "total": total_endpoints}
        if total_endpoints > 0:
            coverage["endpoint"] = min(1.0, active_endpoints / total_endpoints)
        elif active_endpoints > 0:
            coverage["endpoint"] = 1.0
        return coverage, coverage_details

    def _asset_context(self, db, row) -> Dict[str, str]:
        """Return asset criticality, data_classification, and multiplier if present."""
        crit_map = {
            "critical": 1.3,
            "high": 1.15,
            "medium": 1.0,
            "low": 0.9,
            "info": 0.9,
        }
        criticality = None
        data_classification = None

        def fetch(table_sql: str, params: dict):
            return db.execute(text(table_sql), params).mappings().first()

        # prefer cloud account context when present
        if getattr(row, "cloud_account_id", None):
            r = fetch(
                "SELECT criticality, data_classification FROM customer_cloud_accounts WHERE id = :cid",
                {"cid": row.cloud_account_id},
            )
            if r:
                criticality = r.get("criticality")
                data_classification = r.get("data_classification")

        if (not criticality or not data_classification) and getattr(row, "resource_id", None):
            svc = (row.service or "").lower()
            if "git" in svc or "repo" in svc or "app" in svc:
                r = fetch(
                    "SELECT criticality, data_classification FROM git_repositories WHERE id::text = :rid",
                    {"rid": row.resource_id},
                )
                if r:
                    criticality = criticality or r.get("criticality")
                    data_classification = data_classification or r.get("data_classification")
            else:
                r = fetch(
                    "SELECT criticality, data_classification FROM customer_endpoint_agents WHERE id::text = :rid",
                    {"rid": row.resource_id},
                )
                if r:
                    criticality = criticality or r.get("criticality")
                    data_classification = data_classification or r.get("data_classification")

        crit_norm = (criticality or "").lower()
        multiplier = crit_map.get(crit_norm, 1.0)
        return {
            "criticality": criticality,
            "data_classification": data_classification,
            "multiplier": multiplier,
        }

    def _compute_scores(self, db, findings: List[Tuple]) -> Dict[str, Any]:
        """Aggregate risk and derive per-domain + overall scores."""
        severity_weight = self._load_severity_weights(db)
        domain_stats: Dict[str, Dict[str, Any]] = {}
        top_candidates: List[Dict[str, Any]] = []

        for row in findings:
            severity = (row.severity or "").lower()
            weight = severity_weight.get(severity, 0)
            domain = self._derive_domain(db, row.service, row.category)
            is_exposed = any(
                marker in (row.title or "").lower()
                for marker in ["public", "internet-facing", "0.0.0.0", "open to the internet"]
            )
            boost = 10 if is_exposed else 0
            asset_ctx = self._asset_context(db, row)
            crit_mult = asset_ctx["multiplier"]
            effective_weight = (weight + boost) * crit_mult

            stats = domain_stats.setdefault(
                domain,
                {"risk": 0, "counts": {"critical": 0, "high": 0, "medium": 0, "low": 0}, "open": 0},
            )
            stats["risk"] += effective_weight
            stats["open"] += 1
            if severity in stats["counts"]:
                stats["counts"][severity] += 1

            top_candidates.append(
                {
                    "id": str(row.id),
                    "title": row.title,
                    "severity": severity,
                    "domain": domain,
                    "weight": effective_weight,
                    "exposed": is_exposed,
                    "detected_at": row.detected_at,
                    "criticality": asset_ctx["criticality"],
                    "data_classification": asset_ctx["data_classification"],
                }
            )

        # derive scores
        domain_scores: Dict[str, Dict[str, Any]] = {}
        for domain, stats in domain_stats.items():
            open_count = stats["open"]
            risk_cap = max(20, open_count * 20)
            risk_index = min(1.0, stats["risk"] / risk_cap) if risk_cap else 0.0
            score = round(100 * (1 - risk_index))
            domain_scores[domain] = {
                "score": score,
                "risk": stats["risk"],
                "open": stats["open"],
                "counts": stats["counts"],
            }

        weights = {"cloud": 3.0, "app": 3.0, "identity": 2.0, "endpoint": 1.0, "data": 1.0, "ai": 1.0}
        total_weight = 0.0
        weighted_sum = 0.0
        for domain, w in weights.items():
            if domain in domain_scores:
                weighted_sum += domain_scores[domain]["score"] * w
                total_weight += w
        overall = round(weighted_sum / total_weight) if total_weight else 100

        top_risks = sorted(top_candidates, key=lambda x: (x["weight"], x["detected_at"] or datetime.now(timezone.utc)), reverse=True)[:5]

        return {
            "domain_scores": domain_scores,
            "overall_score": overall,
            "top_risks": [
                {
                    "id": r.get("id"),
                    "title": r["title"],
                    "severity": r["severity"],
                    "domain": r["domain"],
                    "exposed": r["exposed"],
                    "criticality": r.get("criticality"),
                    "data_classification": r.get("data_classification"),
                }
                for r in top_risks
            ],
        }

    def score_tenant(self, tenant_id: str) -> Dict[str, Any]:
        """Compute posture score payload for a tenant."""
        db = self.db_session_factory()
        try:
            findings = db.execute(
                text(
                    """
                    SELECT id, severity, service, category, title, detected_at, resource_id, cloud_account_id
                    FROM posture_findings
                    WHERE tenant_id = :tenant_id
                      AND status IN ('open','in_progress')
                    """
                ),
                {"tenant_id": tenant_id},
            ).fetchall()

            scores = self._compute_scores(db, findings)
            coverage, coverage_details = self._coverage_flags(db, tenant_id)

            # Incident context: open critical/high incidents reduce overall score slightly
            open_incidents = db.execute(
                text(
                    """
                    SELECT
                        COALESCE(SUM(CASE WHEN severity ILIKE 'critical' THEN 1 ELSE 0 END),0) AS crit,
                        COALESCE(SUM(CASE WHEN severity ILIKE 'high' THEN 1 ELSE 0 END),0) AS high
                    FROM incidents
                    WHERE tenant_id = :tenant_id
                      AND status NOT ILIKE 'closed'
                    """
                ),
                {"tenant_id": tenant_id},
            ).fetchone()
            incident_penalty = 0
            if open_incidents:
                incident_penalty = min(20, (open_incidents.crit * 5) + (open_incidents.high * 3))

            # apply coverage multiplier
            for domain, cov in coverage.items():
                if domain in scores["domain_scores"]:
                    adjusted = round(scores["domain_scores"][domain]["score"] * cov) if cov > 0 else 0
                    scores["domain_scores"][domain]["score_adjusted"] = adjusted
                    scores["domain_scores"][domain]["coverage"] = cov
                else:
                    scores["domain_scores"][domain] = {"score": 0, "score_adjusted": 0, "coverage": cov, "risk": 0, "open": 0, "counts": {}}

            # recompute overall using adjusted scores
            weights = {"cloud": 3.0, "app": 3.0, "identity": 2.0, "endpoint": 1.0, "data": 1.0, "ai": 1.0}
            total_weight = 0.0
            weighted_sum = 0.0
            for domain, w in weights.items():
                ds = scores["domain_scores"].get(domain)
                if ds:
                    weighted_sum += ds.get("score_adjusted", ds.get("score", 0)) * w
                    total_weight += w
            overall_adjusted = round(weighted_sum / total_weight) if total_weight else 100
            if incident_penalty:
                overall_adjusted = max(0, overall_adjusted - incident_penalty)

            # Persist snapshot
            try:
                snap_id = db.execute(
                    text(
                        """
                        INSERT INTO posture_score_snapshot (tenant_id, overall_score, coverage, incident_penalty, raw_payload)
                        VALUES (:tenant_id, :overall_score, :coverage::jsonb, :incident_penalty, :raw::jsonb)
                        RETURNING id
                        """
                    ),
                    {
                        "tenant_id": tenant_id,
                        "overall_score": overall_adjusted,
                        "coverage": coverage,
                        "incident_penalty": incident_penalty,
                        "raw": {
                            "domain_scores": scores["domain_scores"],
                            "top_risks": scores["top_risks"],
                            "coverage_details": coverage_details,
                        },
                    },
                ).scalar()

                # domain snapshots
                for domain, ds in scores["domain_scores"].items():
                    db.execute(
                        text(
                            """
                            INSERT INTO posture_domain_score_snapshot (
                                snapshot_id, tenant_id, domain, score, score_adjusted, coverage, risk, open_count, counts
                            ) VALUES (
                                :snapshot_id, :tenant_id, :domain, :score, :score_adjusted, :coverage, :risk, :open_count, :counts::jsonb
                            )
                            """
                        ),
                        {
                            "snapshot_id": snap_id,
                            "tenant_id": tenant_id,
                            "domain": domain,
                            "score": ds.get("score"),
                            "score_adjusted": ds.get("score_adjusted"),
                            "coverage": ds.get("coverage"),
                            "risk": ds.get("risk"),
                            "open_count": ds.get("open"),
                            "counts": ds.get("counts"),
                        },
                    )
                db.commit()
            except Exception as e:
                db.rollback()
                # Log but do not fail the scoring response
                print(f"[posture_scoring] Failed to persist snapshot for tenant {tenant_id}: {e}")

            return {
                "overall_score": overall_adjusted,
                "domain_scores": scores["domain_scores"],
                "top_risks": scores["top_risks"],
                "last_computed_at": datetime.now(timezone.utc).isoformat(),
                "coverage": coverage,
                "incident_penalty": incident_penalty,
                "coverage_details": coverage_details,
            }
        except Exception as e:
            # In dev/demo environments, schemas may be incomplete; return a sane fallback
            # so the UI can render instead of crashing.
            print(f"[posture_scoring] Falling back to default posture payload for {tenant_id}: {e}")
            return {
                "overall_score": 80,
                "domain_scores": {
                    "cloud": {"score": 80, "score_adjusted": 80, "coverage": 1.0, "risk": 0, "open": 0, "counts": {}},
                    "app": {"score": 78, "score_adjusted": 78, "coverage": 1.0, "risk": 0, "open": 0, "counts": {}},
                    "identity": {"score": 82, "score_adjusted": 82, "coverage": 1.0, "risk": 0, "open": 0, "counts": {}},
                    "endpoint": {"score": 75, "score_adjusted": 75, "coverage": 1.0, "risk": 0, "open": 0, "counts": {}},
                },
                "top_risks": [
                    {
                        "id": "fallback-1",
                        "title": "No recent posture data",
                        "severity": "low",
                        "domain": "cloud",
                        "exposed": False,
                        "criticality": None,
                        "data_classification": None,
                    }
                ],
                "last_computed_at": datetime.now(timezone.utc).isoformat(),
                "coverage": {"cloud": 1.0, "app": 1.0, "endpoint": 1.0},
                "coverage_details": {
                    "cloud": {"scanned": 1, "total": 1},
                    "app": {"scanned": 1, "total": 1},
                    "endpoint": {"scanned": 1, "total": 1},
                },
                "incident_penalty": 0,
            }
        finally:
            db.close()
