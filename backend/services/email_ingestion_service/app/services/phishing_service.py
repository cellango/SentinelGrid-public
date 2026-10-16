"""Service for managing phishing reports."""

import sys
import os
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc

# Add libs to path
libs_path = os.path.join(os.path.dirname(__file__), "../../../../libs")
if os.path.exists(libs_path):
    sys.path.insert(0, libs_path)

from sg_core.models import PhishingReport, PhishingObservable
from sg_core.schemas import PhishingReportCreate, PhishingReportUpdate, PhishingObservableCreate


class PhishingService:
    """Service for managing phishing reports."""
    
    def __init__(self, db: Session):
        """Initialize phishing service."""
        self.db = db
    
    def create_report(
        self,
        tenant_id: UUID,
        report_data: PhishingReportCreate
    ) -> PhishingReport:
        """Create a new phishing report."""
        # Check if report already exists (by message_id)
        existing = self.db.query(PhishingReport).filter(
            and_(
                PhishingReport.tenant_id == tenant_id,
                PhishingReport.message_id == report_data.message_id
            )
        ).first()
        
        if existing:
            return existing
        
        # Create new report
        report = PhishingReport(
            tenant_id=tenant_id,
            message_id=report_data.message_id,
            subject=report_data.subject,
            from_address=report_data.from_address,
            to_address=report_data.to_address,
            reply_to=report_data.reply_to,
            received_date=report_data.received_date,
            reported_by=report_data.reported_by,
            raw_email=report_data.raw_email,
            html_body=report_data.html_body,
            text_body=report_data.text_body,
            attachments=report_data.attachments or [],
            status="new"
        )
        
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        
        return report
    
    def get_report(self, tenant_id: UUID, report_id: UUID) -> Optional[PhishingReport]:
        """Get a phishing report by ID."""
        return self.db.query(PhishingReport).filter(
            and_(
                PhishingReport.id == report_id,
                PhishingReport.tenant_id == tenant_id
            )
        ).first()
    
    def list_reports(
        self,
        tenant_id: UUID,
        status: Optional[str] = None,
        classification: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[PhishingReport]:
        """List phishing reports with filters."""
        query = self.db.query(PhishingReport).filter(
            PhishingReport.tenant_id == tenant_id
        )
        
        if status:
            query = query.filter(PhishingReport.status == status)
        
        if classification:
            query = query.filter(PhishingReport.classification == classification)
        
        return query.order_by(desc(PhishingReport.created_at)).limit(limit).offset(offset).all()
    
    def update_report(
        self,
        tenant_id: UUID,
        report_id: UUID,
        update_data: PhishingReportUpdate
    ) -> Optional[PhishingReport]:
        """Update a phishing report."""
        report = self.get_report(tenant_id, report_id)
        if not report:
            return None
        
        # Update fields
        update_dict = update_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(report, key, value)
        
        report.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(report)
        
        return report
    
    def add_observable(
        self,
        tenant_id: UUID,
        report_id: UUID,
        observable_data: PhishingObservableCreate
    ) -> PhishingObservable:
        """Add an observable to a phishing report."""
        # Check if observable already exists
        existing = self.db.query(PhishingObservable).filter(
            and_(
                PhishingObservable.phishing_report_id == report_id,
                PhishingObservable.observable_type == observable_data.observable_type,
                PhishingObservable.observable_value == observable_data.observable_value
            )
        ).first()
        
        if existing:
            return existing
        
        observable = PhishingObservable(
            tenant_id=tenant_id,
            phishing_report_id=report_id,
            observable_type=observable_data.observable_type,
            observable_value=observable_data.observable_value,
            observable_context=observable_data.observable_context,
            threat_intel=observable_data.threat_intel,
            reputation_score=observable_data.reputation_score,
            is_malicious=observable_data.is_malicious or False
        )
        
        self.db.add(observable)
        self.db.commit()
        self.db.refresh(observable)
        
        return observable
    
    def get_observables(
        self,
        tenant_id: UUID,
        report_id: UUID
    ) -> List[PhishingObservable]:
        """Get all observables for a phishing report."""
        return self.db.query(PhishingObservable).filter(
            and_(
                PhishingObservable.phishing_report_id == report_id,
                PhishingObservable.tenant_id == tenant_id
            )
        ).all()

