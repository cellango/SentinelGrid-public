"""
AI Chat Service for IAM
Provides natural language interface for IAM queries using LLM
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import httpx

from app.core.config import settings
from app.services.keycloak_client import KeycloakClient
# Embeddings service - optional (has dependency conflicts)
try:
    from app.services.embeddings_service import EmbeddingsService
except ImportError:
    EmbeddingsService = None
from app.services.model_provider import get_model_provider, ModelProvider

logger = logging.getLogger(__name__)


class IAMChatService:
    """AI-powered chat service for IAM queries."""
    
    def __init__(self, keycloak_client: KeycloakClient, model_provider: Optional[ModelProvider] = None):
        self.keycloak_client = keycloak_client
        self.model_provider = model_provider or get_model_provider()
        
    async def chat(
        self,
        query: str,
        tenant_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        conversation_history: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Process a natural language IAM query.
        
        Args:
            query: Natural language question about IAM
            tenant_id: Optional tenant ID for multi-tenancy
            context: Optional additional context
            user_id: Optional user ID for app onboarding
            conversation_history: Optional conversation history
            
        Returns:
            Dictionary with answer, entities, confidence, and sources
        """
        try:
            # Extract entities and intent from query
            intent = self._classify_intent(query)
            
            # Handle app onboarding requests
            if intent["type"] == "app_onboarding":
                from app.services.ai_app_onboarding import AIAppOnboardingService
                onboarding_service = AIAppOnboardingService()
                
                # Check if we have onboarding state in context
                onboarding_state = context.get("onboarding_state") if context else None
                
                if onboarding_state:
                    # Continue existing onboarding
                    result = await onboarding_service.continue_onboarding_conversation(
                        user_response=query,
                        onboarding_state=onboarding_state,
                        tenant_id=tenant_id or "",
                        user_id=user_id or ""
                    )
                else:
                    # Start new onboarding
                    result = await onboarding_service.process_app_onboarding_request(
                        user_message=query,
                        tenant_id=tenant_id or "",
                        user_id=user_id or "",
                        conversation_context=conversation_history
                    )
                
                return {
                    "answer": result.get("response", "I can help you connect applications!"),
                    "entities": [],
                    "confidence": 0.9,
                    "sources": [],
                    "onboarding_state": result.get("onboarding_state"),
                    "next_step": result.get("next_step"),
                    "app_onboarding": True
                }
            
            # Gather relevant IAM data based on intent
            iam_data = self._gather_iam_data(intent, tenant_id)
            
            # Build prompt with context
            prompt = self._build_prompt(query, intent, iam_data, context)
            
            # Query LLM via Model Gateway
            response = self._query_llm(prompt)
            
            # Parse and structure response
            return self._parse_response(response, intent, iam_data)
            
        except Exception as e:
            logger.error(f"Error processing chat query: {e}", exc_info=True)
            return {
                "answer": "I encountered an error processing your query. Please try rephrasing it.",
                "entities": [],
                "confidence": 0.0,
                "sources": [],
                "error": str(e)
            }
    
    def _classify_intent(self, query: str) -> Dict[str, Any]:
        """Classify the intent of the query."""
        query_lower = query.lower()
        
        # Simple intent classification (can be enhanced with LLM)
        intent = {
            "type": "general",
            "entities": [],
            "action": None
        }
        
        # Check for access-related queries
        if any(word in query_lower for word in ["who has", "who can", "access", "permission"]):
            intent["type"] = "access_query"
            intent["action"] = "list_access"
            
            # Extract resource mentions
            if "production" in query_lower or "prod" in query_lower:
                intent["entities"].append({"type": "resource", "value": "production"})
            if "database" in query_lower or "db" in query_lower:
                intent["entities"].append({"type": "resource", "value": "database"})
            if "api" in query_lower:
                intent["entities"].append({"type": "resource", "value": "api"})
        
        # Check for policy-related queries
        elif any(word in query_lower for word in ["policy", "policies", "rule", "rules"]):
            intent["type"] = "policy_query"
            intent["action"] = "list_policies"
        
        # Check for role-related queries
        elif any(word in query_lower for word in ["role", "roles", "permission"]):
            intent["type"] = "role_query"
            intent["action"] = "list_roles"
        
        # Check for user-related queries
        elif any(word in query_lower for word in ["user", "users", "who is"]):
            intent["type"] = "user_query"
            intent["action"] = "list_users"
        
        # Check for recommendation requests
        elif any(word in query_lower for word in ["recommend", "suggest", "should", "best practice"]):
            intent["type"] = "recommendation"
            intent["action"] = "recommend"
        
        # Check for app onboarding requests
        elif any(word in query_lower for word in ["connect", "add", "setup", "configure", "install", "integrate"]) and \
             any(word in query_lower for word in ["app", "application", "sso", "microsoft", "google", "slack", "zoom"]):
            intent["type"] = "app_onboarding"
            intent["action"] = "onboard_app"
        
        return intent
    
    def _gather_iam_data(self, intent: Dict[str, Any], tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """Gather relevant IAM data based on intent."""
        data = {}
        
        try:
            if intent["type"] in ["access_query", "user_query"]:
                # Get users and their roles
                users = self.keycloak_client.list_users()
                data["users"] = users[:50]  # Limit to first 50 for context
                
                # Get roles
                roles = self.keycloak_client.get_realm_roles()
                data["roles"] = roles[:20]  # Limit for context
            
            elif intent["type"] == "role_query":
                roles = self.keycloak_client.get_realm_roles()
                data["roles"] = roles
            
            elif intent["type"] == "policy_query":
                # Get policies from Keycloak
                policies = self.keycloak_client.get_authorization_policies()
                data["policies"] = policies[:20]  # Limit for context
            
        except Exception as e:
            logger.error(f"Error gathering IAM data: {e}")
            data["error"] = str(e)
        
        return data
    
    def _build_prompt(
        self,
        query: str,
        intent: Dict[str, Any],
        iam_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build prompt for LLM with IAM context."""
        
        prompt_parts = [
            "You are an AI assistant specialized in Identity and Access Management (IAM) for SentinelGrid.",
            "Your role is to help administrators understand and manage access controls, policies, users, and roles.",
            "",
            f"User Query: {query}",
            "",
            "Relevant IAM Data:"
        ]
        
        # Add IAM data context
        if "users" in iam_data:
            prompt_parts.append(f"\nUsers (showing {len(iam_data['users'])} of available):")
            for user in iam_data["users"][:10]:  # Show first 10
                username = user.get("username", "N/A")
                email = user.get("email", "N/A")
                prompt_parts.append(f"  - {username} ({email})")
        
        if "roles" in iam_data:
            prompt_parts.append(f"\nRoles (showing {len(iam_data['roles'])} of available):")
            for role in iam_data["roles"][:10]:  # Show first 10
                role_name = role.get("name", "N/A")
                prompt_parts.append(f"  - {role_name}")
        
        if "policies" in iam_data:
            prompt_parts.append(f"\nPolicies (showing {len(iam_data['policies'])} of available):")
            for policy in iam_data["policies"][:10]:  # Show first 10
                policy_name = policy.get("name", "N/A")
                policy_type = policy.get("type", "N/A")
                prompt_parts.append(f"  - {policy_name} ({policy_type})")
        
        prompt_parts.extend([
            "",
            "Instructions:",
            "1. Answer the user's query based on the IAM data provided.",
            "2. If the query asks about specific access, identify which users/roles have that access.",
            "3. Be concise and accurate. If you don't have enough information, say so.",
            "4. Format your response in a clear, structured way.",
            "5. If recommending policies or changes, explain the reasoning.",
            "",
            "Response:"
        ])
        
        return "\n".join(prompt_parts)
    
    def _query_llm(self, prompt: str) -> str:
        """Query LLM using model provider abstraction."""
        try:
            # Build full prompt with system message
            full_prompt = f"""You are an IAM assistant for SentinelGrid. Provide helpful, accurate answers about access control and policies.

{prompt}"""
            
            # Use model provider abstraction (enables easy model swapping)
            response = self.model_provider.generate(
                full_prompt,
                temperature=0.3,
                max_tokens=500
            )
            return response
            
        except Exception as e:
            logger.error(f"Error querying LLM: {e}")
            return f"Error processing query: {str(e)}"
                    
        except httpx.RequestError as e:
            logger.error(f"Error connecting to Model Gateway: {e}")
            # Fallback response
            return "I'm having trouble connecting to the AI service. Please try again later."
        except Exception as e:
            logger.error(f"Error querying LLM: {e}")
            return f"Error processing query: {str(e)}"
    
    def _parse_response(
        self,
        response: str,
        intent: Dict[str, Any],
        iam_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse and structure LLM response."""
        
        # Extract entities mentioned in response
        entities = []
        
        # Look for user mentions
        if "users" in iam_data:
            for user in iam_data["users"]:
                username = user.get("username", "")
                if username and username.lower() in response.lower():
                    entities.append({
                        "type": "user",
                        "id": user.get("id"),
                        "name": username
                    })
        
        # Look for role mentions
        if "roles" in iam_data:
            for role in iam_data["roles"]:
                role_name = role.get("name", "")
                if role_name and role_name.lower() in response.lower():
                    entities.append({
                        "type": "role",
                        "id": role.get("id"),
                        "name": role_name
                    })
        
        # Calculate confidence (simple heuristic - can be improved)
        confidence = 0.8 if entities else 0.6
        
        return {
            "answer": response,
            "entities": entities[:10],  # Limit entities
            "confidence": confidence,
            "sources": self._get_sources(intent, iam_data),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _get_sources(self, intent: Dict[str, Any], iam_data: Dict[str, Any]) -> List[str]:
        """Get source references for the answer."""
        sources = []
        
        if "users" in iam_data:
            sources.append(f"Keycloak Users API ({len(iam_data['users'])} users)")
        if "roles" in iam_data:
            sources.append(f"Keycloak Roles API ({len(iam_data['roles'])} roles)")
        if "policies" in iam_data:
            sources.append(f"Keycloak Policies API ({len(iam_data['policies'])} policies)")
        
        return sources

