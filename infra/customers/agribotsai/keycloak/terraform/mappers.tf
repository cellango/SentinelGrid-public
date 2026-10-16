# Protocol Mapper: tenant_id for Web Client
resource "keycloak_openid_user_attribute_protocol_mapper" "tenant_id_web" {
  realm_id            = keycloak_realm.agribotsai.id
  client_id           = keycloak_openid_client.agribotsai_web.id
  name                = "tenant-id-mapper"
  user_attribute      = "tenant_id"
  claim_name          = "tenant_id"
  claim_value_type    = "String"
  add_to_id_token     = true
  add_to_access_token = true
  add_to_userinfo     = true
}

# Protocol Mapper: tenant_id for API Client
resource "keycloak_openid_user_attribute_protocol_mapper" "tenant_id_api" {
  realm_id            = keycloak_realm.agribotsai.id
  client_id           = keycloak_openid_client.agribotsai_api.id
  name                = "tenant-id-mapper"
  user_attribute      = "tenant_id"
  claim_name          = "tenant_id"
  claim_value_type    = "String"
  add_to_id_token     = true
  add_to_access_token = true
  add_to_userinfo     = true
}

# Protocol Mapper: email for Web Client
resource "keycloak_openid_user_property_protocol_mapper" "email_web" {
  realm_id            = keycloak_realm.agribotsai.id
  client_id           = keycloak_openid_client.agribotsai_web.id
  name                = "email"
  user_property       = "email"
  claim_name          = "email"
  claim_value_type    = "String"
  add_to_id_token     = true
  add_to_access_token = true
  add_to_userinfo     = true
}

# Protocol Mapper: email for API Client
resource "keycloak_openid_user_property_protocol_mapper" "email_api" {
  realm_id            = keycloak_realm.agribotsai.id
  client_id           = keycloak_openid_client.agribotsai_api.id
  name                = "email"
  user_property       = "email"
  claim_name          = "email"
  claim_value_type    = "String"
  add_to_id_token     = true
  add_to_access_token = true
  add_to_userinfo     = true
}

