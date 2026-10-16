"""Alert service layer."""

from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional, Tuple, List
import httpx
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../libs"))

from sg_core.models import Alert
from app.core.config import settings


class AlertService:
    """Service for alert operations."""
    
    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
        # Convert tenant_id string to UUID for database queries
        try:
            self.tenant_uuid = UUID(tenant_id)
        except (ValueError, TypeError):
            self.tenant_uuid = None
        self.orchestrator_url = settings.ORCHESTRATOR_URL
    
    def list_alerts(
        self,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[Alert], int]:
        """List alerts with filters."""
        if not self.tenant_uuid:
            return [], 0
        
        query = self.db.query(Alert).filter(Alert.tenant_id == self.tenant_uuid)
        
        if status:
            query = query.filter(Alert.status == status)
        if severity:
            # In V1, we'd join with alert_ai_analysis table
            # For now, stub
            pass
        
        total = query.count()
        alerts = query.order_by(Alert.detection_time.desc()).offset(offset).limit(limit).all()
        
        return alerts, total
    
    def get_alert(self, alert_id: UUID) -> Optional[Alert]:
        """Get alert by ID."""
        if not self.tenant_uuid:
            return None
        
        return self.db.query(Alert).filter(
            Alert.id == alert_id,
            Alert.tenant_id == self.tenant_uuid
        ).first()
    
    def get_ai_analysis(self, alert_id: UUID) -> List[dict]:
        """Get AI analysis for an alert."""
        # In V1, query alert_ai_analysis table
        # For now, return empty list
        return []
    
    def triage_alert(self, alert_id: UUID, force_reanalyze: bool = False) -> Optional[dict]:
        """Trigger AI triage via orchestrator."""
        alert = self.get_alert(alert_id)
        if not alert:
            return None
        
        # Call orchestrator service
        try:
            with httpx.Client() as client:
                response = client.post(
                    f"{self.orchestrator_url}/internal/orchestrator/handle_alert",
                    json={
                        "tenant_id": self.tenant_id,
                        "alert_id": str(alert_id),
                        "force_reanalyze": force_reanalyze
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
        except httpx.RequestError as e:
            raise Exception(f"Failed to call orchestrator: {e}")
    
    def submit_feedback(self, alert_id: UUID, feedback: dict) -> str:
        """Submit feedback on AI triage."""
        # Store feedback in alert_triage_feedback table
        # For V1 stub, return a fake ID
        return "fb-123"

