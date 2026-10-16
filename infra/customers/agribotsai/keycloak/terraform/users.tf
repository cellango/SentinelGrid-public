# AgribotsAI Admin User
resource "keycloak_user" "admin" {
  realm_id = keycloak_realm.agribotsai.id
  username = "admin@agribotsai.com"
  enabled  = true
  
  email      = "admin@agribotsai.com"
  first_name = "Admin"
  last_name  = "User"
  
  # Set tenant_id attribute (must be a map of string to string)
  attributes = {
    tenant_id = "agribotsai-tenant-uuid" # This should match tenant UUID in database
  }
  
  initial_password {
    value     = "ChangeMe123!" # TEMPORARY - user must change on first login
    temporary = true
  }
}

# Assign TENANT_ADMIN role to admin user
resource "keycloak_user_roles" "admin_roles" {
  realm_id = keycloak_realm.agribotsai.id
  user_id  = keycloak_user.admin.id
  
  role_ids = [
    keycloak_role.tenant_admin.id
  ]
}

# Test User - SOC Analyst
resource "keycloak_user" "soc_analyst" {
  realm_id = keycloak_realm.agribotsai.id
  username = "analyst@agribotsai.com"
  enabled  = true
  
  email      = "analyst@agribotsai.com"
  first_name = "SOC"
  last_name  = "Analyst"
  
  attributes = {
    tenant_id = "agribotsai-tenant-uuid"
  }
  
  initial_password {
    value     = "TestAnalyst123!"
    temporary = true
  }
}

resource "keycloak_user_roles" "soc_analyst_roles" {
  realm_id = keycloak_realm.agribotsai.id
  user_id  = keycloak_user.soc_analyst.id
  
  role_ids = [
    keycloak_role.soc_analyst.id
  ]
}

# Test User - View Only
resource "keycloak_user" "viewer" {
  realm_id = keycloak_realm.agribotsai.id
  username = "viewer@agribotsai.com"
  enabled  = true
  
  email      = "viewer@agribotsai.com"
  first_name = "View"
  last_name  = "Only"
  
  attributes = {
    tenant_id = "agribotsai-tenant-uuid"
  }
  
  initial_password {
    value     = "TestViewer123!"
    temporary = true
  }
}

resource "keycloak_user_roles" "viewer_roles" {
  realm_id = keycloak_realm.agribotsai.id
  user_id  = keycloak_user.viewer.id
  
  role_ids = [
    keycloak_role.view_only.id
  ]
}

