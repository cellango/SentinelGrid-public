terraform {
  required_version = ">= 1.5.0"
  
  required_providers {
    keycloak = {
      source  = "mrparkers/keycloak"
      version = "~> 4.3.0"
    }
  }
}

# Provider configuration will be set via variables in customer-specific configs
# This file defines the provider requirements only

