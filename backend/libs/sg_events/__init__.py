"""SentinelGrid Events Library

Redis Streams-backed event bus for inter-service communication.
"""

__version__ = "0.2.0"

from .bus import EventBus, get_event_bus, publish_sync
from .event_types import Event, EventType, create_event

__all__ = [
    "EventBus",
    "get_event_bus",
    "publish_sync",
    "Event",
    "EventType",
    "create_event",
]
