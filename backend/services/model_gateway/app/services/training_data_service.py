"""
Training Data Service
Collects and manages training data for per-tenant model fine-tuning
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
import uuid as uuid_lib

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

try:
    from app.models.database import TenantTrainingData
    MODELS_AVAILABLE = True
except ImportError:
    MODELS_AVAILABLE = False
    logger.warning("Database models not available")


class DataType(str, Enum):
    """Types of training data."""
    QA_PAIR = "qa_pair"
    INCIDENT = "incident"
    LOG = "log"
    DOCUMENT = "document"
    POLICY = "policy"
    PLAYBOOK = "playbook"
    ALERT = "alert"
    QUERY = "query"


class TrainingDataService:
    """Service for collecting and managing training data per tenant."""
    
    def __init__(self, db_session: Optional[Session] = None):
        self.db = db_session  # Will be injected via dependency
    
    def store_training_data(
        self,
        tenant_id: str,
        module: str,
        data_type: DataType,
        raw_data: Dict[str, Any],
        processed_data: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Store raw training data for a tenant.
        
        This data will be used later for fine-tuning the tenant's adapter.
        """
        training_record = {
            "tenant_id": tenant_id,
            "module": module,
            "data_type": data_type.value,
            "raw_data": raw_data,
            "processed_data": processed_data,
            "tags": tags or [],
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Store in database if available
        if self.db and MODELS_AVAILABLE:
            try:
                db_record = TenantTrainingData(
                    tenant_id=uuid_lib.UUID(tenant_id) if isinstance(tenant_id, str) else tenant_id,
                    module=module,
                    data_type=data_type.value,
                    raw_data=raw_data,
                    processed_data=processed_data,
                    tags=tags or []
                )
                self.db.add(db_record)
                self.db.commit()
                self.db.refresh(db_record)
                
                training_record["id"] = str(db_record.id)
                logger.info(f"Stored training data in database: {db_record.id}")
            except Exception as e:
                logger.error(f"Error storing training data in database: {e}")
                self.db.rollback()
                training_record["id"] = "error"
        else:
            logger.info(f"Stored training data (no DB): tenant={tenant_id}, module={module}, type={data_type.value}")
            training_record["id"] = "no-db"
        
        return {
            "status": "stored",
            **training_record
        }
    
    def store_qa_pair(
        self,
        tenant_id: str,
        module: str,
        question: str,
        answer: str,
        context: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Store a Q&A pair for training."""
        raw_data = {
            "question": question,
            "answer": answer,
            "context": context or {}
        }
        
        processed_data = {
            "input": question,
            "output": answer,
            "instruction": f"You are a cybersecurity expert. Answer the following question about {module}:"
        }
        
        return self.store_training_data(
            tenant_id=tenant_id,
            module=module,
            data_type=DataType.QA_PAIR,
            raw_data=raw_data,
            processed_data=processed_data,
            tags=tags
        )
    
    def store_incident(
        self,
        tenant_id: str,
        incident_id: str,
        incident_data: Dict[str, Any],
        ai_summary: Optional[str] = None,
        ai_recommendations: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Store incident data for training."""
        raw_data = {
            "incident_id": incident_id,
            "incident_data": incident_data,
            "ai_summary": ai_summary,
            "ai_recommendations": ai_recommendations
        }
        
        # Process into training format
        processed_data = None
        if ai_summary:
            processed_data = {
                "input": f"Summarize this incident: {incident_data.get('description', '')}",
                "output": ai_summary,
                "instruction": "You are a SOC analyst. Provide a concise incident summary."
            }
        
        return self.store_training_data(
            tenant_id=tenant_id,
            module="soc",
            data_type=DataType.INCIDENT,
            raw_data=raw_data,
            processed_data=processed_data
        )
    
    def get_training_data(
        self,
        tenant_id: str,
        module: Optional[str] = None,
        data_type: Optional[DataType] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Retrieve training data for a tenant.
        
        Used for preparing training datasets.
        """
        if not self.db or not MODELS_AVAILABLE:
            return []
        
        try:
            from sqlalchemy import select
            
            stmt = select(TenantTrainingData).where(
                TenantTrainingData.tenant_id == uuid_lib.UUID(tenant_id)
            )
            
            if module:
                stmt = stmt.where(TenantTrainingData.module == module)
            if data_type:
                stmt = stmt.where(TenantTrainingData.data_type == data_type.value)
            
            stmt = stmt.limit(limit).order_by(TenantTrainingData.created_at.desc())
            
            records = self.db.execute(stmt).scalars().all()
            
            return [
                {
                    "id": str(record.id),
                    "tenant_id": str(record.tenant_id),
                    "module": record.module,
                    "data_type": record.data_type,
                    "raw_data": record.raw_data,
                    "processed_data": record.processed_data,
                    "tags": record.tags or [],
                    "created_at": record.created_at.isoformat() if record.created_at else None
                }
                for record in records
            ]
        except Exception as e:
            logger.error(f"Error retrieving training data: {e}")
            return []
    
    def export_training_data(
        self,
        tenant_id: str,
        module: Optional[str] = None,
        format: str = "jsonl"
    ) -> str:
        """
        Export training data for model training.
        
        Returns path to exported file (for git storage or training pipeline).
        """
        training_data = self.get_training_data(tenant_id, module)
        
        if format == "jsonl":
            # Export as JSONL (one JSON object per line)
            export_path = f"/tmp/training-{tenant_id}-{module or 'all'}.jsonl"
            # TODO: Write to file
            return export_path
        
        return ""
    
    def prepare_training_dataset(
        self,
        tenant_id: str,
        module: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Prepare training dataset from collected data.
        
        Converts raw data into format suitable for fine-tuning.
        """
        training_data = self.get_training_data(tenant_id, module)
        
        # Filter and format
        qa_pairs = []
        for record in training_data:
            if record.get("processed_data"):
                qa_pairs.append(record["processed_data"])
        
        dataset = {
            "tenant_id": tenant_id,
            "module": module or "all",
            "sample_count": len(qa_pairs),
            "samples": qa_pairs,
            "prepared_at": datetime.utcnow().isoformat()
        }
        
        return dataset
    
    def cleanup_old_data(
        self,
        tenant_id: str,
        older_than_days: int = 365
    ) -> Dict[str, Any]:
        """Archive old training data (keep for re-training but move to archive)."""
        # TODO: Implement archival logic
        return {
            "archived": 0,
            "remaining": 0
        }

