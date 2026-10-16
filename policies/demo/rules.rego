# Sample demo policies for SentinelGrid OPA
package sentinelgrid.authz

import future.keywords.if

default allow = false

# Normalize roles to lowercase for matching
roles := {lower(r) | r := input.user.roles[_]}

# Role helpers (cover actual Keycloak roles)
is_admin if {
  roles[_] == "admin"
}

is_admin if {
  roles[_] == "tenant_admin"
}

is_defender if {
  roles[_] == "defender"
}

is_defender if {
  roles[_] == "tenant_secops"
}

is_analyst if {
  roles[_] == "analyst"
}

is_analyst if {
  roles[_] == "tenant_analyst"
}

# Tenant guard
resource_owner_matches if {
  input.resource.owner_tenant == input.tenant_id
}

# Plan-tier guard for compliance/governance areas
plan_allows_compliance if {
  input.resource.type != "compliance"
}

plan_allows_compliance if {
  input.resource.type == "compliance"
  input.context.plan_tier == "protect_defend_comply"
}

# Admin: full access within tenant (honors plan compliance guard)
allow if {
  is_admin
  resource_owner_matches
  plan_allows_compliance
}

# Defender: manage detections/SIEM, but not destructive deletes
allow if {
  is_defender
  resource_owner_matches
  lower(input.resource.type) == "detection-rules"
  input.request.method != "DELETE"
  plan_allows_compliance
}

allow if {
  is_defender
  resource_owner_matches
  lower(input.resource.type) == "alerts"
  input.request.method != "DELETE"
  plan_allows_compliance
}

allow if {
  is_defender
  resource_owner_matches
  lower(input.resource.type) == "logs"
  input.request.method != "DELETE"
  plan_allows_compliance
}

allow if {
  is_defender
  resource_owner_matches
  lower(input.resource.type) == "source-health"
  input.request.method == "GET"
  plan_allows_compliance
}

allow if {
  is_defender
  resource_owner_matches
  lower(input.resource.type) == "stats"
  input.request.method == "GET"
  plan_allows_compliance
}

# Analyst: read-only on detections/SIEM within tenant
allow if {
  is_analyst
  resource_owner_matches
  lower(input.resource.type) == "detection-rules"
  input.request.method == "GET"
  plan_allows_compliance
}

allow if {
  is_analyst
  resource_owner_matches
  lower(input.resource.type) == "alerts"
  input.request.method == "GET"
  plan_allows_compliance
}

allow if {
  is_analyst
  resource_owner_matches
  lower(input.resource.type) == "logs"
  input.request.method == "GET"
  plan_allows_compliance
}

allow if {
  is_analyst
  resource_owner_matches
  lower(input.resource.type) == "source-health"
  input.request.method == "GET"
  plan_allows_compliance
}

allow if {
  is_analyst
  resource_owner_matches
  lower(input.resource.type) == "stats"
  input.request.method == "GET"
  plan_allows_compliance
}
