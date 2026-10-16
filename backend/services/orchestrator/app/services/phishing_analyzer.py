"""Phishing email analyzer service."""

import sys
import os
from typing import Dict, Any, Optional
from uuid import UUID
from datetime import datetime
import httpx
import logging

# Add libs to path
libs_path = os.path.join(os.path.dirname(__file__), "../../../../libs")
if os.path.exists(libs_path):
    sys.path.insert(0, libs_path)

from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sg_core.models import PhishingReport, PhishingObservable
from app.core.config import settings
from app.services.model_gateway_client import ModelGatewayClient
from app.services.framework_client import FrameworkClient

logger = logging.getLogger(__name__)


class PhishingAnalyzer:
    """Service for analyzing phishing emails using AI."""
    
    def __init__(self):
        """Initialize analyzer."""
        self.model_gateway = ModelGatewayClient()
        self.framework_client = FrameworkClient()
        
        # Database connection for fetching reports
        engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        self.db_session_factory = SessionLocal
    
    async def analyze_phishing_email(
        self,
        tenant_id: UUID,
        phishing_report_id: UUID,
        force_reanalyze: bool = False
    ) -> Dict[str, Any]:
        """
        Analyze a phishing email.
        
        Args:
            tenant_id: Tenant ID
            phishing_report_id: Phishing report ID
            force_reanalyze: Force re-analysis even if already classified
            
        Returns:
            Analysis results dictionary
        """
        db = self.db_session_factory()
        try:
            # Fetch phishing report
            report = db.query(PhishingReport).filter(
                PhishingReport.id == phishing_report_id,
                PhishingReport.tenant_id == tenant_id
            ).first()
            
            if not report:
                raise ValueError(f"Phishing report {phishing_report_id} not found")
            
            # Check if already analyzed
            if not force_reanalyze and report.classification and report.classified_by == "ai":
                logger.info(f"Report {phishing_report_id} already analyzed, returning existing results")
                result = self._format_existing_analysis(report)
                return result
            
            # Prepare email content for AI analysis
            email_content = self._prepare_email_content(report)
            
            # Call Model Gateway for AI analysis
            ai_response = await self.model_gateway.analyze_phishing_email(str(tenant_id), email_content)
            analysis_available = ai_response.get("analysis_available", True) is not False
            
            # Extract observables from AI response
            observables = ai_response.get("indicators", {})
            
            if analysis_available:
                framework_mapping = await self._map_to_frameworks(
                    tenant_id,
                    ai_response.get("classification", "suspicious"),
                    observables
                )
                severity = self._determine_severity(
                    ai_response.get("classification"),
                    ai_response.get("confidence", 0)
                )
            else:
                framework_mapping = {
                    "mitre_tactics": [],
                    "mitre_techniques": [],
                    "nist_controls": [],
                }
                severity = None
            
            # Update report with analysis results
            report.classification = ai_response.get("classification", "suspicious")
            report.classification_confidence = ai_response.get("confidence", 0)
            report.classified_by = "ai" if analysis_available else None
            report.classified_at = datetime.utcnow() if analysis_available else None
            report.ai_analysis = ai_response
            report.ai_summary = ai_response.get("reasoning", "")
            report.ai_recommended_actions = ai_response.get("recommended_actions", [])
            report.mitre_tactics = framework_mapping.get("mitre_tactics", [])
            report.mitre_techniques = framework_mapping.get("mitre_techniques", [])
            report.nist_controls = framework_mapping.get("nist_controls", [])
            report.severity = severity
            
            # Update status based on classification
            if report.classification == "phishing":
                report.status = "confirmed_phishing"
            elif report.classification == "benign":
                report.status = "confirmed_benign"
            else:
                report.status = "in_review"
            
            db.commit()
            db.refresh(report)
            
            # Store observables
            await self._store_observables(db, tenant_id, report.id, observables)
            
            result = {
                "phishing_report_id": str(report.id),
                "classification": report.classification,
                "confidence": float(report.classification_confidence or 0),
                "reasoning": report.ai_summary or "",
                "indicators": observables,
                "recommended_actions": report.ai_recommended_actions or [],
                "mitre_mapping": {
                    "tactics": report.mitre_tactics or [],
                    "techniques": report.mitre_techniques or []
                },
                "nist_mapping": {
                    "controls": report.nist_controls or []
                },
                "severity": severity
            }
            
            return result
        finally:
            db.close()
    
    def _prepare_email_content(self, report: PhishingReport) -> Dict[str, Any]:
        """Prepare email content for AI analysis."""
        return {
            "from_address": report.from_address,
            "subject": report.subject or "",
            "to_address": report.to_address,
            "html_body": report.html_body or "",
            "text_body": report.text_body or "",
            "attachments": report.attachments or []
        }
    
    async def _map_to_frameworks(
        self,
        tenant_id: UUID,
        classification: str,
        observables: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Map phishing email to MITRE/NIST frameworks."""
        try:
            # Prepare incident data for framework mapping
            incident_data = {
                "category": "phishing" if classification == "phishing" else "email_security",
                "severity": "high" if classification == "phishing" else "medium",
                "observables": observables
            }
            
            # Call framework service
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{settings.FRAMEWORK_SERVICE_URL}/api/v1/framework/map",
                    json={"ticket_data": incident_data, "tenant_id": str(tenant_id)},
                    headers={
                        "X-Tenant-ID": str(tenant_id),
                        "Authorization": f"Bearer {settings.INTERNAL_SERVICE_TOKEN}"
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    mapping = response.json()
                    return {
                        "mitre_tactics": mapping.get("mitre_tactics", []),
                        "mitre_techniques": mapping.get("mitre_techniques", []),
                        "nist_controls": mapping.get("nist_controls", [])
                    }
        except Exception as e:
            logger.error(f"Error mapping to frameworks: {e}")
        
        # Default mappings for phishing
        return {
            "mitre_tactics": ["TA0001", "TA0004"],  # Initial Access, Privilege Escalation
            "mitre_techniques": ["T1566", "T1566.001"],  # Phishing, Spearphishing Attachment
            "nist_controls": ["AT-2", "IR-4", "SI-4"]  # Security Awareness, Incident Response, System Monitoring
        }
    
    def _determine_severity(self, classification: str, confidence: float) -> str:
        """Determine severity based on classification and confidence."""
        if classification == "phishing":
            if confidence >= 90:
                return "critical"
            elif confidence >= 70:
                return "high"
            else:
                return "medium"
        elif classification == "suspicious":
            return "medium"
        else:
            return "low"
    
    async def _store_observables(
        self,
        db: Session,
        tenant_id: UUID,
        report_id: UUID,
        observables: Dict[str, Any]
    ):
        """Store observables extracted from email."""
        # Get existing observables to avoid duplicates
        existing = {
            (o.observable_type, o.observable_value)
            for o in db.query(PhishingObservable).filter(
                PhishingObservable.phishing_report_id == report_id
            ).all()
        }
        
        # Add URLs
        for url in observables.get("urls", []):
            if ("url", url) not in existing:
                observable = PhishingObservable(
                    tenant_id=tenant_id,
                    phishing_report_id=report_id,
                    observable_type="url",
                    observable_value=url,
                    observable_context="AI-extracted from email"
                )
                db.add(observable)
        
        # Add domains
        for domain in observables.get("domains", []):
            if ("domain", domain) not in existing:
                observable = PhishingObservable(
                    tenant_id=tenant_id,
                    phishing_report_id=report_id,
                    observable_type="domain",
                    observable_value=domain,
                    observable_context="AI-extracted from email"
                )
                db.add(observable)
        
        # Add IPs
        for ip in observables.get("ips", []):
            if ("ip", ip) not in existing:
                observable = PhishingObservable(
                    tenant_id=tenant_id,
                    phishing_report_id=report_id,
                    observable_type="ip",
                    observable_value=ip,
                    observable_context="AI-extracted from email"
                )
                db.add(observable)
        
        # Add emails
        for email in observables.get("email_addresses", []):
            if ("email", email) not in existing:
                observable = PhishingObservable(
                    tenant_id=tenant_id,
                    phishing_report_id=report_id,
                    observable_type="email",
                    observable_value=email,
                    observable_context="AI-extracted from email"
                )
                db.add(observable)
        
        db.commit()
    
    def _format_existing_analysis(self, report: PhishingReport) -> Dict[str, Any]:
        """Format existing analysis results."""
        return {
            "phishing_report_id": str(report.id),
            "classification": report.classification or "pending",
            "confidence": float(report.classification_confidence or 0),
            "reasoning": report.ai_summary or "",
            "indicators": report.ai_analysis.get("indicators", {}) if report.ai_analysis else {},
            "recommended_actions": report.ai_recommended_actions or [],
            "mitre_mapping": {
                "tactics": report.mitre_tactics or [],
                "techniques": report.mitre_techniques or []
            },
            "nist_mapping": {
                "controls": report.nist_controls or []
            },
            "severity": report.severity
        }
