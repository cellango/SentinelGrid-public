# Platform Admin Policy
# Full access to SentinelGrid internal secrets
# Used by platform administrators

# Full access to SentinelGrid internal secrets
path "sentinelgrid/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

# Read access to all customer/org/tenant metadata (for support)
path "customers/+/metadata" {
  capabilities = ["read", "list"]
}

path "organizations/+/metadata" {
  capabilities = ["read", "list"]
}

path "tenants/+/metadata" {
  capabilities = ["read", "list"]
}

# System administration
path "sys/policy/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "sys/mounts/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "auth/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

# Token management
path "auth/token/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

# Audit access
path "sys/audit" {
  capabilities = ["read", "list"]
}

path "sys/audit-hash" {
  capabilities = ["create", "update"]
}

