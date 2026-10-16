"""
Knowledge Base Loader
Loads cybersecurity frameworks (NIST, MITRE, OWASP) into vector database for RAG.
"""

import logging
import os
import sys
import json
import uuid
from typing import List, Dict, Any, Optional
from pathlib import Path

from sqlalchemy.orm import Session
from app.services.rag_service import RAGService
from app.services.embeddings_service import EmbeddingsService

logger = logging.getLogger(__name__)


class KnowledgeBaseLoader:
    """Loader for cybersecurity knowledge bases."""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.rag_service = RAGService(db_session=db_session)
        self.embeddings_service = EmbeddingsService()
    
    def load_nist_controls(self, data_source: Optional[str] = None) -> Dict[str, Any]:
        """
        Load NIST 800-53 controls into knowledge base.
        
        Args:
            data_source: Path to JSON file with NIST controls, or None to use embedded data
            
        Returns:
            Summary of loaded controls
        """
        logger.info("Loading NIST 800-53 controls...")
        
        # Load NIST data
        if data_source and Path(data_source).exists():
            with open(data_source, 'r') as f:
                nist_data = json.load(f)
        else:
            # Use embedded sample data (for initial population)
            nist_data = self._get_sample_nist_controls()
        
        stored = 0
        errors = 0
        
        for control in nist_data.get("controls", []):
            try:
                # Prepare content
                content_parts = [control.get("description", "")]
                
                if control.get("guidance"):
                    content_parts.append(f"\n\nGuidance: {control.get('guidance')}")
                
                if control.get("supplemental_guidance"):
                    content_parts.append(f"\n\nSupplemental Guidance: {control.get('supplemental_guidance')}")
                
                content = "\n".join(content_parts)
                
                # Store in knowledge base
                result = self.rag_service.store_knowledge(
                    category="nist",
                    title=control.get("id", "NIST Control"),
                    content=content,
                    subcategory="control",
                    metadata={
                        "control_id": control.get("id"),
                        "control_family": control.get("family", ""),
                        "control_type": control.get("type", "base"),
                        "priority": control.get("priority", ""),
                        "baseline": control.get("baseline", [])
                    },
                    framework_version=control.get("version", "800-53r5"),
                    source_url=control.get("url")
                )
                
                if result.get("status") == "success":
                    stored += 1
                else:
                    errors += 1
                    logger.warning(f"Failed to store NIST control {control.get('id')}: {result.get('error')}")
                    
            except Exception as e:
                errors += 1
                logger.error(f"Error loading NIST control {control.get('id', 'unknown')}: {e}")
        
        logger.info(f"NIST controls loaded: {stored} stored, {errors} errors")
        
        return {
            "framework": "NIST 800-53",
            "loaded": stored,
            "errors": errors,
            "total": len(nist_data.get("controls", []))
        }
    
    def load_mitre_techniques(self, data_source: Optional[str] = None) -> Dict[str, Any]:
        """
        Load MITRE ATT&CK techniques into knowledge base.
        
        Args:
            data_source: Path to JSON file with MITRE data, or None to use embedded data
            
        Returns:
            Summary of loaded techniques
        """
        logger.info("Loading MITRE ATT&CK techniques...")
        
        # Load MITRE data
        if data_source and Path(data_source).exists():
            with open(data_source, 'r') as f:
                mitre_data = json.load(f)
        else:
            # Use embedded sample data
            mitre_data = self._get_sample_mitre_techniques()
        
        stored = 0
        errors = 0
        
        for technique in mitre_data.get("techniques", []):
            try:
                # Prepare content
                content_parts = [technique.get("description", "")]
                
                if technique.get("detection"):
                    content_parts.append(f"\n\nDetection: {technique.get('detection')}")
                
                if technique.get("mitigation"):
                    content_parts.append(f"\n\nMitigation: {technique.get('mitigation')}")
                
                content = "\n".join(content_parts)
                
                # Store in knowledge base
                result = self.rag_service.store_knowledge(
                    category="mitre",
                    title=technique.get("name", technique.get("id", "MITRE Technique")),
                    content=content,
                    subcategory="technique",
                    metadata={
                        "technique_id": technique.get("id"),
                        "tactic": technique.get("tactic", []),
                        "platform": technique.get("platform", []),
                        "kill_chain_phase": technique.get("kill_chain_phase", ""),
                        "data_sources": technique.get("data_sources", []),
                        "defense_bypassed": technique.get("defense_bypassed", [])
                    },
                    framework_version=technique.get("version", "ATT&CK v13"),
                    source_url=technique.get("url")
                )
                
                if result.get("status") == "success":
                    stored += 1
                else:
                    errors += 1
                    logger.warning(f"Failed to store MITRE technique {technique.get('id')}: {result.get('error')}")
                    
            except Exception as e:
                errors += 1
                logger.error(f"Error loading MITRE technique {technique.get('id', 'unknown')}: {e}")
        
        logger.info(f"MITRE techniques loaded: {stored} stored, {errors} errors")
        
        return {
            "framework": "MITRE ATT&CK",
            "loaded": stored,
            "errors": errors,
            "total": len(mitre_data.get("techniques", []))
        }
    
    def load_owasp_content(self, data_source: Optional[str] = None) -> Dict[str, Any]:
        """
        Load OWASP content (Top 10, ASVS, etc.) into knowledge base.
        
        Args:
            data_source: Path to JSON file with OWASP data, or None to use embedded data
            
        Returns:
            Summary of loaded content
        """
        logger.info("Loading OWASP content...")
        
        # Load OWASP data
        if data_source and Path(data_source).exists():
            with open(data_source, 'r') as f:
                owasp_data = json.load(f)
        else:
            # Use embedded sample data
            owasp_data = self._get_sample_owasp_content()
        
        stored = 0
        errors = 0
        
        for item in owasp_data.get("items", []):
            try:
                # Prepare content
                content_parts = [item.get("description", "")]
                
                if item.get("how_to_prevent"):
                    content_parts.append(f"\n\nHow to Prevent: {item.get('how_to_prevent')}")
                
                if item.get("example_attacks"):
                    content_parts.append(f"\n\nExample Attacks: {item.get('example_attacks')}")
                
                content = "\n".join(content_parts)
                
                # Store in knowledge base
                result = self.rag_service.store_knowledge(
                    category="owasp",
                    title=item.get("name", item.get("id", "OWASP Item")),
                    content=content,
                    subcategory=item.get("type", "top10"),  # top10, asvs, etc.
                    metadata={
                        "item_id": item.get("id"),
                        "category": item.get("category", ""),
                        "risk_rating": item.get("risk_rating", ""),
                        "cwes": item.get("cwes", []),
                        "owasp_category": item.get("owasp_category", "")
                    },
                    framework_version=item.get("version", "2021"),
                    source_url=item.get("url")
                )
                
                if result.get("status") == "success":
                    stored += 1
                else:
                    errors += 1
                    logger.warning(f"Failed to store OWASP item {item.get('id')}: {result.get('error')}")
                    
            except Exception as e:
                errors += 1
                logger.error(f"Error loading OWASP item {item.get('id', 'unknown')}: {e}")
        
        logger.info(f"OWASP content loaded: {stored} stored, {errors} errors")
        
        return {
            "framework": "OWASP",
            "loaded": stored,
            "errors": errors,
            "total": len(owasp_data.get("items", []))
        }

    def load_soc2_content(self, data_source: Optional[str] = None) -> Dict[str, Any]:
        """
        Load SOC 2 criteria, mappings, and reporting schema into the knowledge base.
        Seeds are system-wide (tenant_id=None) to be shared across tenants with isolation enforced at query time.
        """
        logger.info("Loading SOC 2 criteria and mappings...")

        if data_source and Path(data_source).exists():
            with open(data_source, 'r') as f:
                soc2_data = json.load(f)
        else:
            soc2_data = self._get_sample_soc2_content()

        stored = 0
        errors = 0

        for item in soc2_data.get("items", []):
            try:
                content_lines = [item.get("description", "")]
                if item.get("implementation"):
                    content_lines.append(f"\nImplementation Guidance:\n{item['implementation']}")
                if item.get("mappings"):
                    content_lines.append(f"\nMappings:\n{item['mappings']}")
                if item.get("reporting"):
                    content_lines.append(f"\nReporting Schema:\n{item['reporting']}")

                content = "\n".join(content_lines)

                result = self.rag_service.store_knowledge(
                    category="soc2",
                    subcategory=item.get("subcategory", "criteria"),
                    title=item.get("title", "SOC 2 Control"),
                    content=content,
                    metadata={
                        "criteria_id": item.get("criteria_id"),
                        "pillar": item.get("pillar"),
                        "control_family": item.get("family"),
                        "mappings": item.get("mapping_refs", []),
                        "report_section": item.get("report_section"),
                        "tenant_scope": "system"
                    },
                    framework_version=item.get("version", "TSC 2017"),
                    source_url=item.get("source_url")
                )

                if result.get("status") == "success":
                    stored += 1
                else:
                    errors += 1
                    logger.warning(f"Failed to store SOC 2 item {item.get('criteria_id')}: {result.get('error')}")
            except Exception as e:
                errors += 1
                logger.error(f"Error loading SOC 2 item {item.get('criteria_id', 'unknown')}: {e}")

        logger.info(f"SOC 2 content loaded: {stored} stored, {errors} errors")
        return {
            "framework": "SOC 2",
            "loaded": stored,
            "errors": errors,
            "total": len(soc2_data.get("items", []))
        }

    def load_report_content(
        self,
        tenant_id: str,
        realm_name: Optional[str],
        report_id: str,
        template_id: Optional[str],
        template_name: Optional[str],
        file_path: Optional[str],
        sections: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Load a generated report (summary + sections) into the tenant-scoped knowledge base.
        """
        if not tenant_id:
            raise ValueError("tenant_id is required to ingest report content")

        sections = sections or []
        stored = 0
        errors = 0

        def _stringify(data: Any) -> str:
            if isinstance(data, str):
                return data
            try:
                return json.dumps(data, indent=2, default=str)
            except Exception:
                return str(data)

        # Store a high-level summary entry
        summary_lines = [
            f"Report ID: {report_id}",
            f"Template: {template_name or template_id or 'Unknown'}",
        ]
        if file_path:
            summary_lines.append(f"File: {file_path}")
        summary_lines.append(f"Sections: {len(sections)}")
        summary_content = "\n".join(summary_lines)

        try:
            result = self.rag_service.store_knowledge(
                category="report",
                subcategory="summary",
                title=f"Report {report_id} summary",
                content=summary_content,
                tenant_id=tenant_id,
                metadata={
                    "report_id": report_id,
                    "template_id": template_id,
                    "template_name": template_name,
                    "realm_name": realm_name,
                    "file_path": file_path,
                    "section_count": len(sections),
                },
            )
            if result.get("status") == "success":
                stored += 1
            else:
                errors += 1
        except Exception as e:
            errors += 1
            logger.error(f"Failed to store report summary for {report_id}: {e}")

        # Store each section as its own KB entry
        for section in sections:
            title = section.get("title") or "Untitled section"
            widget = section.get("widget")
            data = section.get("data") or section.get("content") or {}
            content = f"{title}\n\n{_stringify(data)}"
            metadata = {
                "report_id": report_id,
                "template_id": template_id,
                "template_name": template_name,
                "realm_name": realm_name,
                "file_path": file_path,
                "widget": widget,
            }

            try:
                result = self.rag_service.store_knowledge(
                    category="report",
                    subcategory="section",
                    title=f"{template_name or 'Report'} - {title}",
                    content=content,
                    tenant_id=tenant_id,
                    metadata=metadata,
                )
                if result.get("status") == "success":
                    stored += 1
                else:
                    errors += 1
            except Exception as e:
                errors += 1
                logger.error(f"Failed to store report section {title}: {e}")

        return {
            "stored": stored,
            "errors": errors,
            "total": len(sections) + 1,  # summary + sections
        }
    
    def load_playbooks(self, data_source: Optional[str] = None) -> Dict[str, Any]:
        """
        Load SOC playbooks into knowledge base.
        
        Args:
            data_source: Path to JSON file with playbooks, or None to use embedded data
            
        Returns:
            Summary of loaded playbooks
        """
        logger.info("Loading SOC playbooks...")
        
        # Load playbook data
        if data_source and Path(data_source).exists():
            with open(data_source, 'r') as f:
                playbooks_data = json.load(f)
        else:
            # Use embedded sample data
            playbooks_data = self._get_sample_playbooks()
        
        stored = 0
        errors = 0
        
        for playbook in playbooks_data.get("playbooks", []):
            try:
                # Prepare content from playbook steps
                content_parts = [playbook.get("description", "")]
                
                if playbook.get("steps"):
                    content_parts.append("\n\nSteps:")
                    for i, step in enumerate(playbook.get("steps", []), 1):
                        content_parts.append(f"\n{i}. {step.get('name', '')}")
                        if step.get("description"):
                            content_parts.append(f"   {step.get('description')}")
                
                content = "\n".join(content_parts)
                
                # Store in knowledge base
                result = self.rag_service.store_knowledge(
                    category="playbook",
                    title=playbook.get("name", playbook.get("id", "SOC Playbook")),
                    content=content,
                    subcategory="incident_response",
                    metadata={
                        "playbook_id": playbook.get("id"),
                        "mitre_tactics": playbook.get("mitre_tactics", []),
                        "mitre_techniques": playbook.get("mitre_techniques", []),
                        "nist_controls": playbook.get("nist_controls", []),
                        "soc2_criteria": playbook.get("soc2_criteria", []),
                        "severity_levels": playbook.get("severity_levels", []),
                        "estimated_duration": playbook.get("estimated_duration", "")
                    },
                    source_url=playbook.get("url")
                )
                
                if result.get("status") == "success":
                    stored += 1
                else:
                    errors += 1
                    logger.warning(f"Failed to store playbook {playbook.get('id')}: {result.get('error')}")
                    
            except Exception as e:
                errors += 1
                logger.error(f"Error loading playbook {playbook.get('id', 'unknown')}: {e}")
        
        logger.info(f"Playbooks loaded: {stored} stored, {errors} errors")
        
        return {
            "framework": "SOC Playbooks",
            "loaded": stored,
            "errors": errors,
            "total": len(playbooks_data.get("playbooks", []))
        }
    
    def load_all(self, 
                 nist_source: Optional[str] = None,
                 mitre_source: Optional[str] = None,
                 owasp_source: Optional[str] = None,
                 playbooks_source: Optional[str] = None) -> Dict[str, Any]:
        """Load all knowledge bases."""
        logger.info("Loading all cybersecurity knowledge bases...")
        
        results = {
            "nist": self.load_nist_controls(nist_source),
            "mitre": self.load_mitre_techniques(mitre_source),
            "owasp": self.load_owasp_content(owasp_source),
            "playbooks": self.load_playbooks(playbooks_source)
        }
        
        total_loaded = sum(r["loaded"] for r in results.values())
        total_errors = sum(r["errors"] for r in results.values())
        
        logger.info(f"Knowledge base loading complete: {total_loaded} items loaded, {total_errors} errors")
        
        return {
            "results": results,
            "summary": {
                "total_loaded": total_loaded,
                "total_errors": total_errors
            }
        }
    
    def _get_sample_nist_controls(self) -> Dict[str, Any]:
        """Sample NIST 800-53 controls for initial population."""
        return {
            "controls": [
                {
                    "id": "AC-2",
                    "family": "Access Control",
                    "type": "base",
                    "priority": "P1",
                    "baseline": ["low", "moderate", "high"],
                    "version": "800-53r5",
                    "description": "The organization manages information system accounts, including establishing, activating, modifying, disabling, and removing accounts. Organizations manage user accounts by establishing and managing account types (e.g., individual, group, system, application, guest/anonymous, emergency), account identifiers, account authorization, account access authorizations, and account removal.",
                    "guidance": "Account management addresses the management of user, system, service, and application accounts. Account management includes the identification of account types, the establishment of conditions for group membership and account privileges, and the identification of authorized users of the system. Account management also includes processes for requesting, establishing, issuing, suspending, modifying, disabling, and removing accounts.",
                    "supplemental_guidance": "Account management functions include assigning account managers, creating, activating, modifying, disabling, and removing accounts, and conducting account reviews."
                },
                {
                    "id": "AC-3",
                    "family": "Access Control",
                    "type": "base",
                    "priority": "P1",
                    "baseline": ["low", "moderate", "high"],
                    "version": "800-53r5",
                    "description": "The information system enforces approved authorizations for logical access to information and system resources in accordance with applicable access control policies.",
                    "guidance": "Access control policies specify what users are authorized to do on the system. These policies are implemented through access control mechanisms. Access enforcement mechanisms employ access control lists, access control matrices, and cryptography to enforce authorized access to information and system resources."
                },
                {
                    "id": "IR-4",
                    "family": "Incident Response",
                    "type": "base",
                    "priority": "P1",
                    "baseline": ["low", "moderate", "high"],
                    "version": "800-53r5",
                    "description": "The organization implements an incident handling capability for security incidents that includes preparation, detection and analysis, containment, eradication, and recovery activities.",
                    "guidance": "Incident handling capability includes the development of incident response plans and procedures; the establishment of incident response teams; the training of incident response personnel; the acquisition of tools and resources to support incident response activities; and the integration of incident response activities into organizational contingency planning."
                }
            ]
        }
    
    def _get_sample_mitre_techniques(self) -> Dict[str, Any]:
        """Sample MITRE ATT&CK techniques for initial population."""
        return {
            "techniques": [
                {
                    "id": "T1078",
                    "name": "Valid Accounts",
                    "tactic": ["Initial Access", "Persistence", "Privilege Escalation", "Defense Evasion"],
                    "platform": ["Windows", "Linux", "macOS", "SaaS", "Office 365", "Azure AD", "Google Workspace", "IaaS", "Containers"],
                    "version": "ATT&CK v13",
                    "description": "Adversaries may steal and use credentials from existing accounts as a means of gaining Initial Access, Persistence, Privilege Escalation, or Defense Evasion. Compromised credentials may be used to bypass access controls placed on various resources on systems within the network and may even be used for persistent access to remote systems and externally available services.",
                    "detection": "Monitor for suspicious account use that may indicate stolen credentials being used. Monitor for authentication attempts that may use compromised credentials. Monitor for abnormal account access patterns (e.g., access at unusual times, access from unusual locations).",
                    "mitigation": "Use multifactor authentication for user and privileged accounts. Enforce account use policies. Disable or remove inactive accounts. Regularly audit account usage and access patterns.",
                    "data_sources": ["Application Logs", "Authentication Logs", "Process Monitoring"],
                    "defense_bypassed": ["MFA", "Network Segmentation"]
                },
                {
                    "id": "T1059",
                    "name": "Command and Scripting Interpreter",
                    "tactic": ["Execution"],
                    "platform": ["Linux", "macOS", "Windows"],
                    "version": "ATT&CK v13",
                    "description": "Adversaries may abuse command and script interpreters to execute commands, scripts, or binaries. These interfaces and languages provide ways of interacting with computer systems and are a common feature across many different platforms.",
                    "detection": "Monitor for command line arguments and execution of commands and scripts. Monitor for unusual processes and process arguments. Monitor for script execution on systems.",
                    "mitigation": "Disable or restrict command and script interpreters. Limit execution of scripts to specific users or systems. Implement application whitelisting.",
                    "data_sources": ["Process Monitoring", "Command Line Arguments", "Script Execution"]
                }
            ]
        }
    
    def _get_sample_owasp_content(self) -> Dict[str, Any]:
        """Sample OWASP content for initial population."""
        return {
            "items": [
                {
                    "id": "A01:2021",
                    "name": "Broken Access Control",
                    "type": "top10",
                    "category": "Security Misconfiguration",
                    "risk_rating": "Critical",
                    "version": "2021",
                    "description": "Access control enforces policy such that users cannot act outside of their intended permissions. Failures typically lead to unauthorized information disclosure, modification, or destruction of all data or performing a business function outside the user's limits.",
                    "how_to_prevent": "Access control is only effective if enforced in trusted server-side code or server-less API, where the attacker cannot modify the access control check or metadata. Deny by default, except public resources. Implement access control mechanisms once and reuse them throughout the application. Rate limiting API and controller access to minimize the harm from automated attack tooling.",
                    "example_attacks": "Attacker modifies the URL to access another user's account page. Attacker modifies a parameter to access privileged functions. Attacker forces browsing to admin pages."
                },
                {
                    "id": "A07:2021",
                    "name": "Identification and Authentication Failures",
                    "type": "top10",
                    "category": "Authentication",
                    "risk_rating": "High",
                    "version": "2021",
                    "description": "Confirmation of the user's identity, authentication, and session management is critical to protect against authentication-related attacks. There may be authentication weaknesses if the application permits automated attacks such as credential stuffing, uses weak or well-known passwords, uses plain text or weakly hashed password data stores.",
                    "how_to_prevent": "Implement multi-factor authentication. Do not deploy any default credentials. Implement weak password checks. Limit or increasingly delay failed login attempts.",
                    "example_attacks": "Credential stuffing attacks using automated tools. Weak password policies allowing common passwords. Session fixation attacks."
                }
            ]
        }
    
    def _get_sample_playbooks(self) -> Dict[str, Any]:
        """Sample SOC playbooks for initial population."""
        return {
            "playbooks": [
                {
                    "id": "malware-response-v1",
                    "name": "Malware Detection & Response",
                    "description": "Comprehensive playbook for detecting, containing, and eradicating malware infections across endpoints and networks.",
                    "mitre_tactics": ["Execution", "Persistence", "Defense Evasion", "Command and Control"],
                    "mitre_techniques": ["T1059", "T1547", "T1070"],
                    "nist_controls": ["IR-4", "SI-3", "IR-5"],
                    "soc2_criteria": ["CC6.1", "CC7.1", "CC4.1"],
                    "severity_levels": ["high", "critical"],
                    "estimated_duration": "4-8 hours",
                    "steps": [
                        {
                            "name": "Detection & Triage",
                            "description": "EDR/SIEM alert analysis, hash lookup, behavioral analysis"
                        },
                        {
                            "name": "Containment",
                            "description": "Network isolation, disable compromised accounts, block malicious IPs"
                        },
                        {
                            "name": "Investigation",
                            "description": "Timeline reconstruction, artifact collection, IOC extraction"
                        },
                        {
                            "name": "Eradication",
                            "description": "Malware removal, registry cleanup, service removal"
                        },
                        {
                            "name": "Recovery",
                            "description": "System restoration, security hardening, monitoring enhancement"
                        }
                    ]
                },
                {
                    "id": "phishing-response-v1",
                    "name": "Phishing Incident Response",
                    "description": "Response procedures for phishing attacks, including email analysis, user notification, and account compromise assessment.",
                    "mitre_tactics": ["Initial Access"],
                    "mitre_techniques": ["T1566"],
                    "nist_controls": ["IR-4", "AT-2"],
                    "soc2_criteria": ["CC2.1", "CC6.1", "CC4.1"],
                    "severity_levels": ["medium", "high"],
                    "estimated_duration": "2-4 hours",
                    "steps": [
                        {
                            "name": "Email Analysis",
                            "description": "Analyze email headers, links, attachments, sender reputation"
                        },
                        {
                            "name": "User Notification",
                            "description": "Notify affected users, provide guidance, request password reset"
                        },
                        {
                            "name": "Account Assessment",
                            "description": "Check for account compromise, review access logs"
                        },
                        {
                            "name": "Remediation",
                            "description": "Block malicious domains/IPs, remove emails, update filters"
                        }
                    ]
                }
            ]
        }

    def _get_sample_soc2_content(self) -> Dict[str, Any]:
        """Sample SOC 2 criteria, mappings, and reporting schema."""
        return {
            "items": [
                {
                    "criteria_id": "CC1.1",
                    "title": "Control Environment & Governance",
                    "description": "The entity demonstrates a commitment to integrity and ethical values; establishes oversight responsibilities; and enforces accountability for internal control.",
                    "implementation": "Use access reviews, privileged access policies, and separation of duties. Enforce MFA for all admin roles.",
                    "mappings": "Mapped to IAM policies, access reviews, privileged access alerts, and evidence of quarterly certifications.",
                    "mapping_refs": [
                        "playbook:access-review",
                        "detection:privileged-access-anomaly",
                        "report:soc2_coverage"
                    ],
                    "pillar": "Security",
                    "family": "Common Criteria",
                    "report_section": "Governance",
                    "version": "TSC 2017",
                    "subcategory": "criteria"
                },
                {
                    "criteria_id": "CC6.1",
                    "title": "Logical Access Security",
                    "description": "Logical access to information assets is restricted to authorized users, processes, or devices, and to authorized activities and transactions.",
                    "implementation": "IAM MFA hygiene, SSO, least privilege roles, endpoint agent deployment, and continuous monitoring for stale accounts.",
                    "mappings": "Mapped to IAM MFA Hygiene report, Endpoint coverage, Playbooks for joiner/mover/leaver automation, detections for stale credentials.",
                    "mapping_refs": [
                        "report:iam_mfa_hygiene",
                        "playbook:joiner-mover-leaver",
                        "detection:stale-account",
                        "report:log_coverage"
                    ],
                    "pillar": "Security",
                    "family": "Logical Access",
                    "report_section": "Access Control",
                    "version": "TSC 2017",
                    "subcategory": "criteria"
                },
                {
                    "criteria_id": "CC7.2",
                    "title": "Monitoring for Security Events",
                    "description": "Security incidents are detected, analyzed, and reported in a timely manner.",
                    "implementation": "Centralize logs (SIEM), detect anomalies, run SOAR playbooks for incident triage, and capture incident timelines for evidence.",
                    "mappings": "Mapped to SIEM detections, SOAR incident response playbooks, Incident reports, and Log coverage report sections.",
                    "mapping_refs": [
                        "report:log_coverage",
                        "playbook:incident-response",
                        "report:incident_response",
                        "detection:siem-anomaly"
                    ],
                    "pillar": "Security",
                    "family": "Monitoring",
                    "report_section": "Detection & Response",
                    "version": "TSC 2017",
                    "subcategory": "criteria"
                },
                {
                    "criteria_id": "CC8.1",
                    "title": "Change Management",
                    "description": "Changes to infrastructure, data, software, and procedures are authorized, tested, approved, and documented.",
                    "implementation": "Use change tickets, approvals, and deployment pipelines with audit logs; detect unauthorized config drifts.",
                    "mappings": "Mapped to ticketing workflows, approvals on playbook clones, and detections for config drift.",
                    "mapping_refs": [
                        "ticketing:change",
                        "playbook:change-approval",
                        "detection:config-drift"
                    ],
                    "pillar": "Availability",
                    "family": "Change Management",
                    "report_section": "Change Control",
                    "version": "TSC 2017",
                    "subcategory": "criteria"
                },
                {
                    "criteria_id": "REPORT_SCHEMA",
                    "title": "SOC 2 Reporting Schema",
                    "description": "Standard sections for SOC 2 reports: Coverage matrix, Findings summary, Evidence links, CCM status, and Incident timelines.",
                    "implementation": "Populate report templates with compliance matrix, metrics summary, evidence and control mappings.",
                    "mappings": "Templates: SOC 2 Coverage Report, SOC 2 CCM Status, SOC 2 Evidence Summary.",
                    "mapping_refs": [
                        "template:soc2_coverage",
                        "template:soc2_ccm_status",
                        "template:soc2_evidence_summary"
                    ],
                    "pillar": "Reporting",
                    "family": "Reporting",
                    "report_section": "Reporting Schema",
                    "version": "TSC 2017",
                    "subcategory": "reporting"
                }
            ]
        }
