from app.services.realm_manager import RealmManager


def test_get_realm_for_customer_shared(mock_keycloak_admin, customer_record_factory):
    manager = RealmManager(mock_keycloak_admin)

    realm = manager.get_realm_for_customer(
        "customer-123",
        customer_record_factory(pricing_tier="starter", user_count=10, org_count=0),
    )

    assert realm == "sentinelgrid"


def test_get_realm_for_customer_dedicated(mock_keycloak_admin, customer_record_factory):
    manager = RealmManager(mock_keycloak_admin)

    realm = manager.get_realm_for_customer(
        "customer-123",
        customer_record_factory(
            pricing_tier="enterprise",
            user_count=100,
            org_count=0,
            name="Enterprise Corp",
        ),
    )

    assert realm.startswith("sg-ent-")
    assert realm != "sentinelgrid"


def test_get_realm_for_org_uses_org_realm_name(mock_keycloak_admin):
    manager = RealmManager(mock_keycloak_admin)

    realm = manager.get_realm_for_org("org-123", {"realm_name": "org-dedicated-realm-12345"})

    assert realm == "org-dedicated-realm-12345"


def test_get_realm_for_org_falls_back_to_sentinelgrid(mock_keycloak_admin):
    manager = RealmManager(mock_keycloak_admin)

    realm = manager.get_realm_for_org("org-123", {})

    assert realm == "sentinelgrid"


def test_get_realm_for_customer_professional_shared(mock_keycloak_admin, customer_record_factory):
    manager = RealmManager(mock_keycloak_admin)

    realm = manager.get_realm_for_customer(
        "customer-123",
        customer_record_factory(pricing_tier="professional", user_count=100, org_count=0),
    )

    assert realm == "sentinelgrid"


def test_get_realm_for_customer_professional_dedicated_users(mock_keycloak_admin, customer_record_factory):
    manager = RealmManager(mock_keycloak_admin)

    realm = manager.get_realm_for_customer(
        "customer-123",
        customer_record_factory(
            pricing_tier="professional",
            user_count=600,
            org_count=0,
            name="Large Professional Corp",
        ),
    )

    assert realm.startswith("sg-ent-")


def test_get_realm_for_customer_professional_dedicated_orgs(mock_keycloak_admin, customer_record_factory):
    manager = RealmManager(mock_keycloak_admin)

    realm = manager.get_realm_for_customer(
        "customer-123",
        customer_record_factory(
            pricing_tier="professional",
            user_count=100,
            org_count=2,
            name="Multi Org Professional",
        ),
    )

    assert realm.startswith("sg-ent-")


def test_get_realm_for_customer_existing_dedicated(mock_keycloak_admin, customer_record_factory):
    manager = RealmManager(mock_keycloak_admin)

    realm = manager.get_realm_for_customer(
        "customer-123",
        customer_record_factory(
            has_dedicated_realm=True,
            realm_name="existing-dedicated-realm-abc123",
        ),
    )

    assert realm == "existing-dedicated-realm-abc123"


def test_generate_realm_name_sanitizes_company_name(mock_keycloak_admin):
    manager = RealmManager(mock_keycloak_admin)

    realm_name = manager._generate_realm_name("Company & Co. (Inc.)")

    assert realm_name.startswith("sg-ent-")
    assert "company" in realm_name
    assert "&" not in realm_name


def test_generate_realm_name_handles_edge_cases(mock_keycloak_admin):
    manager = RealmManager(mock_keycloak_admin)

    assert manager._generate_realm_name("A").startswith("sg-ent-")
    assert len(manager._generate_realm_name("A" * 100)) <= 57
