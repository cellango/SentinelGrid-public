# Vault Production Configuration
# File storage backend for persistent secrets

ui = true

# File storage backend - data persists in volume
storage "file" {
  path = "/vault/file"
}

# HTTPS listener for production
listener "tcp" {
  address       = "0.0.0.0:8200"
  tls_cert_file = "/vault/certs/vault.crt"
  tls_key_file  = "/vault/certs/vault.key"
  tls_client_ca_file = "/vault/certs/sentinelgridca.pem"
  tls_disable   = 0  # TLS enabled
}

# API address (HTTPS)
api_addr = "https://vault:8200"

# Cluster address (HTTPS for production)
cluster_addr = "https://vault:8201"

# Log level
log_level = "info"

# Default lease TTL and max
default_lease_ttl = "24h"
max_lease_ttl = "720h"  # 30 days

# Telemetry (optional - for monitoring)
telemetry {
  disable_hostname = false
  prometheus_retention_time = "30s"
}
