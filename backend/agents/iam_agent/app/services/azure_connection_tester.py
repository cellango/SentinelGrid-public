"""
Azure Connection Tester Service

Tests Azure service principal authentication for onboarding.
"""

import logging
from typing import Dict, Any, Optional
from azure.identity import ClientSecretCredential
from azure.mgmt.subscription import SubscriptionClient
from azure.core.exceptions import AzureError, ClientAuthenticationError

logger = logging.getLogger(__name__)


class AzureConnectionTester:
    """Service for testing Azure service principal connections."""

    def __init__(self):
        """Initialize Azure connection tester."""
        pass

    def test_service_principal(
        self,
        tenant_id: str,
        client_id: str,
        client_secret: str,
        subscription_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Test authenticating with Azure using service principal credentials.

        Args:
            tenant_id: Azure AD tenant ID
            client_id: Application (client) ID
            client_secret: Client secret
            subscription_id: Optional subscription ID to test access to

        Returns:
            Dictionary with test results:
            {
                "success": bool,
                "message": str,
                "subscription_id": str (if successful),
                "subscription_name": str (if successful),
                "error": str (if failed)
            }
        """
        try:
            # Validate inputs
            if not tenant_id or not tenant_id.strip():
                return {
                    "success": False,
                    "message": "Tenant ID is required",
                    "error": "Tenant ID cannot be empty"
                }

            if not client_id or not client_id.strip():
                return {
                    "success": False,
                    "message": "Client ID is required",
                    "error": "Client ID cannot be empty"
                }

            if not client_secret or not client_secret.strip():
                return {
                    "success": False,
                    "message": "Client Secret is required",
                    "error": "Client Secret cannot be empty"
                }

            # Create credential
            logger.info(f"Testing Azure authentication with tenant: {tenant_id}, client_id: {client_id[:8]}...")

            credential = ClientSecretCredential(
                tenant_id=tenant_id,
                client_id=client_id,
                client_secret=client_secret
            )

            # Test authentication by getting subscription info
            subscription_client = SubscriptionClient(credential)

            if subscription_id:
                # Test access to specific subscription
                try:
                    subscription = subscription_client.subscriptions.get(subscription_id)
                    logger.info(f"Successfully authenticated and accessed subscription: {subscription.display_name}")

                    return {
                        "success": True,
                        "message": f"Successfully authenticated and accessed subscription: {subscription.display_name}",
                        "subscription_id": subscription.subscription_id,
                        "subscription_name": subscription.display_name,
                        "tenant_id": tenant_id
                    }
                except AzureError as e:
                    logger.error(f"Azure error accessing subscription: {e}")
                    return {
                        "success": False,
                        "message": f"Cannot access subscription {subscription_id}. Please verify the service principal has Reader role assigned.",
                        "error": str(e)
                    }
            else:
                # List subscriptions to verify authentication works
                try:
                    subscriptions = list(subscription_client.subscriptions.list())
                    if subscriptions:
                        sub = subscriptions[0]
                        logger.info(f"Successfully authenticated. Found {len(subscriptions)} subscription(s)")

                        return {
                            "success": True,
                            "message": f"Successfully authenticated. Found {len(subscriptions)} subscription(s)",
                            "subscription_id": sub.subscription_id,
                            "subscription_name": sub.display_name,
                            "tenant_id": tenant_id,
                            "subscription_count": len(subscriptions)
                        }
                    else:
                        return {
                            "success": False,
                            "message": "Authentication succeeded but no subscriptions found",
                            "error": "No subscriptions accessible"
                        }
                except AzureError as e:
                    logger.error(f"Azure error listing subscriptions: {e}")
                    return {
                        "success": False,
                        "message": "Authentication failed or insufficient permissions",
                        "error": str(e)
                    }

        except ClientAuthenticationError as e:
            logger.error(f"Azure authentication error: {e}")
            error_message = str(e)
            
            if "AADSTS700016" in error_message or "Application" in error_message:
                return {
                    "success": False,
                    "message": "Application not found in the directory. Please verify the Client ID and Tenant ID are correct.",
                    "error": error_message
                }
            elif "AADSTS7000215" in error_message or "invalid client secret" in error_message.lower():
                return {
                    "success": False,
                    "message": "Invalid client secret. Please verify the Client Secret is correct and has not expired.",
                    "error": error_message
                }
            elif "AADSTS50034" in error_message or "tenant" in error_message.lower():
                return {
                    "success": False,
                    "message": "Invalid tenant ID. Please verify the Tenant ID is correct.",
                    "error": error_message
                }
            else:
                return {
                    "success": False,
                    "message": "Authentication failed. Please verify all credentials are correct.",
                    "error": error_message
                }

        except AzureError as e:
            logger.error(f"Azure service error: {e}")
            return {
                "success": False,
                "message": "Azure service error. Please try again later.",
                "error": str(e)
            }

        except Exception as e:
            logger.error(f"Unexpected error testing Azure connection: {e}", exc_info=True)
            return {
                "success": False,
                "message": "Unexpected error during connection test",
                "error": str(e)
            }

    def validate_tenant_id(self, tenant_id: str) -> bool:
        """
        Validate Azure tenant ID format (UUID).

        Args:
            tenant_id: Azure tenant ID to validate

        Returns:
            True if valid format, False otherwise
        """
        import re
        # Azure tenant IDs are UUIDs
        uuid_pattern = re.compile(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
            re.IGNORECASE
        )
        return bool(uuid_pattern.match(tenant_id)) if tenant_id else False

    def validate_client_id(self, client_id: str) -> bool:
        """
        Validate Azure client ID format (UUID).

        Args:
            client_id: Azure client ID to validate

        Returns:
            True if valid format, False otherwise
        """
        import re
        # Azure client IDs are UUIDs
        uuid_pattern = re.compile(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
            re.IGNORECASE
        )
        return bool(uuid_pattern.match(client_id)) if client_id else False

    def validate_subscription_id(self, subscription_id: str) -> bool:
        """
        Validate Azure subscription ID format (UUID).

        Args:
            subscription_id: Azure subscription ID to validate

        Returns:
            True if valid format, False otherwise
        """
        import re
        # Azure subscription IDs are UUIDs
        uuid_pattern = re.compile(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
            re.IGNORECASE
        )
        return bool(uuid_pattern.match(subscription_id)) if subscription_id else False

