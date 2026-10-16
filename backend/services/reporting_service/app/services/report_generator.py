"""Report generation service - orchestrates data fetching and report generation."""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from uuid import UUID
import httpx
from sqlalchemy.orm import Session
from app.models.report import Report, ReportTemplate, ReportStatus, ReportFormat
from app.models.template import TemplateSection, DataQuery
from app.services.pdf_generator import PDFGenerator
from app.services.csv_generator import CSVGenerator
from app.core.config import settings
from app.services.audit_client import AuditClient
from app.services.vector_client import VectorClient
from app.services.compliance_report_data import ComplianceReportDataProvider
from app.services.observability import record_report_generation

logger = logging.getLogger(__name__)


class ReportGeneratorService:
    """Service for generating reports from templates."""
    
    def __init__(self):
        self.pdf_generator = PDFGenerator()
        self.csv_generator = CSVGenerator()
        self.internal_token = settings.INTERNAL_SERVICE_TOKEN
        self.audit_client = AuditClient()
        self.vector_client = VectorClient()
        self.compliance_data_provider = ComplianceReportDataProvider()
    
    async def generate_report(
        self,
        db: Session,
        report: Report,
        template: ReportTemplate,
        tenant_id: str,
        realm_name: str = "unknown",
        date_range: Optional[Dict[str, str]] = None,
        sections_filter: Optional[List[str]] = None,
        report_parameters: Optional[Dict[str, Any]] = None,
    ) -> Report:
        """
        Generate a report from a template.
        
        Args:
            db: Database session
            report: Report record
            template: Report template
            tenant_id: Tenant ID
            date_range: Optional date range
            sections_filter: Optional list of section titles to include
            
        Returns:
            Updated report record
        """
        try:
            # Update status
            report.status = ReportStatus.GENERATING
            db.commit()
            
            # Fetch data for each section
            sections_data = []
            template_sections = template.sections if isinstance(template.sections, list) else []
            report_parameters = report_parameters or {}
            compliance_snapshot = None

            if self._should_attach_compliance_snapshot(template, report_parameters):
                compliance_snapshot = await self.compliance_data_provider.build_snapshot(
                    tenant_id=tenant_id,
                    date_range=date_range,
                    report_parameters=report_parameters,
                )
                sections_data.append(
                    {
                        "title": "Evidence Basis",
                        "widget": "metrics_summary",
                        "data": {"summary": compliance_snapshot.get("evidence_summary", {})},
                        "config": {
                            "source": "durable_evidence_repository",
                            "snapshot_hash_sha256": compliance_snapshot.get("snapshot_hash_sha256"),
                        },
                    }
                )
                dynamic_sections = self._build_compliance_snapshot_sections(
                    compliance_snapshot,
                    template_sections,
                )
                sections_data.extend(dynamic_sections)
                self._persist_compliance_snapshot_metadata(db, report, compliance_snapshot, report_parameters)
            
            for section_config in template_sections:
                # Skip if filtered
                if sections_filter and section_config.get('title') not in sections_filter:
                    continue
                
                section_data = self._section_data_from_compliance_snapshot(section_config, compliance_snapshot)
                if section_data is None:
                    section_data = await self._fetch_section_data(
                        section_config,
                        tenant_id,
                        date_range,
                        report_parameters,
                    )
                
                sections_data.append({
                    'title': section_config.get('title', 'Untitled'),
                    'widget': section_config.get('widget', 'text'),
                    'data': section_data,
                    'config': section_config.get('config', {}) or {},
                })
            
            # Generate report based on format
            if report.format == ReportFormat.PDF:
                result = self.pdf_generator.generate(
                    report.id,
                    template.name,
                    sections_data,
                    tenant_id,
                    date_range
                )
            elif report.format == ReportFormat.CSV:
                result = self.csv_generator.generate(
                    report.id,
                    template.name,
                    sections_data,
                    tenant_id,
                    date_range
                )
            else:
                raise ValueError(f"Unsupported report format: {report.format}")
            
            # Update report with results
            report.status = ReportStatus.COMPLETED
            report.file_path = result['file_path']
            report.file_size_bytes = result['file_size_bytes']
            report.download_url = result['download_url']
            report.generated_at = datetime.now(timezone.utc)
            report.sections = [s['title'] for s in sections_data]
            if compliance_snapshot:
                self._persist_compliance_snapshot_metadata(db, report, compliance_snapshot, report_parameters, commit=False)
            
            db.commit()
            logger.info(f"Successfully generated report {report.id}")
            self._record_generation_metric("success", report=report, template=template)

            # Audit success
            try:
                await self.audit_client.log_event({
                    "tenant_id": tenant_id,
                    "realm_name": realm_name,
                    "action": "report_generated",
                    "action_category": "compliance",
                    "actor_user_id": getattr(report, "generated_by", None) or "system",
                    "resource_type": "report",
                    "resource_id": report.id,
                    "resource_name": report.name,
                    "success": True,
                    "metadata": {
                        "template_id": template.id,
                        "template_name": template.name,
                        "format": report.format.value if hasattr(report, "format") else str(report.format),
                        "sections": report.sections,
                        "date_range": date_range,
                        "download_url": report.download_url,
                        "compliance_snapshot_hash_sha256": (
                            compliance_snapshot or {}
                        ).get("snapshot_hash_sha256"),
                        "evidence_package_ids": (
                            (compliance_snapshot or {}).get("evidence_summary") or {}
                        ).get("evidence_package_ids", []),
                    }
                })
            except Exception as audit_err:
                logger.warning(f"Failed to audit report generation {report.id}: {audit_err}")

            # Vectorize report for tenant-scoped RAG (so chatbot can answer on reports)
            try:
                await self.vector_client.index_report(
                    tenant_id=tenant_id,
                    realm_name=realm_name,
                    report_id=report.id,
                    template_id=template.id,
                    template_name=template.name,
                    file_path=report.file_path,
                    sections=sections_data
                )
            except Exception as vec_err:
                logger.warning(f"Failed to vectorize report {report.id}: {vec_err}")
            
            return report
        
        except Exception as e:
            logger.error(f"Failed to generate report {report.id}: {e}", exc_info=True)
            report.status = ReportStatus.FAILED
            report.error_message = str(e)
            db.commit()
            self._record_generation_metric("failed", report=report, template=template)
            try:
                await self.audit_client.log_event({
                    "tenant_id": tenant_id,
                    "realm_name": realm_name,
                    "action": "report_generation_failed",
                    "action_category": "compliance",
                    "actor_user_id": getattr(report, "generated_by", None) or "system",
                    "resource_type": "report",
                    "resource_id": report.id,
                    "resource_name": report.name,
                    "success": False,
                    "error_message": str(e),
                    "metadata": {
                        "template_id": template.id,
                        "template_name": template.name,
                        "format": getattr(report, 'format', None),
                    }
                })
            except Exception as audit_err:
                logger.warning(f"Failed to audit report failure {report.id}: {audit_err}")
            raise

    def _record_generation_metric(
        self,
        outcome: str,
        *,
        report: Report,
        template: ReportTemplate,
    ) -> None:
        """Record operational report-generation metrics without changing generation flow."""
        try:
            report_format = getattr(getattr(report, "format", None), "value", None) or getattr(report, "format", None)
            record_report_generation(
                outcome=outcome,
                report_format=str(report_format).lower() if report_format else None,
                template_type=getattr(template, "type", None),
            )
        except Exception as metric_err:  # pragma: no cover - metrics must not block reports.
            logger.warning(f"Failed to record report generation metric for {getattr(report, 'id', None)}: {metric_err}")
    
    async def _fetch_section_data(
        self,
        section_config: Dict[str, Any],
        tenant_id: str,
        date_range: Optional[Dict[str, str]] = None,
        report_parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Fetch data for a report section.
        
        Args:
            section_config: Section configuration from template
            tenant_id: Tenant ID
            date_range: Optional date range
            
        Returns:
            Section data dictionary
        """
        data_source = section_config.get('data_source', '')
        
        if not data_source:
            return {}

        if data_source == "internal://ai-governance/summary":
            from app.services.ai_governance_reporting import AiGovernanceReportingService

            lookback_days = int((section_config.get("config") or {}).get("lookback_days", 30) or 30)
            service = AiGovernanceReportingService()
            return await service.build_summary(tenant_id, lookback_days=lookback_days)
        
        # Replace template variables
        data_source = data_source.replace('{tenant_id}', tenant_id)
        
        # Determine which service to call
        if '/orchestrator/' in data_source:
            base_url = settings.ORCHESTRATOR_URL
            endpoint = data_source.replace('/api/v1/orchestrator', '')
        elif '/siem/' in data_source or '/alerts' in data_source:
            base_url = settings.SIEM_AGENT_URL
            endpoint = data_source.replace('/api/v1', '')
        elif '/iam/' in data_source:
            base_url = settings.IAM_AGENT_URL
            endpoint = data_source.replace('/api/v1', '')
        elif '/compliance/' in data_source:
            base_url = settings.COMPLIANCE_SERVICE_URL
            endpoint = data_source.replace('/api/v1', '')
        else:
            # Default to API Gateway
            base_url = "http://api_gateway:8000"
            endpoint = data_source
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {
                    "Authorization": f"Bearer {self.internal_token}",
                    "X-Tenant-ID": tenant_id
                }
                
                # Add date range to params if provided
                params = {}
                if date_range:
                    params.update(date_range)
                if report_parameters and "/compliance/" in data_source:
                    for key in (
                        "framework_ids",
                        "control_ids",
                        "evidence_package_ids",
                        "include_gaps",
                        "include_expired_evidence",
                    ):
                        value = report_parameters.get(key)
                        if value not in (None, "", []):
                            params[key] = value
                
                response = await client.get(
                    f"{base_url}{endpoint}",
                    headers=headers,
                    params=params
                )
                response.raise_for_status()
                return response.json()
        
        except httpx.RequestError as e:
            logger.error(f"Failed to fetch data from {data_source}: {e}")
            return {"error": f"Failed to fetch data: {str(e)}"}
        except Exception as e:
            logger.error(f"Error fetching section data: {e}")
            return {"error": str(e)}

    def _build_compliance_snapshot_sections(
        self,
        compliance_snapshot: Dict[str, Any],
        template_sections: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Build reproducible compliance sections from the captured snapshot."""
        existing_titles = {
            str(section.get("title") or "").strip().lower()
            for section in template_sections
            if isinstance(section, dict)
        }
        dynamic_sections: List[Dict[str, Any]] = []

        for coverage in compliance_snapshot.get("coverage_snapshots") or []:
            if not isinstance(coverage, dict) or coverage.get("error"):
                continue
            section_data = self._framework_coverage_section_data(coverage)
            framework_name = section_data.get("framework_name") or section_data.get("framework_id") or "Framework"
            title = f"{framework_name} Coverage Snapshot"
            if title.strip().lower() in existing_titles:
                continue
            dynamic_sections.append(
                {
                    "title": title,
                    "widget": "compliance_matrix",
                    "data": section_data,
                    "config": {
                        "source": "compliance_snapshot",
                        "snapshot_hash_sha256": compliance_snapshot.get("snapshot_hash_sha256"),
                    },
                }
            )

        if "control evidence mapping" not in existing_titles:
            dynamic_sections.append(
                {
                    "title": "Control Evidence Mapping",
                    "widget": "control_evidence_mapping",
                    "data": self._control_evidence_mapping_data(compliance_snapshot),
                    "config": {
                        "source": "compliance_snapshot",
                        "snapshot_hash_sha256": compliance_snapshot.get("snapshot_hash_sha256"),
                    },
                }
            )

        return dynamic_sections

    def _section_data_from_compliance_snapshot(
        self,
        section_config: Dict[str, Any],
        compliance_snapshot: Optional[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """Return section data for widgets backed by the report snapshot."""
        if not compliance_snapshot:
            return None

        widget = section_config.get("widget")
        if widget == "control_evidence_mapping":
            return self._control_evidence_mapping_data(compliance_snapshot)
        if widget == "evidence_package_summary":
            return self._evidence_package_summary_data(compliance_snapshot)
        return None

    def _framework_coverage_section_data(self, coverage: Dict[str, Any]) -> Dict[str, Any]:
        controls = []
        for control in coverage.get("controls") or []:
            if not isinstance(control, dict):
                continue
            gaps = control.get("gaps") or control.get("coverage_gaps") or []
            evidence_requirements = control.get("evidence_requirements") or []
            evidence_count = control.get("evidence_items")
            if evidence_count is None:
                evidence_count = sum(
                    1
                    for requirement in evidence_requirements
                    if isinstance(requirement, dict)
                    and requirement.get("status") not in {"missing", "not_started", "needs_evidence"}
                )
            controls.append(
                {
                    "id": control.get("control_id") or control.get("id") or "unknown",
                    "title": control.get("title") or control.get("control_name") or "",
                    "description": control.get("description") or control.get("summary") or "",
                    "status": control.get("status") or control.get("coverage_status") or "not_assessed",
                    "open_findings": control.get("open_findings", len(gaps)),
                    "evidence_items": evidence_count or 0,
                    "coverage_confidence": control.get("confidence") or control.get("coverage_confidence"),
                    "gap_count": len(gaps),
                }
            )

        return {
            "framework_id": coverage.get("framework_code") or coverage.get("framework_id"),
            "framework_name": coverage.get("framework_name") or coverage.get("framework_code") or coverage.get("framework_id"),
            "runtime_support": coverage.get("runtime_support"),
            "selection_status": coverage.get("selection_status"),
            "status": coverage.get("status", "Unknown"),
            "status_counts": coverage.get("status_counts") or {},
            "average_confidence": coverage.get("average_confidence"),
            "control_count": coverage.get("control_count") or len(controls),
            "controls": controls,
        }

    def _evidence_package_summary_data(self, compliance_snapshot: Dict[str, Any]) -> Dict[str, Any]:
        packages = []
        for package in compliance_snapshot.get("evidence_packages") or []:
            if not isinstance(package, dict) or package.get("error"):
                continue
            packages.append(
                {
                    "id": package.get("id"),
                    "package_name": package.get("package_name") or package.get("name") or package.get("id"),
                    "framework_id": package.get("framework_id"),
                    "status": package.get("status"),
                    "review_status": package.get("review_status"),
                    "report_period_start": package.get("report_period_start"),
                    "report_period_end": package.get("report_period_end"),
                    "evidence_item_count": package.get("evidence_item_count") or len(package.get("items") or []),
                    "export_format": package.get("export_format"),
                }
            )
        return {
            "packages": packages,
            "summary": compliance_snapshot.get("evidence_summary") or {},
            "source": "durable_evidence_repository",
        }

    def _control_evidence_mapping_data(self, compliance_snapshot: Dict[str, Any]) -> Dict[str, Any]:
        controls = self._snapshot_controls(compliance_snapshot)
        evidence_items = self._snapshot_evidence_items(compliance_snapshot)
        rows: List[Dict[str, Any]] = []
        mapped_control_keys: set[str] = set()

        for item in evidence_items:
            refs = self._evidence_control_refs(item)
            if not refs:
                rows.append(self._control_evidence_row(None, item, {}))
                continue

            for ref in refs:
                control = self._find_snapshot_control(controls, ref)
                if control:
                    mapped_control_keys.add(control["key"])
                rows.append(self._control_evidence_row(control, item, ref))

        for control in controls:
            if control["key"] not in mapped_control_keys:
                rows.append(self._control_evidence_row(control, None, {}))

        mapped_controls = len(mapped_control_keys)
        return {
            "rows": rows,
            "summary": {
                "control_count": len(controls),
                "mapped_control_count": mapped_controls,
                "unmapped_control_count": max(len(controls) - mapped_controls, 0),
                "evidence_item_count": len(evidence_items),
            },
            "snapshot_hash_sha256": compliance_snapshot.get("snapshot_hash_sha256"),
            "source": "compliance_snapshot",
        }

    def _snapshot_controls(self, compliance_snapshot: Dict[str, Any]) -> List[Dict[str, Any]]:
        controls: List[Dict[str, Any]] = []
        for coverage in compliance_snapshot.get("coverage_snapshots") or []:
            if not isinstance(coverage, dict) or coverage.get("error"):
                continue
            framework_ref = coverage.get("framework_code") or coverage.get("framework_id") or ""
            framework_name = coverage.get("framework_name") or framework_ref
            for control in coverage.get("controls") or []:
                if not isinstance(control, dict):
                    continue
                control_ref = control.get("control_id") or control.get("id")
                if not control_ref:
                    continue
                controls.append(
                    {
                        "key": self._mapping_key(framework_ref, control_ref),
                        "framework_id": framework_ref,
                        "framework_name": framework_name,
                        "control_id": str(control_ref),
                        "control_title": control.get("title") or control.get("control_name") or "",
                        "coverage_status": control.get("status") or control.get("coverage_status") or "not_assessed",
                        "gap_count": len(control.get("gaps") or control.get("coverage_gaps") or []),
                    }
                )
        return controls

    def _snapshot_evidence_items(self, compliance_snapshot: Dict[str, Any]) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        seen_ids: set[str] = set()

        def add_item(item: Dict[str, Any], package: Optional[Dict[str, Any]] = None) -> None:
            item_id = str(item.get("id") or "")
            if item_id and item_id in seen_ids:
                return
            if item_id:
                seen_ids.add(item_id)
            payload = dict(item)
            if package:
                payload.setdefault("package_id", package.get("id"))
                payload.setdefault("package_name", package.get("package_name") or package.get("name"))
            items.append(payload)

        for package in compliance_snapshot.get("evidence_packages") or []:
            if not isinstance(package, dict):
                continue
            for item in package.get("items") or []:
                if isinstance(item, dict):
                    add_item(item, package)

        inventory_items = (compliance_snapshot.get("evidence_inventory") or {}).get("items") or []
        for item in inventory_items:
            if isinstance(item, dict):
                add_item(item)

        return items

    def _evidence_control_refs(self, item: Dict[str, Any]) -> List[Dict[str, Any]]:
        refs: List[Dict[str, Any]] = []
        for link in item.get("control_links") or []:
            if not isinstance(link, dict):
                continue
            control_ref = link.get("control_ref") or link.get("control_id")
            if not control_ref:
                continue
            refs.append(
                {
                    "control_id": str(control_ref),
                    "control_name": link.get("control_name"),
                    "framework_id": link.get("framework_code") or link.get("framework_id"),
                    "framework_name": link.get("framework_name"),
                    "link_status": link.get("status"),
                    "link_type": link.get("link_type"),
                }
            )

        metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
        for key in ("control_ref", "control_id", "nist_control_id"):
            value = metadata.get(key)
            if value and not self._looks_uuid(str(value)):
                refs.append({"control_id": str(value), "framework_id": metadata.get("framework_id")})

        direct_control = item.get("control_id")
        if direct_control and not self._looks_uuid(str(direct_control)):
            refs.append({"control_id": str(direct_control), "framework_id": None})

        deduped: List[Dict[str, Any]] = []
        seen: set[str] = set()
        for ref in refs:
            key = self._mapping_key(ref.get("framework_id"), ref.get("control_id"))
            if key not in seen:
                seen.add(key)
                deduped.append(ref)
        return deduped

    def _find_snapshot_control(
        self,
        controls: List[Dict[str, Any]],
        ref: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        framework_ref = ref.get("framework_id")
        control_ref = ref.get("control_id")
        exact_key = self._mapping_key(framework_ref, control_ref)
        for control in controls:
            if control["key"] == exact_key:
                return control
        normalized_control = self._normalize_ref(control_ref)
        for control in controls:
            if self._normalize_ref(control.get("control_id")) == normalized_control:
                return control
        return None

    def _control_evidence_row(
        self,
        control: Optional[Dict[str, Any]],
        item: Optional[Dict[str, Any]],
        ref: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "framework_id": (control or {}).get("framework_id") or ref.get("framework_id") or "",
            "framework_name": (control or {}).get("framework_name") or ref.get("framework_name") or "",
            "control_id": (control or {}).get("control_id") or ref.get("control_id") or "unmapped",
            "control_title": (control or {}).get("control_title") or ref.get("control_name") or "",
            "coverage_status": (control or {}).get("coverage_status") or "unmapped",
            "gap_count": (control or {}).get("gap_count", ""),
            "evidence_item_id": (item or {}).get("id", ""),
            "evidence_title": (item or {}).get("title", ""),
            "evidence_type": (item or {}).get("evidence_type", ""),
            "review_status": (item or {}).get("review_status", "missing" if control else "unmapped"),
            "valid_until": (item or {}).get("valid_until", ""),
            "package_id": (item or {}).get("package_id", ""),
            "package_name": (item or {}).get("package_name", ""),
            "source_system": (item or {}).get("source_system", ""),
        }

    def _mapping_key(self, framework_ref: Any, control_ref: Any) -> str:
        return f"{self._normalize_ref(framework_ref)}::{self._normalize_ref(control_ref)}"

    def _normalize_ref(self, value: Any) -> str:
        return str(value or "").strip().lower().replace("_", "").replace("-", "")

    def _looks_uuid(self, value: str) -> bool:
        try:
            UUID(str(value))
        except (TypeError, ValueError):
            return False
        return True

    def _should_attach_compliance_snapshot(
        self,
        template: ReportTemplate,
        report_parameters: Dict[str, Any],
    ) -> bool:
        if getattr(template, "type", None) in {"compliance", "soc2"}:
            return True
        if any(
            report_parameters.get(key)
            for key in ("framework_ids", "control_ids", "evidence_package_ids")
        ):
            return True
        sections = template.sections if isinstance(template.sections, list) else []
        return any("/compliance/" in str(section.get("data_source", "")) for section in sections)

    def _persist_compliance_snapshot_metadata(
        self,
        db: Session,
        report: Report,
        compliance_snapshot: Dict[str, Any],
        report_parameters: Dict[str, Any],
        *,
        commit: bool = True,
    ) -> None:
        metadata = dict(getattr(report, "report_metadata", None) or {})
        metadata["report_inputs"] = {
            **metadata.get("report_inputs", {}),
            **report_parameters,
        }
        metadata["compliance_snapshot"] = compliance_snapshot
        metadata["compliance_snapshot_hash_sha256"] = compliance_snapshot.get("snapshot_hash_sha256")
        metadata["evidence_package_ids"] = (
            compliance_snapshot.get("evidence_summary") or {}
        ).get("evidence_package_ids", [])
        metadata["evidence_summary"] = compliance_snapshot.get("evidence_summary", {})
        metadata["coverage_snapshot_source"] = compliance_snapshot.get("source")
        report.report_metadata = metadata
        if commit:
            db.commit()
