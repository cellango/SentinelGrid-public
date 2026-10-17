"""Main ingestion service."""

import logging
from typing import List, Tuple
from uuid import UUID, uuid4
from app.models.event import RawEvent, IngestEvent, IngestBatchRequest, IngestResponse
from app.services.normalizer import ECSNormalizer
from app.services.validator import EventValidator
from app.services.batch_processor import get_batch_processor
from app.core.config import settings
from sg_core.service_metrics import get_service_metrics

logger = logging.getLogger(__name__)
runtime_metrics = get_service_metrics(settings.SERVICE_NAME)


class IngestionService:
    """Main service for event ingestion."""
    
    def __init__(self):
        """Initialize ingestion service."""
        self.normalizer = ECSNormalizer()
        self.validator = EventValidator()
        self.batch_processor = get_batch_processor()
    
    async def ingest_batch(
        self,
        request: IngestBatchRequest,
        tenant_id: str
    ) -> IngestResponse:
        """
        Ingest a batch of events.
        
        Args:
            request: Batch ingestion request
            tenant_id: Tenant ID (from auth context or request)
        
        Returns:
            Ingestion response with counts and errors
        """
        # The caller must supply verified workload authority separately. Body fields
        # are matching hints only; this internal argument is never body-overridden.
        effective_tenant_id = self._canonical_tenant(tenant_id)
        if request.tenant_id is not None and request.tenant_id != effective_tenant_id:
            raise ValueError("tenant_id mismatch between batch and auth context")
        
        ingested_count = 0
        failed_count = 0
        errors = []
        
        for raw_event in request.events:
            try:
                # Set tenant_id if not in event
                if raw_event.tenant_id and raw_event.tenant_id != effective_tenant_id:
                    failed_count += 1
                    errors.append("tenant_id mismatch between event and auth context")
                    continue
                if not raw_event.tenant_id:
                    raw_event.tenant_id = effective_tenant_id
                
                # Validate event
                is_valid, validation_errors = self.validator.validate(raw_event)
                if not is_valid:
                    failed_count += 1
                    errors.extend([f"Event validation failed: {e}" for e in validation_errors])
                    continue
                
                # Normalize to ECS
                ecs_fields = self.normalizer.normalize(raw_event, effective_tenant_id)
                
                # Create ingest event
                ingest_event = IngestEvent(
                    ecs_fields=ecs_fields,
                    raw_data=raw_event.raw_data
                )
                
                # Add to batch processor
                await self.batch_processor.add_event(effective_tenant_id, ingest_event)
                ingested_count += 1
                
            except Exception as e:
                logger.error(f"Failed to process event: {e}")
                failed_count += 1
                errors.append(f"Event processing error: {str(e)}")

        runtime_metrics.increment_counter(
            "ingestion_batches_received_total",
            outcome=(
                "success"
                if failed_count == 0
                else "partial_failure"
                if ingested_count > 0
                else "failure"
            ),
        )
        if failed_count:
            runtime_metrics.increment_counter(
                "ingestion_events_total",
                amount=failed_count,
                outcome="rejected",
            )
        
        return IngestResponse(
            ingested_count=ingested_count,
            failed_count=failed_count,
            errors=errors[:10],  # Limit errors returned
            batch_id=str(uuid4())
        )
    
    async def flush_tenant_batch(self, tenant_id: str) -> None:
        """
        Force flush batch for a tenant.
        
        Args:
            tenant_id: Tenant ID
        """
        await self.batch_processor._flush_batch(self._canonical_tenant(tenant_id))

    @staticmethod
    def _canonical_tenant(tenant_id: str) -> str:
        try:
            value = UUID(tenant_id)
            if not value.int or str(value) != tenant_id:
                raise ValueError()
        except (ValueError, TypeError, AttributeError):
            raise ValueError("Expected a canonical non-nil tenant UUID") from None
        return tenant_id
