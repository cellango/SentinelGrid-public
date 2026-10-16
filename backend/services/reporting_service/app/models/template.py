"""Report template Pydantic models for API."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import datetime


class DataQuery(BaseModel):
    """Data query configuration for a report section."""
    endpoint: str = Field(..., description="API endpoint to fetch data from")
    method: str = Field(default="GET", description="HTTP method")
    params: Optional[Dict[str, Any]] = Field(default=None, description="Query parameters")
    headers: Optional[Dict[str, str]] = Field(default=None, description="Additional headers")
    transform: Optional[str] = Field(default=None, description="Data transformation function name")


class TemplateSection(BaseModel):
    """Report section configuration."""
    title: str = Field(..., description="Section title")
    widget: str = Field(..., description="Widget type (risk_score, alert_table, compliance_matrix, etc.)")
    data_source: str = Field(..., description="Data source endpoint or query ID")
    config: Optional[Dict[str, Any]] = Field(default=None, description="Widget-specific configuration")
    order: int = Field(default=0, description="Display order in report")


class ScheduleConfig(BaseModel):
    """Schedule configuration for automated reports."""
    frequency: str = Field(..., description="Frequency: daily, weekly, monthly, quarterly")
    day: Optional[str] = Field(
        default=None,
        description="Day of week (for weekly) or day of month (for monthly/quarterly)"
    )
    time: str = Field(..., description="Time in HH:MM format")
    recipients: List[str] = Field(default_factory=list, description="Email recipients")
    enabled: bool = Field(default=True, description="Whether schedule is enabled")

    @model_validator(mode="after")
    def validate_schedule(self):
        """Normalize and validate schedule inputs."""
        allowed = {"daily", "weekly", "monthly", "quarterly"}
        freq = (self.frequency or "").lower()
        if freq not in allowed:
            raise ValueError(f"frequency must be one of {sorted(allowed)}")

        # Normalize defaults for day based on frequency
        if freq == "weekly" and not self.day:
            self.day = "monday"
        if freq in {"monthly", "quarterly"} and not self.day:
            self.day = "1"

        self.frequency = freq
        return self


class ReportTemplateCreate(BaseModel):
    """Request model for creating a report template."""
    name: str
    description: Optional[str] = None
    type: str  # executive, compliance, incident, custom
    sections: List[TemplateSection]
    data_queries: Optional[List[DataQuery]] = None
    schedule: Optional[ScheduleConfig] = None
    required_roles: Optional[List[str]] = None


class ReportTemplateResponse(BaseModel):
    """Response model for report template."""
    id: str
    tenant_id: Optional[str]
    name: str
    description: Optional[str]
    type: str
    sections: List[TemplateSection]
    data_queries: Optional[List[DataQuery]]
    schedule: Optional[ScheduleConfig]
    required_roles: Optional[List[str]]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
        # Pydantic v2 compatibility
        model_config = {"from_attributes": True}


class ReportGenerateRequest(BaseModel):
    """Request model for generating a report."""
    template_id: str
    format: str = "pdf"  # implemented generation formats: pdf, csv
    date_range: Optional[Dict[str, str]] = None  # {"start": "2025-01-01", "end": "2025-01-31"}
    sections: Optional[List[str]] = None  # Optional: subset of sections to include
    framework_ids: Optional[List[str]] = None
    control_ids: Optional[List[str]] = None
    evidence_package_ids: Optional[List[str]] = None
    include_gaps: bool = True
    include_expired_evidence: bool = False
    parameters: Optional[Dict[str, Any]] = None  # Additional parameters for template

    @field_validator("format", mode="before")
    @classmethod
    def normalize_format(cls, value):
        if value in (None, ""):
            return "pdf"
        return str(value).strip().lower()


class ReportResponse(BaseModel):
    """Response model for a generated report."""
    id: str
    tenant_id: str
    template_id: Optional[str]
    name: str
    format: str
    status: str
    generated_at: Optional[datetime]
    generated_by: Optional[str]
    date_range_start: Optional[datetime]
    date_range_end: Optional[datetime]
    file_path: Optional[str]
    file_size_bytes: Optional[int]
    download_url: Optional[str]
    sections: Optional[List[str]]
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, alias="report_metadata"
    )
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
        # Pydantic v2 compatibility
        model_config = {"from_attributes": True, "populate_by_name": True}
