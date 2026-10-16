# AgribotsAI Keycloak Configuration

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../../../../RELEASE_SCOPE.md) first.


> **Synthetic local example:** the owner confirmed this material does not describe
> real customers or engagements. Historical launch and live-run wording does not
> establish production use or qualify the public source preview.

This directory contains the Infrastructure as Code (IaC) configuration for AgribotsAI's Keycloak realm.

## Quick Start

### 1. Configure Variables

Copy the example variables file:
```bash
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` with your Keycloak credentials:
```hcl
keycloak_url      = "http://localhost:8081"
keycloak_password = "your-admin-password"
```

### 2. Initialize Terraform

```bash
terraform init
```

### 3. Review Changes

```bash
terraform plan
```

### 4. Apply Configuration

```bash
terraform apply
```

Or use the onboarding script:
```bash
../../../../shared/scripts/onboard-customer.sh agribotsai
```

## Configuration Details

### Realm
- **Name:** `agribotsai`
- **Display Name:** `AgribotsAI`
- **SSL Required:** External only
- **Password Policy:** 8+ chars, 1 digit, 1 lowercase, 1 uppercase

### Clients
- **agribotsai-web** - Public client for frontend
- **agribotsai-api** - Confidential client for backend
- **sentinelgrid-iam-agent** - Service account for IAM Agent

### Roles
- `TENANT_ADMIN` - Full control
- `SOC_MANAGER` - SOC operations management
- `SOC_ANALYST` - Alert triage and incident management
- `VIEW_ONLY` - Read-only access

### Users

#### Admin User
- **Username:** `admin@agribotsai.com`
- **Password:** `ChangeMe123!` (temporary, must change on first login)
- **Role:** TENANT_ADMIN
- **Tenant ID:** `agribotsai-tenant-uuid`

#### Test Users
- `analyst@agribotsai.com` - SOC_ANALYST role
- `viewer@agribotsai.com` - VIEW_ONLY role

## Testing

### Get JWT Token

```bash
../../../../shared/scripts/get-token.sh agribotsai agribotsai-web admin@agribotsai.com ChangeMe123!
```

### Test Full Auth Flow

```bash
../../../../shared/scripts/test-auth-flow.sh
```

## Outputs

After applying, get outputs with:
```bash
terraform output
```

Important outputs:
- `iam_agent_client_secret` - For IAM Agent configuration
- `token_endpoint` - Token endpoint URL

## Notes

- Initial passwords are temporary - users must change on first login
- `tenant_id` attribute must match tenant UUID in SentinelGrid database
- Update `frontend_urls` in `variables.tf` or `terraform.tfvars` for production

