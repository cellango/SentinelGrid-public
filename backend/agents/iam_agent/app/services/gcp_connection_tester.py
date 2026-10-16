"""
GCP Connection Tester Service

Tests GCP service account authentication for onboarding.
"""

import logging
import json
from typing import Dict, Any, Optional
from google.oauth2 import service_account
from google.cloud import resourcemanager
from google.api_core import exceptions as google_exceptions

logger = logging.getLogger(__name__)


class GCPConnectionTester:
    """Service for testing GCP service account connections."""

    def __init__(self):
        """Initialize GCP connection tester."""
        pass

    def test_service_account(
        self,
        project_id: str,
        service_account_key_json: str
    ) -> Dict[str, Any]:
        """
        Test authenticating with GCP using service account JSON key.

        Args:
            project_id: GCP project ID
            service_account_key_json: Service account JSON key as string

        Returns:
            Dictionary with test results:
            {
                "success": bool,
                "message": str,
                "project_id": str (if successful),
                "project_name": str (if successful),
                "service_account_email": str (if successful),
                "error": str (if failed)
            }
        """
        try:
            # Validate inputs
            if not project_id or not project_id.strip():
                return {
                    "success": False,
                    "message": "Project ID is required",
                    "error": "Project ID cannot be empty"
                }

            if not service_account_key_json or not service_account_key_json.strip():
                return {
                    "success": False,
                    "message": "Service Account JSON key is required",
                    "error": "Service Account JSON key cannot be empty"
                }

            # Parse JSON key
            try:
                key_data = json.loads(service_account_key_json)
            except json.JSONDecodeError as e:
                return {
                    "success": False,
                    "message": "Invalid JSON format for service account key",
                    "error": f"JSON parse error: {str(e)}"
                }

            # Validate required fields in JSON key
            required_fields = ["type", "project_id", "private_key_id", "private_key", "client_email"]
            missing_fields = [field for field in required_fields if field not in key_data]
            if missing_fields:
                return {
                    "success": False,
                    "message": f"Service account key missing required fields: {', '.join(missing_fields)}",
                    "error": "Invalid service account key format"
                }

            # Extract service account email
            service_account_email = key_data.get("client_email", "")

            # Validate project ID matches
            key_project_id = key_data.get("project_id", "")
            if key_project_id and key_project_id != project_id:
                logger.warning(f"Project ID mismatch: key has {key_project_id}, provided {project_id}")

            # Create credentials
            logger.info(f"Testing GCP authentication with project: {project_id}, service account: {service_account_email[:20]}...")

            credentials = service_account.Credentials.from_service_account_info(
                key_data
            )

            # Test authentication by getting project info
            client = resourcemanager.ProjectsClient(credentials=credentials)

            try:
                project = client.get_project(name=f"projects/{project_id}")
                logger.info(f"Successfully authenticated and accessed project: {project.display_name}")

                return {
                    "success": True,
                    "message": f"Successfully authenticated and accessed project: {project.display_name}",
                    "project_id": project.project_id,
                    "project_name": project.display_name,
                    "project_number": str(project.name.split('/')[-1]) if project.name else None,
                    "service_account_email": service_account_email,
                    "state": project.state.name if hasattr(project, 'state') else None
                }

            except google_exceptions.PermissionDenied as e:
                logger.error(f"Permission denied accessing project: {e}")
                return {
                    "success": False,
                    "message": f"Cannot access project {project_id}. Please verify the service account has Viewer role assigned.",
                    "error": str(e)
                }
            except google_exceptions.NotFound as e:
                logger.error(f"Project not found: {e}")
                return {
                    "success": False,
                    "message": f"Project {project_id} not found. Please verify the project ID is correct.",
                    "error": str(e)
                }

        except ValueError as e:
            logger.error(f"Value error testing GCP connection: {e}")
            return {
                "success": False,
                "message": "Invalid service account key format",
                "error": str(e)
            }

        except google_exceptions.GoogleAPIError as e:
            logger.error(f"Google API error: {e}")
            error_message = str(e)
            
            if "invalid_grant" in error_message.lower() or "invalid" in error_message.lower():
                return {
                    "success": False,
                    "message": "Invalid service account key. Please verify the JSON key is correct and has not been deleted.",
                    "error": error_message
                }
            elif "permission" in error_message.lower() or "denied" in error_message.lower():
                return {
                    "success": False,
                    "message": "Permission denied. Please verify the service account has the required IAM roles.",
                    "error": error_message
                }
            else:
                return {
                    "success": False,
                    "message": "Google Cloud API error. Please try again later.",
                    "error": error_message
                }

        except Exception as e:
            logger.error(f"Unexpected error testing GCP connection: {e}", exc_info=True)
            return {
                "success": False,
                "message": "Unexpected error during connection test",
                "error": str(e)
            }

    def validate_project_id(self, project_id: str) -> bool:
        """
        Validate GCP project ID format.

        Args:
            project_id: GCP project ID to validate

        Returns:
            True if valid format, False otherwise
        """
        if not project_id:
            return False
        
        # GCP project IDs: 6-30 characters, lowercase letters, numbers, hyphens
        # Must start with lowercase letter
        import re
        pattern = re.compile(r'^[a-z][a-z0-9-]{4,28}[a-z0-9]$')
        return bool(pattern.match(project_id))

    def validate_service_account_email(self, email: str) -> bool:
        """
        Validate GCP service account email format.

        Args:
            email: Service account email to validate

        Returns:
            True if valid format, False otherwise
        """
        if not email:
            return False
        
        # GCP service account emails: sa-id@project-id.iam.gserviceaccount.com
        import re
        pattern = re.compile(r'^[a-z][a-z0-9-]{4,28}[a-z0-9]@[a-z][a-z0-9-]{4,28}[a-z0-9]\.iam\.gserviceaccount\.com$')
        return bool(pattern.match(email))

