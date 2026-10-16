"""Observable tracker for managing observables."""

import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models import (
    Observable,
    ObservableCreate,
    ObservableType,
    EnrichmentStatus,
)
from app.services.enrichment_engine import EnrichmentEngine

logger = logging.getLogger(__name__)


class ObservableTracker:
    """Service for tracking and managing observables."""
    
    def __init__(self, db: Session):
        self.db = db
        self.enrichment_engine = EnrichmentEngine(db)
    
    def create_observable(
        self,
        tenant_id: UUID,
        observable_data: ObservableCreate,
    ) -> Observable:
        """
        Create or update an observable.
        
        If the observable already exists for this tenant, update last_seen
        and return the existing record.
        
        Args:
            tenant_id: Tenant ID
            observable_data: Observable creation data
        
        Returns:
            Created or existing observable
        """
        # Check if observable already exists
        existing = self.db.query(Observable).filter(
            Observable.tenant_id == tenant_id,
            Observable.observable_type == observable_data.observable_type.value,
            Observable.value == observable_data.value,
        ).first()
        
        if existing:
            # Update last_seen
            existing.last_seen = datetime.utcnow()
            if observable_data.source_event_id:
                existing.source_event_id = observable_data.source_event_id
            self.db.commit()
            self.db.refresh(existing)
            logger.info(f"Updated existing observable {existing.id}")
            return existing
        
        # Create new observable
        observable = Observable(
            tenant_id=tenant_id,
            observable_type=observable_data.observable_type.value,
            value=observable_data.value,
            source_event_id=observable_data.source_event_id,
            tlp_level=observable_data.tlp_level,
            enrichment_status=EnrichmentStatus.PENDING.value,
        )
        
        self.db.add(observable)
        self.db.commit()
        self.db.refresh(observable)
        
        logger.info(f"Created new observable {observable.id}")
        return observable
    
    async def create_and_enrich(
        self,
        tenant_id: UUID,
        observable_data: ObservableCreate,
    ) -> Observable:
        """
        Create an observable and automatically enrich it.
        
        Args:
            tenant_id: Tenant ID
            observable_data: Observable creation data
        
        Returns:
            Created and enriched observable
        """
        # Create observable
        observable = self.create_observable(tenant_id, observable_data)
        
        # Enrich if requested and not already enriched
        if observable_data.auto_enrich and observable.enrichment_status != "completed":
            try:
                observable = await self.enrichment_engine.enrich_observable(observable.id)
            except Exception as e:
                logger.error(f"Failed to auto-enrich observable {observable.id}: {e}")
                # Don't fail the creation, just log the error
        
        return observable
    
    def get_observable(
        self,
        tenant_id: UUID,
        observable_id: UUID,
    ) -> Optional[Observable]:
        """
        Get an observable by ID.
        
        Args:
            tenant_id: Tenant ID
            observable_id: Observable ID
        
        Returns:
            Observable or None
        """
        return self.db.query(Observable).filter(
            Observable.id == observable_id,
            Observable.tenant_id == tenant_id,
        ).first()
    
    def search_observables(
        self,
        tenant_id: UUID,
        observable_type: Optional[str] = None,
        value_pattern: Optional[str] = None,
        enrichment_status: Optional[str] = None,
        source_event_id: Optional[UUID] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Observable]:
        """
        Search observables with filters.
        
        Args:
            tenant_id: Tenant ID
            observable_type: Filter by type
            value_pattern: Filter by value (partial match)
            enrichment_status: Filter by enrichment status
            source_event_id: Filter by source event
            limit: Maximum results
            offset: Results offset
        
        Returns:
            List of observables
        """
        query = self.db.query(Observable).filter(Observable.tenant_id == tenant_id)
        
        if observable_type:
            query = query.filter(Observable.observable_type == observable_type)
        
        if value_pattern:
            query = query.filter(Observable.value.ilike(f"%{value_pattern}%"))
        
        if enrichment_status:
            query = query.filter(Observable.enrichment_status == enrichment_status)
        
        if source_event_id:
            query = query.filter(Observable.source_event_id == source_event_id)
        
        query = query.order_by(Observable.created_at.desc())
        query = query.limit(limit).offset(offset)
        
        return query.all()
    
    async def bulk_create_and_enrich(
        self,
        tenant_id: UUID,
        observables_data: List[ObservableCreate],
    ) -> List[Observable]:
        """
        Create multiple observables and enrich them.
        
        Args:
            tenant_id: Tenant ID
            observables_data: List of observable creation data
        
        Returns:
            List of created observables
        """
        observables = []
        to_enrich = []
        
        # Create all observables first
        for obs_data in observables_data:
            try:
                observable = self.create_observable(tenant_id, obs_data)
                observables.append(observable)
                
                if obs_data.auto_enrich and observable.enrichment_status != "completed":
                    to_enrich.append(observable.id)
            
            except Exception as e:
                logger.error(f"Failed to create observable: {e}")
                continue
        
        # Enrich in batch if requested
        if to_enrich:
            try:
                await self.enrichment_engine.bulk_enrich(to_enrich)
            except Exception as e:
                logger.error(f"Failed to bulk enrich observables: {e}")
        
        return observables

