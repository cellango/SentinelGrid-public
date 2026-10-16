# Playbook Editor Integration with NIST & MITRE Framework

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Date:** 2025-01-28  
**Status:** 📋 Design Document  
**Priority:** P1 (Hero Flow 2)

---

## Executive Summary

This document extends the playbook editor to integrate with:
1. **Playbook Editor Compatibility** - Ensure playbooks work with existing React Flow editor
2. **NIST Control Mapping** - Map incidents to NIST SP 800-53 controls
3. **MITRE ATT&CK Framework** - Full integration with tactics, techniques, and procedures

**Key Principles:**
- **Editor Compatibility** - Playbooks must work with existing React Flow editor
- **NIST Compliance** - Automatic mapping to NIST SP 800-53 controls
- **MITRE Integration** - Tactics, techniques, and procedures (TTPs) mapping
- **Framework Alignment** - Show how incidents relate to both frameworks

---

## 1. Playbook Editor Integration

### 1.1 Playbook Data Model (Editor-Compatible)

```python
# backend/services/soar_agent/app/models/playbook.py

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from enum import Enum

class NodeType(str, Enum):
    """Playbook node types compatible with React Flow editor."""
    # Triggers
    ALERT_TRIGGER = "alert_trigger"
    INCIDENT_TRIGGER = "incident_trigger"
    MANUAL_TRIGGER = "manual_trigger"
    SCHEDULED_TRIGGER = "scheduled_trigger"
    
    # Actions
    IAM_ACTION = "iam_action"
    ENDPOINT_ACTION = "endpoint_action"
    NETWORK_ACTION = "network_action"
    EMAIL_ACTION = "email_action"
    CLOUD_ACTION = "cloud_action"
    
    # Logic
    CONDITION = "condition"
    LOOP = "loop"
    PARALLEL = "parallel"
    
    # Observables & Analyzers
    EXTRACT_OBSERVABLE = "extract_observable"
    RUN_ANALYZER = "run_analyzer"
    
    # Integration
    CREATE_TICKET = "create_ticket"
    UPDATE_INCIDENT = "update_incident"
    SEND_NOTIFICATION = "send_notification"

class PlaybookNode(BaseModel):
    """Playbook node compatible with React Flow."""
    id: str
    type: NodeType
    position: Dict[str, float]  # {x, y} for React Flow
    data: Dict[str, Any]  # Node-specific configuration
    
    # React Flow compatibility
    source_position: Optional[str] = "right"
    target_position: Optional[str] = "left"
    
    # Node configuration
    label: Optional[str] = None
    config: Dict[str, Any] = Field(default_factory=dict)

class PlaybookEdge(BaseModel):
    """Playbook edge (connection) compatible with React Flow."""
    id: str
    source: str  # Source node ID
    target: str  # Target node ID
    source_handle: Optional[str] = None
    target_handle: Optional[str] = None
    animated: bool = False
    style: Optional[Dict[str, Any]] = None
    label: Optional[str] = None
    
    # Conditional logic
    condition: Optional[str] = None  # JavaScript expression for conditional edges

class Playbook(BaseModel):
    """Playbook model compatible with React Flow editor."""
    id: str
    tenant_id: str
    name: str
    description: Optional[str] = None
    category: str  # malware, phishing, suspicious_login, etc.
    version: str = "1.0.0"
    
    # React Flow graph structure
    nodes: List[PlaybookNode] = Field(default_factory=list)
    edges: List[PlaybookEdge] = Field(default_factory=list)
    
    # Framework mappings
    nist_controls: List[str] = Field(default_factory=list)  # NIST SP 800-53 control IDs
    mitre_tactics: List[str] = Field(default_factory=list)  # MITRE tactics (TA0001, etc.)
    mitre_techniques: List[str] = Field(default_factory=list)  # MITRE techniques (T1078, etc.)
    
    # Execution
    enabled: bool = True
    requires_approval: bool = False
    
    # Metadata
    created_at: str
    updated_at: str
    created_by: Optional[str] = None
```

### 1.2 Playbook Execution from Editor

```python
# backend/services/soar_agent/app/services/playbook_executor.py

from app.models.playbook import Playbook, PlaybookNode, NodeType
from app.services.action_service import ActionExecutionService

class PlaybookExecutor:
    """Execute playbooks created in the editor."""
    
    def __init__(self):
        self.action_service = ActionExecutionService()
    
    async def execute_playbook(
        self,
        playbook: Playbook,
        context: Dict[str, Any],
        tenant_id: str,
        incident_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute playbook from React Flow graph structure.
        
        Args:
            playbook: Playbook with nodes and edges
            context: Execution context (alert, incident, observables, etc.)
            tenant_id: Tenant identifier
            incident_id: Optional incident ID
            
        Returns:
            Execution results
        """
        # Find start node (trigger)
        start_node = self._find_start_node(playbook.nodes)
        if not start_node:
            raise ValueError("No start node found in playbook")
        
        # Execute graph traversal
        execution_results = []
        visited_nodes = set()
        
        await self._execute_node(
            node=start_node,
            playbook=playbook,
            context=context,
            tenant_id=tenant_id,
            incident_id=incident_id,
            visited=visited_nodes,
            results=execution_results
        )
        
        return {
            "playbook_id": playbook.id,
            "status": "completed",
            "nodes_executed": len(execution_results),
            "results": execution_results
        }
    
    async def _execute_node(
        self,
        node: PlaybookNode,
        playbook: Playbook,
        context: Dict[str, Any],
        tenant_id: str,
        incident_id: Optional[str],
        visited: set,
        results: List[Dict[str, Any]]
    ):
        """Execute a single node and traverse edges."""
        if node.id in visited:
            return  # Prevent cycles
        
        visited.add(node.id)
        
        # Execute node based on type
        node_result = await self._execute_node_by_type(
            node,
            context,
            tenant_id,
            incident_id
        )
        
        results.append({
            "node_id": node.id,
            "node_type": node.type.value,
            "result": node_result
        })
        
        # Find outgoing edges
        outgoing_edges = [
            edge for edge in playbook.edges
            if edge.source == node.id
        ]
        
        # Evaluate edge conditions and traverse
        for edge in outgoing_edges:
            should_traverse = True
            
            # Check conditional edge
            if edge.condition:
                should_traverse = self._evaluate_condition(
                    edge.condition,
                    context,
                    node_result
                )
            
            if should_traverse:
                # Find target node
                target_node = next(
                    (n for n in playbook.nodes if n.id == edge.target),
                    None
                )
                
                if target_node:
                    await self._execute_node(
                        target_node,
                        playbook,
                        context,
                        tenant_id,
                        incident_id,
                        visited,
                        results
                    )
    
    async def _execute_node_by_type(
        self,
        node: PlaybookNode,
        context: Dict[str, Any],
        tenant_id: str,
        incident_id: Optional[str]
    ) -> Dict[str, Any]:
        """Execute node based on its type."""
        node_type = node.type
        config = node.data.get("config", {})
        
        if node_type == NodeType.IAM_ACTION:
            action_type = config.get("action_type")
            parameters = self._resolve_parameters(config.get("parameters", {}), context)
            return await self.action_service.execute_action(
                ActionType(action_type),
                parameters,
                tenant_id,
                incident_id
            )
        
        elif node_type == NodeType.ENDPOINT_ACTION:
            action_type = config.get("action_type")
            parameters = self._resolve_parameters(config.get("parameters", {}), context)
            return await self.action_service.execute_action(
                ActionType(action_type),
                parameters,
                tenant_id,
                incident_id
            )
        
        elif node_type == NodeType.EXTRACT_OBSERVABLE:
            # Extract observable from context
            observable_type = config.get("observable_type")
            source_field = config.get("source_field")
            value = self._get_nested_value(context, source_field)
            
            return {
                "observable_type": observable_type,
                "value": value,
                "extracted": True
            }
        
        elif node_type == NodeType.RUN_ANALYZER:
            # Run analyzer on observable
            analyzer_id = config.get("analyzer_id")
            observable_id = config.get("observable_id")
            
            # Implementation depends on analyzer service
            return {"analyzer_id": analyzer_id, "status": "completed"}
        
        # ... handle other node types
        
        return {"status": "completed"}
```

---

## 2. NIST Control Mapping

### 2.1 NIST SP 800-53 Control Categories

**Reference:** NIST SP 800-53 Rev. 5

**Control Families:**
- **AC** - Access Control
- **AU** - Audit and Accountability
- **CA** - Assessment, Authorization, and Monitoring
- **CM** - Configuration Management
- **CP** - Contingency Planning
- **IA** - Identification and Authentication
- **IR** - Incident Response
- **MA** - Maintenance
- **MP** - Media Protection
- **PE** - Physical and Environmental Protection
- **PL** - Planning
- **PS** - Personnel Security
- **RA** - Risk Assessment
- **SA** - System and Services Acquisition
- **SC** - System and Communications Protection
- **SI** - System and Information Integrity
- **SR** - Supply Chain Risk Management

### 2.2 NIST Control Mapping Service

```python
# backend/services/orchestrator/app/services/nist_mapper.py

from typing import Dict, Any, List, Optional
from app.models.incident import Incident
from app.models.alert import Alert

class NISTControlMapper:
    """Map incidents and alerts to NIST SP 800-53 controls."""
    
    # Mapping of threat types to NIST controls
    THREAT_TO_CONTROLS = {
        "malware": [
            "SI-3",  # Malicious Code Protection
            "SI-4",  # System Monitoring
            "IR-4",  # Incident Handling
            "SC-7",  # Boundary Protection
        ],
        "phishing": [
            "AT-2",  # Security Awareness Training
            "IR-4",  # Incident Handling
            "SI-4",  # System Monitoring
            "AC-2",  # Account Management
        ],
        "suspicious_login": [
            "AC-2",  # Account Management
            "AC-7",  # Unsuccessful Logon Attempts
            "IA-2",  # Identification and Authentication
            "IA-4",  # Identifier Management
            "IR-4",  # Incident Handling
        ],
        "data_exfiltration": [
            "AC-3",  # Access Enforcement
            "AC-4",  # Information Flow Enforcement
            "AU-2",  # Audit Events
            "SC-7",  # Boundary Protection
            "IR-4",  # Incident Handling
        ],
        "insider_threat": [
            "AC-2",  # Account Management
            "AC-3",  # Access Enforcement
            "AU-2",  # Audit Events
            "PS-3",  # Personnel Screening
            "IR-4",  # Incident Handling
        ],
        "ddos": [
            "SC-5",  # Denial of Service Protection
            "SC-7",  # Boundary Protection
            "IR-4",  # Incident Handling
        ],
        "ransomware": [
            "SI-3",  # Malicious Code Protection
            "CP-9",  # System Backup
            "CP-10", # System Recovery and Reconstitution
            "IR-4",  # Incident Handling
        ]
    }
    
    # Mapping of actions to NIST controls
    ACTION_TO_CONTROLS = {
        "disable_user": ["AC-2", "IA-4"],
        "force_password_reset": ["IA-2", "IA-5"],
        "quarantine_machine": ["SC-7", "SI-4"],
        "add_firewall_rule": ["SC-7", "AC-4"],
        "collect_forensics": ["AU-4", "AU-9"],
        "block_ip": ["SC-7", "AC-4"],
    }
    
    async def map_incident_to_controls(
        self,
        incident: Incident
    ) -> Dict[str, Any]:
        """
        Map incident to relevant NIST controls.
        
        Returns:
            {
                "controls": [
                    {
                        "id": "IR-4",
                        "family": "IR",
                        "title": "Incident Handling",
                        "relevance": "primary",
                        "reasoning": "Incident response playbook execution"
                    },
                    ...
                ],
                "primary_controls": ["IR-4", "SI-3"],
                "supporting_controls": ["AC-2", "AU-2"]
            }
        """
        controls = []
        
        # Map based on threat classification
        if incident.threat_classification:
            threat_controls = self.THREAT_TO_CONTROLS.get(
                incident.threat_classification,
                []
            )
            
            for control_id in threat_controls:
                control_info = await self._get_control_info(control_id)
                controls.append({
                    **control_info,
                    "relevance": "primary",
                    "reasoning": f"Threat type: {incident.threat_classification}"
                })
        
        # Map based on actions taken
        if incident.actions_taken:
            for action in incident.actions_taken:
                action_type = action.get("action_type")
                action_controls = self.ACTION_TO_CONTROLS.get(action_type, [])
                
                for control_id in action_controls:
                    # Avoid duplicates
                    if not any(c["id"] == control_id for c in controls):
                        control_info = await self._get_control_info(control_id)
                        controls.append({
                            **control_info,
                            "relevance": "supporting",
                            "reasoning": f"Action taken: {action_type}"
                        })
        
        # Categorize controls
        primary_controls = [
            c["id"] for c in controls if c["relevance"] == "primary"
        ]
        supporting_controls = [
            c["id"] for c in controls if c["relevance"] == "supporting"
        ]
        
        return {
            "controls": controls,
            "primary_controls": primary_controls,
            "supporting_controls": supporting_controls,
            "total_controls": len(controls)
        }
    
    async def _get_control_info(self, control_id: str) -> Dict[str, Any]:
        """Get NIST control information."""
        # Load from knowledge base or database
        # Format: "IR-4" -> family="IR", number=4
        family = control_id.split("-")[0]
        number = control_id.split("-")[1]
        
        # Query knowledge base for control details
        # This would come from NIST SP 800-53 knowledge base
        return {
            "id": control_id,
            "family": family,
            "number": number,
            "title": self._get_control_title(control_id),
            "description": self._get_control_description(control_id),
            "url": f"https://csrc.nist.gov/projects/risk-management/sp800-53-controls/release-search#!/control?version=5.1&number={control_id}"
        }
    
    def _get_control_title(self, control_id: str) -> str:
        """Get control title from mapping."""
        titles = {
            "IR-4": "Incident Handling",
            "SI-3": "Malicious Code Protection",
            "SI-4": "System Monitoring",
            "AC-2": "Account Management",
            "AC-7": "Unsuccessful Logon Attempts",
            "IA-2": "Identification and Authentication",
            "SC-7": "Boundary Protection",
            # ... more mappings
        }
        return titles.get(control_id, control_id)
```

### 2.3 NIST Control Display in UI

```typescript
// frontend/src/app/dashboard/incidents/[id]/components/NISTControlsPanel.tsx

'use client';

import { useQuery } from '@tanstack/react-query';
import { getIncidentNISTControls } from '@/lib/api/incidents';

interface NISTControl {
  id: string;
  family: string;
  title: string;
  description: string;
  relevance: 'primary' | 'supporting';
  reasoning: string;
  url: string;
}

export default function NISTControlsPanel({ incidentId }: { incidentId: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ['incident-nist-controls', incidentId],
    queryFn: () => getIncidentNISTControls(incidentId),
  });

  if (isLoading) return <div>Loading NIST controls...</div>;

  const primaryControls = data?.controls.filter(c => c.relevance === 'primary') || [];
  const supportingControls = data?.controls.filter(c => c.relevance === 'supporting') || [];

  return (
    <div className="bg-[rgba(15,23,42,0.9)] rounded-xl border border-[rgba(15,23,42,0.95)] p-6">
      <h2 className="text-xl font-semibold text-text-main mb-4">
        NIST SP 800-53 Controls
      </h2>
      
      <div className="mb-4">
        <p className="text-sm text-text-muted">
          {data?.total_controls} controls mapped to this incident
        </p>
      </div>

      {primaryControls.length > 0 && (
        <div className="mb-6">
          <h3 className="text-lg font-semibold text-text-main mb-3">
            Primary Controls ({primaryControls.length})
          </h3>
          <div className="space-y-2">
            {primaryControls.map((control: NISTControl) => (
              <div
                key={control.id}
                className="p-3 rounded-lg border border-primary/30 bg-primary/10"
              >
                <div className="flex items-center justify-between mb-1">
                  <a
                    href={control.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-semibold text-primary hover:underline"
                  >
                    {control.id} - {control.title}
                  </a>
                  <span className="text-xs px-2 py-1 rounded bg-primary/20 text-primary">
                    Primary
                  </span>
                </div>
                <p className="text-sm text-text-muted mb-1">{control.description}</p>
                <p className="text-xs text-text-muted italic">{control.reasoning}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {supportingControls.length > 0 && (
        <div>
          <h3 className="text-lg font-semibold text-text-main mb-3">
            Supporting Controls ({supportingControls.length})
          </h3>
          <div className="space-y-2">
            {supportingControls.map((control: NISTControl) => (
              <div
                key={control.id}
                className="p-3 rounded-lg border border-[rgba(15,23,42,0.9)]"
              >
                <div className="flex items-center justify-between mb-1">
                  <a
                    href={control.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-medium text-text-main hover:underline"
                  >
                    {control.id} - {control.title}
                  </a>
                  <span className="text-xs px-2 py-1 rounded bg-text-muted/20 text-text-muted">
                    Supporting
                  </span>
                </div>
                <p className="text-sm text-text-muted mb-1">{control.description}</p>
                <p className="text-xs text-text-muted italic">{control.reasoning}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
```

---

## 3. MITRE ATT&CK Framework Integration

### 3.1 MITRE ATT&CK Data Model

```python
# backend/services/orchestrator/app/models/mitre.py

from typing import Dict, Any, List, Optional
from pydantic import BaseModel

class MITRETactic(BaseModel):
    """MITRE ATT&CK tactic."""
    id: str  # TA0001, TA0002, etc.
    name: str
    description: str
    url: str

class MITRETechnique(BaseModel):
    """MITRE ATT&CK technique."""
    id: str  # T1078, T1566, etc.
    name: str
    description: str
    tactics: List[str]  # List of tactic IDs
    subtechniques: Optional[List[Dict[str, Any]]] = None
    platforms: List[str]  # Windows, Linux, macOS, etc.
    url: str

class MITREMapping(BaseModel):
    """MITRE mapping for incident/alert."""
    tactics: List[MITRETactic]
    techniques: List[MITRETechnique]
    subtechniques: Optional[List[Dict[str, Any]]] = None
    confidence: float  # 0-1
    reasoning: str
```

### 3.2 MITRE Mapping Service

```python
# backend/services/orchestrator/app/services/mitre_mapper.py

from typing import Dict, Any, List, Optional
from app.models.incident import Incident
from app.models.alert import Alert
from app.models.mitre import MITRETactic, MITRETechnique, MITREMapping

class MITREMapper:
    """Map incidents and alerts to MITRE ATT&CK framework."""
    
    # Threat type to MITRE technique mapping
    THREAT_TO_TECHNIQUES = {
        "malware": {
            "tactics": ["TA0001", "TA0002", "TA0003"],  # Initial Access, Execution, Persistence
            "techniques": ["T1059", "T1055", "T1078"],  # Command and Scripting, Process Injection, Valid Accounts
        },
        "phishing": {
            "tactics": ["TA0001"],  # Initial Access
            "techniques": ["T1566"],  # Phishing
        },
        "suspicious_login": {
            "tactics": ["TA0001", "TA0004"],  # Initial Access, Privilege Escalation
            "techniques": ["T1078", "T1078.001", "T1078.003"],  # Valid Accounts, Default Accounts, Local Accounts
        },
        "data_exfiltration": {
            "tactics": ["TA0010"],  # Exfiltration
            "techniques": ["T1041", "T1048"],  # Exfiltration Over C2 Channel, Exfiltration Over Alternative Protocol
        },
        "insider_threat": {
            "tactics": ["TA0001", "TA0004", "TA0006"],  # Initial Access, Privilege Escalation, Credential Access
            "techniques": ["T1078", "T1083", "T1005"],  # Valid Accounts, File and Directory Discovery, Data from Local System
        },
        "ddos": {
            "tactics": ["TA0040"],  # Impact
            "techniques": ["T1498"],  # T1498 - Network Denial of Service
        },
        "ransomware": {
            "tactics": ["TA0040", "TA0002"],  # Impact, Execution
            "techniques": ["T1486", "T1059"],  # Data Encrypted for Impact, Command and Scripting
        }
    }
    
    async def map_incident_to_mitre(
        self,
        incident: Incident,
        alert: Optional[Alert] = None
    ) -> MITREMapping:
        """
        Map incident to MITRE ATT&CK framework.
        
        Returns:
            MITREMapping with tactics, techniques, and reasoning
        """
        tactics = []
        techniques = []
        reasoning_parts = []
        
        # Map based on threat classification
        if incident.threat_classification:
            threat_mapping = self.THREAT_TO_TECHNIQUES.get(
                incident.threat_classification,
                {}
            )
            
            # Get tactics
            for tactic_id in threat_mapping.get("tactics", []):
                tactic = await self._get_tactic(tactic_id)
                if tactic:
                    tactics.append(tactic)
                    reasoning_parts.append(f"Threat type '{incident.threat_classification}' maps to tactic {tactic_id}")
            
            # Get techniques
            for technique_id in threat_mapping.get("techniques", []):
                technique = await self._get_technique(technique_id)
                if technique:
                    techniques.append(technique)
                    reasoning_parts.append(f"Threat type '{incident.threat_classification}' maps to technique {technique_id}")
        
        # Enhance with AI analysis if available
        if alert and alert.ai_classification:
            ai_mitre = await self._get_ai_mitre_mapping(alert)
            if ai_mitre:
                # Merge AI-suggested mappings
                for tactic in ai_mitre.get("tactics", []):
                    if not any(t.id == tactic.id for t in tactics):
                        tactics.append(tactic)
                
                for technique in ai_mitre.get("techniques", []):
                    if not any(t.id == technique.id for t in techniques):
                        techniques.append(technique)
                
                reasoning_parts.append("AI analysis provided additional MITRE mappings")
        
        return MITREMapping(
            tactics=tactics,
            techniques=techniques,
            confidence=0.85,  # Calculate based on evidence
            reasoning="; ".join(reasoning_parts)
        )
    
    async def _get_tactic(self, tactic_id: str) -> Optional[MITRETactic]:
        """Get MITRE tactic from knowledge base."""
        # Query knowledge base or MITRE API
        tactics_map = {
            "TA0001": {
                "name": "Initial Access",
                "description": "The adversary is trying to get into your network.",
                "url": "https://attack.mitre.org/tactics/TA0001"
            },
            "TA0002": {
                "name": "Execution",
                "description": "The adversary is trying to run malicious code.",
                "url": "https://attack.mitre.org/tactics/TA0002"
            },
            # ... more tactics
        }
        
        tactic_data = tactics_map.get(tactic_id)
        if tactic_data:
            return MITRETactic(
                id=tactic_id,
                **tactic_data
            )
        return None
    
    async def _get_technique(self, technique_id: str) -> Optional[MITRETechnique]:
        """Get MITRE technique from knowledge base."""
        # Query knowledge base or MITRE API
        techniques_map = {
            "T1078": {
                "name": "Valid Accounts",
                "description": "Adversaries may obtain and abuse credentials of existing accounts.",
                "tactics": ["TA0001", "TA0004"],
                "platforms": ["Windows", "Linux", "macOS"],
                "url": "https://attack.mitre.org/techniques/T1078"
            },
            "T1566": {
                "name": "Phishing",
                "description": "Adversaries may send phishing messages to gain access to victim systems.",
                "tactics": ["TA0001"],
                "platforms": ["Windows", "Linux", "macOS"],
                "url": "https://attack.mitre.org/techniques/T1566"
            },
            # ... more techniques
        }
        
        technique_data = techniques_map.get(technique_id)
        if technique_data:
            return MITRETechnique(
                id=technique_id,
                **technique_data
            )
        return None
    
    async def _get_ai_mitre_mapping(self, alert: Alert) -> Optional[Dict[str, Any]]:
        """Get MITRE mapping from AI analysis."""
        # Use AI to analyze alert and suggest MITRE mappings
        # This would call Model Gateway with MITRE knowledge base
        pass
```

### 3.3 MITRE Display in UI

```typescript
// frontend/src/app/dashboard/incidents/[id]/components/MITREPanel.tsx

'use client';

import { useQuery } from '@tanstack/react-query';
import { getIncidentMITREMapping } from '@/lib/api/incidents';

interface MITRETactic {
  id: string;
  name: string;
  description: string;
  url: string;
}

interface MITRETechnique {
  id: string;
  name: string;
  description: string;
  tactics: string[];
  platforms: string[];
  url: string;
}

export default function MITREPanel({ incidentId }: { incidentId: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ['incident-mitre', incidentId],
    queryFn: () => getIncidentMITREMapping(incidentId),
  });

  if (isLoading) return <div>Loading MITRE mapping...</div>;

  return (
    <div className="bg-[rgba(15,23,42,0.9)] rounded-xl border border-[rgba(15,23,42,0.95)] p-6">
      <h2 className="text-xl font-semibold text-text-main mb-4">
        MITRE ATT&CK Framework
      </h2>
      
      <div className="mb-4">
        <p className="text-sm text-text-muted">
          Confidence: <span className="font-semibold">{(data?.confidence * 100).toFixed(0)}%</span>
        </p>
        <p className="text-xs text-text-muted italic mt-1">{data?.reasoning}</p>
      </div>

      {data?.tactics && data.tactics.length > 0 && (
        <div className="mb-6">
          <h3 className="text-lg font-semibold text-text-main mb-3">
            Tactics ({data.tactics.length})
          </h3>
          <div className="space-y-2">
            {data.tactics.map((tactic: MITRETactic) => (
              <div
                key={tactic.id}
                className="p-3 rounded-lg border border-[rgba(15,23,42,0.9)] hover:border-primary/30 transition-colors"
              >
                <a
                  href={tactic.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-semibold text-primary hover:underline"
                >
                  {tactic.id} - {tactic.name}
                </a>
                <p className="text-sm text-text-muted mt-1">{tactic.description}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {data?.techniques && data.techniques.length > 0 && (
        <div>
          <h3 className="text-lg font-semibold text-text-main mb-3">
            Techniques ({data.techniques.length})
          </h3>
          <div className="space-y-2">
            {data.techniques.map((technique: MITRETechnique) => (
              <div
                key={technique.id}
                className="p-3 rounded-lg border border-[rgba(15,23,42,0.9)] hover:border-primary/30 transition-colors"
              >
                <div className="flex items-center justify-between mb-1">
                  <a
                    href={technique.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-semibold text-primary hover:underline"
                  >
                    {technique.id} - {technique.name}
                  </a>
                  <span className="text-xs px-2 py-1 rounded bg-primary/20 text-primary">
                    {technique.platforms.join(', ')}
                  </span>
                </div>
                <p className="text-sm text-text-muted mb-2">{technique.description}</p>
                <div className="flex flex-wrap gap-1">
                  {technique.tactics.map((tacticId) => (
                    <span
                      key={tacticId}
                      className="text-xs px-2 py-0.5 rounded bg-text-muted/20 text-text-muted"
                    >
                      {tacticId}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
```

---

## 4. Playbook Editor Integration

### 4.1 Playbook Node Configuration with NIST/MITRE

```typescript
// frontend/src/components/playbook-editor/PlaybookPropertiesPanel.tsx

// Add NIST/MITRE fields to node configuration

interface NodeConfig {
  // ... existing fields
  nist_controls?: string[];  // NIST control IDs
  mitre_tactics?: string[];  // MITRE tactic IDs
  mitre_techniques?: string[];  // MITRE technique IDs
}

// In the properties panel, add:
<div className="mb-4">
  <label className="block text-sm font-medium text-text-main mb-2">
    NIST Controls
  </label>
  <NISTControlSelector
    value={localNode.data.nist_controls || []}
    onChange={(controls) => handleUpdate({ nist_controls: controls })}
  />
</div>

<div className="mb-4">
  <label className="block text-sm font-medium text-text-main mb-2">
    MITRE ATT&CK
  </label>
  <MITRESelector
    tactics={localNode.data.mitre_tactics || []}
    techniques={localNode.data.mitre_techniques || []}
    onTacticsChange={(tactics) => handleUpdate({ mitre_tactics: tactics })}
    onTechniquesChange={(techniques) => handleUpdate({ mitre_techniques: techniques })}
  />
</div>
```

### 4.2 Playbook Execution with Framework Context

```python
# backend/services/soar_agent/app/services/playbook_executor.py

# Enhanced to include NIST/MITRE context

async def execute_playbook(
    self,
    playbook: Playbook,
    context: Dict[str, Any],
    tenant_id: str,
    incident_id: Optional[str] = None
) -> Dict[str, Any]:
    """Execute playbook with framework context."""
    
    # Add NIST/MITRE context to execution
    if incident_id:
        # Get incident framework mappings
        nist_mapper = NISTControlMapper()
        mitre_mapper = MITREMapper()
        
        incident = await self._get_incident(incident_id)
        nist_mapping = await nist_mapper.map_incident_to_controls(incident)
        mitre_mapping = await mitre_mapper.map_incident_to_mitre(incident)
        
        context["nist_controls"] = nist_mapping
        context["mitre_attack"] = mitre_mapping
    
    # Execute playbook nodes
    # ... existing execution logic
```

---

## 5. Incident Detail View Integration

### 5.1 Complete Incident View

```typescript
// frontend/src/app/dashboard/incidents/[id]/page.tsx

'use client';

import NISTControlsPanel from './components/NISTControlsPanel';
import MITREPanel from './components/MITREPanel';
import PlaybookRecommendation from './components/PlaybookRecommendation';

export default function IncidentDetailPage({ params }: { params: { id: string } }) {
  const { data: incident } = useQuery({
    queryKey: ['incident', params.id],
    queryFn: () => getIncident(params.id),
  });

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-text-main mb-2">
          {incident?.title}
        </h1>
        <p className="text-text-muted">Incident ID: {params.id}</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2 mb-8">
        {/* NIST Controls Panel */}
        <NISTControlsPanel incidentId={params.id} />
        
        {/* MITRE ATT&CK Panel */}
        <MITREPanel incidentId={params.id} />
      </div>

      {/* Playbook Recommendation */}
      <div className="mb-8">
        <PlaybookRecommendation
          incidentId={params.id}
          mitreMapping={incident?.mitre_mapping}
          nistControls={incident?.nist_controls}
        />
      </div>

      {/* Other incident details... */}
    </div>
  );
}
```

---

## 6. API Endpoints

### 6.1 Framework Mapping APIs

```
# NIST Controls
GET  /api/v1/incidents/{id}/nist-controls        # Get NIST control mapping
POST /api/v1/incidents/{id}/nist-controls      # Update NIST mapping

# MITRE ATT&CK
GET  /api/v1/incidents/{id}/mitre-mapping      # Get MITRE mapping
POST /api/v1/incidents/{id}/mitre-mapping      # Update MITRE mapping

# Playbook Integration
GET  /api/v1/playbooks?mitre_technique=T1078   # Filter by MITRE technique
GET  /api/v1/playbooks?nist_control=IR-4       # Filter by NIST control
POST /api/v1/playbooks/{id}/execute            # Execute with framework context
```

---

## 7. Database Schema Extensions

```sql
-- Add framework mappings to incidents
ALTER TABLE incidents ADD COLUMN nist_controls JSONB;
ALTER TABLE incidents ADD COLUMN mitre_tactics TEXT[];
ALTER TABLE incidents ADD COLUMN mitre_techniques TEXT[];

-- Add framework mappings to playbooks
ALTER TABLE playbooks ADD COLUMN nist_controls TEXT[];
ALTER TABLE playbooks ADD COLUMN mitre_tactics TEXT[];
ALTER TABLE playbooks ADD COLUMN mitre_techniques TEXT[];

-- MITRE knowledge base cache
CREATE TABLE mitre_tactics (
    id TEXT PRIMARY KEY,  -- TA0001, etc.
    name TEXT NOT NULL,
    description TEXT,
    url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE mitre_techniques (
    id TEXT PRIMARY KEY,  -- T1078, etc.
    name TEXT NOT NULL,
    description TEXT,
    tactics TEXT[],
    platforms TEXT[],
    url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- NIST controls cache
CREATE TABLE nist_controls (
    id TEXT PRIMARY KEY,  -- IR-4, etc.
    family TEXT NOT NULL,  -- IR, SI, etc.
    number TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 8. Implementation Phases

### Phase 1: Framework Mapping (Week 1-2)
- NIST control mapper
- MITRE mapper
- Database schema updates
- API endpoints

### Phase 2: UI Integration (Week 3)
- NIST controls panel
- MITRE panel
- Incident detail view updates

### Phase 3: Playbook Editor Integration (Week 4)
- NIST/MITRE selectors in editor
- Playbook execution with framework context
- Framework-based playbook filtering

---

**Document Owner:** Architecture Team  
**Last Updated:** 2025-01-28  
**Status:** 📋 Ready for Implementation

