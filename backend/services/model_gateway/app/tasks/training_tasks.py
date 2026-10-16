"""
Training Tasks
Functions that can be executed by RQ workers
"""

import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.adapter_training_service import AdapterTrainingService
from app.services.training_data_service import TrainingDataService
from app.core.database import SessionLocal, set_tenant_context

logger = logging.getLogger(__name__)


def execute_training_task(
    job_id: str,
    tenant_id: str,
    training_config: dict
) -> dict:
    """
    Execute adapter training task.
    
    This function is called by RQ workers.
    
    Args:
        job_id: Training job ID
        tenant_id: Tenant ID
        training_config: Training configuration
        
    Returns:
        Dictionary with training results
    """
    logger.info(f"Starting training task {job_id} for tenant {tenant_id}")
    
    # Create database session for worker
    db = SessionLocal()
    try:
        # Set tenant context for RLS
        set_tenant_context(db, tenant_id)
        
        # Initialize services
        training_data_service = TrainingDataService(db_session=db)
        training_service = AdapterTrainingService(db_session=db)
        
        # Prepare training dataset
        dataset = training_data_service.prepare_training_dataset(
            tenant_id=tenant_id,
            module=None  # All modules
        )
        
        if not dataset or len(dataset.get("samples", [])) == 0:
            raise ValueError("No training data found")
        
        # Validate dataset
        validation = training_service.validate_training_data(tenant_id, dataset)
        if not validation["valid"]:
            raise ValueError(f"Invalid training data: {validation.get('error')}")
        
        # Execute training
        result = training_service.execute_training(
            tenant_id=tenant_id,
            training_dataset=dataset,
            config=training_config,
            job_id=job_id
        )
        
        logger.info(f"Training task {job_id} completed: {result.get('status')}")
        return result
        
    except Exception as e:
        logger.error(f"Training task {job_id} failed: {e}", exc_info=True)
        # Update job status to failed
        if db:
            try:
                training_service = AdapterTrainingService(db_session=db)
                training_service._update_job_status(
                    job_id,
                    "failed",
                    error_message=str(e)
                )
            except Exception as update_error:
                logger.error(f"Failed to update job status: {update_error}")
        
        raise  # Re-raise to mark job as failed in RQ
    finally:
        db.close()

