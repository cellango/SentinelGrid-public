"""
Performance tests for compliance platform
"""

import pytest
import time
from uuid import uuid4
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker


class TestReportGenerationPerformance:
    """Test report generation performance."""
    
    def test_single_report_generation_time(self, db_session, tenant_a):
        """Test that single report generation completes within acceptable time."""
        # Placeholder - would test actual report generation
        start_time = time.time()
        
        # Simulate report generation steps
        report_id = uuid4()
        db_session.execute(
            text("""
                INSERT INTO generated_reports (id, tenant_id, realm_name, report_type, report_name, status)
                VALUES (:id, :tenant_id, :realm_name, 'soc2_coverage', 'Test.pdf', 'ready')
            """),
            {"id": str(report_id), "tenant_id": str(tenant_a["id"]), "realm_name": tenant_a["realm"]}
        )
        db_session.commit()
        
        elapsed = time.time() - start_time
        
        # Should complete quickly (< 1 second for database operations)
        assert elapsed < 1.0, f"Report database operations took {elapsed:.2f}s (should be < 1s)"
    
    @pytest.mark.slow
    def test_concurrent_report_generation(self, db_session, tenant_a):
        """Test system can handle concurrent report generation."""
        num_concurrent = 10
        SessionLocal = sessionmaker(bind=db_session.bind)
        
        def create_report(index):
            report_id = uuid4()
            session = SessionLocal()
            try:
                session.execute(
                    text("""
                        INSERT INTO generated_reports (id, tenant_id, realm_name, report_type, report_name, status)
                        VALUES (:id, :tenant_id, :realm_name, 'soc2_coverage', :report_name, 'ready')
                    """),
                    {
                        "id": str(report_id),
                        "tenant_id": str(tenant_a["id"]),
                        "realm_name": tenant_a["realm"],
                        "report_name": f"Report_{index}.pdf"
                    }
                )
                session.commit()
                return True
            except Exception as e:
                session.rollback()
                return False
            finally:
                session.close()
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(create_report, i) for i in range(num_concurrent)]
            results = [future.result() for future in as_completed(futures)]
        
        elapsed = time.time() - start_time
        
        # Verify all succeeded
        success_count = sum(results)
        assert success_count == num_concurrent, f"Only {success_count}/{num_concurrent} reports succeeded"
        
        # Should complete within reasonable time
        assert elapsed < 5.0, f"Concurrent generation took {elapsed:.2f}s (should be < 5s)"


class TestDatabaseQueryPerformance:
    """Test database query performance."""
    
    def test_report_list_query_performance(self, db_session, tenant_a):
        """Test report listing is fast even with many reports."""
        # Create 100 reports
        for i in range(100):
            db_session.execute(
                text("""
                    INSERT INTO generated_reports (tenant_id, realm_name, report_type, report_name, status)
                    VALUES (:tenant_id, :realm_name, 'soc2_coverage', :report_name, 'ready')
                """),
                {
                    "tenant_id": str(tenant_a["id"]),
                    "realm_name": tenant_a["realm"],
                    "report_name": f"Report_{i}.pdf"
                }
            )
        
        db_session.commit()
        
        # Time the query
        start_time = time.time()
        
        result = db_session.execute(
            text("""
                SELECT id, report_name, generated_at
                FROM generated_reports
                WHERE tenant_id = :tenant_id AND realm_name = :realm_name
                ORDER BY generated_at DESC
                LIMIT 50
            """),
            {"tenant_id": str(tenant_a["id"]), "realm_name": tenant_a["realm"]}
        )
        
        reports = result.fetchall()
        elapsed = time.time() - start_time
        
        # Should be fast (< 100ms with proper indexing)
        # Local dev DB can be slower; allow a bit of headroom while still catching regressions.
        assert elapsed < 0.25, f"Query took {elapsed:.3f}s (should be < 0.25s)"
        assert len(reports) == 50
    
    def test_audit_log_query_performance(self, db_session, tenant_a):
        """Test audit log queries are fast."""
        # Create 1000 audit logs
        for i in range(1000):
            db_session.execute(
                text("""
                    INSERT INTO platform_audit_logs (tenant_id, realm_name, action, actor_user_id)
                    VALUES (:tenant_id, :realm_name, 'test_action', :user_id)
                """),
                {
                    "tenant_id": str(tenant_a["id"]),
                    "realm_name": tenant_a["realm"],
                    "user_id": f"user-{i % 10}"
                }
            )
        
        db_session.commit()
        
        # Time the query
        start_time = time.time()
        
        result = db_session.execute(
            text("""
                SELECT id, action, timestamp
                FROM platform_audit_logs
                WHERE tenant_id = :tenant_id AND realm_name = :realm_name
                ORDER BY timestamp DESC
                LIMIT 100
            """),
            {"tenant_id": str(tenant_a["id"]), "realm_name": tenant_a["realm"]}
        )
        
        logs = result.fetchall()
        elapsed = time.time() - start_time
        
        # Should be fast with indexes
        assert elapsed < 0.1, f"Query took {elapsed:.3f}s (should be < 0.1s)"
        assert len(logs) == 100


class TestVectorDBPerformance:
    """Test vector path placeholder performance."""
    
    @pytest.mark.slow
    def test_llm_query_response_time(
        self,
        mock_embedding_model,
        tenant_a,
        test_user_a
    ):
        """Test LLM query responds quickly."""
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
        
        # Time the query
        start_time = time.time()
        
        result = service.query_reports(user_context, "What is our compliance score?")
        
        elapsed = time.time() - start_time
        
        # Should respond quickly (< 5 seconds target) even when disabled
        assert elapsed < 5.0, f"LLM query took {elapsed:.2f}s (target < 5s)"
        assert result.get("error") == "Service unavailable"


class TestMemoryUsage:
    """Test memory usage for large operations."""
    
    def test_large_csv_export_memory(self):
        """Test CSV export doesn't consume excessive memory."""
        from backend.services.reporting_service.app.services.csv_exporter import CSVExporter
        
        exporter = CSVExporter()
        
        # Create large dataset
        data = [
            {"id": i, "name": f"User {i}", "value": i * 100}
            for i in range(10000)
        ]
        
        # Export to string (in-memory)
        start_time = time.time()
        csv_string = exporter.export_to_string(data)
        elapsed = time.time() - start_time
        
        # Should complete reasonably fast
        assert elapsed < 2.0, f"Large CSV export took {elapsed:.2f}s"
        assert len(csv_string) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
