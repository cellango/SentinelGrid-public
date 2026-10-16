"""Load and manage alert type to playbook mappings."""

import yaml
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from uuid import UUID, uuid4
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)


class PlaybookMappingLoader:
    """Loads and manages alert-to-playbook mappings."""
    
    def __init__(self, db: Session):
        """
        Initialize mapping loader.
        
        Args:
            db: Database session
        """
        self.db = db
    
    def load_mappings_from_yaml(self, yaml_path: Optional[Path] = None) -> List[Dict[str, Any]]:
        """
        Load alert-to-playbook mappings from YAML file.
        
        Args:
            yaml_path: Path to YAML file (defaults to config/alert_playbook_mapping.yaml)
        
        Returns:
            List of mapping configurations
        """
        if yaml_path is None:
            yaml_path = Path(__file__).parent.parent / "config" / "alert_playbook_mapping.yaml"
        
        if not yaml_path.exists():
            logger.error(f"Mapping file not found: {yaml_path}")
            return []
        
        with open(yaml_path, "r") as f:
            data = yaml.safe_load(f)
            return data.get("mappings", [])
    
    def seed_mappings_for_tenant(
        self,
        tenant_id: str,
        overwrite: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Seed default playbook mappings for a tenant.
        
        Args:
            tenant_id: Tenant UUID
            overwrite: If True, delete existing mappings first
        
        Returns:
            List of created mappings
        """
        try:
            # Load mappings from YAML
            mappings = self.load_mappings_from_yaml()
            
            if not mappings:
                logger.warning("No mappings found in YAML file")
                return []
            
            # Optionally delete existing mappings
            if overwrite:
                delete_query = text("""
                    DELETE FROM detection_playbook_mappings
                    WHERE tenant_id = :tenant_id
                """)
                self.db.execute(delete_query, {"tenant_id": UUID(tenant_id)})
                logger.info(f"Deleted existing mappings for tenant {tenant_id}")
            
            created_mappings = []
            
            for mapping in mappings:
                alert_type = mapping.get("alert_type")
                playbook_key = mapping.get("playbook_key")
                
                # Check if mapping already exists
                check_query = text("""
                    SELECT id FROM detection_playbook_mappings
                    WHERE tenant_id = :tenant_id AND alert_type = :alert_type
                """)
                existing = self.db.execute(check_query, {
                    "tenant_id": UUID(tenant_id),
                    "alert_type": alert_type
                }).fetchone()
                
                if existing and not overwrite:
                    logger.info(f"Mapping already exists for {alert_type}, skipping")
                    continue
                
                # Insert mapping
                insert_query = text("""
                    INSERT INTO detection_playbook_mappings (
                        id, tenant_id, alert_type, playbook_key,
                        auto_execute, requires_approval, severity_threshold,
                        created_at, updated_at
                    )
                    VALUES (
                        :id, :tenant_id, :alert_type, :playbook_key,
                        :auto_execute, :requires_approval, :severity_threshold,
                        NOW(), NOW()
                    )
                    ON CONFLICT (tenant_id, alert_type) DO UPDATE
                    SET playbook_key = EXCLUDED.playbook_key,
                        auto_execute = EXCLUDED.auto_execute,
                        requires_approval = EXCLUDED.requires_approval,
                        severity_threshold = EXCLUDED.severity_threshold,
                        updated_at = NOW()
                """)
                
                self.db.execute(insert_query, {
                    "id": uuid4(),
                    "tenant_id": UUID(tenant_id),
                    "alert_type": alert_type,
                    "playbook_key": playbook_key,
                    "auto_execute": mapping.get("auto_execute", False),
                    "requires_approval": mapping.get("requires_approval", True),
                    "severity_threshold": mapping.get("severity_threshold", "high")
                })
                
                created_mappings.append({
                    "alert_type": alert_type,
                    "playbook_key": playbook_key,
                    "auto_execute": mapping.get("auto_execute", False)
                })
                
                logger.info(f"Created mapping: {alert_type} → {playbook_key}")
            
            self.db.commit()
            
            logger.info(f"Seeded {len(created_mappings)} mappings for tenant {tenant_id}")
            return created_mappings
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error seeding mappings: {e}")
            raise
    
    def get_mapping_for_alert_type(
        self,
        tenant_id: str,
        alert_type: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get playbook mapping for an alert type.
        
        Args:
            tenant_id: Tenant UUID
            alert_type: Alert type identifier
        
        Returns:
            Mapping configuration or None
        """
        try:
            query = text("""
                SELECT 
                    id, alert_type, playbook_key, playbook_id,
                    auto_execute, requires_approval, severity_threshold
                FROM detection_playbook_mappings
                WHERE tenant_id = :tenant_id AND alert_type = :alert_type
            """)
            
            result = self.db.execute(query, {
                "tenant_id": UUID(tenant_id),
                "alert_type": alert_type
            }).fetchone()
            
            if not result:
                return None
            
            return {
                "id": str(result[0]),
                "alert_type": result[1],
                "playbook_key": result[2],
                "playbook_id": str(result[3]) if result[3] else None,
                "auto_execute": result[4],
                "requires_approval": result[5],
                "severity_threshold": result[6]
            }
            
        except Exception as e:
            logger.error(f"Error getting mapping: {e}")
            return None
    
    def list_mappings_for_tenant(self, tenant_id: str) -> List[Dict[str, Any]]:
        """
        List all playbook mappings for a tenant.
        
        Args:
            tenant_id: Tenant UUID
        
        Returns:
            List of mappings
        """
        try:
            query = text("""
                SELECT 
                    id, alert_type, playbook_key, playbook_id,
                    auto_execute, requires_approval, severity_threshold,
                    created_at, updated_at
                FROM detection_playbook_mappings
                WHERE tenant_id = :tenant_id
                ORDER BY alert_type
            """)
            
            results = self.db.execute(query, {
                "tenant_id": UUID(tenant_id)
            }).fetchall()
            
            return [
                {
                    "id": str(row[0]),
                    "alert_type": row[1],
                    "playbook_key": row[2],
                    "playbook_id": str(row[3]) if row[3] else None,
                    "auto_execute": row[4],
                    "requires_approval": row[5],
                    "severity_threshold": row[6],
                    "created_at": row[7].isoformat() if row[7] else None,
                    "updated_at": row[8].isoformat() if row[8] else None
                }
                for row in results
            ]
            
        except Exception as e:
            logger.error(f"Error listing mappings: {e}")
            return []


def seed_default_mappings(tenant_id: str, db: Session):
    """
    Seed default playbook mappings for a tenant.
    
    Standalone function for use in scripts.
    """
    loader = PlaybookMappingLoader(db)
    mappings = loader.seed_mappings_for_tenant(tenant_id)
    
    print(f"\n✓ Seeded {len(mappings)} playbook mappings for tenant {tenant_id}")
    print("\nMappings:")
    for mapping in mappings:
        auto = "AUTO" if mapping["auto_execute"] else "MANUAL"
        print(f"  {mapping['alert_type']} → {mapping['playbook_key']} ({auto})")
    
    return mappings


if __name__ == "__main__":
    import argparse
    import sys
    import os
    
    # Add parent directory to path
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
    
    from app.core.database import get_db
    
    parser = argparse.ArgumentParser(description="Seed playbook mappings for tenant")
    parser.add_argument("--tenant-id", required=True, help="Tenant UUID")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing mappings")
    
    args = parser.parse_args()
    
    # Get database session
    db = next(get_db())
    
    try:
        loader = PlaybookMappingLoader(db)
        mappings = loader.seed_mappings_for_tenant(
            tenant_id=args.tenant_id,
            overwrite=args.overwrite
        )
        
        print(f"\n✓ Successfully seeded {len(mappings)} mappings")
        
    finally:
        db.close()

