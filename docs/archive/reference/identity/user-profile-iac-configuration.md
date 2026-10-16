# User Profile Configuration via Infrastructure as Code

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Date:** 2025-11-28  
**Status:** ✅ Implemented

---

## Summary

Configured User Profile in Keycloak 26.x using Infrastructure as Code (IaC) approach. This enables `unmanagedAttributePolicy: "ENABLED"`, allowing custom attributes like `tenant_id` to be set without pre-definition.

---

## Implementation Methods

### Method 1: Realm Export JSON ✅ PRIMARY

**For realms imported via `--import-realm` flag**

Added User Profile component configuration to realm export JSON files:

#### Files Updated:
1. **`infra/keycloak/realm-export.json`** (SentinelGrid realm)
2. **`infra/customers/agribotsai/keycloak/realm-export.json`** (AgribotsAI realm)

#### Configuration Structure:
```json
{
  "components": {
    "org.keycloak.userprofile.UserProfileProvider": [
      {
        "name": "declarative-user-profile",
        "providerId": "declarative-user-profile",
        "providerType": "org.keycloak.userprofile.UserProfileProvider",
        "parentId": "{realm-name}",
        "config": {
          "kc.user.profile.config": [
            "{\"attributes\":[],\"unmanagedAttributePolicy\":\"ENABLED\"}"
          ]
        }
      }
    ]
  }
}
```

#### How It Works:
1. Keycloak starts with `--import-realm` flag
2. Realm JSON is imported from mounted volume
3. Components (including User Profile) are created automatically
4. Configuration applies to all realms defined in JSON

#### Testing:
```bash
# Restart Keycloak to import configuration
docker-compose -f docker-compose.dev.yml restart keycloak

# Verify User Profile component exists
docker-compose exec keycloak /opt/keycloak/bin/kcadm.sh \
  get components -r agribotsai | grep -i "user-profile"
```

---

### Method 2: Terraform ✅ ALTERNATIVE

**For realms managed via Terraform**

Created Terraform resource for User Profile component:

#### File Created:
**`infra/customers/agribotsai/keycloak/terraform/user-profile.tf`**

#### Terraform Resource:
```hcl
resource "keycloak_component" "user_profile" {
  realm_id     = keycloak_realm.agribotsai.realm_id
  name         = "declarative-user-profile"
  provider_id  = "declarative-user-profile"
  provider_type = "org.keycloak.userprofile.UserProfileProvider"
  parent_id    = keycloak_realm.agribotsai.realm_id

  config = {
    "kc.user.profile.config" = jsonencode({
      attributes              = []
      unmanagedAttributePolicy = "ENABLED"
    })
  }
}
```

#### How It Works:
1. Terraform manages realm via Keycloak provider
2. `keycloak_component` resource creates User Profile provider
3. Configuration is version-controlled and idempotent
4. Can be applied independently or as part of full infrastructure

#### Usage:
```bash
cd infra/customers/agribotsai/keycloak/terraform
terraform init
terraform plan
terraform apply
```

**Note:** Requires Keycloak Terraform provider authentication to be configured (see `PARKING_LOT.md` for current status).

---

## Configuration Details

### Unmanaged Attribute Policy

Setting `unmanagedAttributePolicy: "ENABLED"` allows:
- ✅ Setting any user attribute without pre-definition
- ✅ Flexibility for custom attributes (e.g., `tenant_id`)
- ✅ No need to update User Profile when adding new attributes

### Alternative: Explicit Attribute Definition

If you prefer to define attributes explicitly:

```json
{
  "attributes": [
    {
      "name": "tenant_id",
      "displayName": "Tenant ID",
      "validations": {"length": {"max": 255}},
      "permissions": {"view": ["admin", "user"], "edit": ["admin"]},
      "multivalued": false
    }
  ],
  "unmanagedAttributePolicy": "DISABLED"
}
```

**Current approach (unmanaged enabled) is simpler and more flexible.**

---

## Verification

After configuration is applied:

1. **Check User Profile Component:**
   ```bash
   docker-compose exec keycloak /opt/keycloak/bin/kcadm.sh \
     get components -r agribotsai | grep -i "user-profile"
   ```

2. **Set Attribute:**
   ```bash
   docker-compose exec keycloak /opt/keycloak/bin/kcadm.sh \
     update users/{user-id} -r agribotsai \
     -s 'attributes.tenant_id=["6306bd5e-0bf2-4622-b789-ba0d18ae8003"]'
   ```

3. **Verify Attribute Persists:**
   ```bash
   docker-compose exec keycloak /opt/keycloak/bin/kcadm.sh \
     get users/{user-id} -r agribotsai --fields attributes
   ```

4. **Verify Token Contains Claim:**
   ```bash
   # Generate token and decode JWT
   # Check for tenant_id claim
   ```

---

## For New Realms

When creating new realm configurations:

1. **Realm Export JSON:**
   - Copy component configuration from existing realm-export.json
   - Update `parentId` to match new realm name

2. **Terraform:**
   - Copy `user-profile.tf` file
   - Update `realm_id` reference to new realm resource

---

## Benefits of IaC Approach

✅ **Version Controlled** - Configuration in Git  
✅ **Reproducible** - Same config every time  
✅ **Automated** - No manual Admin Console steps  
✅ **Scalable** - Easy to add to new realms  
✅ **Documented** - Configuration is self-documenting  

---

## Related Files

- `infra/keycloak/realm-export.json` - SentinelGrid realm
- `infra/customers/agribotsai/keycloak/realm-export.json` - AgribotsAI realm
- `infra/customers/agribotsai/keycloak/terraform/user-profile.tf` - Terraform resource

---

**Related Documentation:**
- `USER_PROFILE_API_INVESTIGATION.md` - API investigation
- `KEYCLOAK_26_USER_PROFILE.md` - User Profile feature overview
- `KEYCLOAK_IAC_PLAN.md` - Overall IaC strategy

