"""
Pricing service - determines realm strategy based on pricing tier.
Integrates pricing with realm architecture decisions.
"""

from typing import Optional
import logging

logger = logging.getLogger(__name__)


class PricingService:
    """
    Service for pricing and tier management.
    Determines realm strategy based on pricing tier and usage.
    """
    
    # Pricing tiers and their realm strategy configuration
    TIER_CONFIG = {
        "free": {
            "realm_strategy": "shared",
            "max_users": 5,  # Updated: Allow companies with 5 users or less to use free tier
            "max_orgs": 0,
            "dedicated_realm": False,
            "can_upgrade_to_dedicated": False
        },
        "starter": {
            "realm_strategy": "shared",
            "max_users": 100,
            "max_orgs": 0,
            "dedicated_realm": False,
            "can_upgrade_to_dedicated": False
        },
        "professional": {
            "realm_strategy": "shared",  # Can upgrade to dedicated
            "max_users": 1000,
            "max_orgs": 1,
            "dedicated_realm": False,  # Optional upgrade
            "can_upgrade_to_dedicated": True
        },
        "enterprise": {
            "realm_strategy": "dedicated",
            "max_users": -1,  # Unlimited
            "max_orgs": -1,  # Unlimited
            "dedicated_realm": True,
            "can_upgrade_to_dedicated": False  # Already has it
        }
    }
    
    @classmethod
    def get_realm_strategy(
        cls,
        pricing_tier: str,
        user_count: int = 0,
        org_count: int = 0
    ) -> str:
        """
        Determine realm strategy based on pricing tier and usage.
        
        Args:
            pricing_tier: Customer pricing tier (free, starter, professional, enterprise)
            user_count: Current number of users
            org_count: Current number of organizations
        
        Returns:
            "shared" or "dedicated"
        """
        tier_config = cls.TIER_CONFIG.get(pricing_tier, cls.TIER_CONFIG["starter"])
        
        # Enterprise always gets dedicated realm
        if pricing_tier == "enterprise":
            return "dedicated"
        
        # Professional can upgrade to dedicated if needed
        if pricing_tier == "professional":
            # Auto-upgrade if >500 users or multiple orgs
            if user_count > 500 or org_count > 1:
                return "dedicated"
            return "shared"
        
        # Starter and Free always use shared
        return "shared"
    
    @classmethod
    def can_create_org(cls, pricing_tier: str, current_org_count: int) -> bool:
        """
        Check if customer can create another organization.
        
        Args:
            pricing_tier: Customer pricing tier
            current_org_count: Current number of organizations
        
        Returns:
            True if can create org, False otherwise
        """
        tier_config = cls.TIER_CONFIG.get(pricing_tier, cls.TIER_CONFIG["starter"])
        max_orgs = tier_config["max_orgs"]
        
        if max_orgs == -1:
            return True  # Unlimited
        
        return current_org_count < max_orgs
    
    @classmethod
    def can_add_user(cls, pricing_tier: str, current_user_count: int) -> bool:
        """
        Check if customer can add another user.
        
        Args:
            pricing_tier: Customer pricing tier
            current_user_count: Current number of users
        
        Returns:
            True if can add user, False otherwise
        """
        tier_config = cls.TIER_CONFIG.get(pricing_tier, cls.TIER_CONFIG["starter"])
        max_users = tier_config["max_users"]
        
        if max_users == -1:
            return True  # Unlimited
        
        return current_user_count < max_users
    
    @classmethod
    def get_tier_config(cls, pricing_tier: str) -> dict:
        """
        Get full configuration for a pricing tier.
        
        Args:
            pricing_tier: Customer pricing tier
        
        Returns:
            Tier configuration dictionary
        """
        return cls.TIER_CONFIG.get(pricing_tier, cls.TIER_CONFIG["starter"])
    
    @classmethod
    def requires_dedicated_realm(
        cls,
        pricing_tier: str,
        user_count: int = 0,
        org_count: int = 0,
        compliance_required: bool = False
    ) -> bool:
        """
        Determine if customer requires dedicated realm.
        
        Args:
            pricing_tier: Customer pricing tier
            user_count: Current number of users
            org_count: Current number of organizations
            compliance_required: Whether compliance requires isolation
        
        Returns:
            True if dedicated realm required, False otherwise
        """
        # Compliance requirement always needs dedicated realm
        if compliance_required:
            return True
        
        # Check realm strategy
        strategy = cls.get_realm_strategy(pricing_tier, user_count, org_count)
        return strategy == "dedicated"
    
    @classmethod
    def can_upgrade_to_dedicated(cls, pricing_tier: str) -> bool:
        """
        Check if customer can upgrade to dedicated realm.
        
        Args:
            pricing_tier: Customer pricing tier
        
        Returns:
            True if can upgrade, False otherwise
        """
        tier_config = cls.TIER_CONFIG.get(pricing_tier, cls.TIER_CONFIG["starter"])
        return tier_config.get("can_upgrade_to_dedicated", False)
    
    @classmethod
    def determine_tier_from_employee_count(cls, employee_count: int) -> str:
        """
        Determine pricing tier based on employee count.
        
        Args:
            employee_count: Number of employees in the company
        
        Returns:
            Pricing tier: free, starter, professional, or enterprise
        """
        if employee_count <= 5:
            return "free"
        elif employee_count <= 100:
            return "starter"
        elif employee_count <= 1000:
            return "professional"
        else:
            return "enterprise"
    
    @classmethod
    def get_pricing_info(cls, tier: str) -> dict:
        """
        Get pricing information for a tier.
        
        Args:
            tier: Pricing tier (free, starter, professional, enterprise)
        
        Returns:
            Dictionary with price, features, limits, and display information
        """
        pricing_info = {
            "free": {
                "name": "Free",
                "price": 0,
                "price_display": "Free",
                "max_users": 5,
                "max_orgs": 0,
                "features": [
                    "Basic SIEM",
                    "Core SOAR playbooks",
                    "IAM hygiene checks",
                    "Posture scans",
                    "Community support"
                ],
                "description": "Perfect for small teams getting started"
            },
            "starter": {
                "name": "Starter",
                "price": 500,  # Example pricing - adjust as needed
                "price_display": "$500/month",
                "max_users": 100,
                "max_orgs": 0,
                "features": [
                    "Full SIEM capabilities",
                    "SOAR playbooks",
                    "IAM hygiene monitoring",
                    "Posture scans",
                    "Email support",
                    "90 days log retention"
                ],
                "description": "Get a SOC without hiring one"
            },
            "professional": {
                "name": "Professional",
                "price": 2000,  # Example pricing - adjust as needed
                "price_display": "$2,000/month",
                "max_users": 1000,
                "max_orgs": 1,
                "features": [
                    "Everything in Starter",
                    "Priority support",
                    "Custom playbooks",
                    "Extended log retention (180 days)",
                    "Advanced analytics",
                    "Dedicated realm (if >500 users)"
                ],
                "description": "Mid-market security backbone"
            },
            "enterprise": {
                "name": "Enterprise",
                "price": None,
                "price_display": "Custom pricing",
                "max_users": -1,  # Unlimited
                "max_orgs": -1,  # Unlimited
                "features": [
                    "Everything in Professional",
                    "Dedicated infrastructure",
                    "Custom SLAs",
                    "On-prem deployment options",
                    "24/7 dedicated support",
                    "Unlimited users and organizations"
                ],
                "description": "For large enterprises and MSSPs"
            }
        }
        return pricing_info.get(tier, pricing_info["starter"])

