"""Tests for phishing service."""

import pytest
from uuid import uuid4
from datetime import datetime
from sqlalchemy.orm import Session
from app.services.phishing_service import PhishingService
from sg_core.models import PhishingReport, PhishingObservable
from sg_core.schemas import PhishingReportCreate


class TestPhishingService:
    """Test phishing service functionality."""
    
    def test_create_report(self, db_session: Session):
        """Test creating a phishing report."""
        service = PhishingService(db_session)
        tenant_id = uuid4()
        
        report_data = PhishingReportCreate(
            message_id="test123@example.com",
            from_address="attacker@example.com",
            to_address="victim@company.com",
            subject="Test Phishing",
            received_date=datetime.utcnow(),
            raw_email="Raw email content",
            text_body="Email body text",
        )
        
        report = service.create_report(tenant_id, report_data)
        
        assert report.id is not None
        assert report.tenant_id == tenant_id
        assert report.from_address == "attacker@example.com"
        assert report.status == "new"
    
    def test_get_report(self, db_session: Session):
        """Test retrieving a phishing report."""
        service = PhishingService(db_session)
        tenant_id = uuid4()
        
        # Create a report
        report_data = PhishingReportCreate(
            message_id="test456@example.com",
            from_address="test@example.com",
            to_address="user@company.com",
            subject="Test",
            received_date=datetime.utcnow(),
            raw_email="Raw email",
        )
        created_report = service.create_report(tenant_id, report_data)
        
        # Retrieve it
        retrieved_report = service.get_report(tenant_id, created_report.id)
        
        assert retrieved_report is not None
        assert retrieved_report.id == created_report.id
        assert retrieved_report.message_id == "test456@example.com"
    
    def test_list_reports(self, db_session: Session):
        """Test listing phishing reports."""
        service = PhishingService(db_session)
        tenant_id = uuid4()
        
        # Create multiple reports
        for i in range(3):
            report_data = PhishingReportCreate(
                message_id=f"test{i}@example.com",
                from_address=f"sender{i}@example.com",
                to_address="user@company.com",
                subject=f"Test {i}",
                received_date=datetime.utcnow(),
                raw_email=f"Raw email {i}",
            )
            service.create_report(tenant_id, report_data)
        
        # List reports
        reports = service.list_reports(tenant_id, limit=10)
        
        assert len(reports) >= 3
    
    def test_update_report(self, db_session: Session):
        """Test updating a phishing report."""
        service = PhishingService(db_session)
        tenant_id = uuid4()
        
        # Create a report
        report_data = PhishingReportCreate(
            message_id="test789@example.com",
            from_address="test@example.com",
            to_address="user@company.com",
            subject="Test",
            received_date=datetime.utcnow(),
            raw_email="Raw email",
        )
        report = service.create_report(tenant_id, report_data)
        
        # Update it
        from sg_core.schemas import PhishingReportUpdate
        update_data = PhishingReportUpdate(
            classification="phishing",
            status="confirmed_phishing",
            severity="high",
        )
        updated_report = service.update_report(tenant_id, report.id, update_data)
        
        assert updated_report.classification == "phishing"
        assert updated_report.status == "confirmed_phishing"
        assert updated_report.severity == "high"
    
    def test_create_observable(self, db_session: Session):
        """Test creating an observable."""
        service = PhishingService(db_session)
        tenant_id = uuid4()
        
        # Create a report first
        report_data = PhishingReportCreate(
            message_id="test999@example.com",
            from_address="test@example.com",
            to_address="user@company.com",
            subject="Test",
            received_date=datetime.utcnow(),
            raw_email="Raw email",
        )
        report = service.create_report(tenant_id, report_data)
        
        # Create observable
        from sg_core.schemas import PhishingObservableCreate
        observable_data = PhishingObservableCreate(
            observable_type="url",
            observable_value="https://malicious.com",
            observable_context="Found in email body",
        )
        observable = service.create_observable(tenant_id, report.id, observable_data)
        
        assert observable.id is not None
        assert observable.phishing_report_id == report.id
        assert observable.observable_type == "url"
        assert observable.observable_value == "https://malicious.com"
    
    def test_get_observables(self, db_session: Session):
        """Test retrieving observables for a report."""
        service = PhishingService(db_session)
        tenant_id = uuid4()
        
        # Create report and observables
        report_data = PhishingReportCreate(
            message_id="test111@example.com",
            from_address="test@example.com",
            to_address="user@company.com",
            subject="Test",
            received_date=datetime.utcnow(),
            raw_email="Raw email",
        )
        report = service.create_report(tenant_id, report_data)
        
        from sg_core.schemas import PhishingObservableCreate
        for i in range(3):
            observable_data = PhishingObservableCreate(
                observable_type="url",
                observable_value=f"https://malicious{i}.com",
                observable_context=f"URL {i}",
            )
            service.create_observable(tenant_id, report.id, observable_data)
        
        # Get observables
        observables = service.get_observables(tenant_id, report.id)
        
        assert len(observables) == 3
    
    def test_detect_duplicate(self, db_session: Session):
        """Test duplicate detection."""
        service = PhishingService(db_session)
        tenant_id = uuid4()
        
        message_id = "duplicate@example.com"
        
        # Create first report
        report_data = PhishingReportCreate(
            message_id=message_id,
            from_address="test@example.com",
            to_address="user@company.com",
            subject="Test",
            received_date=datetime.utcnow(),
            raw_email="Raw email",
        )
        first_report = service.create_report(tenant_id, report_data)
        
        # Try to create duplicate
        duplicate = service.get_report_by_message_id(tenant_id, message_id)
        
        assert duplicate is not None
        assert duplicate.id == first_report.id

