# Keycloak User Profile Setup Guide

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Quick Reference Guide for Setting Up User Profile in Keycloak 26.x**

---

## Quick Setup

### For New Realm (Automated)
```bash
# Run the setup script - includes User Profile component creation
./infra/shared/scripts/setup-agribotsai-kcadm.sh
```

### For Existing Realm (Manual)
```bash
# Create User Profile component
python3 scripts/create-user-profile-component.py {realm-name}

# Create protocol mapper (if not exists)
# See setup-agribotsai-kcadm.sh for mapper creation commands
```

---

## What User Profile Component Does

1. **Enables Unmanaged Attributes:**
   - Allows setting any custom attribute (e.g., `tenant_id`)
   - No need to pre-define attributes in User Profile

2. **Configuration:**
   - `unmanagedAttributePolicy: "ENABLED"` - Key setting
   - Includes default attributes (username, email) - Required by Keycloak

---

## Verification Steps

### 1. Check Component Exists
```bash
docker exec {container} /opt/keycloak/bin/kcadm.sh get components -r {realm} | grep user-profile
```

### 2. Verify Attribute Persists
```bash
# Set attribute
docker exec {container} /opt/keycloak/bin/kcadm.sh update users/{user-id} -r {realm} \
  -s 'attributes.tenant_id=["value"]'

# Verify (use full representation, not --fields filter)
docker exec {container} /opt/keycloak/bin/kcadm.sh get users/{user-id} -r {realm} | grep tenant_id
```

### 3. Verify Token Claim
```bash
# Generate token and decode
# Should contain tenant_id claim
```

---

## Troubleshooting

### Component Creation Fails
- **Error:** "The attribute username can not be removed"
  - **Fix:** Ensure default attributes (username, email) are included in config

### Attributes Not Persisting
- **Check:** Component exists and `unmanagedAttributePolicy` is `ENABLED`
- **Verify:** Use full user representation, not `--fields attributes` filter

### Token Missing Claim
- **Check:** Protocol mapper exists and is configured correctly
- **Verify:** Attribute exists in user (full representation)
- **Regenerate:** Generate new token after setting attribute

---

**Related:**
- `USER_PROFILE_SOLUTION_COMPLETE.md` - Complete solution documentation

