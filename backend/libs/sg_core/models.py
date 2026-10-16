"""SQLAlchemy models for SentinelGrid core."""

from sqlalchemy import Column, String, Integer, Boolean, DateTime, JSON, ForeignKey, UUID, Text, Numeric, ARRAY, Index, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime
import uuid

# Create Base class for all models
Base = declarative_base()


class Tenant(Base):
    """Tenant model for multi-tenancy."""
    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    slug = Column(Text, unique=True, nullable=False)
    status = Column(Text, nullable=False, default="active")
    # Realm/architecture fields (may be null for legacy rows)
    realm_name = Column(Text)
    customer_id = Column(UUID(as_uuid=True))
    organization_id = Column(UUID(as_uuid=True))
    pricing_tier = Column(Text)
    plan_tier = Column(Text)
    realm_strategy = Column(Text)
    region = Column(Text, default="us")
    package_name = Column(Text)
    incident_management_mode = Column(Text, nullable=False, default="saas_managed")  # saas_managed | customer_managed
    services_selected = Column(JSON)  # Raw services/add-ons selected at signup
    ticketing_provider = Column(Text, nullable=False, default="internal")  # internal | jira | servicenow
    ticketing_project = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class Alert(Base):
    """Alert model for security alerts/detections."""
    __tablename__ = "alerts"
    __table_args__ = {"schema": "security_ops"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    source = Column(Text, nullable=False)  # e.g., "wazuh", "suricata", "custom"
    external_id = Column(Text, nullable=False)  # ID from source system
    title = Column(Text, nullable=False)
    description = Column(Text)
    raw_severity = Column(Text)  # Severity from source system
    status = Column(Text, nullable=False, default="open")  # 'open', 'investigating', 'resolved', 'false_positive'
    detection_time = Column(DateTime(timezone=True), nullable=False)
    asset_id = Column(Text)  # Affected asset
    user_identifier = Column(Text)  # Affected user
    raw_payload = Column(JSON)  # Full alert data from source
    
    # NIST/MITRE framework fields (from migration 002)
    nist_controls = Column(JSON)  # NIST SP 800-53 control mappings
    mitre_tactics = Column(JSON)  # MITRE ATT&CK tactics
    mitre_techniques = Column(JSON)  # MITRE ATT&CK techniques
    cve_ids = Column(ARRAY(Text))  # Associated CVE IDs
    exploit_indicators = Column(JSON)  # Exploit indicators
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    tenant = relationship("Tenant", backref="alerts")


class Incident(Base):
    """Incident model for security incidents."""
    __tablename__ = "incidents"
    __table_args__ = {"schema": "security_ops"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    source = Column(Text, nullable=False, default="thehive")
    external_id = Column(Text, nullable=True)
    title = Column(Text, nullable=False)
    status = Column(Text, nullable=False)
    severity = Column(Text)
    external_ticket_id = Column(Text, nullable=True)
    external_ticket_provider = Column(Text, nullable=True)
    raw_payload = Column(JSON)
    
    # NIST/MITRE framework fields (from migration 002)
    nist_controls = Column(JSON)
    mitre_tactics = Column(JSON)
    mitre_techniques = Column(JSON)
    cve_ids = Column(ARRAY(Text))
    exploit_indicators = Column(JSON)
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    tenant = relationship("Tenant", backref="incidents")
    ticket_id = Column(UUID(as_uuid=True), ForeignKey("security_ops.tickets.id"), nullable=True)
    ticket = relationship("Ticket", backref="incidents", foreign_keys=[ticket_id])

    @property
    def assigned_to(self):
        raw_payload = self.raw_payload or {}
        if isinstance(raw_payload, dict):
            return raw_payload.get("assigned_to") or raw_payload.get("assignee") or raw_payload.get("owner")
        return None

    @assigned_to.setter
    def assigned_to(self, value):
        raw_payload = dict(self.raw_payload or {})
        if value:
            raw_payload["assigned_to"] = value
            raw_payload["assignee"] = value
        else:
            raw_payload.pop("assigned_to", None)
            raw_payload.pop("assignee", None)
        self.raw_payload = raw_payload or None

    @property
    def phase(self):
        raw_payload = self.raw_payload or {}
        if isinstance(raw_payload, dict):
            return raw_payload.get("phase") or raw_payload.get("workflow_state")
        return None

    @phase.setter
    def phase(self, value):
        raw_payload = dict(self.raw_payload or {})
        if value:
            raw_payload["phase"] = value
        else:
            raw_payload.pop("phase", None)
        self.raw_payload = raw_payload or None

    @property
    def description(self):
        raw_payload = self.raw_payload or {}
        if isinstance(raw_payload, dict):
            return raw_payload.get("description") or raw_payload.get("summary")
        return None

    @description.setter
    def description(self, value):
        raw_payload = dict(self.raw_payload or {})
        if value:
            raw_payload["description"] = value
        else:
            raw_payload.pop("description", None)
        self.raw_payload = raw_payload or None

    @property
    def due_date(self):
        raw_payload = self.raw_payload or {}
        if isinstance(raw_payload, dict):
            return raw_payload.get("due_date") or raw_payload.get("sla_due_at")
        return None

    @due_date.setter
    def due_date(self, value):
        raw_payload = dict(self.raw_payload or {})
        if value:
            raw_payload["due_date"] = value
            raw_payload["sla_due_at"] = value
        else:
            raw_payload.pop("due_date", None)
            raw_payload.pop("sla_due_at", None)
        self.raw_payload = raw_payload or None


class Playbook(Base):
    """Playbook model for automated response workflows."""
    __tablename__ = "playbooks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    key = Column(Text, nullable=False)
    name = Column(Text, nullable=False)
    description = Column(Text)
    target_type = Column(Text, nullable=False)
    severity_filter = Column(JSON)
    category_filter = Column(JSON)
    workflow_ref = Column(Text, nullable=False)
    requires_approval = Column(Boolean, nullable=False, default=True)
    is_enabled = Column(Boolean, nullable=False, default=True)
    is_builtin = Column(Boolean, default=False)  # True for system OOTB playbooks
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    trigger_conditions = Column(JSON)
    auto_trigger_enabled = Column(Boolean, default=False)
    trigger_priority = Column(Integer, default=0)
    playbook_key = Column(String(255))
    severity_default = Column(String(50))
    applicable_sources = Column(ARRAY(Text))
    triggers = Column(ARRAY(Text))
    prerequisites = Column(ARRAY(Text))
    artifacts_required = Column(ARRAY(Text))
    phases = Column(JSON)
    cis_controls = Column(ARRAY(Text))
    is_template = Column(Boolean, default=False)
    template_key = Column(Text)
    category = Column(String(50))
    version = Column(String(50), default="1.0.0")
    workflow = Column(JSON)
    timeout_seconds = Column(Integer, default=3600)
    retry_policy = Column(JSON)
    on_failure = Column(String(50), default="fail")
    tags = Column(ARRAY(Text))
    nist_controls = Column(ARRAY(Text))
    soc2_criteria = Column(ARRAY(Text))
    mitre_tactics = Column(ARRAY(Text))
    mitre_techniques = Column(ARRAY(Text))
    n8n_workflow_id = Column(String(255))
    n8n_webhook_url = Column(Text)
    created_by = Column(UUID(as_uuid=True))

    tenant = relationship("Tenant", backref="playbooks")


class PlaybookExecution(Base):
    """Execution history for playbooks (links alerts/incidents to runs)."""
    __tablename__ = "playbook_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    playbook_id = Column(UUID(as_uuid=True), ForeignKey("playbooks.id"), nullable=False)
    target_type = Column(Text, nullable=False)  # alert | incident | manual | scheduled
    target_id = Column(UUID(as_uuid=True), nullable=False)
    status = Column(Text, nullable=False, default="pending")
    workflow_exec_id = Column(Text)
    triggered_by = Column(Text, nullable=False, default="manual")
    approval_status = Column(Text, nullable=False, default="pending")
    started_at = Column(DateTime(timezone=True))
    finished_at = Column(DateTime(timezone=True))
    result_summary = Column(Text)
    logs = Column(JSON)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    alert_id = Column(UUID(as_uuid=True), ForeignKey("security_ops.alerts.id"))
    trigger_rule_id = Column(UUID(as_uuid=True), ForeignKey("playbooks.id"))

    tenant = relationship("Tenant", backref="playbook_executions")
    playbook = relationship("Playbook", foreign_keys=[playbook_id])
    alert = relationship("Alert", foreign_keys=[alert_id])


class Ticket(Base):
    """Ticket model for security tickets/cases."""
    __tablename__ = "tickets"
    __table_args__ = {"schema": "security_ops"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    tenant_slug = Column(Text)  # Used for SG-branded ticket IDs
    external_id = Column(Text)
    source = Column(Text, nullable=False, default="thehive")
    title = Column(Text, nullable=False)
    description = Column(Text)
    status = Column(Text, nullable=False)
    severity = Column(Text)
    priority = Column(Text)
    category = Column(Text)
    
    # Framework associations
    nist_controls = Column(JSON)
    mitre_tactics = Column(JSON)
    mitre_techniques = Column(JSON)
    cve_ids = Column(ARRAY(Text))
    exploit_indicators = Column(JSON)
    
    # Tab data
    iam_data = Column(JSON)
    vm_data = Column(JSON)
    network_data = Column(JSON)
    cmdb_data = Column(JSON)
    timeline_data = Column(JSON)
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    external_vendor_id = Column(Text)
    tenant = relationship("Tenant", backref="tickets")
    enrichments = relationship("TicketAIEnrichment", back_populates="ticket")

    @property
    def assigned_to(self):
        timeline = self.timeline_data or {}
        if isinstance(timeline, dict):
            return timeline.get("assigned_to")
        return None

    @assigned_to.setter
    def assigned_to(self, value):
        timeline = dict(self.timeline_data or {})
        if value:
            timeline["assigned_to"] = value
        else:
            timeline.pop("assigned_to", None)
        self.timeline_data = timeline or None

    @property
    def due_date(self):
        timeline = self.timeline_data or {}
        if isinstance(timeline, dict):
            return timeline.get("due_date")
        return None

    @due_date.setter
    def due_date(self, value):
        timeline = dict(self.timeline_data or {})
        if value:
            timeline["due_date"] = value
        else:
            timeline.pop("due_date", None)
        self.timeline_data = timeline or None


class TicketAIEnrichment(Base):
    """AI-generated enrichment data for tickets."""
    __tablename__ = "ticket_ai_enrichments"
    __table_args__ = {"schema": "security_ops"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    ticket_id = Column(UUID(as_uuid=True), ForeignKey("security_ops.tickets.id"), nullable=False)
    enrichment_type = Column(String(100), nullable=False) # e.g., "iam_summary", "vm_analysis"
    model_name = Column(String(255), nullable=False)
    model_version = Column(String(50), nullable=False)
    content = Column(JSON) # The actual AI-generated data
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    tenant = relationship("Tenant", backref="ticket_enrichments")
    ticket = relationship("Ticket", back_populates="enrichments")


class PhishingReport(Base):
    """Phishing email report model."""
    __tablename__ = "phishing_reports"
    __table_args__ = {"schema": "security_ops"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    
    # Email metadata
    message_id = Column(String(500), unique=True, nullable=False)
    subject = Column(String(1000))
    from_address = Column(String(500), nullable=False)
    to_address = Column(String(500), nullable=False)
    reply_to = Column(String(500))
    received_date = Column(DateTime(timezone=True), nullable=False)
    reported_by = Column(String(500))  # Email address of reporter
    
    # Email content
    raw_email = Column(Text, nullable=False)  # Full RFC 822 email
    html_body = Column(Text)
    text_body = Column(Text)
    attachments = Column(JSON)  # Array of attachment metadata
    
    # Classification
    classification = Column(String(50))  # 'phishing', 'benign', 'suspicious', 'pending'
    classification_confidence = Column(Numeric(5, 2))  # 0-100
    classified_by = Column(String(50))  # 'ai', 'analyst', 'system'
    classified_at = Column(DateTime(timezone=True))
    
    # AI Analysis
    ai_analysis = Column(JSON)  # Full AI analysis response
    ai_summary = Column(Text)
    ai_recommended_actions = Column(JSON)
    mitre_tactics = Column(JSON)
    mitre_techniques = Column(JSON)
    nist_controls = Column(JSON)
    
    # Status
    status = Column(String(50), nullable=False, default="new")
    severity = Column(String(50))  # 'critical', 'high', 'medium', 'low'
    assigned_to = Column(String(255))  # User ID
    
    # Ticket/Incident linkage
    ticket_id = Column(UUID(as_uuid=True), ForeignKey("security_ops.tickets.id"))
    incident_id = Column(UUID(as_uuid=True), ForeignKey("security_ops.incidents.id"))
    
    # Similar emails
    similar_emails = Column(JSON)  # Array of similar email IDs found
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    tenant = relationship("Tenant", backref="phishing_reports")
    ticket = relationship("Ticket", backref="phishing_reports")
    incident = relationship("Incident", backref="phishing_reports")
    observables = relationship("PhishingObservable", back_populates="phishing_report", cascade="all, delete-orphan")


class PhishingObservable(Base):
    """Indicators of compromise extracted from phishing emails."""
    __tablename__ = "phishing_observables"
    __table_args__ = {"schema": "security_ops"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    phishing_report_id = Column(UUID(as_uuid=True), ForeignKey("security_ops.phishing_reports.id"), nullable=False)
    
    observable_type = Column(String(50), nullable=False)  # 'ip', 'domain', 'url', 'email', 'hash'
    observable_value = Column(String(2000), nullable=False)
    observable_context = Column(String(500))  # Where it was found
    
    # Threat intelligence
    threat_intel = Column(JSON)  # CTI enrichment results
    reputation_score = Column(Integer)  # 0-100
    is_malicious = Column(Boolean, default=False)
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    tenant = relationship("Tenant", backref="phishing_observables")
    phishing_report = relationship("PhishingReport", back_populates="observables")


class IAMFinding(Base):
    """IAM finding model for identity and access management issues."""
    __tablename__ = "iam_findings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    identity_id = Column(UUID(as_uuid=True))  # References iam_identities(id) if that table exists
    finding_type = Column(String(100), nullable=False)  # 'dormant_account', 'overprivileged', 'missing_mfa', etc.
    severity = Column(String(50), nullable=False)  # 'critical', 'high', 'medium', 'low'
    description = Column(Text, nullable=False)
    recommendation = Column(Text)
    status = Column(String(50), nullable=False, default="open")  # 'open', 'accepted', 'resolved', 'false_positive'
    detected_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    
    # Compliance remediation fields (Hero Flow 5)
    nist_control_id = Column(String(100))
    remediation_plan = Column(JSON)
    remediation_status = Column(String(50), default="open")  # 'open', 'in_progress', 'resolved', 'failed'
    remediated_at = Column(DateTime(timezone=True))
    remediated_by = Column(UUID(as_uuid=True))  # User ID who remediated
    soc2_criteria = Column(JSON)  # SOC 2 Common Criteria mappings (optional)
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    tenant = relationship("Tenant", backref="iam_findings")


class PostureFinding(Base):
    """Posture finding model for cloud security posture management issues."""
    __tablename__ = "posture_findings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    cloud_account_id = Column(UUID(as_uuid=True))  # References cloud_accounts(id) if that table exists
    scan_id = Column(UUID(as_uuid=True))  # References posture_scans(id) if that table exists
    check_id = Column(String(255))  # Prowler check ID or similar
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(String(50), nullable=False)  # 'critical', 'high', 'medium', 'low'
    resource_id = Column(String(500))  # Affected cloud resource
    service = Column(String(100))  # 's3', 'iam', 'ec2', 'rds', etc.
    category = Column(String(100))  # 'network', 'identity', 'logging', 'encryption', etc.
    framework = Column(String(100))  # 'CIS', 'NIST', 'PCI', etc.
    remediation = Column(Text)  # Remediation steps from tool
    status = Column(String(50), nullable=False, default="open")  # 'open', 'accepted', 'fixed', 'false_positive'
    detected_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    
    # Compliance remediation fields (Hero Flow 5)
    nist_control_id = Column(String(100))
    remediation_plan = Column(JSON)
    remediation_status = Column(String(50), default="open")
    remediated_at = Column(DateTime(timezone=True))
    remediated_by = Column(UUID(as_uuid=True))
    soc2_criteria = Column(JSON)  # SOC 2 Common Criteria mappings (optional)
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    tenant = relationship("Tenant", backref="posture_findings")


class InfrastructureChangeRequest(Base):
    """Approval-gated infrastructure change request."""
    __tablename__ = "infrastructure_change_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
                server_default=text("gen_random_uuid()"))
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
    cloud_account_id = Column(UUID(as_uuid=True))
    scan_id = Column(UUID(as_uuid=True))
    fix_group_id = Column(UUID(as_uuid=True))
    provider = Column(String(50), nullable=False)
    action_type = Column(String(100), nullable=False)
    status = Column(String(32), nullable=False, default="draft", server_default=text("'draft'"))
    server_id = Column(Text, nullable=False)
    firewall_id = Column(Text, nullable=False)
    scope_hash = Column(Text, nullable=False)
    pre_state = Column(JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))
    proposed_diff = Column(JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))
    approval_required = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    approved_by = Column(Text)
    approved_at = Column(DateTime(timezone=True))
    approval_notes = Column(Text)
    apply_requested_by = Column(Text)
    apply_started_at = Column(DateTime(timezone=True))
    apply_completed_at = Column(DateTime(timezone=True))
    apply_result = Column(JSONB)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow,
                        server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow,
                        onupdate=datetime.utcnow, server_default=text("CURRENT_TIMESTAMP"))

    __table_args__ = (
        Index("idx_infra_change_requests_tenant_created", tenant_id, created_at.desc()),
        Index("idx_infra_change_requests_status", tenant_id, status),
        Index("idx_infra_change_requests_cloud_account", cloud_account_id),
        Index("idx_infra_change_requests_scan", scan_id),
        {"schema": "public"},
    )


class RemediationMetadata(Base):
    """Metadata for remediation actions - links findings to playbook executions."""
    __tablename__ = "remediation_metadata"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    finding_id = Column(UUID(as_uuid=True), nullable=False)  # References iam_findings.id or posture_findings.id
    finding_type = Column(String(50), nullable=False)  # 'iam_finding', 'posture_finding'
    playbook_execution_id = Column(UUID(as_uuid=True), ForeignKey("playbook_executions(id)"))  # Links to actual execution
    remediation_plan = Column(JSON)  # Structured remediation steps
    status = Column(String(50), nullable=False, default="pending")  # 'pending', 'in_progress', 'completed', 'failed'
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    tenant = relationship("Tenant", backref="remediation_metadata")


class AlertPlaybookTrigger(Base):
    """Metadata tracking which playbooks were triggered by which alerts."""
    __tablename__ = "alert_playbook_triggers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    alert_id = Column(UUID(as_uuid=True), ForeignKey("security_ops.alerts.id"), nullable=False)
    playbook_id = Column(UUID(as_uuid=True), ForeignKey("playbooks.id"), nullable=False)
    playbook_execution_id = Column(UUID(as_uuid=True), ForeignKey("playbook_executions(id)"))
    trigger_reason = Column(Text)  # Why this playbook was triggered
    evaluated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    triggered_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    tenant = relationship("Tenant", backref="alert_playbook_triggers")
    alert = relationship("Alert", backref="playbook_triggers")
    playbook = relationship("Playbook", backref="alert_triggers")
