"""Event validation service."""

import logging
from typing import List, Tuple
from app.models.event import RawEvent

logger = logging.getLogger(__name__)


class EventValidator:
    """Service for validating events before ingestion."""
    
    def validate(self, event: RawEvent) -> Tuple[bool, List[str]]:
        """
        Validate a raw event.
        
        Args:
            event: Raw event to validate
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Required fields
        if not event.event_type:
            errors.append("event_type is required")
        
        if not event.source:
            errors.append("source is required")
        
        if not event.timestamp:
            errors.append("timestamp is required")
        
        if not event.raw_data:
            errors.append("raw_data is required")
        elif not isinstance(event.raw_data, dict):
            errors.append("raw_data must be a dictionary")
        
        if event.tenant_id and not isinstance(event.tenant_id, str):
            errors.append("tenant_id must be a string")
        
        # Validate timestamp is reasonable (not too far in future/past)
        if event.timestamp:
            from datetime import datetime, timedelta, timezone
            now = datetime.now(timezone.utc)
            max_future = now + timedelta(days=1)
            max_past = now - timedelta(days=365)
            
            if event.timestamp > max_future:
                errors.append(f"timestamp is too far in the future: {event.timestamp}")
            elif event.timestamp < max_past:
                errors.append(f"timestamp is too far in the past: {event.timestamp}")
        
        # Validate event_type format
        if event.event_type and not isinstance(event.event_type, str):
            errors.append("event_type must be a string")
        elif event.event_type and len(event.event_type) > 100:
            errors.append("event_type is too long (max 100 characters)")
        
        # Validate source format
        if event.source and not isinstance(event.source, str):
            errors.append("source must be a string")
        elif event.source and len(event.source) > 100:
            errors.append("source is too long (max 100 characters)")
        
        return (len(errors) == 0, errors)
