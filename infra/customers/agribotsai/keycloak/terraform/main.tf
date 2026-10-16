terraform {
  required_version = ">= 1.5.0"
  
  required_providers {
    keycloak = {
      source  = "mrparkers/keycloak"
      version = "~> 4.3.0"
    }
  }
  
  # Backend configuration (for production, use remote state)
  # backend "s3" {
  #   bucket = "sentinelgrid-terraform-state"
  #   key    = "customers/agribotsai/keycloak/terraform.tfstate"
  #   region = "us-east-1"
  # }
}

provider "keycloak" {
  client_id                = var.keycloak_client_id
  client_secret            = var.keycloak_client_secret != "" ? var.keycloak_client_secret : null
  url                      = var.keycloak_url
  username                 = var.keycloak_username
  password                 = var.keycloak_password
  tls_insecure_skip_verify = var.keycloak_tls_insecure
  # For dev mode, use username/password authentication
  base_path                = ""
}

