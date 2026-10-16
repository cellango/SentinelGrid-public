"""
Compliance Tracking Service
Tracks compliance status for NIST controls and generates compliance reports
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict

from app.services.nist_controls import NISTControlsService, ControlCategory

logger = logging.getLogger(__name__)


class ComplianceTrackingService:
    """Service for tracking compliance status and generating reports."""
    
    def __init__(self):
        self.nist_service = NISTControlsService()
    
    def track_compliance_status(
        self,
        tenant_id: str,
        control_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Track overall compliance status for a tenant.
        """
        if control_ids:
            controls = [self.nist_service.get_control(cid) for cid in control_ids]
            controls = [c for c in controls if c]
        else:
            controls = self.nist_service.get_iam_controls()
        
        compliance_records = []
        status_counts = defaultdict(int)
        
        for control in controls:
            # In a real implementation, fetch actual compliance data from database
            # For now, this is a placeholder structure
            record = {
                "control_id": control["control_id"],
                "control_name": control["control_name"],
                "category": control["category"],
                "status": "not_assessed",  # Would be fetched from DB
                "compliance_score": 0.0,
                "last_assessed": None,
                "next_assessment_due": None
            }
            
            compliance_records.append(record)
            status_counts[record["status"]] += 1
        
        # Calculate overall compliance score
        total_controls = len(compliance_records)
        compliant_count = status_counts.get("compliant", 0)
        partially_compliant_count = status_counts.get("partially_compliant", 0)
        
        overall_score = (
            (compliant_count * 1.0 + partially_compliant_count * 0.5) / total_controls
            if total_controls > 0 else 0.0
        )
        
        return {
            "tenant_id": tenant_id,
            "overall_compliance_score": round(overall_score, 2),
            "total_controls": total_controls,
            "status_breakdown": dict(status_counts),
            "compliant_count": compliant_count,
            "partially_compliant_count": partially_compliant_count,
            "non_compliant_count": status_counts.get("non_compliant", 0),
            "not_assessed_count": status_counts.get("not_assessed", 0),
            "controls": compliance_records,
            "assessed_at": datetime.utcnow().isoformat()
        }
    
    def get_compliance_gaps(
        self,
        tenant_id: str,
        control_category: Optional[ControlCategory] = None
    ) -> List[Dict[str, Any]]:
        """
        Identify compliance gaps (non-compliant or missing controls).
        """
        if control_category:
            controls = self.nist_service.get_iam_controls(control_category)
        else:
            controls = self.nist_service.get_iam_controls()
        
        gaps = []
        
        for control in controls:
            # Check compliance status (would fetch from DB)
            status = "not_assessed"  # Placeholder
            
            if status in ["non_compliant", "partially_compliant", "not_assessed"]:
                gap = {
                    "control_id": control["control_id"],
                    "control_name": control["control_name"],
                    "category": control["category"],
                    "impact": control["impact"],
                    "status": status,
                    "gap_description": self._describe_gap(control, status),
                    "recommended_actions": self._recommend_actions(control),
                    "priority": "high" if control["impact"] == "high" else "medium",
                    "identified_at": datetime.utcnow().isoformat()
                }
                gaps.append(gap)
        
        # Sort by priority and impact
        gaps.sort(key=lambda x: (
            0 if x["priority"] == "high" else 1,
            0 if x["impact"] == "high" else 1 if x["impact"] == "moderate" else 2
        ))
        
        return gaps
    
    def generate_compliance_report(
        self,
        tenant_id: str,
        report_type: str = "summary",
        control_category: Optional[ControlCategory] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Generate a compliance report.
        
        Report types:
        - summary: High-level compliance overview
        - detailed: Full control-by-control breakdown
        - gap_analysis: Focus on compliance gaps
        - trend: Compliance trends over time
        """
        end_date = end_date or datetime.utcnow()
        start_date = start_date or (end_date - timedelta(days=90))
        
        compliance_status = self.track_compliance_status(tenant_id)
        gaps = self.get_compliance_gaps(tenant_id, control_category)
        
        if report_type == "summary":
            return {
                "tenant_id": tenant_id,
                "report_type": "summary",
                "report_period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                },
                "summary": {
                    "overall_compliance_score": compliance_status["overall_compliance_score"],
                    "total_controls": compliance_status["total_controls"],
                    "compliant": compliance_status["compliant_count"],
                    "partially_compliant": compliance_status["partially_compliant_count"],
                    "non_compliant": compliance_status["non_compliant_count"],
                    "not_assessed": compliance_status["not_assessed_count"]
                },
                "critical_gaps": [g for g in gaps if g["priority"] == "high"][:10],
                "generated_at": datetime.utcnow().isoformat()
            }
        
        elif report_type == "detailed":
            return {
                "tenant_id": tenant_id,
                "report_type": "detailed",
                "report_period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                },
                "compliance_status": compliance_status,
                "gaps": gaps,
                "generated_at": datetime.utcnow().isoformat()
            }
        
        elif report_type == "gap_analysis":
            return {
                "tenant_id": tenant_id,
                "report_type": "gap_analysis",
                "report_period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                },
                "total_gaps": len(gaps),
                "high_priority_gaps": len([g for g in gaps if g["priority"] == "high"]),
                "gaps": gaps,
                "recommended_actions": self._consolidate_recommendations(gaps),
                "generated_at": datetime.utcnow().isoformat()
            }
        
        elif report_type == "trend":
            # Would include historical compliance data
            return {
                "tenant_id": tenant_id,
                "report_type": "trend",
                "report_period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                },
                "current_status": compliance_status,
                "trend": "improving",  # Would calculate from historical data
                "generated_at": datetime.utcnow().isoformat()
            }
        
        else:
            raise ValueError(f"Unknown report type: {report_type}")
    
    def record_evidence(
        self,
        control_id: str,
        evidence: Dict[str, Any],
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Record evidence for a control assessment.
        """
        assessment = self.nist_service.assess_control_compliance(
            control_id,
            evidence,
            tenant_id
        )
        
        # In a real implementation, save to database
        # For now, return the assessment
        
        return {
            "control_id": control_id,
            "assessment": assessment,
            "evidence_recorded_at": datetime.utcnow().isoformat(),
            "tenant_id": tenant_id
        }
    
    def schedule_assessment(
        self,
        control_id: str,
        assessment_date: datetime,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Schedule a compliance assessment for a control."""
        control = self.nist_service.get_control(control_id)
        
        if not control:
            return {
                "control_id": control_id,
                "status": "error",
                "error": "Control not found"
            }
        
        # In a real implementation, save to database
        return {
            "control_id": control_id,
            "control_name": control["control_name"],
            "scheduled_date": assessment_date.isoformat(),
            "tenant_id": tenant_id,
            "scheduled_at": datetime.utcnow().isoformat()
        }
    
    def _describe_gap(
        self,
        control: Dict[str, Any],
        status: str
    ) -> str:
        """Describe a compliance gap."""
        if status == "not_assessed":
            return f"Control {control['control_id']} ({control['control_name']}) has not been assessed."
        elif status == "non_compliant":
            return f"Control {control['control_id']} ({control['control_name']}) is non-compliant."
        elif status == "partially_compliant":
            return f"Control {control['control_id']} ({control['control_name']}) is partially compliant."
        else:
            return f"Unknown status for control {control['control_id']}."
    
    def _recommend_actions(self, control: Dict[str, Any]) -> List[str]:
        """Recommend actions to address a compliance gap."""
        actions = []
        
        features = control.get("sentinelgrid_features", [])
        if features:
            actions.append(f"Implement or configure: {', '.join(features)}")
        
        required_evidence = control.get("required_evidence", [])
        if required_evidence:
            actions.append(f"Gather evidence for: {', '.join(required_evidence)}")
        
        actions.append("Review control requirements and implementation guidance")
        actions.append("Schedule reassessment after remediation")
        
        return actions
    
    def _consolidate_recommendations(self, gaps: List[Dict[str, Any]]) -> List[str]:
        """Consolidate recommendations across multiple gaps."""
        all_recommendations = []
        
        for gap in gaps:
            all_recommendations.extend(gap.get("recommended_actions", []))
        
        # Remove duplicates while preserving order
        seen = set()
        unique_recommendations = []
        
        for rec in all_recommendations:
            if rec not in seen:
                seen.add(rec)
                unique_recommendations.append(rec)
        
        return unique_recommendations

