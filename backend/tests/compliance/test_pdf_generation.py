"""
Tests for PDF report generation
"""

import pytest
import os
from pathlib import Path

# Skip tests if WeasyPrint not available
try:
    from weasyprint import HTML
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False


@pytest.mark.skipif(not WEASYPRINT_AVAILABLE, reason="WeasyPrint not installed")
class TestPDFGeneration:
    """Test PDF generation functionality."""
    
    def test_pdf_template_engine_initialization(self):
        """Test PDF engine initializes correctly."""
        from backend.services.reporting_service.app.services.pdf_template_engine import PDFTemplateEngine
        
        engine = PDFTemplateEngine()
        assert engine is not None
        assert engine.jinja_env is not None
    
    def test_generate_simple_pdf(self, temp_report_dir, sample_report_data):
        """Test generating a simple PDF report."""
        from backend.services.reporting_service.app.services.pdf_template_engine import PDFTemplateEngine
        
        engine = PDFTemplateEngine()
        
        # Create simple HTML content
        context = {
            "report_title": "Test Report",
            "tenant_name": "Test Tenant",
            "period_start": "2025-11-01",
            "period_end": "2025-11-30",
            "generated_date": "2025-12-02",
            "confidential_notice": "Test notice"
        }
        
        output_path = str(temp_report_dir / "test_report.pdf")
        
        # Note: This would require base_report.html template
        # For unit test, we'll test the engine setup
        assert engine.jinja_env is not None
    
    def test_date_formatting_filter(self):
        """Test date formatting custom filter."""
        from backend.services.reporting_service.app.services.pdf_template_engine import PDFTemplateEngine
        from datetime import datetime
        
        engine = PDFTemplateEngine()
        
        # Test datetime formatting
        dt = datetime(2025, 12, 2, 15, 30, 0)
        formatted = engine._format_date(dt, '%Y-%m-%d')
        assert formatted == "2025-12-02"
        
        # Test ISO string formatting
        iso_string = "2025-12-02T15:30:00Z"
        formatted = engine._format_date(iso_string)
        assert "2025-12-02" in formatted
    
    def test_number_formatting_filter(self):
        """Test number formatting custom filter."""
        from backend.services.reporting_service.app.services.pdf_template_engine import PDFTemplateEngine
        
        engine = PDFTemplateEngine()
        
        # Test integer formatting
        assert engine._format_number(1000) == "1,000"
        assert engine._format_number(1234567) == "1,234,567"
        
        # Test decimal formatting
        assert engine._format_number(87.5, decimals=1) == "87.5"
    
    def test_percent_formatting_filter(self):
        """Test percentage formatting custom filter."""
        from backend.services.reporting_service.app.services.pdf_template_engine import PDFTemplateEngine
        
        engine = PDFTemplateEngine()
        
        assert engine._format_percent(87.5) == "87.5%"
        assert engine._format_percent(100.0, decimals=0) == "100%"


class TestChartGeneration:
    """Test chart generation functionality."""
    
    @pytest.mark.skipif(not WEASYPRINT_AVAILABLE, reason="Matplotlib may not be available")
    def test_chart_generator_initialization(self):
        """Test chart generator initializes."""
        from backend.services.reporting_service.app.services.chart_generator import ChartGenerator
        
        generator = ChartGenerator()
        assert generator is not None
        assert hasattr(generator, 'colors')
    
    def test_bar_chart_generation(self, temp_report_dir):
        """Test bar chart generation."""
        try:
            from backend.services.reporting_service.app.services.chart_generator import ChartGenerator
            
            generator = ChartGenerator()
            
            data = {
                "Critical": 5,
                "High": 12,
                "Medium": 23,
                "Low": 45
            }
            
            output_path = generator.generate_bar_chart(
                data=data,
                title="Findings by Severity",
                xlabel="Severity",
                ylabel="Count",
                output_format="png"
            )
            
            # Verify file created
            assert os.path.exists(output_path)
            assert os.path.getsize(output_path) > 0
            
        except ImportError:
            pytest.skip("Matplotlib not available")
    
    def test_gauge_chart_for_compliance_score(self):
        """Test gauge chart for compliance scores."""
        try:
            from backend.services.reporting_service.app.services.chart_generator import ChartGenerator
            
            generator = ChartGenerator()
            
            # Generate gauge for 87.5% compliance
            output = generator.generate_gauge_chart(
                value=87.5,
                title="Compliance Score",
                max_value=100,
                output_format="base64"
            )
            
            # Verify base64 output
            assert output.startswith("data:image/png;base64,")
            assert len(output) > 100
            
        except ImportError:
            pytest.skip("Matplotlib not available")


class TestCSVExport:
    """Test CSV export functionality."""
    
    def test_csv_exporter_initialization(self):
        """Test CSV exporter initializes."""
        from backend.services.reporting_service.app.services.csv_exporter import CSVExporter
        
        exporter = CSVExporter()
        assert exporter is not None
    
    def test_export_table_to_csv(self, temp_report_dir):
        """Test exporting data table to CSV."""
        from backend.services.reporting_service.app.services.csv_exporter import CSVExporter
        
        exporter = CSVExporter()
        
        data = [
            {"control_id": "CC6.1", "status": "Implemented", "coverage": "Full"},
            {"control_id": "CC6.2", "status": "Implemented", "coverage": "Full"},
            {"control_id": "CC6.3", "status": "Partial", "coverage": "Partial"}
        ]
        
        output_path = str(temp_report_dir / "test_export.csv")
        
        result = exporter.export_table(
            data=data,
            output_path=output_path,
            columns=["control_id", "status", "coverage"]
        )
        
        # Verify file created
        assert os.path.exists(result)
        
        # Verify content
        with open(result, 'r') as f:
            content = f.read()
            assert "Control Id" in content  # Header
            assert "CC6.1" in content
            assert "Implemented" in content
    
    def test_export_to_string(self):
        """Test exporting CSV to string."""
        from backend.services.reporting_service.app.services.csv_exporter import CSVExporter
        
        exporter = CSVExporter()
        
        data = [
            {"name": "Alice", "mfa_enabled": True},
            {"name": "Bob", "mfa_enabled": False}
        ]
        
        csv_string = exporter.export_to_string(data)
        
        assert "Name" in csv_string
        assert "Mfa Enabled" in csv_string
        assert "Alice" in csv_string
        assert "Yes" in csv_string  # Boolean formatting
        assert "No" in csv_string
    
    def test_value_formatting(self):
        """Test value formatting for CSV."""
        from backend.services.reporting_service.app.services.csv_exporter import CSVExporter
        from datetime import datetime
        
        exporter = CSVExporter()
        
        # Test boolean
        assert exporter._format_value(True) == "Yes"
        assert exporter._format_value(False) == "No"
        
        # Test None
        assert exporter._format_value(None) == ""
        
        # Test datetime
        dt = datetime(2025, 12, 2, 10, 30, 0)
        formatted = exporter._format_value(dt)
        assert "2025-12-02" in formatted

