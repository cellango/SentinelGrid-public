# Keycloak 26.x User Profile Configuration

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Status:** Investigating  
**Date:** 2025-11-28

---

## Keycloak 26.x User Profile Feature

Keycloak 26.x introduced the **User Profile** feature which changes how user attributes are managed:

- **Managed Attributes** - Defined in User Profile, validated
- **Unmanaged Attributes** - Can be set freely
- **Attribute Permissions** - Read/write permissions per attribute

---

## Our Issue

User attributes (`tenant_id`) may need to be configured in **User Profile** before they can be set via API.

---

## Configuration Steps

### Via Admin Console UI

1. Log into Admin Console: http://localhost:8081/admin
2. Select realm: `agribotsai`
3. Navigate to: **Realm Settings → User Profile**
4. Check/Add `tenant_id` attribute:
   - If not present, add it as an attribute
   - Mark as "unmanaged" (or "managed" with validation)
   - Set permissions (read/write)
5. Save configuration
6. Try setting attribute via API again

### Via kcadm.sh (If API exists)

```bash
# May need to configure User Profile via API first
# Check if there's a User Profile API endpoint
```

---

## Testing After Configuration

1. Configure `tenant_id` in User Profile
2. Set attribute via kcadm.sh
3. Verify attribute persists
4. Generate token and check for `tenant_id` claim

---

## Alternative: Database Workaround

If User Profile configuration doesn't resolve the issue:

- Implement database lookup for `tenant_id`
- Unblocks development immediately
- Continue investigating Keycloak
- Remove workaround when fixed

---

**Related:**
- `KEYCLOAK_26_ATTRIBUTE_ISSUE.md` - Current issue status

