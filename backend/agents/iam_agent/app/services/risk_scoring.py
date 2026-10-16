"""
Risk Scoring Service for IAM
Calculates risk scores for users, entitlements, resources, and tenants
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)


class RiskScoringService:
    """Service for calculating IAM risk scores."""
    
    def __init__(self):
        self.risk_weights = {
            "privilege_level": 0.3,
            "access_frequency": 0.2,
            "last_activity": 0.15,
            "anomaly_count": 0.25,
            "entitlement_count": 0.1
        }
    
    def calculate_user_risk_score(
        self,
        user_id: str,
        user_data: Dict[str, Any],
        access_history: List[Dict[str, Any]],
        anomalies: List[Dict[str, Any]],
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive risk score for a user.
        
        Factors:
        - Privilege level (high-privilege roles = higher risk)
        - Access frequency (unusual patterns = higher risk)
        - Last activity (stale accounts = higher risk)
        - Anomaly count (more anomalies = higher risk)
        - Entitlement count (over-privileged = higher risk)
        """
        risk_factors = {}
        
        # 1. Privilege Level Risk (0-100)
        privilege_risk = self._calculate_privilege_risk(user_data)
        risk_factors["privilege_level"] = privilege_risk
        
        # 2. Access Frequency Risk (0-100)
        frequency_risk = self._calculate_frequency_risk(access_history)
        risk_factors["access_frequency"] = frequency_risk
        
        # 3. Last Activity Risk (0-100)
        activity_risk = self._calculate_activity_risk(access_history)
        risk_factors["last_activity"] = activity_risk
        
        # 4. Anomaly Risk (0-100)
        anomaly_risk = self._calculate_anomaly_risk(anomalies)
        risk_factors["anomaly_count"] = anomaly_risk
        
        # 5. Entitlement Count Risk (0-100)
        entitlement_risk = self._calculate_entitlement_risk(user_data)
        risk_factors["entitlement_count"] = entitlement_risk
        
        # Calculate weighted overall risk score
        overall_risk = sum(
            risk_factors.get(factor, 0) * weight
            for factor, weight in self.risk_weights.items()
        )
        
        # Determine risk level
        if overall_risk >= 70:
            risk_level = "critical"
        elif overall_risk >= 50:
            risk_level = "high"
        elif overall_risk >= 30:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        return {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "overall_risk_score": round(overall_risk, 2),
            "risk_level": risk_level,
            "risk_factors": risk_factors,
            "calculated_at": datetime.utcnow().isoformat(),
            "recommendations": self._generate_user_recommendations(overall_risk, risk_factors)
        }
    
    def calculate_entitlement_risk_score(
        self,
        entitlement: Dict[str, Any],
        usage_history: List[Dict[str, Any]],
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculate risk score for an entitlement.
        
        Factors:
        - Resource sensitivity
        - Usage frequency
        - User count
        - Last usage
        """
        risk_factors = {}
        
        # Resource sensitivity
        resource = entitlement.get("resource_type") or entitlement.get("resource", "")
        sensitivity = self._assess_resource_sensitivity(resource)
        risk_factors["resource_sensitivity"] = sensitivity * 100
        
        # Usage frequency
        usage_risk = self._calculate_entitlement_usage_risk(usage_history)
        risk_factors["usage_frequency"] = usage_risk
        
        # User count (many users = lower per-user risk, but higher aggregate risk)
        user_count = entitlement.get("user_count", 1)
        risk_factors["user_count"] = min(100, user_count * 5)  # Cap at 100
        
        # Last usage
        last_usage_risk = self._calculate_last_usage_risk(usage_history)
        risk_factors["last_usage"] = last_usage_risk
        
        # Calculate overall risk
        overall_risk = (
            risk_factors["resource_sensitivity"] * 0.4 +
            risk_factors["usage_frequency"] * 0.2 +
            risk_factors["user_count"] * 0.2 +
            risk_factors["last_usage"] * 0.2
        )
        
        risk_level = "critical" if overall_risk >= 70 else \
                    "high" if overall_risk >= 50 else \
                    "medium" if overall_risk >= 30 else "low"
        
        return {
            "entitlement_id": entitlement.get("id"),
            "tenant_id": tenant_id,
            "overall_risk_score": round(overall_risk, 2),
            "risk_level": risk_level,
            "risk_factors": risk_factors,
            "calculated_at": datetime.utcnow().isoformat()
        }
    
    def calculate_resource_risk_score(
        self,
        resource: Dict[str, Any],
        access_history: List[Dict[str, Any]],
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Calculate risk score for a resource."""
        resource_id = resource.get("resource_id") or resource.get("id") or ""
        resource_type = resource.get("resource_type") or ""
        
        sensitivity = self._assess_resource_sensitivity(resource_type or resource_id)
        access_count = len(access_history)
        unique_users = len(set(a.get("user_id") for a in access_history if a.get("user_id")))
        
        # Risk increases with sensitivity and access
        overall_risk = (sensitivity * 60) + min(40, (access_count / 100) * 40)
        
        risk_level = "critical" if overall_risk >= 70 else \
                    "high" if overall_risk >= 50 else \
                    "medium" if overall_risk >= 30 else "low"
        
        return {
            "resource_id": resource_id,
            "resource_type": resource_type,
            "tenant_id": tenant_id,
            "overall_risk_score": round(overall_risk, 2),
            "risk_level": risk_level,
            "metrics": {
                "sensitivity": sensitivity,
                "access_count": access_count,
                "unique_users": unique_users
            },
            "calculated_at": datetime.utcnow().isoformat()
        }
    
    def calculate_tenant_risk_score(
        self,
        tenant_id: str,
        users: List[Dict[str, Any]],
        entitlements: List[Dict[str, Any]],
        anomalies: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate aggregate risk score for a tenant."""
        
        # Calculate average user risk
        user_risks = [u.get("risk_score", 0) for u in users if u.get("risk_score")]
        avg_user_risk = sum(user_risks) / len(user_risks) if user_risks else 0
        
        # Calculate average entitlement risk
        entitlement_risks = [e.get("risk_score", 0) for e in entitlements if e.get("risk_score")]
        avg_entitlement_risk = sum(entitlement_risks) / len(entitlement_risks) if entitlement_risks else 0
        
        # Anomaly count risk
        critical_anomalies = sum(1 for a in anomalies if a.get("severity") == "critical")
        high_anomalies = sum(1 for a in anomalies if a.get("severity") == "high")
        anomaly_risk = min(100, (critical_anomalies * 20) + (high_anomalies * 10))
        
        # Overall tenant risk (weighted average)
        overall_risk = (
            avg_user_risk * 0.4 +
            avg_entitlement_risk * 0.3 +
            anomaly_risk * 0.3
        )
        
        risk_level = "critical" if overall_risk >= 70 else \
                    "high" if overall_risk >= 50 else \
                    "medium" if overall_risk >= 30 else "low"
        
        return {
            "tenant_id": tenant_id,
            "overall_risk_score": round(overall_risk, 2),
            "risk_level": risk_level,
            "components": {
                "avg_user_risk": round(avg_user_risk, 2),
                "avg_entitlement_risk": round(avg_entitlement_risk, 2),
                "anomaly_risk": round(anomaly_risk, 2),
                "user_count": len(users),
                "entitlement_count": len(entitlements),
                "anomaly_count": len(anomalies)
            },
            "calculated_at": datetime.utcnow().isoformat()
        }
    
    def _calculate_privilege_risk(self, user_data: Dict[str, Any]) -> float:
        """Calculate risk based on privilege level."""
        roles = user_data.get("roles", [])
        
        high_privilege_keywords = ['ADMIN', 'SUPER', 'ROOT', 'SYS', 'OWNER', 'MANAGER']
        medium_privilege_keywords = ['WRITE', 'MODIFY', 'DELETE', 'CREATE']
        
        privilege_score = 0
        for role in roles:
            role_name = (role.get("name") or role.get("role") or "").upper()
            
            if any(kw in role_name for kw in high_privilege_keywords):
                privilege_score += 30
            elif any(kw in role_name for kw in medium_privilege_keywords):
                privilege_score += 15
            else:
                privilege_score += 5
        
        return min(100, privilege_score)
    
    def _calculate_frequency_risk(self, access_history: List[Dict[str, Any]]) -> float:
        """Calculate risk based on access frequency patterns."""
        if not access_history:
            return 50  # Moderate risk if no history
        
        # Check for unusual spikes
        daily_counts = defaultdict(int)
        for access in access_history[-30:]:  # Last 30 days
            timestamp = access.get("timestamp")
            if timestamp:
                try:
                    if isinstance(timestamp, str):
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    else:
                        dt = timestamp
                    day_key = dt.date().isoformat()
                    daily_counts[day_key] += 1
                except:
                    continue
        
        if not daily_counts:
            return 30
        
        counts = list(daily_counts.values())
        avg = sum(counts) / len(counts)
        max_count = max(counts)
        
        # High risk if max is > 3x average
        if max_count > (avg * 3):
            return 80
        elif max_count > (avg * 2):
            return 60
        else:
            return 30
    
    def _calculate_activity_risk(self, access_history: List[Dict[str, Any]]) -> float:
        """Calculate risk based on last activity."""
        if not access_history:
            return 70  # Higher risk for inactive accounts
        
        # Get most recent access
        latest = max(
            (a.get("timestamp") for a in access_history if a.get("timestamp")),
            default=None
        )
        
        if not latest:
            return 70
        
        try:
            if isinstance(latest, str):
                latest_dt = datetime.fromisoformat(latest.replace('Z', '+00:00'))
            else:
                latest_dt = latest
            
            days_since = (datetime.utcnow() - latest_dt.replace(tzinfo=None)).days
            
            # Higher risk for stale accounts
            if days_since > 90:
                return 80
            elif days_since > 30:
                return 50
            else:
                return 20
        except:
            return 40
    
    def _calculate_anomaly_risk(self, anomalies: List[Dict[str, Any]]) -> float:
        """Calculate risk based on anomaly count."""
        if not anomalies:
            return 0
        
        critical_count = sum(1 for a in anomalies if a.get("severity") == "critical")
        high_count = sum(1 for a in anomalies if a.get("severity") == "high")
        medium_count = sum(1 for a in anomalies if a.get("severity") == "medium")
        
        risk = (critical_count * 30) + (high_count * 20) + (medium_count * 10)
        return min(100, risk)
    
    def _calculate_entitlement_risk(self, user_data: Dict[str, Any]) -> float:
        """Calculate risk based on entitlement count."""
        entitlement_count = user_data.get("entitlement_count", 0) or len(user_data.get("entitlements", []))
        
        # Higher risk for over-privileged users
        if entitlement_count > 50:
            return 70
        elif entitlement_count > 20:
            return 50
        elif entitlement_count > 10:
            return 30
        else:
            return 10
    
    def _assess_resource_sensitivity(self, resource: str) -> float:
        """Assess resource sensitivity (0.0 to 1.0)."""
        resource_upper = resource.upper()
        
        # Critical resources
        critical_keywords = ['PROD', 'PRODUCTION', 'PII', 'PHI', 'CREDIT', 'PAYMENT', 'SSN', 'PASSWORD']
        if any(kw in resource_upper for kw in critical_keywords):
            return 1.0
        
        # High sensitivity
        high_keywords = ['DATABASE', 'DB', 'SECRET', 'KEY', 'TOKEN', 'CREDENTIAL']
        if any(kw in resource_upper for kw in high_keywords):
            return 0.8
        
        # Medium sensitivity
        medium_keywords = ['ADMIN', 'CONFIG', 'SETTING', 'USER']
        if any(kw in resource_upper for kw in medium_keywords):
            return 0.5
        
        # Low sensitivity (default)
        return 0.3
    
    def _calculate_entitlement_usage_risk(self, usage_history: List[Dict[str, Any]]) -> float:
        """Calculate risk based on entitlement usage."""
        if not usage_history:
            return 70  # High risk for unused entitlements
        
        # Recent usage (last 30 days)
        recent = [u for u in usage_history if self._is_recent(u, days=30)]
        
        if not recent:
            return 70  # Unused = high risk
        elif len(recent) < 5:
            return 50  # Rarely used = medium risk
        else:
            return 20  # Regularly used = low risk
    
    def _calculate_last_usage_risk(self, usage_history: List[Dict[str, Any]]) -> float:
        """Calculate risk based on last usage time."""
        if not usage_history:
            return 80
        
        latest = max(
            (u.get("timestamp") for u in usage_history if u.get("timestamp")),
            default=None
        )
        
        if not latest:
            return 80
        
        try:
            if isinstance(latest, str):
                latest_dt = datetime.fromisoformat(latest.replace('Z', '+00:00'))
            else:
                latest_dt = latest
            
            days_since = (datetime.utcnow() - latest_dt.replace(tzinfo=None)).days
            
            if days_since > 90:
                return 80
            elif days_since > 30:
                return 50
            else:
                return 20
        except:
            return 40
    
    def _generate_user_recommendations(
        self,
        overall_risk: float,
        risk_factors: Dict[str, float]
    ) -> List[str]:
        """Generate recommendations based on risk factors."""
        recommendations = []
        
        if overall_risk >= 70:
            recommendations.append("Consider immediate access review and potential revocation")
        
        if risk_factors.get("privilege_level", 0) > 60:
            recommendations.append("User has high-privilege roles - review necessity")
        
        if risk_factors.get("anomaly_count", 0) > 50:
            recommendations.append("Multiple anomalies detected - investigate user activity")
        
        if risk_factors.get("entitlement_count", 0) > 50:
            recommendations.append("User has excessive entitlements - apply least privilege")
        
        if risk_factors.get("last_activity", 0) > 60:
            recommendations.append("Account appears inactive - consider disabling or reviewing")
        
        if not recommendations:
            recommendations.append("Risk level is acceptable - continue monitoring")
        
        return recommendations
    
    def _is_recent(self, item: Dict[str, Any], days: int = 30) -> bool:
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

