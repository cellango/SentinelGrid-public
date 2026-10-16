"""
Knowledge Base Loader Service
Loads cybersecurity framework content into vector database
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import httpx
import json

# Embeddings service - optional (has dependency conflicts)
try:
    from app.services.embeddings_service import EmbeddingsService
except ImportError:
    EmbeddingsService = None
from app.core.database import get_db

logger = logging.getLogger(__name__)


class KnowledgeBaseLoader:
    """Service for loading cybersecurity knowledge into vector database."""
    
    def __init__(self):
        self.embeddings_service = EmbeddingsService()
    
    def load_nist_controls(
        self,
        controls_data: List[Dict[str, Any]],
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Load NIST 800-53 controls into knowledge base.
        
        Expected format:
        {
            "control_id": "AC-2",
            "control_name": "Account Management",
            "description": "...",
            "supplemental_guidance": "...",
            "assessment_procedures": "..."
        }
        """
        loaded = 0
        errors = 0
        
        for control in controls_data:
            try:
                # Combine all text for embedding
                content = f"""
Control ID: {control.get('control_id')}
Control Name: {control.get('control_name')}
Description: {control.get('description', '')}
Supplemental Guidance: {control.get('supplemental_guidance', '')}
Assessment Procedures: {control.get('assessment_procedures', '')}
"""
                
                # Generate embedding
                embedding = self.embeddings_service.generate_embedding(content)
                
                if embedding:
                    # Store in database
                    # TODO: Insert into cybersecurity_knowledge_base table
                    loaded += 1
                else:
                    errors += 1
                    
            except Exception as e:
                logger.error(f"Error loading control {control.get('control_id')}: {e}")
                errors += 1
        
        return {
            "loaded": loaded,
            "errors": errors,
            "total": len(controls_data)
        }
    
    def load_mitre_attack(
        self,
        techniques_data: List[Dict[str, Any]],
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Load MITRE ATT&CK techniques into knowledge base.
        
        Expected format:
        {
            "technique_id": "T1059",
            "name": "Command and Scripting Interpreter",
            "description": "...",
            "tactics": ["Execution"],
            "detection": "...",
            "mitigation": "..."
        }
        """
        loaded = 0
        errors = 0
        
        for technique in techniques_data:
            try:
                content = f"""
Technique ID: {technique.get('technique_id')}
Name: {technique.get('name')}
Description: {technique.get('description', '')}
Tactics: {', '.join(technique.get('tactics', []))}
Detection: {technique.get('detection', '')}
Mitigation: {technique.get('mitigation', '')}
"""
                
                embedding = self.embeddings_service.generate_embedding(content)
                
                if embedding:
                    # TODO: Store in database
                    loaded += 1
                else:
                    errors += 1
                    
            except Exception as e:
                logger.error(f"Error loading technique {technique.get('technique_id')}: {e}")
                errors += 1
        
        return {
            "loaded": loaded,
            "errors": errors,
            "total": len(techniques_data)
        }
    
    def load_owasp_content(
        self,
        owasp_data: List[Dict[str, Any]],
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Load OWASP content (Top 10, ASVS) into knowledge base."""
        loaded = 0
        errors = 0
        
        for item in owasp_data:
            try:
                content = f"""
Category: {item.get('category')}
Title: {item.get('title')}
Description: {item.get('description', '')}
Risk: {item.get('risk', '')}
Prevention: {item.get('prevention', '')}
"""
                
                embedding = self.embeddings_service.generate_embedding(content)
                
                if embedding:
                    # TODO: Store in database
                    loaded += 1
                else:
                    errors += 1
                    
            except Exception as e:
                logger.error(f"Error loading OWASP content: {e}")
                errors += 1
        
        return {
            "loaded": loaded,
            "errors": errors,
            "total": len(owasp_data)
        }
    
    def load_soc_playbook(
        self,
        playbook: Dict[str, Any],
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Load a SOC playbook into knowledge base.
        
        Expected format from SOC_PLAYBOOKS_TEMPLATES.md
        """
        try:
            # Combine all playbook content
            content = f"""
Playbook: {playbook.get('name')}
Description: {playbook.get('description', '')}
Category: {playbook.get('category', '')}
MITRE Tactics: {', '.join(playbook.get('mitre_tactics', []))}
MITRE Techniques: {', '.join(playbook.get('mitre_techniques', []))}
NIST Controls: {', '.join(playbook.get('nist_controls', []))}

Steps:
{json.dumps(playbook.get('steps', []), indent=2)}
"""
            
            embedding = self.embeddings_service.generate_embedding(content)
            
            if embedding:
                # TODO: Store in database with metadata
                return {
                    "playbook_id": playbook.get('playbook_id'),
                    "status": "loaded",
                    "loaded_at": datetime.utcnow().isoformat()
                }
            else:
                return {
                    "playbook_id": playbook.get('playbook_id'),
                    "status": "error",
                    "error": "Failed to generate embedding"
                }
                
        except Exception as e:
            logger.error(f"Error loading playbook {playbook.get('playbook_id')}: {e}")
            return {
                "playbook_id": playbook.get('playbook_id'),
                "status": "error",
                "error": str(e)
            }
    
    def sync_cve_database(
        self,
        cve_list: List[Dict[str, Any]],
        min_cvss: float = 7.0,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Sync CVE database from NVD.
        
        Filters by minimum CVSS score.
        """
        loaded = 0
        skipped = 0
        errors = 0
        
        for cve in cve_list:
            try:
                # Filter by CVSS score
                cvss_score = cve.get('cvss_score', 0.0)
                if cvss_score < min_cvss:
                    skipped += 1
                    continue
                
                content = f"""
CVE ID: {cve.get('cve_id')}
Description: {cve.get('description', '')}
CVSS Score: {cvss_score}
CVSS Vector: {cve.get('cvss_vector', '')}
Affected Products: {', '.join(cve.get('affected_products', []))}
Remediation: {cve.get('remediation', '')}
"""
                
                embedding = self.embeddings_service.generate_embedding(content)
                
                if embedding:
                    # TODO: Store in database
                    loaded += 1
                else:
                    errors += 1
                    
            except Exception as e:
                logger.error(f"Error loading CVE {cve.get('cve_id')}: {e}")
                errors += 1
        
        return {
            "loaded": loaded,
            "skipped": skipped,
            "errors": errors,
            "total": len(cve_list)
        }

