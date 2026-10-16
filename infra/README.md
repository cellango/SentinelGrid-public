# SentinelGrid Infrastructure as Code (IaC)

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../RELEASE_SCOPE.md) first.


This directory contains Infrastructure as Code configurations for managing SentinelGrid's multi-tenant infrastructure, starting with Keycloak.

## Structure

```
infra/
├── customers/            # Customer-specific configurations
│   ├── agribotsai/      # First customer
│   └── _template/       # Template for new customers (future)
├── shared/              # Shared infrastructure and scripts
│   ├── terraform/       # Shared Terraform providers
│   └── scripts/         # Automation scripts
└── README.md            # This file
```

## Philosophy

- **Configuration as Code** - All infrastructure defined in code
- **Git-based Version Control** - All configs versioned in Git
- **Customer Isolation** - Each customer has separate configuration
- **Automated Onboarding** - Scripts to automate customer setup

## Technology Stack

- **Terraform** - Infrastructure provisioning
- **Keycloak Provider** - Terraform provider for Keycloak
- **Git** - Version control

## Getting Started

### For a New Customer

1. Copy customer template (when available)
2. Update customer-specific variables
3. Run onboarding script
4. Verify configuration

### For Existing Customer

1. Navigate to customer directory
2. Update Terraform configuration
3. Run `terraform plan` to review
4. Run `terraform apply` to apply

## Scripts

- `shared/scripts/onboard-customer.sh` - Onboard new customer
- `shared/scripts/get-token.sh` - Get JWT token for testing
- `shared/scripts/test-auth-flow.sh` - Test end-to-end auth flow

## Security

- Never commit `terraform.tfvars` with real passwords
- Use `.gitignore` to exclude sensitive files
- Use Terraform Cloud or Vault for production secrets

## Documentation

- [Keycloak IaC Plan](../docs/archive/README.md#retired-references) - Detailed implementation plan
- Customer-specific READMEs in each customer directory

