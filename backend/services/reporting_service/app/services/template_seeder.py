"""Seed standard report templates."""

import logging
from sqlalchemy.orm import Session
from app.models.report import ReportTemplate
from datetime import datetime

logger = logging.getLogger(__name__)


def seed_standard_templates(db: Session):
    """Seed standard report templates (system templates, tenant_id=None)."""
    
    templates = [
        {
            "name": "Executive Weekly Summary",
            "description": "High-level security posture and risk overview for executives",
            "type": "executive",
            "sections": [
                {
                    "title": "Security Posture",
                    "widget": "risk_score",
                    "data_source": "/api/v1/orchestrator/tenant/{tenant_id}/security-snapshot",
                    "config": {},
                    "order": 1
                },
                {
                    "title": "Top Alerts",
                    "widget": "alert_table",
                    "data_source": "/api/v1/alerts?limit=10&severity=high,critical",
                    "config": {
                        "columns": ["title", "severity", "status", "created_at"]
                    },
                    "order": 2
                },
                {
                    "title": "Key Metrics",
                    "widget": "metrics_summary",
                    "data_source": "/api/v1/orchestrator/tenant/{tenant_id}/security-snapshot",
                    "config": {},
                    "order": 3
                }
            ],
            "data_queries": [],
            "schedule": {
                "frequency": "weekly",
                "day": "monday",
                "time": "09:00",
                "recipients": [],
                "enabled": False
            },
            "required_roles": ["ciso", "executive", "tenant_admin"]
        },
        {
            "name": "Compliance Status Report",
            "description": "Evidence-backed compliance status across selected frameworks",
            "type": "compliance",
            "sections": [
                {
                    "title": "Evidence Packages",
                    "widget": "evidence_package_summary",
                    "data_source": "internal://compliance/evidence-packages",
                    "config": {},
                    "order": 1
                },
                {
                    "title": "Control Evidence Mapping",
                    "widget": "control_evidence_mapping",
                    "data_source": "internal://compliance/control-evidence-mapping",
                    "config": {},
                    "order": 2
                },
                {
                    "title": "Priority Compliance Gaps",
                    "widget": "priority_criteria_table",
                    "data_source": "/api/v1/compliance/dashboard",
                    "config": {
                        "source_field": "priority_criteria",
                        "limit": 12
                    },
                    "order": 3
                }
            ],
            "data_queries": [],
            "schedule": {
                "frequency": "monthly",
                "day": "1",
                "time": "09:00",
                "recipients": [],
                "enabled": False
            },
            "required_roles": ["compliance_officer", "tenant_admin"]
        },
        {
            "name": "SOC 2 Coverage Report",
            "description": "SOC 2 Common Criteria coverage and evidence summary",
            "type": "soc2",
            "sections": [
                {
                    "title": "SOC 2 Current Coverage",
                    "widget": "compliance_matrix",
                    "data_source": "/api/v1/compliance/frameworks/soc2/coverage",
                    "config": {},
                    "order": 1
                },
                {
                    "title": "Evidence Packages",
                    "widget": "evidence_package_summary",
                    "data_source": "internal://compliance/evidence-packages",
                    "config": {},
                    "order": 2
                },
                {
                    "title": "Control Evidence Mapping",
                    "widget": "control_evidence_mapping",
                    "data_source": "internal://compliance/control-evidence-mapping",
                    "config": {},
                    "order": 3
                }
            ],
            "data_queries": [],
            "schedule": {
                "frequency": "monthly",
                "day": "1",
                "time": "09:00",
                "recipients": [],
                "enabled": False
            },
            "required_roles": ["compliance_officer", "tenant_admin"]
        },
        {
            "name": "SOC 2 CCM Status",
            "description": "Common Criteria Monitoring status with open findings by control",
            "type": "soc2",
            "sections": [
                {
                    "title": "CCM Status",
                    "widget": "compliance_matrix",
                    "data_source": "/api/v1/compliance/soc2/coverage",
                    "config": {},
                    "order": 1
                },
                {
                    "title": "Status Summary",
                    "widget": "metrics_summary",
                    "data_source": "/api/v1/compliance/soc2/coverage",
                    "config": {},
                    "order": 2
                }
            ],
            "data_queries": [],
            "schedule": {
                "frequency": "monthly",
                "day": "1",
                "time": "09:00",
                "recipients": [],
                "enabled": False
            },
            "required_roles": ["compliance_officer", "tenant_admin"]
        },
        {
            "name": "SOC 2 Evidence Summary",
            "description": "Evidence readiness summary based on durable SOC 2 evidence packages",
            "type": "soc2",
            "sections": [
                {
                    "title": "Evidence Packages",
                    "widget": "evidence_package_summary",
                    "data_source": "internal://compliance/evidence-packages",
                    "config": {},
                    "order": 1
                },
                {
                    "title": "Control Evidence Mapping",
                    "widget": "control_evidence_mapping",
                    "data_source": "internal://compliance/control-evidence-mapping",
                    "config": {},
                    "order": 2
                },
                {
                    "title": "SOC 2 Coverage",
                    "widget": "compliance_matrix",
                    "data_source": "/api/v1/compliance/frameworks/soc2/coverage",
                    "config": {},
                    "order": 3
                }
            ],
            "data_queries": [],
            "schedule": {
                "frequency": "monthly",
                "day": "1",
                "time": "09:00",
                "recipients": [],
                "enabled": False
            },
            "required_roles": ["compliance_officer", "tenant_admin"]
        },
        {
            "name": "SMB Audit Readiness Pack",
            "description": "Auditor-friendly export with readiness summary, priority criteria, mapped detections, and control checks.",
            "type": "compliance",
            "sections": [
                {
                    "title": "Audit Readiness Overview",
                    "widget": "audit_readiness_overview",
                    "data_source": "/api/v1/compliance/dashboard",
                    "config": {},
                    "order": 1
                },
                {
                    "title": "Priority SOC 2 Criteria",
                    "widget": "priority_criteria_table",
                    "data_source": "/api/v1/compliance/dashboard",
                    "config": {
                        "source_field": "priority_criteria",
                        "limit": 8
                    },
                    "order": 2
                },
                {
                    "title": "Key Detections Feeding Audit Evidence",
                    "widget": "compliance_signal_table",
                    "data_source": "/api/v1/compliance/frameworks/soc2/coverage",
                    "config": {
                        "signal_type": "key_detections",
                        "limit": 12
                    },
                    "order": 3
                },
                {
                    "title": "Control Checks Feeding Audit Evidence",
                    "widget": "compliance_signal_table",
                    "data_source": "/api/v1/compliance/frameworks/soc2/coverage",
                    "config": {
                        "signal_type": "control_checks",
                        "limit": 12
                    },
                    "order": 4
                },
                {
                    "title": "Evidence Packages",
                    "widget": "evidence_package_summary",
                    "data_source": "internal://compliance/evidence-packages",
                    "config": {},
                    "order": 5
                },
                {
                    "title": "Control Evidence Mapping",
                    "widget": "control_evidence_mapping",
                    "data_source": "internal://compliance/control-evidence-mapping",
                    "config": {},
                    "order": 6
                }
            ],
            "data_queries": [],
            "schedule": {
                "frequency": "monthly",
                "day": "1",
                "time": "09:00",
                "recipients": [],
                "enabled": False
            },
            "required_roles": ["compliance_officer", "tenant_admin", "executive"]
        },
        {
            "name": "SMB Evidence Attachment Export",
            "description": "Evidence-oriented export for auditors and customer questionnaires with criteria coverage and supporting signals.",
            "type": "compliance",
            "sections": [
                {
                    "title": "Evidence Packages",
                    "widget": "evidence_package_summary",
                    "data_source": "internal://compliance/evidence-packages",
                    "config": {},
                    "order": 1
                },
                {
                    "title": "Control Evidence Mapping",
                    "widget": "control_evidence_mapping",
                    "data_source": "internal://compliance/control-evidence-mapping",
                    "config": {},
                    "order": 2
                },
                {
                    "title": "Criteria Requiring Evidence Updates",
                    "widget": "priority_criteria_table",
                    "data_source": "/api/v1/compliance/frameworks/soc2/coverage",
                    "config": {
                        "source_field": "controls",
                        "limit": 10
                    },
                    "order": 3
                },
                {
                    "title": "Mapped Detections",
                    "widget": "compliance_signal_table",
                    "data_source": "/api/v1/compliance/frameworks/soc2/coverage",
                    "config": {
                        "signal_type": "key_detections",
                        "limit": 15
                    },
                    "order": 4
                },
                {
                    "title": "Mapped Control Checks",
                    "widget": "compliance_signal_table",
                    "data_source": "/api/v1/compliance/frameworks/soc2/coverage",
                    "config": {
                        "signal_type": "control_checks",
                        "limit": 15
                    },
                    "order": 5
                }
            ],
            "data_queries": [],
            "schedule": {
                "frequency": "monthly",
                "day": "1",
                "time": "09:00",
                "recipients": [],
                "enabled": False
            },
            "required_roles": ["compliance_officer", "tenant_admin"]
        },
        {
            "name": "SMB Customer Security Review Pack",
            "description": "Customer-friendly security review export that turns live detections and controls into a concise trust story.",
            "type": "compliance",
            "sections": [
                {
                    "title": "Security Review Overview",
                    "widget": "audit_readiness_overview",
                    "data_source": "/api/v1/compliance/dashboard",
                    "config": {},
                    "order": 1
                },
                {
                    "title": "Priority Criteria Snapshot",
                    "widget": "priority_criteria_table",
                    "data_source": "/api/v1/compliance/dashboard",
                    "config": {
                        "source_field": "priority_criteria",
                        "limit": 6
                    },
                    "order": 2
                },
                {
                    "title": "Top Detection Sources",
                    "widget": "top_detection_sources_table",
                    "data_source": "/api/v1/compliance/soc2/coverage",
                    "config": {
                        "limit": 8
                    },
                    "order": 3
                }
            ],
            "data_queries": [],
            "schedule": {
                "frequency": "monthly",
                "day": "1",
                "time": "09:00",
                "recipients": [],
                "enabled": False
            },
            "required_roles": ["tenant_admin", "executive", "compliance_officer"]
        },
        {
            "name": "AI Governance Executive Summary",
            "description": "Leadership-ready summary of AI usage, policy pressure, high-risk apps, and current AI incidents.",
            "type": "ai_governance",
            "sections": [
                {
                    "title": "AI Governance Overview",
                    "widget": "ai_governance_overview",
                    "data_source": "internal://ai-governance/summary",
                    "config": {"lookback_days": 30},
                    "order": 1
                },
                {
                    "title": "AI Threat Pressure",
                    "widget": "ai_governance_top_threats",
                    "data_source": "internal://ai-governance/summary",
                    "config": {"lookback_days": 30},
                    "order": 2
                },
                {
                    "title": "AI Usage Trend",
                    "widget": "ai_governance_usage_trend",
                    "data_source": "internal://ai-governance/summary",
                    "config": {"lookback_days": 30},
                    "order": 3
                },
                {
                    "title": "AI App Governance Inventory",
                    "widget": "ai_governance_app_inventory",
                    "data_source": "internal://ai-governance/summary",
                    "config": {"lookback_days": 30},
                    "order": 4
                }
            ],
            "data_queries": [],
            "schedule": {
                "frequency": "monthly",
                "day": "1",
                "time": "09:00",
                "recipients": [],
                "enabled": False
            },
            "required_roles": ["tenant_admin", "executive", "compliance_officer"]
        },
        {
            "name": "AI Governance Activity Export",
            "description": "Operational export of AI activity, high-risk apps, and recent governance-relevant activity.",
            "type": "ai_governance",
            "sections": [
                {
                    "title": "AI Governance Overview",
                    "widget": "ai_governance_overview",
                    "data_source": "internal://ai-governance/summary",
                    "config": {"lookback_days": 30},
                    "order": 1
                },
                {
                    "title": "AI App Governance Inventory",
                    "widget": "ai_governance_app_inventory",
                    "data_source": "internal://ai-governance/summary",
                    "config": {"lookback_days": 30},
                    "order": 2
                }
            ],
            "data_queries": [],
            "schedule": {
                "frequency": "monthly",
                "day": "1",
                "time": "09:00",
                "recipients": [],
                "enabled": False
            },
            "required_roles": ["tenant_admin", "executive", "compliance_officer"]
        },
        {
            "name": "Security Posture Report",
            "description": "Weekly security posture and alert summary",
            "type": "security_posture",
            "sections": [
                {
                    "title": "Security Snapshot",
                    "widget": "risk_score",
                    "data_source": "/api/v1/orchestrator/tenant/{tenant_id}/security-snapshot",
                    "config": {},
                    "order": 1
                },
                {
                    "title": "Alert Summary",
                    "widget": "alert_summary",
                    "data_source": "/api/v1/alerts?limit=20",
                    "config": {},
                    "order": 2
                },
                {
                    "title": "Activity Timeline",
                    "widget": "timeline_chart",
                    "data_source": "/api/v1/orchestrator/tenant/{tenant_id}/security-snapshot",
                    "config": {},
                    "order": 3
                }
            ],
            "data_queries": [],
            "schedule": {
                "frequency": "weekly",
                "day": "monday",
                "time": "09:00",
                "recipients": [],
                "enabled": False
            },
            "required_roles": ["soc_manager", "soc_analyst", "tenant_admin"]
        },
        {
            "name": "Incident Report",
            "description": "Detailed incident report with timeline and analysis",
            "type": "incident",
            "sections": [
                {
                    "title": "Incident Overview",
                    "widget": "incident_overview",
                    "data_source": "/api/v1/incidents/{incident_id}",
                    "config": {},
                    "order": 1
                },
                {
                    "title": "Related Alerts",
                    "widget": "alert_table",
                    "data_source": "/api/v1/incidents/{incident_id}/alerts",
                    "config": {},
                    "order": 2
                },
                {
                    "title": "Timeline",
                    "widget": "incident_timeline",
                    "data_source": "/api/v1/incidents/{incident_id}/timeline",
                    "config": {},
                    "order": 3
                }
            ],
            "data_queries": [],
            "schedule": None,
            "required_roles": ["soc_manager", "soc_analyst", "tenant_admin"]
        }
    ]
    
    refreshed_template_names = {
        "Compliance Status Report",
        "SOC 2 Coverage Report",
        "SOC 2 Evidence Summary",
        "SMB Audit Readiness Pack",
        "SMB Evidence Attachment Export",
    }

    for template_data in templates:
        # Check if template already exists
        existing = db.query(ReportTemplate).filter(
            ReportTemplate.name == template_data["name"],
            ReportTemplate.tenant_id.is_(None)
        ).first()
        
        if not existing:
            template = ReportTemplate(
                tenant_id=None,  # System template
                name=template_data["name"],
                description=template_data["description"],
                type=template_data["type"],
                sections=template_data["sections"],
                data_queries=template_data["data_queries"],
                schedule=template_data["schedule"],
                required_roles=template_data["required_roles"]
            )
            db.add(template)
            logger.info(f"Created system template: {template_data['name']}")
        elif template_data["name"] in refreshed_template_names:
            existing.description = template_data["description"]
            existing.type = template_data["type"]
            existing.sections = template_data["sections"]
            existing.data_queries = template_data["data_queries"]
            existing.schedule = template_data["schedule"]
            existing.required_roles = template_data["required_roles"]
            existing.updated_at = datetime.utcnow()
            logger.info(f"Refreshed system template: {template_data['name']}")
        else:
            logger.info(f"Template already exists: {template_data['name']}")
    
    db.commit()
    logger.info("Standard templates seeded successfully")
