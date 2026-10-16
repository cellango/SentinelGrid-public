# Keycloak Service Account Migration Plan

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


## Current State
- IAM Agent uses default `admin` user (username/password authentication)
- `sentinelgrid-iam-agent` client exists with service accounts enabled but not used

## Best Practice: Service Account Authentication

### Why Service Accounts?
1. **Security**: No user account to manage, no password expiration
2. **Automation**: Designed for service-to-service authentication
3. **Rotation**: Easy to rotate via client secret
4. **Least Privilege**: Can grant only necessary permissions
5. **Auditability**: Clear separation between human and service accounts

### Migration Steps

#### 1. Configure Service Account in Keycloak

```bash
# Access Keycloak Admin Console
# Navigate to: Clients → sentinelgrid-iam-agent → Service Account Roles

# Assign realm roles to service account:
# - realm-management → manage-users
# - realm-management → manage-clients  
# - realm-management → view-users
# - realm-management → view-clients
# - realm-management → manage-realm
```

#### 2. Get Client Secret

```bash
# From Keycloak Admin Console:
# Clients → sentinelgrid-iam-agent → Credentials → Copy Secret

# Or via kcadm:
docker-compose exec keycloak /opt/keycloak/bin/kcadm.sh \
  get clients -r sentinelgrid --fields id,clientId \
  | grep sentinelgrid-iam-agent

# Get client secret:
docker-compose exec keycloak /opt/keycloak/bin/kcadm.sh \
  get clients/{CLIENT_ID}/client-secret -r sentinelgrid
```

#### 3. Update IAM Agent Configuration

Update `backend/services/iam_agent/app/services/keycloak_client.py`:

```python
# Replace username/password auth with service account
self.admin = KeycloakAdmin(
    server_url=self.server_url,
    client_id=settings.KEYCLOAK_CLIENT_ID,
    client_secret_key=settings.KEYCLOAK_CLIENT_SECRET,
    realm_name=self.realm,
    verify=True
)
```

#### 4. Update Environment Variables

Remove:
- `KEYCLOAK_ADMIN_USER`
- `KEYCLOAK_ADMIN_PASSWORD`

Ensure:
- `KEYCLOAK_CLIENT_ID=sentinelgrid-iam-agent`
- `KEYCLOAK_CLIENT_SECRET=<secret-from-step-2>`

### Testing

After migration, verify:
1. IAM Agent can connect to Keycloak
2. Signup endpoint works
3. User creation works
4. Role assignment works

## Temporary Fix (Current)

For immediate unblocking, enable the admin account:

```bash
docker-compose exec keycloak /opt/keycloak/bin/kcadm.sh \
  update users/{ADMIN_USER_ID} -r master -s enabled=true
```

But plan to migrate to service account authentication soon.

