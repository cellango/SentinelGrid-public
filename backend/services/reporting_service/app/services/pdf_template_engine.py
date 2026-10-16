"""
PDF Template Engine
Generates professional, branded PDF reports using WeasyPrint
"""

import logging
from typing import Dict, Any, Optional
from pathlib import Path
import os
from datetime import datetime
from jinja2 import Environment, FileSystemLoader, select_autoescape

logger = logging.getLogger(__name__)

# Try to import WeasyPrint, fallback to reportlab if not available
try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except ImportError:
    logger.warning("WeasyPrint not available, PDF generation will be limited")
    WEASYPRINT_AVAILABLE = False


class PDFTemplateEngine:
    """Professional PDF generation engine using Jinja2 + WeasyPrint."""
    
    def __init__(self, templates_dir: Optional[str] = None):
        """
        Initialize PDF template engine.
        
        Args:
            templates_dir: Directory containing HTML templates
        """
        if templates_dir is None:
            # Default to templates directory in reporting service
            templates_dir = os.path.join(
                os.path.dirname(__file__),
                "..",
                "templates"
            )
        
        self.templates_dir = Path(templates_dir)
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        
        # Set up Jinja2 environment
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # Add custom filters
        self.jinja_env.filters['format_date'] = self._format_date
        self.jinja_env.filters['format_number'] = self._format_number
        self.jinja_env.filters['format_percent'] = self._format_percent
    
    def generate_pdf(
        self,
        template_name: str,
        context: Dict[str, Any],
        output_path: str,
        tenant_config: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate PDF report from template.
        
        Args:
            template_name: Name of the Jinja2 template (without .html)
            context: Template context data
            output_path: Path to save PDF
            tenant_config: Tenant branding configuration
            
        Returns:
            Path to generated PDF file
        """
        if not WEASYPRINT_AVAILABLE:
            raise RuntimeError("WeasyPrint is not available. Install with: pip install weasyprint")
        
        # Add tenant branding to context
        if tenant_config:
            context['tenant_logo'] = tenant_config.get('logo_url', '')
            context['tenant_name'] = tenant_config.get('name', 'Organization')
            context['primary_color'] = tenant_config.get('primary_color', '#1E40AF')
            context['secondary_color'] = tenant_config.get('secondary_color', '#64748B')
        else:
            context['tenant_logo'] = ''
            context['tenant_name'] = 'Organization'
            context['primary_color'] = '#1E40AF'
            context['secondary_color'] = '#64748B'
        
        # Add standard context items
        context['generated_date'] = datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')
        context['generated_timestamp'] = datetime.utcnow().isoformat()
        
        # Load and render template
        template = self.jinja_env.get_template(f"{template_name}.html")
        html_content = template.render(**context)
        
        # Generate PDF
        logger.info(f"Generating PDF: {output_path}")
        
        try:
            # Create output directory if it doesn't exist
            output_dir = os.path.dirname(output_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
            
            # Convert HTML to PDF
            html = HTML(string=html_content, base_url=str(self.templates_dir))
            html.write_pdf(output_path)
            
            logger.info(f"PDF generated successfully: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to generate PDF: {e}", exc_info=True)
            raise
    
    def _format_date(self, value: Any, format: str = '%Y-%m-%d') -> str:
        """Format date for template."""
        if isinstance(value, datetime):
            return value.strftime(format)
        elif isinstance(value, str):
            try:
                dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                return dt.strftime(format)
            except:
                return value
        return str(value)
    
    def _format_number(self, value: Any, decimals: int = 0) -> str:
        """Format number with thousands separator."""
        try:
            if decimals == 0:
                return f"{int(value):,}"
            else:
                return f"{float(value):,.{decimals}f}"
        except:
            return str(value)
    
    def _format_percent(self, value: Any, decimals: int = 1) -> str:
        """Format as percentage."""
        try:
            return f"{float(value):.{decimals}f}%"
        except:
            return str(value)
    
    def get_base_context(
        self,
        report_title: str,
        report_period_start: datetime,
        report_period_end: datetime
    ) -> Dict[str, Any]:
        """
        Get base context for all reports.
        
        Args:
            report_title: Report title
            report_period_start: Start of reporting period
            report_period_end: End of reporting period
            
        Returns:
            Base context dict
        """
        return {
            'report_title': report_title,
            'period_start': report_period_start.strftime('%Y-%m-%d'),
            'period_end': report_period_end.strftime('%Y-%m-%d'),
            'generated_date': datetime.utcnow().strftime('%Y-%m-%d'),
            'confidential_notice': 'This report contains confidential information and is intended solely for the use of the recipient organization.'
        }


# Singleton instance
_pdf_engine: Optional[PDFTemplateEngine] = None


def get_pdf_engine() -> PDFTemplateEngine:
    """Get or create the global PDF engine instance."""
    global _pdf_engine
    if _pdf_engine is None:
        _pdf_engine = PDFTemplateEngine()
    return _pdf_engine

