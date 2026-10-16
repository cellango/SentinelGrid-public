"""
Training Data & Adapter Training API
"""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
import logging
from sqlalchemy.orm import Session

from app.services.training_data_service import TrainingDataService, DataType
from app.services.adapter_training_service import AdapterTrainingService, TrainingStatus
from app.services.job_queue import get_job_queue_service
from app.tasks.training_tasks import execute_training_task
from app.core.database import get_db, set_tenant_context

router = APIRouter(prefix="/internal/llm/training", tags=["training"])
logger = logging.getLogger(__name__)


class StoreTrainingDataRequest(BaseModel):
    """Request to store training data."""
    tenant_id: str
    module: str = Field(..., description="Module: iam, soc, siem")
    data_type: str = Field(..., description="Data type: qa_pair, incident, log, document, etc.")
    raw_data: Dict[str, Any]
    tags: Optional[List[str]] = None


class StartTrainingRequest(BaseModel):
    """Request to start adapter training."""
    tenant_id: str
    config: Optional[Dict[str, Any]] = None


class TrainingJobResponse(BaseModel):
    """Training job status response."""
    job_id: str
    tenant_id: str
    status: str
    config: Dict[str, Any]
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


@router.post("/data", summary="Store Training Data")
async def store_training_data(
    request: StoreTrainingDataRequest,
    db: Session = Depends(get_db)
):
    """Store raw training data for a tenant."""
    try:
        # Set tenant context for RLS
        set_tenant_context(db, request.tenant_id)
        
        data_type = DataType(request.data_type)
        service = TrainingDataService(db_session=db)
        result = service.store_training_data(
            tenant_id=request.tenant_id,
            module=request.module,
            data_type=data_type,
            raw_data=request.raw_data,
            tags=request.tags
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid data type: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error storing training data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/qa", summary="Store Q&A Pair")
async def store_qa_pair(
    tenant_id: str,
    module: str,
    question: str,
    answer: str,
    context: Optional[Dict[str, Any]] = None,
    tags: Optional[List[str]] = None,
    db: Session = Depends(get_db)
):
    """Store a Q&A pair for training."""
    try:
        # Set tenant context for RLS
        set_tenant_context(db, tenant_id)
        
        service = TrainingDataService(db_session=db)
        result = service.store_qa_pair(
            tenant_id=tenant_id,
            module=module,
            question=question,
            answer=answer,
            context=context,
            tags=tags
        )
        return result
    except Exception as e:
        logger.error(f"Error storing Q&A pair: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/start", response_model=TrainingJobResponse, summary="Start Adapter Training")
async def start_training(
    request: StartTrainingRequest,
    db: Session = Depends(get_db)
):
    """Start training a LoRA adapter for a tenant."""
    try:
        # Set tenant context for RLS
        set_tenant_context(db, request.tenant_id)
        
        # Get training data for validation
        training_data_service = TrainingDataService(db_session=db)
        dataset = training_data_service.prepare_training_dataset(
            tenant_id=request.tenant_id,
            module=None  # All modules
        )
        
        # Validate dataset
        training_service = AdapterTrainingService(db_session=db)
        validation = training_service.validate_training_data(request.tenant_id, dataset)
        
        if not validation["valid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid training data: {validation.get('error', 'Unknown error')}"
            )
        
        # Start training job (creates DB record)
        job = training_service.start_training_job(
            tenant_id=request.tenant_id,
            training_config=request.config or {}
        )
        
        # Enqueue training task to RQ
        job_queue = get_job_queue_service()
        rq_job = job_queue.enqueue_training_job(
            job_id=job["job_id"],
            tenant_id=request.tenant_id,
            training_func=execute_training_task,
            training_config=job["config"]
        )
        
        if not rq_job:
            # Fallback: If RQ unavailable, update job status
            training_service._update_job_status(
                job["job_id"],
                "failed",
                error_message="Job queue unavailable"
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Job queue service unavailable. Cannot start training."
            )
        
        logger.info(f"Training job {job['job_id']} enqueued to RQ: {rq_job.id}")
        
        return TrainingJobResponse(
            job_id=job["job_id"],
            tenant_id=job["tenant_id"],
            status=job["status"],
            config=job["config"],
            created_at=job["created_at"],
            started_at=job.get("started_at"),
            completed_at=job.get("completed_at")
        )
    except Exception as e:
        logger.error(f"Error starting training job: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/jobs/{job_id}", response_model=TrainingJobResponse, summary="Get Training Job Status")
async def get_training_job_status(
    job_id: str,
    db: Session = Depends(get_db)
):
    """Get status of a training job."""
    try:
        training_service = AdapterTrainingService(db_session=db)
        job = training_service.get_training_job_status(job_id)
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Training job {job_id} not found"
            )
        
        # Set tenant context for RLS
        set_tenant_context(db, job["tenant_id"])
        
        # Try to get RQ job status for additional info
        job_queue = get_job_queue_service()
        rq_status = job_queue.get_job_status(job_id)
        
        # Merge RQ status with DB status if available
        if rq_status:
            # Update status from RQ if DB status is older
            if rq_status.get("status") in ["started", "finished", "failed"]:
                job["status"] = rq_status["status"]
            if rq_status.get("error"):
                job["error_message"] = rq_status["error"]
        
        return TrainingJobResponse(
            job_id=job["job_id"],
            tenant_id=job["tenant_id"],
            status=job["status"],
            config=job["config"],
            created_at=job["created_at"],
            started_at=job.get("started_at"),
            completed_at=job.get("completed_at")
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting training job status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
