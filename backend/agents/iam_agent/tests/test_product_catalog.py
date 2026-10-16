from sg_core.product_catalog import (
    PLAN_TIER_PROTECT,
    PLAN_TIER_PROTECT_DEFEND,
    PLAN_TIER_PROTECT_DEFEND_COMPLY,
    apply_plan_defaults,
    derive_plan_tier,
    normalize_plan_tier,
    requires_dedicated_realm,
)


def test_normalize_plan_tier_accepts_legacy_alias():
    assert normalize_plan_tier("protect_comply") == PLAN_TIER_PROTECT_DEFEND_COMPLY


def test_derive_plan_tier_uses_explicit_signup_selections():
    assert derive_plan_tier(services_selected={"ticketing": "jira"}) == PLAN_TIER_PROTECT_DEFEND
    assert derive_plan_tier(compliance_required=True) == PLAN_TIER_PROTECT_DEFEND_COMPLY
    assert derive_plan_tier() == PLAN_TIER_PROTECT


def test_apply_plan_defaults_enables_trust_profile_for_comply():
    services = apply_plan_defaults(PLAN_TIER_PROTECT_DEFEND_COMPLY, {"cloud": True})
    assert services["cloud"] is True
    assert services["trustProfile"]["enabled"] is True


def test_requires_dedicated_realm_only_for_customer_managed_comply():
    assert requires_dedicated_realm(
        PLAN_TIER_PROTECT_DEFEND_COMPLY,
        {"socManaged": False},
    ) is True
    assert requires_dedicated_realm(
        PLAN_TIER_PROTECT_DEFEND_COMPLY,
        {"socManaged": True},
    ) is False
    assert requires_dedicated_realm(PLAN_TIER_PROTECT_DEFEND, {"socManaged": False}) is False
