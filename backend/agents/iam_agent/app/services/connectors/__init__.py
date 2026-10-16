"""Integration connectors package."""

from app.services.connector_framework import (
    BaseConnector,
    ConnectorFactory,
    SyncDirection,
    SyncStatus,
    SyncJob
)

# Import connectors
from app.services.connectors.active_directory_connector import ActiveDirectoryConnector
from app.services.connectors.azure_ad_connector import AzureADConnector

# Register connectors
ConnectorFactory.register("active_directory", ActiveDirectoryConnector)
ConnectorFactory.register("azure_ad", AzureADConnector)

__all__ = [
    "BaseConnector",
    "ConnectorFactory",
    "SyncDirection",
    "SyncStatus",
    "SyncJob",
    "ActiveDirectoryConnector"
]

