# Realm-level roles for AgribotsAI

resource "keycloak_role" "tenant_admin" {
  realm_id    = keycloak_realm.agribotsai.id
  name        = "TENANT_ADMIN"
  description = "Full control over tenant - can manage users, integrations, and settings"
}

resource "keycloak_role" "soc_manager" {
  realm_id    = keycloak_realm.agribotsai.id
  name        = "SOC_MANAGER"
  description = "Manage SOC operations - incidents, playbooks, team members"
}

resource "keycloak_role" "soc_analyst" {
  realm_id    = keycloak_realm.agribotsai.id
  name        = "SOC_ANALYST"
  description = "View and triage alerts, manage incidents, execute playbooks"
}

resource "keycloak_role" "view_only" {
  realm_id    = keycloak_realm.agribotsai.id
  name        = "VIEW_ONLY"
  description = "Read-only access - can view dashboards and reports"
}

# Role hierarchy: TENANT_ADMIN > SOC_MANAGER > SOC_ANALYST > VIEW_ONLY
# This is managed through Keycloak admin console or via composite roles
# For now, we define them separately and assign as needed

