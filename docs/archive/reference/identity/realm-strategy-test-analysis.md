# Realm Strategy Test Coverage Analysis

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Date:** 2025-01-28  
**Purpose:** Analyze test coverage for realm creation strategies based on organization sizes and pricing tiers

---

## Executive Summary

This document analyzes the test coverage for realm strategy decisions (shared vs dedicated realms) based on customer pricing tiers, user counts, and organization counts. The analysis compares existing tests against the design/architecture requirements defined in `PricingService`.

---

## Architecture Overview

### Realm Strategy Logic (from `PricingService`)

The system uses a **hybrid multi-realm architecture** with the following rules:

1. **Free Tier**
   - Always: `shared` realm
   - Max users: 10
   - Max orgs: 0
   - Cannot upgrade to dedicated

2. **Starter Tier**
   - Always: `shared` realm
   - Max users: 100
   - Max orgs: 0
   - Cannot upgrade to dedicated

3. **Professional Tier**
   - Default: `shared` realm
   - Max users: 1000
   - Max orgs: 1
   - **Auto-upgrade to dedicated if:**
     - `user_count > 500` OR
     - `org_count > 1`
   - Can manually upgrade to dedicated

4. **Enterprise Tier**
   - Always: `dedicated` realm
   - Unlimited users
   - Unlimited orgs
   - Already has dedicated realm

5. **Compliance Requirement**
   - Always requires `dedicated` realm (regardless of tier)

6. **Organizations**
   - Each organization always gets a `dedicated` realm (per `RealmManager.get_realm_for_org()`)

---

## Current Test Coverage

### Test File: `backend/tests/test_auth_api_client.py`

#### ✅ Tests That Exist

1. **`test_get_realm_strategy_starter`**
   - Tests: Starter tier → shared realm
   - Status: ✅ Covered
   - Test: `PricingService.get_realm_strategy("starter", user_count=10, org_count=0) == "shared"`

2. **`test_get_realm_strategy_enterprise`**
   - Tests: Enterprise tier → dedicated realm
   - Status: ✅ Covered
   - Test: `PricingService.get_realm_strategy("enterprise", user_count=100, org_count=0) == "dedicated"`

3. **`test_get_realm_strategy_professional_shared`**
   - Tests: Professional tier with 100 users → shared realm
   - Status: ✅ Covered
   - Test: `PricingService.get_realm_strategy("professional", user_count=100, org_count=0) == "shared"`

4. **`test_get_realm_strategy_professional_dedicated`**
   - Tests: Professional tier with 600 users → dedicated realm
   - Status: ✅ Covered
   - Test: `PricingService.get_realm_strategy("professional", user_count=600, org_count=0) == "dedicated"`

5. **`test_can_create_org`**
   - Tests: Organization creation limits per tier
   - Status: ✅ Covered
   - Tests: Starter (no orgs), Professional (1 org), Enterprise (unlimited)

6. **`test_can_add_user`**
   - Tests: User addition limits per tier
   - Status: ✅ Covered
   - Tests: Starter (100 max), Enterprise (unlimited)

7. **`test_get_realm_for_customer_shared`**
   - Tests: RealmManager returns shared realm for starter tier
   - Status: ✅ Covered

8. **`test_get_realm_for_customer_dedicated`**
   - Tests: RealmManager returns dedicated realm for enterprise tier
   - Status: ✅ Covered

9. **`test_generate_realm_name`**
   - Tests: Realm name generation from customer name
   - Status: ✅ Covered

---

## Missing Test Cases

### 🔴 Critical Missing Tests

#### 1. **Free Tier Tests**
- ❌ `test_get_realm_strategy_free` - Free tier should return "shared"
- ❌ `test_can_add_user_free` - Free tier max 10 users
- ❌ `test_can_create_org_free` - Free tier max 0 orgs

#### 2. **Professional Tier Boundary Cases**
- ❌ `test_get_realm_strategy_professional_500_users` - Exactly 500 users should be "shared" (boundary)
- ❌ `test_get_realm_strategy_professional_501_users` - Exactly 501 users should be "dedicated" (boundary)
- ❌ `test_get_realm_strategy_professional_1_org` - 1 org should be "shared" (within limit)
- ❌ `test_get_realm_strategy_professional_2_orgs` - 2 orgs should trigger "dedicated" (boundary)

#### 3. **Compliance Requirement Tests**
- ❌ `test_requires_dedicated_realm_compliance` - Compliance requirement should force dedicated realm
- ❌ `test_requires_dedicated_realm_starter_with_compliance` - Starter tier with compliance → dedicated
- ❌ `test_requires_dedicated_realm_professional_with_compliance` - Professional tier with compliance → dedicated

#### 4. **Organization Realm Tests**
- ❌ `test_get_realm_for_org` - Organizations should always get dedicated realm
- ❌ `test_org_realm_creation` - Integration test for org realm creation

#### 5. **Upgrade Capability Tests**
- ❌ `test_can_upgrade_to_dedicated_free` - Free tier cannot upgrade
- ❌ `test_can_upgrade_to_dedicated_starter` - Starter tier cannot upgrade
- ❌ `test_can_upgrade_to_dedicated_professional` - Professional tier can upgrade
- ❌ `test_can_upgrade_to_dedicated_enterprise` - Enterprise tier already has it

#### 6. **Integration Tests**
- ❌ `test_realm_creation_starter` - Integration test: actual realm creation for starter tier
- ❌ `test_realm_creation_professional_shared` - Integration test: shared realm for professional
- ❌ `test_realm_creation_professional_dedicated` - Integration test: dedicated realm creation for professional
- ❌ `test_realm_creation_enterprise` - Integration test: dedicated realm creation for enterprise
- ❌ `test_realm_creation_org` - Integration test: dedicated realm creation for organization
- ❌ `test_realm_auto_upgrade_professional` - Integration test: auto-upgrade when user count exceeds 500
- ❌ `test_realm_auto_upgrade_professional_orgs` - Integration test: auto-upgrade when org count exceeds 1

#### 7. **Edge Cases**
- ❌ `test_realm_strategy_invalid_tier` - Invalid tier should default to starter
- ❌ `test_realm_strategy_zero_users` - Zero users should still work
- ❌ `test_realm_strategy_negative_values` - Negative user/org counts (should handle gracefully)
- ❌ `test_realm_name_generation_edge_cases` - Special characters, long names, unicode

#### 8. **RealmManager Additional Tests**
- ❌ `test_get_realm_for_customer_professional_shared` - Professional with <500 users
- ❌ `test_get_realm_for_customer_professional_dedicated_users` - Professional with >500 users
- ❌ `test_get_realm_for_customer_professional_dedicated_orgs` - Professional with >1 org
- ❌ `test_get_realm_for_customer_existing_dedicated` - Customer with `has_dedicated_realm=True`
- ❌ `test_create_dedicated_realm_idempotent` - Creating existing realm should be safe
- ❌ `test_create_dedicated_realm_clients_roles` - Verify clients and roles are created

---

## Test Coverage Matrix

| Test Case | Tier | User Count | Org Count | Expected Strategy | Test Exists | Status |
|-----------|------|------------|-----------|-------------------|-------------|--------|
| Free tier default | free | 0 | 0 | shared | ❌ | Missing |
| Free tier max users | free | 10 | 0 | shared | ❌ | Missing |
| Starter tier default | starter | 10 | 0 | shared | ✅ | Covered |
| Starter tier max users | starter | 100 | 0 | shared | ✅ | Covered |
| Professional tier small | professional | 100 | 0 | shared | ✅ | Covered |
| Professional tier boundary (500) | professional | 500 | 0 | shared | ❌ | Missing |
| Professional tier boundary (501) | professional | 501 | 0 | dedicated | ❌ | Missing |
| Professional tier large | professional | 600 | 0 | dedicated | ✅ | Covered |
| Professional tier 1 org | professional | 0 | 1 | shared | ❌ | Missing |
| Professional tier 2 orgs | professional | 0 | 2 | dedicated | ❌ | Missing |
| Enterprise tier | enterprise | 100 | 0 | dedicated | ✅ | Covered |
| Enterprise tier large | enterprise | 1000 | 0 | dedicated | ❌ | Missing |
| Compliance override (starter) | starter | 10 | 0 | dedicated* | ❌ | Missing |
| Compliance override (professional) | professional | 100 | 0 | dedicated* | ❌ | Missing |
| Organization realm | N/A | N/A | N/A | dedicated | ❌ | Missing |

*Compliance requirement forces dedicated realm regardless of tier

---

## Recommendations

### Priority 1: Critical Missing Tests (Add Immediately)

1. **Professional Tier Boundary Tests**
   - Test exactly 500 users (should be shared)
   - Test exactly 501 users (should be dedicated)
   - Test 1 org (should be shared)
   - Test 2 orgs (should be dedicated)

2. **Compliance Requirement Tests**
   - Test that `compliance_required=True` forces dedicated realm for all tiers

3. **Organization Realm Tests**
   - Test that organizations always get dedicated realms

### Priority 2: Important Missing Tests (Add Soon)

4. **Free Tier Tests**
   - Complete coverage for free tier

5. **Integration Tests**
   - Actual realm creation tests (not just strategy determination)
   - Auto-upgrade scenarios

6. **Edge Cases**
   - Invalid inputs, boundary conditions, error handling

### Priority 3: Nice to Have (Add When Time Permits)

7. **Additional RealmManager Tests**
   - Idempotent realm creation
   - Client and role creation verification
   - Existing dedicated realm handling

---

## Test Implementation Suggestions

### Example Test Structure

```python
class TestPricingServiceRealmStrategy:
    """Comprehensive tests for realm strategy decisions."""
    
    def test_get_realm_strategy_free(self):
        """Test free tier always uses shared realm."""
        assert PricingService.get_realm_strategy("free", 0, 0) == "shared"
        assert PricingService.get_realm_strategy("free", 10, 0) == "shared"
    
    def test_get_realm_strategy_professional_boundary_500(self):
        """Test professional tier with exactly 500 users stays shared."""
        assert PricingService.get_realm_strategy("professional", 500, 0) == "shared"
    
    def test_get_realm_strategy_professional_boundary_501(self):
        """Test professional tier with 501 users upgrades to dedicated."""
        assert PricingService.get_realm_strategy("professional", 501, 0) == "dedicated"
    
    def test_get_realm_strategy_professional_1_org(self):
        """Test professional tier with 1 org stays shared."""
        assert PricingService.get_realm_strategy("professional", 0, 1) == "shared"
    
    def test_get_realm_strategy_professional_2_orgs(self):
        """Test professional tier with 2 orgs upgrades to dedicated."""
        assert PricingService.get_realm_strategy("professional", 0, 2) == "dedicated"
    
    def test_requires_dedicated_realm_compliance(self):
        """Test compliance requirement forces dedicated realm."""
        assert PricingService.requires_dedicated_realm("starter", 10, 0, compliance_required=True) is True
        assert PricingService.requires_dedicated_realm("professional", 100, 0, compliance_required=True) is True
    
    def test_can_upgrade_to_dedicated(self):
        """Test upgrade capability per tier."""
        assert PricingService.can_upgrade_to_dedicated("free") is False
        assert PricingService.can_upgrade_to_dedicated("starter") is False
        assert PricingService.can_upgrade_to_dedicated("professional") is True
        assert PricingService.can_upgrade_to_dedicated("enterprise") is False
```

### Integration Test Structure

```python
@pytest.mark.integration
class TestRealmCreationIntegration:
    """Integration tests for actual realm creation."""
    
    @pytest.mark.asyncio
    async def test_create_dedicated_realm_professional_auto_upgrade(self):
        """Test automatic realm creation when professional tier exceeds 500 users."""
        # Test actual realm creation flow
        pass
    
    @pytest.mark.asyncio
    async def test_create_dedicated_realm_organization(self):
        """Test dedicated realm creation for organization."""
        # Test organization realm creation
        pass
```

---

## Conclusion

**Current Coverage:** ~40% of required test cases  
**Critical Gaps:** Professional tier boundary cases, compliance requirements, organization realms  
**Recommendation:** Implement Priority 1 tests immediately to ensure realm strategy logic works correctly for all customer scenarios.

---

## Related Files

- `backend/services/iam_agent/app/services/pricing_service.py` - Realm strategy logic
- `backend/services/iam_agent/app/services/realm_manager.py` - Realm creation and management
- `backend/tests/test_auth_api_client.py` - Existing tests
- `backend/migrations/009_realm_architecture.sql` - Database schema
- `backend/services/iam_agent/app/api/auth_custom.py` - Signup flow with realm creation

