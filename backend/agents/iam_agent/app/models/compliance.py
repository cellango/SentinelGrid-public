"""Models for NIST compliance features."""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class ControlCategory(str, Enum):
    """NIST control categories."""
    AC = "AC"
    IA = "IA"
    AU = "AU"
    CA = "CA"
    CM = "CM"
    CP = "CP"
    IR = "IR"
    MA = "MA"
    MP = "MP"
    PS = "PS"
    PE = "PE"
    PL = "PL"
    RA = "RA"
    SA = "SA"
    SC = "SC"
    SI = "SI"
    SR = "SR"


class ComplianceStatus(str, Enum):
    """Compliance status values."""
    COMPLIANT = "compliant"
    PARTIALLY_COMPLIANT = "partially_compliant"
    NON_COMPLIANT = "non_compliant"
    NOT_ASSESSED = "not_assessed"


class ReportType(str, Enum):
    """Compliance report types."""
    SUMMARY = "summary"
    DETAILED = "detailed"
    GAP_ANALYSIS = "gap_analysis"
    TREND = "trend"


class EvidenceType(str, Enum):
    """Evidence types."""
    CONFIGURATION = "configuration"
    AUDIT_LOG = "audit_log"
    POLICY_DOCUMENT = "policy_document"
    TEST_RESULT = "test_result"
    SCREENSHOT = "screenshot"
    EXPORT = "export"
    API_RESPONSE = "api_response"


class ControlRequest(BaseModel):
    """Request for control information."""
    control_id: Optional[str] = None
    category: Optional[ControlCategory] = None


class ControlResponse(BaseModel):
    """Response with control information."""
    controls: List[Dict[str, Any]]
    total_count: int


class ComplianceStatusRequest(BaseModel):
    """Request for compliance status."""
    tenant_id: str
    control_ids: Optional[List[str]] = None


class ComplianceStatusResponse(BaseModel):
    """Response with compliance status."""
    tenant_id: str
    overall_compliance_score: float
    total_controls: int
    status_breakdown: Dict[str, int]
    compliant_count: int
    partially_compliant_count: int
    non_compliant_count: int
    not_assessed_count: int
    controls: List[Dict[str, Any]]
    assessed_at: datetime


class ComplianceGapResponse(BaseModel):
    """Response with compliance gaps."""
    tenant_id: str
    gaps: List[Dict[str, Any]]
    total_gaps: int
    high_priority_gaps: int


class ComplianceReportRequest(BaseModel):
    """Request for compliance report."""
    tenant_id: str
    report_type: ReportType = ReportType.SUMMARY
    category: Optional[ControlCategory] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class ComplianceReportResponse(BaseModel):
    """Response with compliance report."""
    tenant_id: str
    report_type: str
    report_period: Dict[str, str]
    data: Dict[str, Any]
    generated_at: datetime


class EvidenceCollectionRequest(BaseModel):
    """Request for evidence collection."""
    control_id: str
    evidence_types: List[EvidenceType]
    tenant_id: Optional[str] = None


class EvidenceCollectionResponse(BaseModel):
    """Response with collected evidence."""
    control_id: str
    tenant_id: Optional[str] = None
    evidence: Dict[str, Any]
    repository: Optional[Dict[str, Any]] = None
    collected_at: datetime


class EvidenceRecordRequest(BaseModel):
    """Request to record evidence."""
    control_id: str
    evidence: Dict[str, Any]
    tenant_id: Optional[str] = None


class EvidenceRecordResponse(BaseModel):
    """Response from evidence recording."""
    control_id: str
    assessment: Dict[str, Any]
    evidence_recorded_at: datetime
    tenant_id: Optional[str] = None
