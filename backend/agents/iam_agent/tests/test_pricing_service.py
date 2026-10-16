from app.services.pricing_service import PricingService


def test_get_realm_strategy_starter_returns_shared():
    assert PricingService.get_realm_strategy("starter", user_count=10, org_count=0) == "shared"


def test_get_realm_strategy_enterprise_returns_dedicated():
    assert PricingService.get_realm_strategy("enterprise", user_count=100, org_count=0) == "dedicated"


def test_get_realm_strategy_professional_500_users_returns_shared():
    assert PricingService.get_realm_strategy("professional", user_count=500, org_count=0) == "shared"


def test_get_realm_strategy_professional_501_users_returns_dedicated():
    assert PricingService.get_realm_strategy("professional", user_count=501, org_count=0) == "dedicated"


def test_get_realm_strategy_professional_1_org_returns_shared():
    assert PricingService.get_realm_strategy("professional", user_count=100, org_count=1) == "shared"


def test_get_realm_strategy_professional_2_orgs_returns_dedicated():
    assert PricingService.get_realm_strategy("professional", user_count=100, org_count=2) == "dedicated"


def test_can_create_org_respects_tier_limits():
    assert PricingService.can_create_org("starter", current_org_count=0) is False
    assert PricingService.can_create_org("professional", current_org_count=0) is True
    assert PricingService.can_create_org("professional", current_org_count=1) is False
    assert PricingService.can_create_org("enterprise", current_org_count=10) is True


def test_can_add_user_respects_tier_limits():
    assert PricingService.can_add_user("free", current_user_count=4) is True
    assert PricingService.can_add_user("free", current_user_count=5) is False
    assert PricingService.can_add_user("starter", current_user_count=99) is True
    assert PricingService.can_add_user("starter", current_user_count=100) is False
    assert PricingService.can_add_user("enterprise", current_user_count=1000) is True


def test_requires_dedicated_realm_when_compliance_is_enabled():
    assert PricingService.requires_dedicated_realm(
        "starter",
        user_count=10,
        org_count=0,
        compliance_required=True,
    ) is True


def test_get_pricing_info_defaults_invalid_tier_to_starter():
    pricing_info = PricingService.get_pricing_info("invalid")

    assert pricing_info["name"] == "Starter"
