"""Payment service - calculates pricing against the canonical product catalog."""

from typing import Optional, Dict, Any
from decimal import Decimal
import logging

from sg_core.product_catalog import (
    PLAN_TIER_PROTECT,
    PLAN_TIER_PROTECT_DEFEND,
    PLAN_TIER_PROTECT_DEFEND_COMPLY,
    apply_plan_defaults,
    derive_plan_tier,
    get_plan_display_name,
    normalize_plan_tier,
)

logger = logging.getLogger(__name__)


class PaymentService:
    """
    Service for payment calculation and processing.
    Calculates prices based on canonical plan tiers and user band.
    """
    
    # Base pricing table (cents) by user band
    BASE_PRICING = {
        PLAN_TIER_PROTECT: {
            "1-25": 29900,       # $299/month
            "26-150": 99900,     # $999/month
            "151-500": 279900,   # $2,799/month
            "500+": None         # Contact sales
        },
        PLAN_TIER_PROTECT_DEFEND: {
            "1-25": 79900,       # $799/month
            "26-150": 239900,    # $2,399/month
            "151-500": 649900,   # $6,499/month
            "500+": None         # Contact sales
        },
        PLAN_TIER_PROTECT_DEFEND_COMPLY: {
            "1-25": 149900,      # $1,499/month
            "26-150": 449900,    # $4,499/month
            "151-500": 1199900,  # $11,999/month
            "500+": None         # Contact sales
        },
    }

    # Add-on pricing (cents) keyed by add-on name
    ADDONS = {
        "git": {"1-25": 15000, "26-150": 40000, "151-500": 90000, "500+": None},
        "appsec": {"1-25": 20000, "26-150": 50000, "151-500": 110000, "500+": None},
        "ai_hosted": {"1-25": 15000, "26-150": 45000, "151-500": 90000, "500+": None},
        "ai_self": {"1-25": 25000, "26-150": 70000, "151-500": 150000, "500+": None},
        "soc_managed": {"1-25": 60000, "26-150": 150000, "151-500": 300000, "500+": None},
    }
    
    # Internal limits per user band (not shown during signup)
    INTERNAL_LIMITS = {
        "1-25": {
            "included_gb_per_day": 2,
            "hot_retention_days": 30,
            "max_cloud_accounts": 1
        },
        "26-50": {
            "included_gb_per_day": 4,
            "hot_retention_days": 45,
            "max_cloud_accounts": 2
        },
        "51-100": {
            "included_gb_per_day": 8,
            "hot_retention_days": 60,
            "max_cloud_accounts": 3
        },
        "101-250": {
            "included_gb_per_day": 15,
            "hot_retention_days": 90,
            "max_cloud_accounts": 5
        },
        "250+": {
            "included_gb_per_day": None,  # Custom
            "hot_retention_days": None,   # Custom
            "max_cloud_accounts": None   # Custom
        }
    }
    
    # Yearly discount (2 months free = 16.67% discount)
    YEARLY_DISCOUNT = Decimal("0.8333")  # Pay for 10 months, get 12
    
    @classmethod
    def get_user_band(cls, user_count: int) -> str:
        """
        Map user count to user band.
        
        Args:
            user_count: Number of users
            
        Returns:
            User band string: '1-25', '26-50', '51-100', '101-250', or '250+'
        """
        if user_count <= 25:
            return "1-25"
        elif user_count <= 150:
            return "26-150"
        elif user_count <= 500:
            return "151-500"
        else:
            return "500+"
    
    @classmethod
    def get_package_name(
        cls,
        compliance_required: bool = False,
        *,
        plan_tier: Optional[str] = None,
        services_selected: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Resolve the canonical package name for the requested product intent.
        
        Args:
            compliance_required: Whether compliance is required
            
        Returns:
            Canonical package / plan name.
        """
        return derive_plan_tier(
            plan_tier=plan_tier,
            compliance_required=compliance_required,
            services_selected=services_selected,
        )
    
    @classmethod
    def calculate_price(
        cls,
        user_count: int,
        compliance_required: bool,
        plan_tier: Optional[str] = None,
        billing_period: str = "monthly",  # "monthly" or "yearly"
        services_selected: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Calculate total price based on package and user band.
        
        Args:
            user_count: Number of users (used to determine user band)
            compliance_required: Whether compliance is required (determines package)
            billing_period: "monthly" or "yearly"
        
        Returns:
            Dictionary with:
            - package_name: canonical plan tier
            - user_band: '1-25', '26-50', etc.
            - base_price: Base price in cents
            - addons: List of add-on charges (empty for now, can add later)
            - subtotal: Subtotal in cents
            - discount: Discount amount in cents (for yearly)
            - total: Total price in cents
            - display: Human-readable price string
            - requires_sales_contact: Whether to contact sales
        """
        # Determine package and user band
        package_name = cls.get_package_name(
            compliance_required,
            plan_tier=plan_tier,
            services_selected=services_selected,
        )
        user_band = cls.get_user_band(user_count)
        svc = apply_plan_defaults(package_name, services_selected or {})

        # Base price
        base_price = cls.BASE_PRICING.get(package_name, {}).get(user_band)
        
        # If price is None, requires sales contact (250+ users)
        if base_price is None:
            return {
                "package_name": package_name,
                "plan_tier": package_name,
                "package_display": get_plan_display_name(package_name),
                "user_band": user_band,
                "base_price": None,
                "addons": [],
                "subtotal": None,
                "discount": 0,
                "total": None,
                "display": "Contact sales for custom pricing",
                "billing_period": billing_period,
                "requires_sales_contact": True
            }
        
        # No add-ons during signup (simplified flow)
        addons = []
        addon_total = 0

        def add_addon(name: str, display: str, key: str):
            nonlocal addon_total, addons
            amount = cls.ADDONS.get(key, {}).get(user_band)
            if amount is None:
                return
            addon_total += amount
            addons.append({
                "name": display,
                "amount": amount,
                "display": f"${amount/100:,.2f}/month"
            })

        if svc.get("git"):
            add_addon("git", "Git Security", "git")
        if svc.get("appsec"):
            add_addon("appsec", "Application Security", "appsec")
        ai_mode = svc.get("aiShield")
        if ai_mode == "hosted":
            add_addon("ai_hosted", "AI Shield (hosted)", "ai_hosted")
        elif ai_mode == "self":
            add_addon("ai_self", "AI Shield (your environment)", "ai_self")
        if svc.get("socManaged"):
            add_addon("soc_managed", "SOC-as-a-Service", "soc_managed")
        
        # Calculate subtotal
        subtotal = base_price + addon_total
        
        # Apply yearly discount if applicable
        discount = 0
        if billing_period == "yearly":
            # Yearly = 10 months of monthly price (2 months free)
            yearly_price = int(Decimal(subtotal) * 12 * cls.YEARLY_DISCOUNT)
            discount = (subtotal * 12) - yearly_price
            total = yearly_price
        else:
            total = subtotal
        
        # Format display price
        if billing_period == "yearly":
            display = f"${total / 100:,.2f}/year"
            if discount > 0:
                display += f" (save ${discount / 100:,.2f})"
        else:
            display = f"${total / 100:,.2f}/month"
        
        return {
            "package_name": package_name,
            "plan_tier": package_name,
            "package_display": get_plan_display_name(package_name),
            "user_band": user_band,
            "base_price": base_price,
            "addons": addons,
            "subtotal": subtotal,
            "discount": discount,
            "total": total,
            "display": display,
            "billing_period": billing_period,
            "requires_sales_contact": False,
            "services_selected": svc,
        }
    
    @classmethod
    def get_pricing_summary(
        cls,
        user_count: int,
        compliance_required: bool,
        plan_tier: Optional[str] = None,
        billing_period: str = "monthly"
    ) -> Dict[str, Any]:
        """
        Get a human-readable pricing summary.
        
        Returns:
            Dictionary with pricing breakdown and summary
        """
        pricing = cls.calculate_price(
            user_count=user_count,
            compliance_required=compliance_required,
            plan_tier=plan_tier,
            billing_period=billing_period,
            services_selected={},  # summary path omits add-ons
        )
        canonical_plan_tier = normalize_plan_tier(plan_tier) or pricing["plan_tier"]
        package_display = get_plan_display_name(canonical_plan_tier)
        
        return {
            "package_name": pricing['package_name'],
            "plan_tier": pricing["plan_tier"],
            "package_display": package_display,
            "user_band": pricing['user_band'],
            "user_count": user_count,
            "billing_period": billing_period,
            "pricing": pricing,
            "summary": {
                "base": f"${pricing['base_price'] / 100:,.2f}/month" if pricing['base_price'] else "Custom",
                "addons_count": len(pricing['addons']),
                "total": pricing['display']
            }
        }
    
    @classmethod
    def get_internal_limits(cls, user_band: str) -> Dict[str, Any]:
        """
        Get internal limits for a user band (not shown during signup).
        
        Args:
            user_band: User band string
            
        Returns:
            Dictionary with included_gb_per_day, hot_retention_days, max_cloud_accounts
        """
        return cls.INTERNAL_LIMITS.get(user_band, {})
