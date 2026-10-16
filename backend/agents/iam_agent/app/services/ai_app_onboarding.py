"""
AI App Onboarding Service.

Uses AI to guide users through application setup step-by-step.
Integrates with chat interface for natural language interaction.
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime

from app.services.keycloak_admin_client import KeycloakAdminClient
from app.services.ai_chat_service import AIChatService
from app.core.config import settings

logger = logging.getLogger(__name__)


class AIAppOnboardingService:
    """Service for AI-powered app onboarding."""
    
    def __init__(self):
        self.keycloak_admin = KeycloakAdminClient()
        self.ai_chat = AIChatService()
    
    async def process_app_onboarding_request(
        self,
        user_message: str,
        tenant_id: str,
        user_id: str,
        conversation_context: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Process an app onboarding request from chat.
        
        Understands natural language requests like:
        - "Help me connect Microsoft 365"
        - "I want to add Slack"
        - "Set up SSO for GitHub"
        
        Returns AI response with next steps or questions.
        """
        realm = settings.KEYCLOAK_REALM
        
        # Detect app name from message
        app_name = self._extract_app_name(user_message)
        
        # Get app catalog info
        app_info = await self._get_app_catalog_info(app_name)
        
        if not app_info:
            return {
                "response": f"I can help you connect applications! I didn't recognize '{app_name}'. Could you tell me which app you'd like to connect? (e.g., Microsoft 365, Google Workspace, Slack, etc.)",
                "next_step": "clarify_app",
                "suggested_apps": await self._get_suggested_apps()
            }
        
        # Check if app is already connected
        existing_app = await self._check_existing_app(app_info["name"], tenant_id, realm)
        
        if existing_app:
            return {
                "response": f"{app_info['display_name']} is already connected. Would you like to update its configuration?",
                "next_step": "update_existing",
                "app_id": existing_app["id"]
            }
        
        # Start onboarding flow
        onboarding_state = {
            "app_name": app_info["name"],
            "app_type": app_info["app_type"],
            "protocol": app_info["protocol"],
            "step": "collect_info",
            "collected_data": {},
            "required_fields": app_info.get("required_fields", [])
        }
        
        # Determine what information we need
        missing_fields = self._determine_missing_fields(onboarding_state, conversation_context)
        
        if missing_fields:
            question = self._generate_question_for_fields(missing_fields[0], app_info)
            return {
                "response": question,
                "next_step": "collect_info",
                "onboarding_state": onboarding_state,
                "missing_fields": missing_fields
            }
        else:
            # All info collected, create the app
            return await self._create_app_from_state(onboarding_state, tenant_id, realm)
    
    async def continue_onboarding_conversation(
        self,
        user_response: str,
        onboarding_state: Dict,
        tenant_id: str,
        user_id: str
    ) -> Dict:
        """
        Continue onboarding conversation with user's response.
        
        Extracts information from user's message and progresses onboarding.
        """
        # Extract information from user response
        extracted_data = self._extract_information(user_response, onboarding_state["required_fields"])
        
        # Update state
        onboarding_state["collected_data"].update(extracted_data)
        
        # Check what's still missing
        missing_fields = self._determine_missing_fields(onboarding_state, [])
        
        if missing_fields:
            app_info = await self._get_app_catalog_info(onboarding_state["app_name"])
            question = self._generate_question_for_fields(missing_fields[0], app_info)
            
            return {
                "response": question,
                "next_step": "collect_info",
                "onboarding_state": onboarding_state,
                "missing_fields": missing_fields
            }
        else:
            # All info collected, create the app
            return await self._create_app_from_state(onboarding_state, tenant_id, settings.KEYCLOAK_REALM)
    
    def _extract_app_name(self, message: str) -> str:
        """Extract app name from user message."""
        message_lower = message.lower()
        
        # Common app name mappings
        app_mappings = {
            "microsoft 365": "microsoft_365",
            "office 365": "microsoft_365",
            "m365": "microsoft_365",
            "google workspace": "google_workspace",
            "g suite": "google_workspace",
            "gworkspace": "google_workspace",
            "slack": "slack",
            "zoom": "zoom",
            "github": "github",
            "gitlab": "gitlab",
            "salesforce": "salesforce",
            "quickbooks": "quickbooks",
            "dropbox": "dropbox",
        }
        
        for keyword, app_name in app_mappings.items():
            if keyword in message_lower:
                return app_name
        
        # Try to extract from message
        # Simple heuristic: look for capitalized words
        words = message.split()
        for word in words:
            if word[0].isupper() and len(word) > 2:
                return word.lower().replace(" ", "_")
        
        return ""
    
    async def _get_app_catalog_info(self, app_name: str) -> Optional[Dict]:
        """Get app information from catalog."""
        # In production, query app_catalog database table
        # For now, return hardcoded info
        
        app_catalog = {
            "microsoft_365": {
                "name": "microsoft_365",
                "display_name": "Microsoft 365",
                "app_type": "SaaS",
                "protocol": "SAML",
                "required_fields": ["redirect_uri", "entity_id"],
                "setup_guide": "Microsoft 365 SAML setup guide..."
            },
            "google_workspace": {
                "name": "google_workspace",
                "display_name": "Google Workspace",
                "app_type": "SaaS",
                "protocol": "SAML",
                "required_fields": ["redirect_uri", "entity_id"],
                "setup_guide": "Google Workspace SAML setup guide..."
            },
            "slack": {
                "name": "slack",
                "display_name": "Slack",
                "app_type": "SaaS",
                "protocol": "SAML",
                "required_fields": ["redirect_uri"],
                "setup_guide": "Slack SAML setup guide..."
            },
        }
        
        return app_catalog.get(app_name)
    
    async def _get_suggested_apps(self) -> List[str]:
        """Get list of suggested apps."""
        return [
            "Microsoft 365",
            "Google Workspace",
            "Slack",
            "Zoom",
            "GitHub",
            "Salesforce"
        ]
    
    async def _check_existing_app(self, app_name: str, tenant_id: str, realm: str) -> Optional[Dict]:
        """Check if app is already connected."""
        try:
            async with self.keycloak_admin as kc:
                # Get all clients
                response = await kc._make_request(
                    "GET",
                    f"/realms/{realm}/clients"
                )
                response.raise_for_status()
                clients = response.json()
                
                # Check if app client exists
                for client in clients:
                    if client.get("clientId") == app_name or client.get("name") == app_name:
                        return {
                            "id": client.get("id"),
                            "name": client.get("name"),
                            "clientId": client.get("clientId")
                        }
                
                return None
        except Exception as e:
            logger.error(f"Error checking existing app: {e}")
            return None
    
    def _determine_missing_fields(
        self,
        onboarding_state: Dict,
        conversation_context: Optional[List[Dict]]
    ) -> List[str]:
        """Determine what fields are still missing."""
        collected = onboarding_state.get("collected_data", {})
        required = onboarding_state.get("required_fields", [])
        
        missing = []
        for field in required:
            if field not in collected:
                missing.append(field)
        
        return missing
    
    def _generate_question_for_fields(self, field: str, app_info: Dict) -> str:
        """Generate a natural language question for a field."""
        questions = {
            "redirect_uri": f"Great! To connect {app_info['display_name']}, I need the redirect URL (also called callback URL or ACS URL). This is usually provided by {app_info['display_name']} in their SSO setup instructions. What's the redirect URL?",
            "entity_id": f"I also need the Entity ID (also called Issuer or Audience). This is another value from {app_info['display_name']}'s SSO setup. What's the Entity ID?",
            "client_id": f"To connect {app_info['display_name']}, I need the Client ID from their OAuth settings. What's the Client ID?",
            "client_secret": f"I also need the Client Secret. This is a sensitive value, so make sure you're in a secure environment. What's the Client Secret?",
        }
        
        return questions.get(field, f"I need the {field} for {app_info['display_name']}. Can you provide it?")
    
    def _extract_information(self, message: str, required_fields: List[str]) -> Dict:
        """Extract information from user's message."""
        extracted = {}
        
        # Simple extraction (in production, use NLP/AI)
        # Look for URLs
        import re
        url_pattern = r'https?://[^\s]+'
        urls = re.findall(url_pattern, message)
        if urls and "redirect_uri" in required_fields:
            extracted["redirect_uri"] = urls[0]
        
        # Look for IDs (alphanumeric strings)
        id_pattern = r'\b[a-zA-Z0-9]{20,}\b'
        ids = re.findall(id_pattern, message)
        if ids:
            if "client_id" in required_fields and "client_id" not in extracted:
                extracted["client_id"] = ids[0]
            elif "entity_id" in required_fields and "entity_id" not in extracted:
                extracted["entity_id"] = ids[0]
        
        return extracted
    
    async def _create_app_from_state(
        self,
        onboarding_state: Dict,
        tenant_id: str,
        realm: str
    ) -> Dict:
        """Create Keycloak client from onboarding state."""
        try:
            async with self.keycloak_admin as kc:
                app_info = await self._get_app_catalog_info(onboarding_state["app_name"])
                
                # Build client configuration based on protocol
                if onboarding_state["protocol"] == "SAML":
                    client_data = {
                        "clientId": onboarding_state["app_name"],
                        "name": app_info["display_name"],
                        "protocol": "saml",
                        "enabled": True,
                        "attributes": {
                            "saml.assertion.signature": "true",
                            "saml.force.post.binding": "true",
                            "saml.server.signature": "true",
                        }
                    }
                else:  # OIDC
                    client_data = {
                        "clientId": onboarding_state["app_name"],
                        "name": app_info["display_name"],
                        "protocol": "openid-connect",
                        "publicClient": False,
                        "redirectUris": [onboarding_state["collected_data"].get("redirect_uri", "")],
                        "standardFlowEnabled": True,
                    }
                
                # Create client
                response = await kc._make_request(
                    "POST",
                    f"/realms/{realm}/clients",
                    json_data=client_data
                )
                response.raise_for_status()
                
                client_id = response.headers.get("Location", "").split("/")[-1]
                
                logger.info(f"App {onboarding_state['app_name']} created for tenant {tenant_id}")
                
                return {
                    "response": f"Perfect! I've successfully connected {app_info['display_name']}. The app is now configured and ready to use. Users can now sign in to {app_info['display_name']} using SentinelGrid SSO.",
                    "next_step": "complete",
                    "app_id": client_id,
                    "success": True
                }
                
        except Exception as e:
            logger.error(f"Error creating app: {e}", exc_info=True)
            return {
                "response": f"I encountered an error while setting up {app_info['display_name']}. Let me try a different approach. Could you provide the setup details again?",
                "next_step": "retry",
                "error": str(e)
            }

