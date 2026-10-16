from app.services.payment_service import PaymentService


def test_calculate_price_uses_canonical_plan_tier():
    pricing = PaymentService.calculate_price(
        user_count=25,
        compliance_required=False,
        plan_tier="protect_defend",
        billing_period="monthly",
        services_selected={},
    )

    assert pricing["plan_tier"] == "protect_defend"
    assert pricing["package_name"] == "protect_defend"
    assert pricing["package_display"] == "SentinelGrid Protect + Defend"
    assert pricing["base_price"] == 79900
    assert pricing["total"] == 79900


def test_calculate_price_normalizes_legacy_package_alias():
    pricing = PaymentService.calculate_price(
        user_count=25,
        compliance_required=False,
        plan_tier="protect_comply",
        billing_period="monthly",
        services_selected={},
    )

    assert pricing["plan_tier"] == "protect_defend_comply"
    assert pricing["package_name"] == "protect_defend_comply"
    assert pricing["base_price"] == 149900


def test_calculate_price_applies_yearly_discount_after_addons():
    pricing = PaymentService.calculate_price(
        user_count=25,
        compliance_required=False,
        plan_tier="protect",
        billing_period="yearly",
        services_selected={"aiShield": "hosted"},
    )

    assert pricing["plan_tier"] == "protect"
    assert pricing["total"] == 448982
    assert pricing["discount"] == 89818
