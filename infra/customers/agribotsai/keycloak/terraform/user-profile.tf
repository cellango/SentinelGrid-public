# User Profile Configuration for Keycloak 26.x
# Enables unmanaged attributes so tenant_id can be set without pre-definition
#
# This configures Keycloak 26.x User Profile to allow unmanaged attributes.
# This enables setting tenant_id and other custom attributes without pre-defining them
# in the User Profile configuration.

resource "keycloak_component" "user_profile" {
  realm_id     = keycloak_realm.agribotsai.realm_id
  name         = "declarative-user-profile"
  provider_id  = "declarative-user-profile"
  provider_type = "org.keycloak.userprofile.UserProfileProvider"
  parent_id    = keycloak_realm.agribotsai.realm_id

  config = {
    "kc.user.profile.config" = jsonencode({
      attributes              = []
      unmanagedAttributePolicy = "ENABLED"
    })
  }
}

