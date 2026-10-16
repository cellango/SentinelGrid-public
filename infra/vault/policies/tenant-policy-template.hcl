# Tenant Policy Template
# This template is used to generate tenant-specific policies
# Replace {{TENANT_ID}}, {{ORG_ID}}, {{CUSTOMER_ID}} when creating policy

# ============================================================================
# TENANT-LEVEL ACCESS (Full Control)
# ============================================================================

# KV Secrets - Full access to tenant's own secrets
path "tenants/{{TENANT_ID}}/kv/data/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "tenants/{{TENANT_ID}}/kv/metadata/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

# Transit Encryption - Tenant-specific encryption key
path "transit/encrypt/{{TENANT_ID}}" {
  capabilities = ["update"]
}

path "transit/decrypt/{{TENANT_ID}}" {
  capabilities = ["update"]
}

path "transit/rewrap/{{TENANT_ID}}" {
  capabilities = ["update"]
}

path "transit/datakey/plaintext/{{TENANT_ID}}" {
  capabilities = ["update"]
}

# Database Dynamic Credentials - Tenant-specific roles
path "database/creds/{{TENANT_ID}}-*" {
  capabilities = ["read"]
}

# PKI - Tenant-specific intermediate CA
path "pki_{{TENANT_ID}}/issue/*" {
  capabilities = ["create", "update"]
}

path "pki_{{TENANT_ID}}/sign/*" {
  capabilities = ["create", "update"]
}

path "pki_{{TENANT_ID}}/revoke" {
  capabilities = ["update"]
}

# ============================================================================
# ORGANIZATION-LEVEL ACCESS (Read-Only)
# ============================================================================

# Read access to organization secrets (if part of an org)
path "organizations/{{ORG_ID}}/kv/data/*" {
  capabilities = ["read", "list"]
}

path "organizations/{{ORG_ID}}/metadata" {
  capabilities = ["read"]
}

# ============================================================================
# CUSTOMER-LEVEL ACCESS (Read-Only)
# ============================================================================

# Read access to customer-wide secrets
path "customers/{{CUSTOMER_ID}}/kv/data/*" {
  capabilities = ["read", "list"]
}

path "customers/{{CUSTOMER_ID}}/metadata" {
  capabilities = ["read"]
}

# ============================================================================
# EXPLICIT DENIALS (Defense in Depth)
# ============================================================================

# DENY access to other tenants
path "tenants/+/kv/*" {
  capabilities = ["deny"]
}

# DENY access to other tenant's encryption keys
path "transit/encrypt/+" {
  capabilities = ["deny"]
}

path "transit/decrypt/+" {
  capabilities = ["deny"]
}

# DENY access to other tenant's database credentials
path "database/creds/*" {
  capabilities = ["deny"]
}

# DENY access to other tenant's PKI
path "pki_+/*" {
  capabilities = ["deny"]
}

# DENY access to other organizations (except own)
path "organizations/+/*" {
  capabilities = ["deny"]
}

# DENY access to other customers (except own)
path "customers/+/*" {
  capabilities = ["deny"]
}

# DENY system paths
path "sys/*" {
  capabilities = ["deny"]
}

path "auth/*" {
  capabilities = ["deny"]
}

# DENY SentinelGrid internal secrets
path "sentinelgrid/*" {
  capabilities = ["deny"]
}

