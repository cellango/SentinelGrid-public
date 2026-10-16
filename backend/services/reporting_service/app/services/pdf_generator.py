"""PDF report generator service using WeasyPrint."""

import logging
from typing import Dict, Any, List
from pathlib import Path
from datetime import datetime, timezone
import httpx
import base64
import io
from app.core.config import settings

try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except Exception as exc:
    WEASYPRINT_AVAILABLE = False
    logging.warning(
        "WeasyPrint not available (missing system deps like libgobject?); PDF generation will use HTML fallback. %s",
        exc,
    )

try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    logging.warning("Matplotlib not available. Charts will not be generated.")

logger = logging.getLogger(__name__)


class PDFGenerator:
    """Generate PDF reports from template data using WeasyPrint."""
    
    def __init__(self):
        self.storage_path = Path(settings.REPORT_STORAGE_PATH)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.use_weasyprint = WEASYPRINT_AVAILABLE
    
    def generate(
        self,
        report_id: str,
        template_name: str,
        sections: List[Dict[str, Any]],
        tenant_id: str,
        date_range: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """
        Generate a PDF report.
        
        Args:
            report_id: Unique report ID
            template_name: Name of the template
            sections: List of section data to include
            tenant_id: Tenant ID
            date_range: Optional date range
            
        Returns:
            Dict with file_path, file_size_bytes, download_url
        """
        try:
            tenant_path = self.storage_path / tenant_id
            tenant_path.mkdir(parents=True, exist_ok=True)

            # Generate HTML content
            html_content = self._generate_html(template_name, sections, tenant_id, date_range)
            
            # Generate PDF file path
            pdf_path = tenant_path / f"{report_id}.pdf"
            
            if self.use_weasyprint:
                # Use WeasyPrint for true PDF generation
                HTML(string=html_content).write_pdf(
                    pdf_path,
                    stylesheets=[CSS(string=self._get_css())]
                )
                logger.info(f"Generated PDF report {report_id} using WeasyPrint")
            else:
                # Fallback: Save as HTML (can be converted to PDF later)
                html_path = self.storage_path / f"{report_id}.html"
                html_path.write_text(html_content, encoding='utf-8')
                pdf_path = html_path
                logger.warning(f"WeasyPrint not available. Saved HTML report {report_id}")
            
            file_size = pdf_path.stat().st_size
            file_extension = "pdf" if self.use_weasyprint else "html"
            download_url = f"{settings.REPORT_STORAGE_URL}/{tenant_id}/{report_id}.{file_extension}"
            
            return {
                "file_path": str(pdf_path),
                "file_size_bytes": file_size,
                "download_url": download_url
            }
        
        except Exception as e:
            logger.error(f"Failed to generate PDF report {report_id}: {e}", exc_info=True)
            raise
    
    def _get_css(self) -> str:
        """Get CSS styles for PDF generation."""
        return """
        @page {
            size: A4;
            margin: 2cm;
        }
        body {
            font-family: Arial, sans-serif;
            font-size: 11pt;
            line-height: 1.6;
            color: #333;
        }
        .header {
            border-bottom: 3px solid #22d3ee;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }
        .header h1 {
            color: #22d3ee;
            margin: 0;
            font-size: 24pt;
        }
        .metadata {
            color: #666;
            font-size: 9pt;
            margin-top: 10px;
        }
        .section {
            margin-bottom: 30px;
            page-break-inside: avoid;
        }
        .section-title {
            font-size: 16pt;
            font-weight: bold;
            color: #a855f7;
            margin-bottom: 15px;
            border-left: 4px solid #a855f7;
            padding-left: 10px;
        }
        .section-content {
            background: #f5f5f5;
            padding: 15px;
            border-radius: 5px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
            font-size: 9pt;
        }
        th, td {
            padding: 8px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background-color: #22d3ee;
            color: white;
            font-weight: bold;
        }
        tr:nth-child(even) {
            background-color: #f9f9f9;
        }
        .footer {
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            color: #666;
            font-size: 9pt;
            text-align: center;
        }
        .risk-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-weight: bold;
            font-size: 10pt;
        }
        .risk-low {
            background-color: #d4edda;
            color: #155724;
        }
        .risk-medium {
            background-color: #fff3cd;
            color: #856404;
        }
        .risk-high {
            background-color: #f8d7da;
            color: #721c24;
        }
        .risk-critical {
            background-color: #721c24;
            color: #fff;
        }
        """
    
    def _generate_html(
        self,
        template_name: str,
        sections: List[Dict[str, Any]],
        tenant_id: str,
        date_range: Dict[str, str] = None
    ) -> str:
        """Generate HTML content for the report."""
        
        date_range_str = ""
        if date_range:
            date_range_str = f"{date_range.get('start', '')} to {date_range.get('end', '')}"
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{template_name}</title>
</head>
<body>
    <div class="header">
        <h1>{template_name}</h1>
        <div class="metadata">
            <p>Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
            {f'<p>Date Range: {date_range_str}</p>' if date_range_str else ''}
            <p>Tenant ID: {tenant_id}</p>
        </div>
    </div>
"""
        
        for section in sections:
            html += f"""
    <div class="section">
        <div class="section-title">{section.get('title', 'Untitled Section')}</div>
        <div class="section-content">
            {self._render_section_content(section)}
        </div>
    </div>
"""
        
        html += f"""
    <div class="footer">
        <p>Generated by SentinelGrid Reporting Service</p>
        <p>© {datetime.now(timezone.utc).year} SentinelGrid. All rights reserved.</p>
    </div>
</body>
</html>
"""
        
        return html
    
    def _render_section_content(self, section: Dict[str, Any]) -> str:
        """Render section content based on widget type."""
        widget_type = section.get('widget', 'text')
        data = section.get('data', {})
        config = section.get('config', {}) or {}
        
        if widget_type == 'alert_table':
            return self._render_alert_table(data)
        elif widget_type == 'risk_score':
            return self._render_risk_score(data)
        elif widget_type == 'compliance_matrix':
            return self._render_compliance_matrix(data)
        elif widget_type == 'metrics_summary':
            return self._render_metrics_summary(data)
        elif widget_type == 'evidence_package_summary':
            return self._render_evidence_package_summary(data)
        elif widget_type == 'control_evidence_mapping':
            return self._render_control_evidence_mapping(data)
        elif widget_type == 'audit_readiness_overview':
            return self._render_audit_readiness_overview(data)
        elif widget_type == 'priority_criteria_table':
            return self._render_priority_criteria_table(data, config)
        elif widget_type == 'compliance_signal_table':
            return self._render_compliance_signal_table(data, config)
        elif widget_type == 'top_detection_sources_table':
            return self._render_top_detection_sources_table(data, config)
        elif widget_type == 'ai_governance_overview':
            return self._render_ai_governance_overview(data)
        elif widget_type == 'ai_governance_top_threats':
            return self._render_ai_governance_top_threats(data)
        elif widget_type == 'ai_governance_usage_trend':
            return self._render_ai_governance_usage_trend(data)
        elif widget_type == 'ai_governance_app_inventory':
            return self._render_ai_governance_app_inventory(data)
        elif widget_type == 'timeline_chart':
            return self._render_timeline_chart(data)
        elif widget_type == 'chart':
            return self._render_chart(data)
        else:
            # Default: render as text/JSON
            return f"<pre>{str(data)}</pre>"
    
    def _render_alert_table(self, data: Dict[str, Any]) -> str:
        """Render alert table."""
        alerts = data.get('items', []) or data.get('alerts', [])
        if not alerts:
            return "<p>No alerts found.</p>"
        
        html = "<table><thead><tr><th>Title</th><th>Severity</th><th>Status</th><th>Created</th></tr></thead><tbody>"
        for alert in alerts[:20]:  # Limit to 20 for PDF
            severity = alert.get('severity', 'unknown').lower()
            html += f"""
            <tr>
                <td>{alert.get('title', 'N/A')}</td>
                <td><span class="risk-badge risk-{severity}">{alert.get('severity', 'N/A')}</span></td>
                <td>{alert.get('status', 'N/A')}</td>
                <td>{alert.get('created_at', 'N/A')}</td>
            </tr>
            """
        html += "</tbody></table>"
        if len(alerts) > 20:
            html += f"<p><em>Showing first 20 of {len(alerts)} alerts</em></p>"
        return html
    
    def _render_risk_score(self, data: Dict[str, Any]) -> str:
        """Render risk score."""
        posture = data.get('posture', data.get('ai_analysis', {}).get('posture', 'Unknown'))
        risk_level = data.get('risk_level', data.get('ai_analysis', {}).get('risk_level', 'Unknown'))
        summary = data.get('summary', data.get('ai_analysis', {}).get('summary', ''))
        
        risk_class = f"risk-{risk_level.lower()}" if risk_level else "risk-medium"
        
        return f"""
        <p><strong>Security Posture:</strong> {posture}</p>
        <p><strong>Risk Level:</strong> <span class="risk-badge {risk_class}">{risk_level}</span></p>
        <p><strong>Summary:</strong> {summary}</p>
        """
    
    def _render_compliance_matrix(self, data: Dict[str, Any]) -> str:
        """Render compliance matrix."""
        status = data.get('status', 'Unknown')
        controls = data.get('controls', [])
        framework_name = data.get('framework_name') or data.get('framework_id')
        status_counts = data.get('status_counts') or {}
        
        html = ""
        if framework_name:
            html += f"<p><strong>Framework:</strong> {framework_name}</p>"
        html += f"<p><strong>Compliance Status:</strong> {status}</p>"
        if status_counts:
            status_summary = ", ".join(f"{key}: {value}" for key, value in status_counts.items())
            html += f"<p><strong>Status Counts:</strong> {status_summary}</p>"
        if controls:
            html += "<table><thead><tr><th>Control ID</th><th>Status</th><th>Open Findings</th><th>Evidence</th><th>Description</th></tr></thead><tbody>"
            for control in controls[:25]:
                description = control.get('description') or control.get('title') or 'N/A'
                html += f"""
                <tr>
                    <td>{control.get('id', 'N/A')}</td>
                    <td>{control.get('status', 'N/A')}</td>
                    <td>{control.get('open_findings', 0)}</td>
                    <td>{control.get('evidence_items', 0)}</td>
                    <td>{description}</td>
                </tr>
                """
            html += "</tbody></table>"
            if len(controls) > 25:
                html += f"<p><em>Showing first 25 of {len(controls)} controls</em></p>"
        
        return html
    
    def _render_metrics_summary(self, data: Dict[str, Any]) -> str:
        """Render metrics summary."""
        summary = data.get('summary', {})
        if isinstance(summary, dict):
            html = "<table><thead><tr><th>Metric</th><th>Value</th></tr></thead><tbody>"
            for key, value in summary.items():
                html += f"<tr><td>{key.replace('_', ' ').title()}</td><td>{value}</td></tr>"
            html += "</tbody></table>"
            return html
        return f"<p>{str(summary)}</p>"

    def _render_evidence_package_summary(self, data: Dict[str, Any]) -> str:
        """Render evidence package summary."""
        packages = data.get('packages', []) or []
        summary = data.get('summary', {}) or {}
        html = ""

        if summary:
            html += self._render_metrics_summary({"summary": summary})

        if not packages:
            return html or "<p>No evidence packages are attached to this report.</p>"

        html += "<table><thead><tr><th>Package</th><th>Framework</th><th>Status</th><th>Review</th><th>Period</th><th>Evidence</th></tr></thead><tbody>"
        for package in packages[:25]:
            period = f"{package.get('report_period_start') or 'N/A'} to {package.get('report_period_end') or 'N/A'}"
            html += f"""
            <tr>
                <td>{package.get('package_name') or package.get('id') or 'N/A'}</td>
                <td>{package.get('framework_id') or 'Any'}</td>
                <td>{package.get('status') or 'N/A'}</td>
                <td>{package.get('review_status') or 'N/A'}</td>
                <td>{period}</td>
                <td>{package.get('evidence_item_count', 0)}</td>
            </tr>
            """
        html += "</tbody></table>"
        return html

    def _render_control_evidence_mapping(self, data: Dict[str, Any]) -> str:
        """Render control to evidence mapping."""
        rows = data.get('rows', []) or []
        summary = data.get('summary', {}) or {}

        html = ""
        if summary:
            html += self._render_metrics_summary({"summary": summary})

        if not rows:
            return html or "<p>No control/evidence mappings are available for this report.</p>"

        html += "<table><thead><tr><th>Framework</th><th>Control</th><th>Coverage</th><th>Evidence</th><th>Review</th><th>Package</th></tr></thead><tbody>"
        for row in rows[:50]:
            evidence_label = row.get('evidence_title') or row.get('evidence_item_id') or 'Missing evidence'
            package_label = row.get('package_name') or row.get('package_id') or 'N/A'
            html += f"""
            <tr>
                <td>{row.get('framework_name') or row.get('framework_id') or 'N/A'}</td>
                <td><strong>{row.get('control_id') or 'N/A'}</strong><br>{row.get('control_title') or ''}</td>
                <td>{row.get('coverage_status') or 'N/A'}</td>
                <td>{evidence_label}</td>
                <td>{row.get('review_status') or 'N/A'}</td>
                <td>{package_label}</td>
            </tr>
            """
        html += "</tbody></table>"
        if len(rows) > 50:
            html += f"<p><em>Showing first 50 of {len(rows)} mappings</em></p>"
        return html

    def _render_audit_readiness_overview(self, data: Dict[str, Any]) -> str:
        """Render SMB-friendly audit readiness summary."""
        overall_stats = data.get('overall_stats', {})
        reporting_summary = data.get('reporting_summary', {})
        criteria_ready = reporting_summary.get('criteria_ready', 0)
        criteria_partial = reporting_summary.get('criteria_partial', 0)
        criteria_attention = reporting_summary.get('criteria_needing_attention', 0)
        mapped_detections = overall_stats.get('mapped_detections', reporting_summary.get('key_detection_count', 0))
        control_checks = overall_stats.get('control_checks', reporting_summary.get('control_check_count', 0))
        evidence_items = overall_stats.get('evidence_items', reporting_summary.get('reportable_evidence_items', 0))
        overall_score = overall_stats.get('overall_score', 0)

        return f"""
        <p>
            This export summarizes the detections, control checks, and evidence objects SentinelGrid can use in an SMB audit
            or customer trust conversation today.
        </p>
        <table>
            <thead>
                <tr><th>Metric</th><th>Value</th><th>Why It Matters</th></tr>
            </thead>
            <tbody>
                <tr><td>Audit Readiness Score</td><td>{overall_score}</td><td>Overall trust and reporting readiness.</td></tr>
                <tr><td>Criteria Ready</td><td>{criteria_ready}</td><td>Controls ready to discuss with auditors or customers.</td></tr>
                <tr><td>Criteria Partial</td><td>{criteria_partial}</td><td>Controls with evidence but still open work.</td></tr>
                <tr><td>Criteria Needing Attention</td><td>{criteria_attention}</td><td>Controls most likely to trigger follow-up questions.</td></tr>
                <tr><td>Mapped Detections</td><td>{mapped_detections}</td><td>Live security signals supporting the control story.</td></tr>
                <tr><td>Control Checks</td><td>{control_checks}</td><td>Configuration and identity checks feeding evidence.</td></tr>
                <tr><td>Evidence Items</td><td>{evidence_items}</td><td>Objects that can be attached to an audit packet.</td></tr>
            </tbody>
        </table>
        """

    def _render_priority_criteria_table(self, data: Dict[str, Any], config: Dict[str, Any]) -> str:
        """Render criteria-focused control table."""
        source_field = config.get('source_field', 'priority_criteria')
        limit = int(config.get('limit', 10) or 10)
        controls = data.get(source_field, data.get('controls', [])) or []

        if not controls:
            return "<p>No criteria are available for this export yet.</p>"

        html = "<table><thead><tr><th>Criterion</th><th>Status</th><th>Open Findings</th><th>Detections</th><th>Checks</th><th>Evidence</th></tr></thead><tbody>"
        for control in controls[:limit]:
            html += f"""
            <tr>
                <td><strong>{control.get('id', 'N/A')}</strong><br>{control.get('title', '')}</td>
                <td>{control.get('status', 'N/A')}</td>
                <td>{control.get('open_findings', 0)}</td>
                <td>{control.get('detection_count', 0)}</td>
                <td>{control.get('control_check_count', 0)}</td>
                <td>{control.get('evidence_items', 0)}</td>
            </tr>
            """
        html += "</tbody></table>"
        return html

    def _render_compliance_signal_table(self, data: Dict[str, Any], config: Dict[str, Any]) -> str:
        """Render mapped detections or control checks for audit exports."""
        signal_type = config.get('signal_type', 'key_detections')
        limit = int(config.get('limit', 12) or 12)
        signals = data.get(signal_type, [])

        if not signals:
            return "<p>No mapped signals are available for this section yet.</p>"

        html = "<table><thead><tr><th>Signal</th><th>Severity</th><th>Status</th><th>Source</th><th>Control</th><th>Observed</th></tr></thead><tbody>"
        for item in signals[:limit]:
            html += f"""
            <tr>
                <td><strong>{item.get('title', 'N/A')}</strong><br>{item.get('description', '') or ''}</td>
                <td>{item.get('severity', 'N/A')}</td>
                <td>{item.get('status', 'N/A')}</td>
                <td>{item.get('source_label') or item.get('source') or 'Signal'}</td>
                <td>{item.get('nist_control_id') or '—'}</td>
                <td>{item.get('detected_at') or '—'}</td>
            </tr>
            """
        html += "</tbody></table>"
        return html

    def _render_top_detection_sources_table(self, data: Dict[str, Any], config: Dict[str, Any]) -> str:
        """Render top detection-source coverage for trust review exports."""
        limit = int(config.get('limit', 8) or 8)
        reporting_summary = data.get('reporting_summary', {})
        items = reporting_summary.get('top_detection_sources', [])

        if not items:
            return "<p>No detection-source summary is available yet.</p>"

        html = "<table><thead><tr><th>Detection Source</th><th>Mapped Signals</th></tr></thead><tbody>"
        for item in items[:limit]:
            html += f"""
            <tr>
                <td>{item.get('source', 'Unknown')}</td>
                <td>{item.get('count', 0)}</td>
            </tr>
            """
        html += "</tbody></table>"
        return html

    def _render_ai_governance_overview(self, data: Dict[str, Any]) -> str:
        """Render leadership-friendly AI governance overview."""
        overview = data.get('overview', {}) or {}
        return f"""
        <p>
            This leadership summary converts SentinelGrid AI activity, AI Shield alerts, and active AI incidents into one governance view.
        </p>
        <table>
            <thead>
                <tr><th>Metric</th><th>Value</th><th>Why It Matters</th></tr>
            </thead>
            <tbody>
                <tr><td>Governance Score</td><td>{overview.get('governance_score', 0)}</td><td>Overall AI control and policy health.</td></tr>
                <tr><td>Active AI Apps</td><td>{overview.get('active_apps', 0)}</td><td>Observed apps or AI workflows used in the reporting window.</td></tr>
                <tr><td>Active AI Users</td><td>{overview.get('active_users', 0)}</td><td>People interacting with monitored AI workflows.</td></tr>
                <tr><td>Requests in Window</td><td>{overview.get('requests_in_window', 0)}</td><td>Total monitored AI interactions across the reporting window.</td></tr>
                <tr><td>Open AI Alerts</td><td>{overview.get('open_ai_alerts', 0)}</td><td>Live AI findings still waiting for follow-through.</td></tr>
                <tr><td>Active AI Incidents</td><td>{overview.get('active_ai_incidents', 0)}</td><td>Escalated AI cases requiring operator or leadership attention.</td></tr>
                <tr><td>Apps Needing Review</td><td>{overview.get('apps_needing_review', 0)}</td><td>Apps with elevated risk, open alerts, or active incidents.</td></tr>
                <tr><td>Unclassified Apps</td><td>{overview.get('unclassified_apps', 0)}</td><td>AI usage without clear governance ownership or approval state.</td></tr>
            </tbody>
        </table>
        """

    def _render_ai_governance_top_threats(self, data: Dict[str, Any]) -> str:
        """Render AI threat pressure summary."""
        threats = data.get('top_threats', []) or []
        top_risk = data.get('top_risk') or {}

        if not threats:
            return "<p>No AI threat pressure is currently active.</p>"

        html = "<table><thead><tr><th>Threat</th><th>Count</th><th>Trend</th></tr></thead><tbody>"
        for item in threats:
            html += f"""
            <tr>
                <td>{item.get('type', 'Unknown')}</td>
                <td>{item.get('count', 0)}</td>
                <td>{item.get('trend', 'flat')}</td>
            </tr>
            """
        html += "</tbody></table>"

        if top_risk:
            html += f"""
            <p><strong>Top AI case:</strong> {top_risk.get('title', 'N/A')} ({top_risk.get('severity', 'unknown')})</p>
            <p>{top_risk.get('summary', '')}</p>
            """

        return html

    def _render_ai_governance_usage_trend(self, data: Dict[str, Any]) -> str:
        """Render AI usage trend table."""
        items = data.get('usage_trend', []) or []
        if not items:
            return "<p>No AI usage trend is available yet.</p>"

        html = "<table><thead><tr><th>Period</th><th>Requests</th><th>Users</th><th>Policy Hits</th></tr></thead><tbody>"
        for item in items:
            html += f"""
            <tr>
                <td>{item.get('label', 'N/A')}</td>
                <td>{item.get('requests', 0)}</td>
                <td>{item.get('unique_users', 0)}</td>
                <td>{item.get('policy_hits', 0)}</td>
            </tr>
            """
        html += "</tbody></table>"
        return html

    def _render_ai_governance_app_inventory(self, data: Dict[str, Any]) -> str:
        """Render app-level governance inventory."""
        items = data.get('app_inventory', []) or []
        if not items:
            return "<p>No AI apps or workflows were observed in this reporting window.</p>"

        html = "<table><thead><tr><th>Application</th><th>State</th><th>Requests</th><th>Users</th><th>Alerts</th><th>Incidents</th><th>Risk</th></tr></thead><tbody>"
        for item in items[:12]:
            html += f"""
            <tr>
                <td><strong>{item.get('label', 'N/A')}</strong><br>{', '.join(item.get('models', [])[:2]) or 'No model metadata'}</td>
                <td>{item.get('governance_state', 'monitored')}</td>
                <td>{item.get('requests_in_window', 0)}</td>
                <td>{item.get('unique_users', 0)}</td>
                <td>{item.get('open_alerts', 0)}</td>
                <td>{item.get('active_incidents', 0)}</td>
                <td>{item.get('highest_severity', 'low')}</td>
            </tr>
            """
        html += "</tbody></table>"
        return html
    
    def _render_timeline_chart(self, data: Dict[str, Any]) -> str:
        """Render timeline chart."""
        timeline = data.get('activity_timeline', []) or data.get('timeline', [])
        if not timeline:
            return "<p>No timeline data available.</p>"
        
        if MATPLOTLIB_AVAILABLE:
            try:
                # Generate chart image
                chart_base64 = self._generate_timeline_chart_image(timeline)
                return f'<img src="data:image/png;base64,{chart_base64}" style="max-width: 100%; height: auto;" />'
            except Exception as e:
                logger.warning(f"Failed to generate timeline chart: {e}")
        
        # Fallback: render as table
        html = "<table><thead><tr><th>Date</th><th>Events</th><th>Alerts</th></tr></thead><tbody>"
        for item in timeline:
            html += f"""
            <tr>
                <td>{item.get('date', 'N/A')}</td>
                <td>{item.get('events', 0)}</td>
                <td>{item.get('alerts', 0)}</td>
            </tr>
            """
        html += "</tbody></table>"
        return html
    
    def _render_chart(self, data: Dict[str, Any]) -> str:
        """Render generic chart."""
        chart_type = data.get('type', 'line')
        chart_data = data.get('data', {})
        
        if MATPLOTLIB_AVAILABLE and chart_data:
            try:
                chart_base64 = self._generate_chart_image(chart_type, chart_data)
                return f'<img src="data:image/png;base64,{chart_base64}" style="max-width: 100%; height: auto;" />'
            except Exception as e:
                logger.warning(f"Failed to generate chart: {e}")
        
        return f"<p>Chart data: {str(chart_data)}</p>"
    
    def _generate_timeline_chart_image(self, timeline: List[Dict[str, Any]]) -> str:
        """Generate timeline chart as base64 image."""
        if not MATPLOTLIB_AVAILABLE:
            return ""
        
        dates = [item.get('date', '') for item in timeline]
        events = [item.get('events', 0) for item in timeline]
        alerts = [item.get('alerts', 0) for item in timeline]
        
        plt.figure(figsize=(10, 4))
        plt.plot(dates, events, marker='o', label='Events', linewidth=2)
        plt.plot(dates, alerts, marker='s', label='Alerts', linewidth=2)
        plt.xlabel('Date')
        plt.ylabel('Count')
        plt.title('Activity Timeline')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        # Convert to base64
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        plt.close()
        
        return image_base64
    
    def _generate_chart_image(self, chart_type: str, data: Dict[str, Any]) -> str:
        """Generate chart image based on type."""
        if not MATPLOTLIB_AVAILABLE:
            return ""
        
        labels = data.get('labels', [])
        values = data.get('values', [])
        
        plt.figure(figsize=(8, 5))
        
        if chart_type == 'bar':
            plt.bar(labels, values)
        elif chart_type == 'pie':
            plt.pie(values, labels=labels, autopct='%1.1f%%')
        else:  # line
            plt.plot(labels, values, marker='o')
        
        plt.title(data.get('title', 'Chart'))
        plt.tight_layout()
        
        # Convert to base64
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        plt.close()
        
        return image_base64
