"""
Playbook Seeder Service

Loads and seeds Out-of-the-Box (OOTB) playbooks from YAML into the database.
Converts NIST phase structure to React Flow workflow format.
"""

import yaml
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from uuid import uuid4
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database import PlaybookDB, Base
from app.core.database import engine, get_db
from app.models import WorkflowStructure

logger = logging.getLogger(__name__)


def convert_phases_to_workflow(phases: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Convert NIST IR phases structure to React Flow workflow format.
    
    Each phase becomes a swimlane (group of nodes), and each step becomes a node.
    """
    nodes = []
    edges = []
    node_id_counter = 0
    
    # Phase colors for visual distinction
    phase_colors = {
        "Detection & Analysis": "#3b82f6",  # Blue
        "Containment": "#ef4444",  # Red
        "Eradication & Recovery": "#10b981",  # Green
        "Post-Incident": "#f59e0b",  # Amber
        "Preparation": "#8b5cf6",  # Purple
    }
    
    y_position = 0
    x_start = 100
    
    for phase_idx, phase in enumerate(phases):
        phase_name = phase.get("name", f"Phase {phase_idx + 1}")
        phase_color = phase_colors.get(phase_name, "#6b7280")
        steps = phase.get("steps", [])
        
        # Create phase header node (for visual grouping)
        phase_node_id = f"phase_{phase_idx}"
        nodes.append({
            "id": phase_node_id,
            "type": "phaseHeader",
            "position": {"x": x_start, "y": y_position},
            "data": {
                "label": phase_name,
                "phase": phase_name,
            },
            "style": {
                "background": phase_color,
                "color": "#ffffff",
                "fontWeight": "bold",
                "width": 300,
                "height": 40,
            }
        })
        y_position += 60
        
        # Create nodes for each step in the phase
        for step_idx, step in enumerate(steps):
            step_id = step.get("id", f"step_{node_id_counter}")
            step_type = step.get("type", "manual")
            step_actor = step.get("actor", "analyst")
            action_ref = step.get("action_ref", "")
            
            # Determine node type based on step type
            if step_type == "decision":
                node_type = "decision"
            elif step_type == "automated":
                node_type = "action"
            else:
                node_type = "manual"
            
            # Node position (horizontal flow within phase)
            x_position = x_start + (step_idx * 350)
            
            node = {
                "id": step_id,
                "type": node_type,
                "position": {"x": x_position, "y": y_position},
                "data": {
                    "label": step.get("label", step_id),
                    "description": step.get("description", ""),
                    "actor": step_actor,
                    "actionRef": action_ref,
                    "phase": phase_name,
                },
                "style": {
                    "background": phase_color,
                    "color": "#ffffff",
                    "border": "2px solid #ffffff",
                }
            }
            
            # Add specific styling for decision nodes
            if node_type == "decision":
                node["style"]["background"] = "#fbbf24"
                node["style"]["borderRadius"] = "50%"
                node["style"]["width"] = 120
                node["style"]["height"] = 120
            else:
                node["style"]["width"] = 280
                node["style"]["height"] = 100
            
            nodes.append(node)
            node_id_counter += 1
            
            # Create edge from previous step (or phase header)
            if step_idx == 0:
                # First step in phase connects from phase header
                edges.append({
                    "id": f"e_{phase_node_id}_{step_id}",
                    "source": phase_node_id,
                    "target": step_id,
                    "type": "smoothstep",
                })
            else:
                # Connect to previous step
                prev_step_id = steps[step_idx - 1].get("id", f"step_{node_id_counter - 2}")
                edges.append({
                    "id": f"e_{prev_step_id}_{step_id}",
                    "source": prev_step_id,
                    "target": step_id,
                    "type": "smoothstep",
                })
        
        # Move to next phase (below current phase)
        y_position += 150
    
    return {
        "nodes": nodes,
        "edges": edges,
        "viewport": {"x": 0, "y": 0, "zoom": 0.8}
    }


def load_ootb_playbooks() -> List[Dict[str, Any]]:
    """Load OOTB playbooks from YAML file."""
    yaml_path = Path(__file__).parent.parent / "data" / "ootb_playbooks.yaml"
    
    if not yaml_path.exists():
        logger.error(f"OOTB playbooks YAML not found at {yaml_path}")
        return []
    
    with open(yaml_path, "r") as f:
        data = yaml.safe_load(f)
        return data.get("playbooks", [])


def seed_playbook(db: Session, playbook_data: Dict[str, Any], tenant_id: Optional[str] = None) -> Optional[PlaybookDB]:
    """
    Seed a single playbook into the database.
    
    If tenant_id is None, playbook is marked as built-in (available to all tenants).
    """
    playbook_key = playbook_data.get("id")
    # Ensure we always have at least one trigger so preview/execution can work
    fallback_trigger = f"Alert: {playbook_key or playbook_data.get('name', 'playbook')}"
    triggers = playbook_data.get("triggers") or [fallback_trigger]
    playbook_data["triggers"] = triggers
    
    # Check if playbook already exists
    existing = db.query(PlaybookDB).filter(
        PlaybookDB.playbook_key == playbook_key,
        PlaybookDB.is_builtin == True
    ).first()
    
    if existing:
        # If category/category_filter are missing, update them from source data so chips render correctly
        needs_update = False
        categories = playbook_data.get("category", [])
        if (existing.category is None or existing.category.strip() == "") and categories:
            existing.category = ",".join(categories)
            needs_update = True
        if (existing.category_filter is None or existing.category_filter == {}) and categories:
            existing.category_filter = {"categories": categories}
            needs_update = True
        # Backfill triggers if missing so preview/execution can work on already-seeded playbooks
        if (not existing.triggers or len(existing.triggers) == 0) and triggers:
            existing.triggers = triggers
            needs_update = True
        if needs_update:
            db.add(existing)
            db.commit()
            db.refresh(existing)
            logger.info(f"Playbook {playbook_key} exists; backfilled category/category_filter/triggers")
        else:
            logger.info(f"Playbook {playbook_key} already exists, skipping")
        return existing
    
    # Convert phases to React Flow workflow
    phases = playbook_data.get("phases", [])
    workflow_dict = convert_phases_to_workflow(phases)
    
    # Use system tenant UUID for built-in playbooks
    from uuid import UUID
    system_tenant_id = UUID('9c7df7a9-5a0b-4412-a41c-0c0ea777b2f0')
    
    # Create playbook record
    playbook = PlaybookDB(
        id=uuid4(),
        tenant_id=system_tenant_id if tenant_id is None else UUID(tenant_id) if isinstance(tenant_id, str) else tenant_id,
        key=playbook_key,  # Required 'key' column uses playbook_key value
        playbook_key=playbook_key,
        name=playbook_data.get("name"),
        description=playbook_data.get("description"),
        target_type="incident",  # Default to 'incident' for OOTB playbooks
        category=",".join(playbook_data.get("category", [])),
        category_filter={"categories": playbook_data.get("category", [])},
        severity_filter={"min": playbook_data.get("severity_default", "medium")},
        workflow_ref=f"playbook:{playbook_key}",  # Workflow reference
        version=playbook_data.get("version", "1.0.0"),
        workflow=workflow_dict,
        is_enabled=True,
        is_builtin=True,
        is_template=True,
        severity_default=playbook_data.get("severity_default"),
        applicable_sources=playbook_data.get("applicable_sources", []),
        triggers=triggers,
        prerequisites=playbook_data.get("prerequisites", []),
        artifacts_required=playbook_data.get("artifacts_required", []),
        phases=phases,  # Store original phase structure as JSON
        nist_controls=playbook_data.get("nist_controls", []),
        soc2_criteria=playbook_data.get("soc2_criteria", []),
        mitre_tactics=playbook_data.get("mitre_tactics", []),
        mitre_techniques=playbook_data.get("mitre_techniques", []),
        cis_controls=playbook_data.get("cis_controls", []),
        tags=playbook_data.get("tags", []),
        requires_approval=False,  # Built-in playbooks don't require approval by default
    )
    
    db.add(playbook)
    db.commit()
    db.refresh(playbook)
    
    logger.info(f"Seeded playbook: {playbook_key} ({playbook.name})")
    return playbook


def seed_all_ootb_playbooks(db: Session) -> List[PlaybookDB]:
    """Seed all OOTB playbooks into the database."""
    playbooks_data = load_ootb_playbooks()
    seeded = []
    
    for playbook_data in playbooks_data:
        try:
            playbook = seed_playbook(db, playbook_data)
            if playbook:
                seeded.append(playbook)
        except Exception as e:
            logger.error(f"Error seeding playbook {playbook_data.get('id')}: {e}")
            continue
    
    logger.info(f"Seeded {len(seeded)} OOTB playbooks")
    return seeded


def get_builtin_playbooks(db: Session, tenant_id: str) -> List[PlaybookDB]:
    """
    Get all built-in playbooks available to a tenant.
    
    Built-in playbooks are shared across all tenants but can be cloned/customized.
    """
    return db.query(PlaybookDB).filter(
        PlaybookDB.is_builtin == True
    ).all()


def clone_builtin_playbook(
    db: Session,
    playbook_key: str,
    tenant_id: str,
    new_name: Optional[str] = None,
    created_by: Optional[str] = None
) -> Optional[PlaybookDB]:
    """
    Clone a built-in playbook for a tenant, allowing customization.
    
    Returns the cloned playbook which can then be modified.
    """
    # Find the built-in playbook
    builtin = db.query(PlaybookDB).filter(
        PlaybookDB.playbook_key == playbook_key,
        PlaybookDB.is_builtin == True
    ).first()
    
    if not builtin:
        logger.error(f"Built-in playbook {playbook_key} not found")
        return None
    
    # Parse phases if stored as JSON string
    phases_data = builtin.phases
    if isinstance(phases_data, str):
        try:
            phases_data = json.loads(phases_data)
        except (json.JSONDecodeError, TypeError):
            phases_data = None
    
    # Create a clone
    cloned = PlaybookDB(
        id=uuid4(),
        tenant_id=tenant_id,
        playbook_key=None,  # Cloned playbooks don't have a key
        name=new_name or f"{builtin.name} (Custom)",
        description=builtin.description,
        category=builtin.category,
        version="1.0.0",  # Start at 1.0.0 for custom
        workflow=builtin.workflow,  # Copy workflow
        is_builtin=False,  # This is a custom playbook
        is_template=False,
        severity_default=builtin.severity_default,
        applicable_sources=builtin.applicable_sources or [],
        triggers=builtin.triggers or [],
        prerequisites=builtin.prerequisites or [],
        artifacts_required=builtin.artifacts_required or [],
        phases=phases_data,  # Copy phases
        nist_controls=builtin.nist_controls or [],
        mitre_tactics=builtin.mitre_tactics or [],
        mitre_techniques=builtin.mitre_techniques or [],
        cis_controls=builtin.cis_controls or [],
        tags=builtin.tags or [],
        requires_approval=True,  # Custom clone should be reviewed/approved
        created_by=created_by,
    )
    
    db.add(cloned)
    db.commit()
    db.refresh(cloned)
    
    logger.info(f"Cloned playbook {playbook_key} for tenant {tenant_id}")
    return cloned


if __name__ == "__main__":
    # Standalone script to seed playbooks
    logging.basicConfig(level=logging.INFO)
    
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)
    
    # Seed playbooks
    db = next(get_db())
    try:
        seeded = seed_all_ootb_playbooks(db)
        print(f"Successfully seeded {len(seeded)} OOTB playbooks")
    finally:
        db.close()
