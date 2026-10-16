"""
NIST 800-53 Controls Service
Manages NIST control database and control-to-feature mapping
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class ControlCategory(str, Enum):
    """NIST 800-53 control families."""
    AC = "AC"  # Access Control
    IA = "IA"  # Identification and Authentication
    AU = "AU"  # Audit and Accountability
    CA = "CA"  # Security Assessment and Authorization
    CM = "CM"  # Configuration Management
    CP = "CP"  # Contingency Planning
    IR = "IR"  # Incident Response
    MA = "MA"  # Maintenance
    MP = "MP"  # Media Protection
    PS = "PS"  # Personnel Security
    PE = "PE"  # Physical and Environmental Protection
    PL = "PL"  # Planning
    RA = "RA"  # Risk Assessment
    SA = "SA"  # System and Services Acquisition
    SC = "SC"  # System and Communications Protection
    SI = "SI"  # System and Information Integrity
    SR = "SR"  # Supply Chain Risk Management


class ControlImpact(str, Enum):
    """NIST control impact levels."""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class NISTControlsService:
    """Service for managing NIST 800-53 controls."""
    
    def __init__(self):
        # Core IAM-related NIST controls
        self.iam_controls = self._initialize_iam_controls()
    
    def get_iam_controls(self, category: Optional[ControlCategory] = None) -> List[Dict[str, Any]]:
        """Get all IAM-related NIST controls, optionally filtered by category."""
        controls = self.iam_controls
        
        if category:
            controls = [c for c in controls if c["control_id"].startswith(category.value)]
        
        return controls
    
    def get_control(self, control_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific control by ID."""
        for control in self.iam_controls:
            if control["control_id"] == control_id:
                return control
        return None
    
    def map_feature_to_controls(
        self,
        feature_name: str,
        feature_description: str
    ) -> List[Dict[str, Any]]:
        """Map a SentinelGrid feature to relevant NIST controls."""
        mapped_controls = []
        
        # Simple keyword-based mapping (can be enhanced with ML)
        feature_lower = feature_description.lower()
        
        for control in self.iam_controls:
            keywords = control.get("keywords", [])
            description = control.get("description", "").lower()
            
            # Check if feature matches control
            if any(keyword in feature_lower for keyword in keywords) or \
               any(keyword in description for keyword in keywords):
                mapped_controls.append({
                    "control_id": control["control_id"],
                    "control_name": control["control_name"],
                    "mapping_strength": "strong" if len([k for k in keywords if k in feature_lower]) > 2 else "weak",
                    "rationale": f"Feature '{feature_name}' addresses {control['control_name']}"
                })
        
        return mapped_controls
    
    def assess_control_compliance(
        self,
        control_id: str,
        evidence: Dict[str, Any],
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Assess compliance status for a specific control.
        
        Evidence should include:
        - Feature implementations
        - Configuration settings
        - Audit logs
        - Test results
        """
        control = self.get_control(control_id)
        if not control:
            return {
                "control_id": control_id,
                "status": "unknown",
                "error": "Control not found"
            }
        
        # Check required evidence
        required_evidence = control.get("required_evidence", [])
        provided_evidence = set(evidence.keys())
        
        missing_evidence = set(required_evidence) - provided_evidence
        
        # Determine compliance status
        if missing_evidence:
            status = "non_compliant"
            score = 0.0
        elif len(provided_evidence) >= len(required_evidence):
            # Evaluate evidence quality
            score = self._evaluate_evidence_quality(control, evidence)
            if score >= 0.8:
                status = "compliant"
            elif score >= 0.6:
                status = "partially_compliant"
            else:
                status = "non_compliant"
        else:
            status = "partially_compliant"
            score = len(provided_evidence) / len(required_evidence) if required_evidence else 0.5
        
        return {
            "control_id": control_id,
            "control_name": control["control_name"],
            "status": status,
            "compliance_score": round(score, 2),
            "provided_evidence": list(provided_evidence),
            "missing_evidence": list(missing_evidence),
            "assessment_date": datetime.utcnow().isoformat(),
            "tenant_id": tenant_id
        }
    
    def _evaluate_evidence_quality(
        self,
        control: Dict[str, Any],
        evidence: Dict[str, Any]
    ) -> float:
        """Evaluate the quality of provided evidence (0.0 to 1.0)."""
        score = 0.0
        max_score = 0.0
        
        for evidence_type in control.get("required_evidence", []):
            max_score += 1.0
            
            if evidence_type in evidence:
                evidence_value = evidence[evidence_type]
                
                # Basic quality checks
                if isinstance(evidence_value, bool) and evidence_value:
                    score += 1.0
                elif isinstance(evidence_value, dict) and evidence_value:
                    score += 0.8
                elif isinstance(evidence_value, list) and len(evidence_value) > 0:
                    score += 0.7
                elif evidence_value:
                    score += 0.5
        
        return score / max_score if max_score > 0 else 0.0
    
    def _initialize_iam_controls(self) -> List[Dict[str, Any]]:
        """Initialize core IAM-related NIST 800-53 controls."""
        return [
            {
                "control_id": "AC-2",
                "control_name": "Account Management",
                "category": ControlCategory.AC.value,
                "impact": ControlImpact.MODERATE.value,
                "description": "The organization manages information system accounts, including establishing, activating, modifying, disabling, and removing accounts.",
                "keywords": ["account", "user", "provisioning", "deprovisioning", "lifecycle"],
                "required_evidence": ["account_lifecycle_management", "account_reviews", "automated_deprovisioning"],
                "sentinelgrid_features": ["user_management", "access_reviews", "certification_campaigns"]
            },
            {
                "control_id": "AC-3",
                "control_name": "Access Enforcement",
                "category": ControlCategory.AC.value,
                "impact": ControlImpact.HIGH.value,
                "description": "The information system enforces approved authorizations for logical access to information and system resources.",
                "keywords": ["authorization", "access control", "policy", "enforcement"],
                "required_evidence": ["authorization_policies", "access_enforcement", "policy_evaluation"],
                "sentinelgrid_features": ["policy_builder", "authorization_policies", "access_control"]
            },
            {
                "control_id": "AC-6",
                "control_name": "Least Privilege",
                "category": ControlCategory.AC.value,
                "impact": ControlImpact.HIGH.value,
                "description": "The organization employs the principle of least privilege, allowing only authorized accesses for users (and processes acting on behalf of users) necessary to accomplish assigned organizational tasks.",
                "keywords": ["least privilege", "minimal access", "role mining", "over-privilege"],
                "required_evidence": ["privilege_analysis", "role_mining", "access_optimization"],
                "sentinelgrid_features": ["role_mining", "access_optimization", "recommendations"]
            },
            {
                "control_id": "AC-7",
                "control_name": "Unsuccessful Logon Attempts",
                "category": ControlCategory.AC.value,
                "impact": ControlImpact.MODERATE.value,
                "description": "The information system enforces a limit of consecutive invalid logon attempts.",
                "keywords": ["logon", "authentication", "failed login", "lockout"],
                "required_evidence": ["failed_login_detection", "account_lockout", "brute_force_protection"],
                "sentinelgrid_features": ["anomaly_detection", "risk_scoring"]
            },
            {
                "control_id": "AC-17",
                "control_name": "Remote Access",
                "category": ControlCategory.AC.value,
                "impact": ControlImpact.MODERATE.value,
                "description": "The organization authorizes, monitors, and controls remote access methods.",
                "keywords": ["remote access", "vpn", "remote connection"],
                "required_evidence": ["remote_access_authorization", "remote_access_monitoring"],
                "sentinelgrid_features": ["access_monitoring", "anomaly_detection"]
            },
            {
                "control_id": "IA-2",
                "control_name": "Identification and Authentication (Organizational Users)",
                "category": ControlCategory.IA.value,
                "impact": ControlImpact.HIGH.value,
                "description": "The information system uniquely identifies and authenticates organizational users.",
                "keywords": ["authentication", "identification", "user authentication", "mfa"],
                "required_evidence": ["user_authentication", "multi_factor_authentication", "identity_proofing"],
                "sentinelgrid_features": ["keycloak_integration", "mfa", "authentication"]
            },
            {
                "control_id": "IA-4",
                "control_name": "Identifier Management",
                "category": ControlCategory.IA.value,
                "impact": ControlImpact.MODERATE.value,
                "description": "The organization manages information system identifiers.",
                "keywords": ["identifier", "user id", "account identifier"],
                "required_evidence": ["identifier_management", "unique_identifiers"],
                "sentinelgrid_features": ["user_management", "identifier_management"]
            },
            {
                "control_id": "IA-5",
                "control_name": "Authenticator Management",
                "category": ControlCategory.IA.value,
                "impact": ControlImpact.HIGH.value,
                "description": "The organization manages information system authenticators.",
                "keywords": ["password", "authenticator", "credential", "token"],
                "required_evidence": ["password_policy", "authenticator_strength", "credential_management"],
                "sentinelgrid_features": ["keycloak_password_policy", "mfa_management"]
            },
            {
                "control_id": "IA-8",
                "control_name": "Identification and Authentication (Non-Organizational Users)",
                "category": ControlCategory.IA.value,
                "impact": ControlImpact.MODERATE.value,
                "description": "The information system uniquely identifies and authenticates non-organizational users.",
                "keywords": ["external user", "guest", "federated identity"],
                "required_evidence": ["non_org_user_auth", "federated_identity"],
                "sentinelgrid_features": ["federated_identity", "external_user_management"]
            },
            {
                "control_id": "AU-2",
                "control_name": "Audit Events",
                "category": ControlCategory.AU.value,
                "impact": ControlImpact.MODERATE.value,
                "description": "The organization determines that the information system is capable of auditing events.",
                "keywords": ["audit", "audit log", "audit event", "logging"],
                "required_evidence": ["audit_logging", "event_auditing", "audit_capabilities"],
                "sentinelgrid_features": ["audit_logging", "compliance_reporting"]
            },
            {
                "control_id": "AU-3",
                "control_name": "Content of Audit Records",
                "category": ControlCategory.AU.value,
                "impact": ControlImpact.MODERATE.value,
                "description": "The information system generates audit records containing information.",
                "keywords": ["audit record", "audit content", "audit information"],
                "required_evidence": ["audit_record_content", "audit_information"],
                "sentinelgrid_features": ["audit_logging", "compliance_reporting"]
            },
            {
                "control_id": "AU-6",
                "control_name": "Audit Review, Analysis, and Reporting",
                "category": ControlCategory.AU.value,
                "impact": ControlImpact.MODERATE.value,
                "description": "The organization reviews and analyzes information system audit records.",
                "keywords": ["audit review", "audit analysis", "audit reporting"],
                "required_evidence": ["audit_reviews", "audit_analysis", "audit_reporting"],
                "sentinelgrid_features": ["audit_reviews", "compliance_dashboards", "reporting"]
            },
            {
                "control_id": "AU-11",
                "control_name": "Audit Record Retention",
                "category": ControlCategory.AU.value,
                "impact": ControlImpact.MODERATE.value,
                "description": "The organization retains audit records for a time period consistent with records retention policy.",
                "keywords": ["audit retention", "log retention", "audit storage"],
                "required_evidence": ["audit_retention_policy", "retention_period"],
                "sentinelgrid_features": ["audit_logging", "compliance_reporting"]
            },
            {
                "control_id": "CA-7",
                "control_name": "Continuous Monitoring",
                "category": ControlCategory.CA.value,
                "impact": ControlImpact.MODERATE.value,
                "description": "The organization develops a continuous monitoring strategy and implements continuous monitoring.",
                "keywords": ["continuous monitoring", "security monitoring", "ongoing assessment"],
                "required_evidence": ["monitoring_strategy", "continuous_monitoring"],
                "sentinelgrid_features": ["risk_scoring", "anomaly_detection", "predictive_analytics"]
            },
            {
                "control_id": "RA-5",
                "control_name": "Vulnerability Scanning",
                "category": ControlCategory.RA.value,
                "impact": ControlImpact.MODERATE.value,
                "description": "The organization scans for vulnerabilities in the information system.",
                "keywords": ["vulnerability", "scanning", "security assessment"],
                "required_evidence": ["vulnerability_scanning", "vulnerability_management"],
                "sentinelgrid_features": ["risk_scoring", "anomaly_detection"]
            }
        ]

