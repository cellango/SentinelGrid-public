"""
Recommendation Engine for IAM
Provides AI-powered recommendations for access optimization, compliance, and security
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict, Counter

from app.services.model_provider import get_model_provider

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """Service for generating IAM recommendations."""
    
    def __init__(self):
        self.model_provider = get_model_provider()
    
    def recommend_role_mining(
        self,
        users: List[Dict[str, Any]],
        entitlements: List[Dict[str, Any]],
        tenant_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Recommend roles based on user entitlement patterns (role mining).
        
        Analyzes common entitlement combinations and suggests new roles.
        """
        recommendations = []
        
        if not users or not entitlements:
            return recommendations
        
        # Group entitlements by user
        user_entitlements = defaultdict(set)
        for entitlement in entitlements:
            user_id = entitlement.get("user_id") or entitlement.get("granted_to")
            if user_id:
                entitlement_key = f"{entitlement.get('resource_type')}:{entitlement.get('action')}"
                user_entitlements[user_id].add(entitlement_key)
        
        # Find common entitlement patterns
        entitlement_patterns = defaultdict(list)
        for user_id, ents in user_entitlements.items():
            pattern_key = tuple(sorted(ents))
            entitlement_patterns[pattern_key].append(user_id)
        
        # Recommend roles for patterns with multiple users
        for pattern, user_list in entitlement_patterns.items():
            if len(user_list) >= 3:  # At least 3 users with same pattern
                recommendations.append({
                    "type": "role_mining",
                    "priority": "high",
                    "title": f"Create role for {len(pattern)} common entitlements",
                    "description": f"{len(user_list)} users share this entitlement pattern. Consider creating a role to simplify management.",
                    "entitlements": list(pattern),
                    "affected_users": user_list,
                    "benefits": [
                        "Simplified access management",
                        "Reduced administrative overhead",
                        "Consistent access patterns"
                    ],
                    "created_at": datetime.utcnow().isoformat()
                })
        
        return recommendations
    
    def recommend_access_optimization(
        self,
        users: List[Dict[str, Any]],
        access_history: List[Dict[str, Any]],
        tenant_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Recommend access optimizations (remove unused entitlements, consolidate access).
        """
        recommendations = []
        
        if not users:
            return recommendations
        
        # Find users with unused entitlements
        for user in users:
            user_id = user.get("id") or user.get("user_id")
            entitlements = user.get("entitlements", [])
            user_access = [a for a in access_history if a.get("user_id") == user_id]
            
            # Check each entitlement for usage
            unused_entitlements = []
            for entitlement in entitlements:
                entitlement_id = entitlement.get("id")
                resource = entitlement.get("resource") or entitlement.get("resource_type")
                action = entitlement.get("action")
                
                # Check if used in last 90 days
                used = any(
                    a.get("resource") == resource and a.get("action") == action
                    for a in user_access
                    if self._is_recent(a, days=90)
                )
                
                if not used:
                    unused_entitlements.append(entitlement)
            
            if unused_entitlements:
                recommendations.append({
                    "type": "access_optimization",
                    "priority": "medium",
                    "title": f"Remove unused entitlements for user {user.get('username', user_id)}",
                    "description": f"User has {len(unused_entitlements)} entitlements not used in the last 90 days",
                    "user_id": user_id,
                    "unused_entitlements": unused_entitlements,
                    "recommended_action": "Review and revoke unused entitlements",
                    "benefits": [
                        "Reduced attack surface",
                        "Compliance with least privilege",
                        "Simplified access management"
                    ],
                    "created_at": datetime.utcnow().isoformat()
                })
        
        return recommendations
    
    def recommend_compliance_improvements(
        self,
        tenant_id: str,
        policies: List[Dict[str, Any]],
        users: List[Dict[str, Any]],
        entitlements: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Recommend compliance improvements based on NIST controls and best practices.
        """
        recommendations = []
        
        # Check for missing MFA
        users_without_mfa = [u for u in users if not u.get("mfa_enabled", False)]
        if users_without_mfa:
            recommendations.append({
                "type": "compliance",
                "priority": "high",
                "control": "NIST AC-2, IA-2",
                "title": "Enable MFA for users",
                "description": f"{len(users_without_mfa)} users do not have MFA enabled",
                "affected_count": len(users_without_mfa),
                "recommended_action": "Enable MFA for all users",
                "compliance_impact": "Improves compliance with NIST AC-2 and IA-2 controls"
            })
        
        # Check for over-privileged users
        over_privileged = [u for u in users if len(u.get("roles", [])) > 5 or len(u.get("entitlements", [])) > 20]
        if over_privileged:
            recommendations.append({
                "type": "compliance",
                "priority": "high",
                "control": "NIST AC-6",
                "title": "Review over-privileged users",
                "description": f"{len(over_privileged)} users have excessive privileges",
                "affected_count": len(over_privileged),
                "recommended_action": "Apply least privilege principle",
                "compliance_impact": "Improves compliance with NIST AC-6 (Least Privilege)"
            })
        
        # Check for stale accounts
        stale_accounts = [
            u for u in users
            if u.get("last_login") and self._is_stale(u.get("last_login"), days=90)
        ]
        if stale_accounts:
            recommendations.append({
                "type": "compliance",
                "priority": "medium",
                "control": "NIST AC-2",
                "title": "Review inactive accounts",
                "description": f"{len(stale_accounts)} accounts have been inactive for >90 days",
                "affected_count": len(stale_accounts),
                "recommended_action": "Disable or review inactive accounts",
                "compliance_impact": "Improves compliance with NIST AC-2 (Account Management)"
            })
        
        return recommendations
    
    def recommend_security_posture_improvements(
        self,
        tenant_id: str,
        risk_scores: Dict[str, Any],
        anomalies: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Recommend security posture improvements based on risk and anomalies.
        """
        recommendations = []
        
        # High-risk users
        high_risk_users = risk_scores.get("high_risk_users", [])
        if high_risk_users:
            recommendations.append({
                "type": "security_posture",
                "priority": "critical",
                "title": "Review high-risk users",
                "description": f"{len(high_risk_users)} users have high risk scores",
                "recommended_action": "Investigate and remediate high-risk user accounts",
                "impact": "Reduces overall security risk"
            })
        
        # Critical anomalies
        critical_anomalies = [a for a in anomalies if a.get("severity") == "critical"]
        if critical_anomalies:
            recommendations.append({
                "type": "security_posture",
                "priority": "critical",
                "title": "Address critical anomalies",
                "description": f"{len(critical_anomalies)} critical anomalies detected",
                "recommended_action": "Investigate and remediate critical security anomalies",
                "impact": "Improves security posture"
            })
        
        # Missing policies
        if not risk_scores.get("policy_count", 0):
            recommendations.append({
                "type": "security_posture",
                "priority": "medium",
                "title": "Implement authorization policies",
                "description": "No authorization policies configured",
                "recommended_action": "Create and apply authorization policies",
                "impact": "Enables fine-grained access control"
            })
        
        return recommendations
    
    def generate_ai_recommendations(
        self,
        query: str,
        context: Dict[str, Any],
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate AI-powered recommendations using LLM.
        
        Example queries:
        - "What access policies should we implement?"
        - "How can we improve our IAM security posture?"
        - "Recommend access controls for production environments"
        """
        try:
            prompt = self._build_recommendation_prompt(query, context)
            
            response = self.model_provider.generate(
                prompt,
                temperature=0.5,  # Slightly higher for creative recommendations
                max_tokens=800
            )
            
            return {
                "query": query,
                "recommendation": response,
                "context_used": list(context.keys()),
                "generated_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Error generating AI recommendations: {e}")
            return {
                "query": query,
                "recommendation": "Unable to generate recommendations at this time.",
                "error": str(e)
            }
    
    def _build_recommendation_prompt(self, query: str, context: Dict[str, Any]) -> str:
        """Build prompt for AI recommendation generation."""
        prompt_parts = [
            "You are an IAM security expert providing recommendations for SentinelGrid.",
            "",
            f"User Query: {query}",
            "",
            "Context:"
        ]
        
        if "users" in context:
            prompt_parts.append(f"- User count: {len(context['users'])}")
        if "roles" in context:
            prompt_parts.append(f"- Role count: {len(context['roles'])}")
        if "policies" in context:
            prompt_parts.append(f"- Policy count: {len(context['policies'])}")
        if "risk_score" in context:
            prompt_parts.append(f"- Current risk score: {context['risk_score']}")
        
        prompt_parts.extend([
            "",
            "Provide specific, actionable recommendations based on IAM best practices.",
            "Include:",
            "1. Specific actions to take",
            "2. Expected benefits",
            "3. Priority level",
            "4. Implementation steps (if applicable)",
            "",
            "Recommendation:"
        ])
        
        return "\n".join(prompt_parts)
    
    def _is_recent(self, item: Dict[str, Any], days: int = 90) -> bool:
        """Check if item is recent."""
        timestamp = item.get("timestamp") or item.get("created_at")
        if not timestamp:
            return False
        
        try:
            if isinstance(timestamp, str):
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            else:
                dt = timestamp
            
            cutoff = datetime.utcnow() - timedelta(days=days)
            return dt.replace(tzinfo=None) >= cutoff
        except:
            return False
    
    def _is_stale(self, timestamp: Any, days: int = 90) -> bool:
        """Check if timestamp is stale."""
        if not timestamp:
            return True
        
        try:
            if isinstance(timestamp, str):
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            else:
                dt = timestamp
            
            cutoff = datetime.utcnow() - timedelta(days=days)
            return dt.replace(tzinfo=None) < cutoff
        except:
            return True

