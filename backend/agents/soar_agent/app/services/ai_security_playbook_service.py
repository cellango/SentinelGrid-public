"""
AI Security Playbook Execution Service
Handles execution of AI-specific SOAR playbooks
"""
import logging
from typing import Dict, Any, Optional
from uuid import UUID
import yaml
from pathlib import Path

logger = logging.getLogger(__name__)

class AISecurityPlaybookService:
    """Service for executing AI security playbooks"""
    
    def __init__(self):
        """Initialize AI Security playbook service"""
        self.playbooks = self._load_playbooks()
    
    def _load_playbooks(self) -> Dict[str, Dict]:
        """Load AI security playbooks from YAML"""
        playbook_file = Path(__file__).parent.parent / "data" / "ai_security_playbooks.yaml"
        
        if not playbook_file.exists():
            logger.warning("AI security playbooks file not found")
            return {}
        
        try:
            with open(playbook_file, 'r') as f:
                data = yaml.safe_load(f)
                playbooks = data.get('playbooks', [])
                return {pb['playbook_key']: pb for pb in playbooks}
        except Exception as e:
            logger.error(f"Failed to load AI security playbooks: {e}")
            return {}
    
    async def execute_playbook(
        self,
        playbook_key: str,
        incident_id: UUID,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute an AI security playbook
        
        Args:
            playbook_key: Key identifying the playbook (e.g., 'ai-001-data-leak')
            incident_id: ID of the incident triggering this playbook
            context: Context data from the detection (org_id, app_id, user_id, etc.)
        
        Returns:
            Execution result with status and actions taken
        """
        if playbook_key not in self.playbooks:
            raise ValueError(f"Unknown playbook: {playbook_key}")
        
        playbook = self.playbooks[playbook_key]
        logger.info(f"Executing AI security playbook: {playbook_key} for incident {incident_id}")
        
        result = {
            "playbook_key": playbook_key,
            "incident_id": str(incident_id),
            "status": "in_progress",
            "phases_executed": [],
            "actions_taken": []
        }
        
        # Execute each phase
        phases = playbook.get('phases', {})
        
        # Detection phase (logging)
        if phases.get('detection'):
            result['phases_executed'].append('detection')
            result['actions_taken'].append({
                "phase": "detection",
                "action": "Incident created from SIEM alert",
                "status": "completed"
            })
        
        # Analysis phase
        if phases.get('analysis'):
            result['phases_executed'].append('analysis')
            for step in phases['analysis']:
                if isinstance(step, dict):
                    action = await self._execute_analysis_step(step, context)
                    result['actions_taken'].append(action)
        
        # Containment phase
        if phases.get('containment'):
            result['phases_executed'].append('containment')
            for step in phases['containment']:
                if isinstance(step, dict):
                    action = await self._execute_containment_step(step, context)
                    result['actions_taken'].append(action)
        
        result['status'] = 'completed'
        return result
    
    async def _execute_analysis_step(self, step: Dict, context: Dict) -> Dict:
        """Execute an analysis step"""
        name = step.get('name', 'Unknown')
        tool = step.get('tool')
        
        logger.info(f"Executing analysis step: {name}")
        
        # Simulate tool execution
        if tool == "opensearch_query":
            return {
                "phase": "analysis",
                "action": name,
                "tool": tool,
                "status": "completed",
                "result": "Retrieved events from OpenSearch"
            }
        elif tool == "mcp_ai_analyze":
            return {
                "phase": "analysis",
                "action": name,
                "tool": tool,
                "status": "completed",
                "result": "AI SOC analysis completed"
            }
        else:
            return {
                "phase": "analysis",
                "action": name,
                "status": "completed"
            }
    
    async def _execute_containment_step(self, step: Dict, context: Dict) -> Dict:
        """Execute a containment step"""
        name = step.get('name', 'Unknown')
        tool = step.get('tool')
        automated = step.get('automated', True)
        
        logger.info(f"Executing containment step: {name}")
        
        if not automated:
            return {
                "phase": "containment",
                "action": name,
                "status": "pending_approval",
                "requires_human": True
            }
        
        # Simulate automated containment
        if tool == "update_ai_policy":
            return {
                "phase": "containment",
                "action": name,
                "tool": tool,
                "status": "completed",
                "result": "Policy updated - external LLMs blocked"
            }
        elif tool == "send_notification":
            return {
                "phase": "containment",
                "action": name,
                "tool": tool,
                "status": "completed",
                "result": "Notification sent to security team"
            }
        elif tool == "apply_rate_limit":
            return {
                "phase": "containment",
                "action": name,
                "tool": tool,
                "status": "completed",
                "result": f"Rate limit applied: {step.get('parameters', {}).get('limit', 'default')}"
            }
        else:
            return {
                "phase": "containment",
                "action": name,
                "status": "completed"
            }
    
    def list_playbooks(self) -> list:
        """List all available AI security playbooks"""
        return [
            {
                "playbook_key": pb['playbook_key'],
                "name": pb['name'],
                "description": pb['description'],
                "severity": pb['severity_default'],
                "triggers": pb['triggers']
            }
            for pb in self.playbooks.values()
        ]
    
    def get_playbook(self, playbook_key: str) -> Optional[Dict]:
        """Get a specific playbook by key"""
        return self.playbooks.get(playbook_key)


# Singleton instance
_service = None

def get_ai_security_playbook_service() -> AISecurityPlaybookService:
    """Get the singleton AI security playbook service"""
    global _service
    if _service is None:
        _service = AISecurityPlaybookService()
    return _service

