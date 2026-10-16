"""CSV report generator service."""

import logging
import csv
from typing import Dict, Any, List
from pathlib import Path
from datetime import datetime, timezone
from app.core.config import settings

logger = logging.getLogger(__name__)


class CSVGenerator:
    """Generate CSV reports from template data."""
    
    def __init__(self):
        self.storage_path = Path(settings.REPORT_STORAGE_PATH)
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    def generate(
        self,
        report_id: str,
        template_name: str,
        sections: List[Dict[str, Any]],
        tenant_id: str,
        date_range: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """
        Generate a CSV report.
        
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
            file_path = tenant_path / f"{report_id}.csv"
            
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # Write header
                writer.writerow([template_name])
                writer.writerow([f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"])
                writer.writerow([f"Tenant ID: {tenant_id}"])
                if date_range:
                    writer.writerow([f"Date Range: {date_range.get('start', '')} to {date_range.get('end', '')}"])
                writer.writerow([])  # Empty row
                
                # Write sections
                for section in sections:
                    writer.writerow([section.get('title', 'Untitled Section')])
                    writer.writerow([])  # Empty row
                    
                    # Write section data based on widget type
                    self._write_section_data(writer, section)
                    writer.writerow([])  # Empty row between sections
            
            file_size = file_path.stat().st_size
            download_url = f"{settings.REPORT_STORAGE_URL}/{tenant_id}/{report_id}.csv"
            
            logger.info(f"Generated CSV report {report_id} at {file_path}")
            
            return {
                "file_path": str(file_path),
                "file_size_bytes": file_size,
                "download_url": download_url
            }
        
        except Exception as e:
            logger.error(f"Failed to generate CSV report {report_id}: {e}", exc_info=True)
            raise
    
    def _write_section_data(self, writer: csv.writer, section: Dict[str, Any]):
        """Write section data to CSV."""
        widget_type = section.get('widget', 'text')
        data = section.get('data', {})
        config = section.get('config', {}) or {}
        
        if widget_type == 'alert_table':
            alerts = data.get('items', [])
            if alerts:
                # Write headers
                writer.writerow(['Title', 'Severity', 'Status', 'Created At', 'Description'])
                # Write rows
                for alert in alerts:
                    writer.writerow([
                        alert.get('title', ''),
                        alert.get('severity', ''),
                        alert.get('status', ''),
                        alert.get('created_at', ''),
                        alert.get('description', '')[:100]  # Truncate description
                    ])
        elif widget_type == 'risk_score':
            writer.writerow(['Security Posture', data.get('posture', 'Unknown')])
            writer.writerow(['Risk Level', data.get('risk_level', 'Unknown')])
            writer.writerow(['Summary', data.get('summary', '')])
        elif widget_type == 'compliance_matrix':
            writer.writerow(['Framework', data.get('framework_name') or data.get('framework_id') or ''])
            writer.writerow(['Status', data.get('status', 'Unknown')])
            writer.writerow([])
            writer.writerow(['Control ID', 'Title', 'Status', 'Open Findings', 'Evidence Items', 'Description'])
            for control in data.get('controls', []) or []:
                writer.writerow([
                    control.get('id', ''),
                    control.get('title', ''),
                    control.get('status', ''),
                    control.get('open_findings', 0),
                    control.get('evidence_items', 0),
                    control.get('description', ''),
                ])
        elif widget_type == 'evidence_package_summary':
            summary = data.get('summary', {}) or {}
            if summary:
                writer.writerow(['Metric', 'Value'])
                for key, value in summary.items():
                    writer.writerow([key, value])
                writer.writerow([])
            writer.writerow(['Package ID', 'Package Name', 'Framework', 'Status', 'Review Status', 'Period Start', 'Period End', 'Evidence Items', 'Export Format'])
            for package in data.get('packages', []) or []:
                writer.writerow([
                    package.get('id', ''),
                    package.get('package_name', ''),
                    package.get('framework_id', ''),
                    package.get('status', ''),
                    package.get('review_status', ''),
                    package.get('report_period_start', ''),
                    package.get('report_period_end', ''),
                    package.get('evidence_item_count', 0),
                    package.get('export_format', ''),
                ])
        elif widget_type == 'control_evidence_mapping':
            summary = data.get('summary', {}) or {}
            if summary:
                writer.writerow(['Metric', 'Value'])
                for key, value in summary.items():
                    writer.writerow([key, value])
                writer.writerow([])
            writer.writerow([
                'Framework ID',
                'Framework Name',
                'Control ID',
                'Control Title',
                'Coverage Status',
                'Gap Count',
                'Evidence Item ID',
                'Evidence Title',
                'Evidence Type',
                'Review Status',
                'Valid Until',
                'Package ID',
                'Package Name',
                'Source System',
            ])
            for row in data.get('rows', []) or []:
                writer.writerow([
                    row.get('framework_id', ''),
                    row.get('framework_name', ''),
                    row.get('control_id', ''),
                    row.get('control_title', ''),
                    row.get('coverage_status', ''),
                    row.get('gap_count', ''),
                    row.get('evidence_item_id', ''),
                    row.get('evidence_title', ''),
                    row.get('evidence_type', ''),
                    row.get('review_status', ''),
                    row.get('valid_until', ''),
                    row.get('package_id', ''),
                    row.get('package_name', ''),
                    row.get('source_system', ''),
                ])
        elif widget_type == 'audit_readiness_overview':
            overall_stats = data.get('overall_stats', {})
            reporting_summary = data.get('reporting_summary', {})
            rows = [
                ['Audit Readiness Score', overall_stats.get('overall_score', 0)],
                ['Criteria Ready', reporting_summary.get('criteria_ready', 0)],
                ['Criteria Partial', reporting_summary.get('criteria_partial', 0)],
                ['Criteria Needing Attention', reporting_summary.get('criteria_needing_attention', 0)],
                ['Mapped Detections', overall_stats.get('mapped_detections', reporting_summary.get('key_detection_count', 0))],
                ['Control Checks', overall_stats.get('control_checks', reporting_summary.get('control_check_count', 0))],
                ['Evidence Items', overall_stats.get('evidence_items', reporting_summary.get('reportable_evidence_items', 0))],
            ]
            writer.writerow(['Metric', 'Value'])
            writer.writerows(rows)
        elif widget_type == 'priority_criteria_table':
            source_field = config.get('source_field', 'priority_criteria')
            limit = int(config.get('limit', 10) or 10)
            controls = data.get(source_field, data.get('controls', [])) or []
            writer.writerow(['Criterion', 'Title', 'Status', 'Open Findings', 'Detections', 'Control Checks', 'Evidence Items'])
            for control in controls[:limit]:
                writer.writerow([
                    control.get('id', ''),
                    control.get('title', ''),
                    control.get('status', ''),
                    control.get('open_findings', 0),
                    control.get('detection_count', 0),
                    control.get('control_check_count', 0),
                    control.get('evidence_items', 0),
                ])
        elif widget_type == 'compliance_signal_table':
            signal_type = config.get('signal_type', 'key_detections')
            limit = int(config.get('limit', 12) or 12)
            signals = data.get(signal_type, []) or []
            writer.writerow(['Signal', 'Description', 'Severity', 'Status', 'Source', 'NIST Control', 'Detected At'])
            for item in signals[:limit]:
                writer.writerow([
                    item.get('title', ''),
                    item.get('description', ''),
                    item.get('severity', ''),
                    item.get('status', ''),
                    item.get('source_label') or item.get('source', ''),
                    item.get('nist_control_id', ''),
                    item.get('detected_at', ''),
                ])
        elif widget_type == 'top_detection_sources_table':
            limit = int(config.get('limit', 8) or 8)
            items = data.get('reporting_summary', {}).get('top_detection_sources', []) or []
            writer.writerow(['Detection Source', 'Mapped Signals'])
            for item in items[:limit]:
                writer.writerow([item.get('source', ''), item.get('count', 0)])
        elif widget_type == 'ai_governance_overview':
            overview = data.get('overview', {}) or {}
            writer.writerow(['Metric', 'Value'])
            writer.writerows(
                [
                    ['Governance Score', overview.get('governance_score', 0)],
                    ['Active AI Apps', overview.get('active_apps', 0)],
                    ['Active AI Users', overview.get('active_users', 0)],
                    ['Requests in Window', overview.get('requests_in_window', 0)],
                    ['Open AI Alerts', overview.get('open_ai_alerts', 0)],
                    ['Active AI Incidents', overview.get('active_ai_incidents', 0)],
                    ['Policy Violations', overview.get('policy_violations', 0)],
                    ['Prompt Injection Events', overview.get('prompt_injection_events', 0)],
                    ['Sensitive Data Events', overview.get('sensitive_data_events', 0)],
                    ['Apps Needing Review', overview.get('apps_needing_review', 0)],
                    ['Unclassified Apps', overview.get('unclassified_apps', 0)],
                ]
            )
        elif widget_type == 'ai_governance_top_threats':
            writer.writerow(['Threat', 'Count', 'Trend'])
            for item in data.get('top_threats', []) or []:
                writer.writerow([item.get('type', ''), item.get('count', 0), item.get('trend', 'flat')])
        elif widget_type == 'ai_governance_usage_trend':
            writer.writerow(['Period', 'Requests', 'Unique Users', 'Policy Hits'])
            for item in data.get('usage_trend', []) or []:
                writer.writerow([
                    item.get('label', ''),
                    item.get('requests', 0),
                    item.get('unique_users', 0),
                    item.get('policy_hits', 0),
                ])
        elif widget_type == 'ai_governance_app_inventory':
            writer.writerow(['Application', 'Governance State', 'Requests', 'Users', 'Open Alerts', 'Active Incidents', 'Risk', 'Models'])
            for item in (data.get('app_inventory', []) or [])[:12]:
                writer.writerow([
                    item.get('label', ''),
                    item.get('governance_state', 'monitored'),
                    item.get('requests_in_window', 0),
                    item.get('unique_users', 0),
                    item.get('open_alerts', 0),
                    item.get('active_incidents', 0),
                    item.get('highest_severity', 'low'),
                    '; '.join(item.get('models', []) or []),
                ])
        else:
            # Default: write as key-value pairs
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    writer.writerow([key, str(value)])
                else:
                    writer.writerow([key, value])
