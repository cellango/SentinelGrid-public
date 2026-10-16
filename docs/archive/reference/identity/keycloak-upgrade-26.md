# Keycloak Upgrade to v26.0.6

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Date:** 2025-11-28  
**Status:** ✅ Completed

---

## Why Upgrade?

- ✅ **Fixes Issue #28220** - Attribute persistence bug fixed in v26.0.6+
- ✅ **Security patches** - Latest security fixes included
- ✅ **Production recommended** - Community recommends v26.0.6+ for production
- ✅ **No workaround needed** - Fixes root cause

---

## Upgrade Details

### Version Change
- **From:** Keycloak v25.0
- **To:** Keycloak v26.0.6
- **Image:** `quay.io/keycloak/keycloak:26.0.6`

### Changes Made
- Updated `docker-compose.dev.yml`:
  ```yaml
  keycloak:
    image: quay.io/keycloak/keycloak:26.0.6
  ```

---

## Testing Results

### Attribute Persistence
- ✅ Attributes now persist correctly
- ✅ `kcadm.sh update` works as expected
- ✅ Attributes appear in JWT tokens

### Test Results
- ✅ Attribute persistence test: **PASSING**
- ✅ Token generation with tenant_id: **PASSING**
- ✅ IAM Agent validation: **PASSING**

---

## Migration Notes

### No Breaking Changes for Our Use Case
- Same Admin API
- Same kcadm.sh commands
- Same configuration format
- Compatible with existing setup

### Verification Checklist
- [x] Keycloak starts successfully
- [x] Admin console accessible
- [x] Realm configuration intact
- [x] Users accessible
- [x] Attribute persistence working
- [x] Token generation working
- [x] Protocol mappers working

---

## Next Steps

1. ✅ Continue with E2E tests
2. ✅ Verify all functionality works
3. ✅ Update production deployment plan
4. ✅ Remove workaround documentation (no longer needed)

---

**Related:**
- `KEYCLOAK_ISSUE_ANALYSIS.md` - Issue analysis
- `KEYCLOAK_STRATEGY.md` - Strategy documentation

