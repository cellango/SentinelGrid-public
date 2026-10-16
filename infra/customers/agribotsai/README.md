# AgribotsAI Configuration

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../../../RELEASE_SCOPE.md) first.


> **Synthetic local example:** the owner confirmed this material does not describe
> real customers or engagements. Historical launch and live-run wording does not
> establish production use or qualify the public source preview.

Configuration for AgribotsAI - SentinelGrid's first customer.

## Structure

```
agribotsai/
├── keycloak/
│   ├── terraform/        # Terraform IaC configuration
│   └── README.md         # Keycloak-specific documentation
└── README.md             # This file
```

## Onboarding Status

- [x] Configuration structure created
- [ ] Terraform configuration applied
- [ ] Keycloak realm created
- [ ] Initial users created
- [ ] Authentication tested
- [ ] Integration verified

## Customer Information

- **Name:** AgribotsAI
- **Realm:** `agribotsai`
- **Tenant ID:** `agribotsai-tenant-uuid` (update when tenant created in DB)

## Next Steps

1. Apply Terraform configuration
2. Create tenant in SentinelGrid database
3. Update tenant_id in user attributes
4. Test authentication flow
5. Verify multi-tenant isolation

