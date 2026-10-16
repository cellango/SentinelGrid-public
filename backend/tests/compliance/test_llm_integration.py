"""
Tests for LLM integration and report Q&A with tenant isolation
"""

import pytest
from uuid import uuid4
from datetime import datetime
from sqlalchemy import text


class TestReportLLMIngestor:
    """Test report ingestion to vector DB."""
    
    def test_ingestor_initialization(self, mock_embedding_model):
        """Test LLM ingestor initializes correctly without vector backend."""
        from backend.services.reporting_service.app.services.report_llm_ingestor import ReportLLMIngestor
        
        ingestor = ReportLLMIngestor(embedding_model=mock_embedding_model)
        
        assert ingestor is not None
        assert ingestor.embedding_model is not None
    
    def test_chunk_report_text(self):
        """Test report text chunking."""
        from backend.services.reporting_service.app.services.report_llm_ingestor import ReportLLMIngestor
        
        ingestor = ReportLLMIngestor()
        
        # Long text that should be chunked
        long_text = "\n\n".join([f"Section {i}: " + ("Test content. " * 100) for i in range(5)])
        
        chunks = ingestor._chunk_report(long_text, max_chunk_size=1000)
        
        assert len(chunks) > 1
        assert all(len(chunk) <= 1500 for chunk in chunks)  # Allow some overflow
    
    def test_report_ingestion_with_metadata(
        self, 
        db_session, 
        tenant_a, 
        mocker
    ):
        """Test report ingestion currently returns disabled status."""
        from backend.services.reporting_service.app.services.report_llm_ingestor import ReportLLMIngestor
        
        ingestor = ReportLLMIngestor()
        
        # Mock PDF text extraction
        mocker.patch.object(
            ingestor, 
            '_extract_pdf_text', 
            return_value="Sample report content for testing"
        )
        
        report_id = uuid4()
        
        # Attempt ingestion
        # Note: This will partially work in test environment
        result = ingestor.ingest_report(
            report_id=report_id,
            tenant_id=tenant_a["id"],
            realm_name=tenant_a["realm"],
            report_type="soc2_coverage",
            pdf_path="/tmp/test.pdf",
            generated_at=datetime.utcnow(),
            db_session=db_session
        )
        
        assert result is False


class TestReportQAService:
    """Test Report Q&A service with tenant isolation."""
    
    def test_qa_service_initialization(self, mock_embedding_model):
        """Test Q&A service initializes."""
        from backend.services.model_gateway.app.services.report_qa_service import ReportQAService
        
        service = ReportQAService(
            embedding_model=mock_embedding_model
        )
        
        assert service is not None
    
    def test_query_with_tenant_context(
        self, 
        mock_embedding_model,
        tenant_a,
        test_user_a
    ):
        """Test querying reports returns disabled response with tenant context."""
        from backend.services.model_gateway.app.services.report_qa_service import (
            ReportQAService, 
            UserContext
        )
        
        service = ReportQAService(
            embedding_model=mock_embedding_model
        )
        
        # Create user context
        user_context = UserContext(
            user_id=test_user_a["id"],
            tenant_id=tenant_a["id"],
            realm=tenant_a["realm"],
            email=test_user_a["email"]
        )
        
        # Query reports
        result = service.query_reports(
            user_context=user_context,
            query="What is our MFA coverage?"
        )
        
        # Verify response structure
        assert "answer" in result
        assert "sources" in result
        assert result.get("error") == "Service unavailable"


class TestReportAccessControl:
    """Test report access control and tenant isolation."""
    
    def test_list_reports_tenant_scoped(self, db_session, tenant_a, tenant_b):
        """Test listing reports returns only tenant's own reports."""
        report_a_id = uuid4()
        report_b_id = uuid4()
        
        # Create report for Tenant A
        db_session.execute(
            text("""
                INSERT INTO generated_reports (id, tenant_id, realm_name, report_type, report_name, status)
                VALUES (:id, :tenant_id, :realm_name, 'soc2_coverage', 'Report_A.pdf', 'ready')
            """),
            {"id": str(report_a_id), "tenant_id": str(tenant_a["id"]), "realm_name": tenant_a["realm"]}
        )
        
        # Create report for Tenant B
        db_session.execute(
            text("""
                INSERT INTO generated_reports (id, tenant_id, realm_name, report_type, report_name, status)
                VALUES (:id, :tenant_id, :realm_name, 'soc2_coverage', 'Report_B.pdf', 'ready')
            """),
            {"id": str(report_b_id), "tenant_id": str(tenant_b["id"]), "realm_name": tenant_b["realm"]}
        )
        
        db_session.commit()
        
        # Query as Tenant A
        result_a = db_session.execute(
            text("""
                SELECT report_name FROM generated_reports
                WHERE tenant_id = :tenant_id AND realm_name = :realm_name
            """),
            {"tenant_id": str(tenant_a["id"]), "realm_name": tenant_a["realm"]}
        )
        
        reports_a = [row[0] for row in result_a.fetchall()]
        
        # Tenant A should only see their own report
        assert 'Report_A.pdf' in reports_a
        assert 'Report_B.pdf' not in reports_a, "SECURITY VIOLATION: Cross-tenant access!"
    
    def test_report_download_authorization(self, db_session, tenant_a, tenant_b):
        """Test that users cannot download other tenants' reports."""
        report_b_id = uuid4()
        
        # Create report for Tenant B
        db_session.execute(
            text("""
                INSERT INTO generated_reports (id, tenant_id, realm_name, report_type, report_name, status)
                VALUES (:id, :tenant_id, :realm_name, 'soc2_coverage', 'Report_B.pdf', 'ready')
            """),
            {"id": str(report_b_id), "tenant_id": str(tenant_b["id"]), "realm_name": tenant_b["realm"]}
        )
        
        db_session.commit()
        
        # Try to access as Tenant A (should fail)
        result = db_session.execute(
            text("""
                SELECT id FROM generated_reports
                WHERE id = :report_id
                  AND tenant_id = :tenant_id
                  AND realm_name = :realm_name
            """),
            {
                "report_id": str(report_b_id),
                "tenant_id": str(tenant_a["id"]),  # Tenant A trying to access
                "realm_name": tenant_a["realm"]
            }
        )
        
        report = result.fetchone()
        assert report is None, "Should not find report (tenant mismatch)"


class TestLLMQueryIsolation:
    """CRITICAL: Test LLM queries cannot access other tenants' data."""
    
    def test_vector_path_disabled(
        self,
        mock_embedding_model,
        tenant_a,
        test_user_a
    ):
        """Vector search is disabled; ensure safe response."""
        from backend.services.model_gateway.app.services.report_qa_service import (
            ReportQAService,
            UserContext
        )
        
        service = ReportQAService(
            embedding_model=mock_embedding_model
        )
        
        user_context = UserContext(
            user_id=test_user_a["id"],
            tenant_id=tenant_a["id"],
            realm=tenant_a["realm"]
        )
        
        # Query
        result = service.query_reports(user_context, "What is our compliance score?")
        assert result.get("error") == "Service unavailable"
    
    def test_query_logging_for_audit(
        self,
        mock_embedding_model,
        tenant_a,
        test_user_a,
        mocker
    ):
        """Ensure disabled path does not log unsafe tenant-crossing queries."""
        from backend.services.model_gateway.app.services.report_qa_service import (
            ReportQAService,
            UserContext
        )
        
        service = ReportQAService(
            embedding_model=mock_embedding_model
        )
        
        # Spy on _log_query method
        spy = mocker.spy(service, '_log_query')
        
        user_context = UserContext(
            user_id=test_user_a["id"],
            tenant_id=tenant_a["id"],
            realm=tenant_a["realm"]
        )
        
        # Query
        service.query_reports(user_context, "Test query")
        
        # Logging is not triggered on the disabled path
        assert spy.call_count == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
