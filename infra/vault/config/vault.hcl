# Vault Server Configuration
# For production deployment (dev mode uses simpler config)

ui = true

storage "file" {
  path = "/vault/file"
}

listener "tcp" {
  address       = "0.0.0.0:8200"
  tls_cert_file = "/vault/certs/vault.crt"
  tls_key_file  = "/vault/certs/vault.key"
  tls_disable   = 0  # TLS enabled (even in dev)
}

# API address (HTTPS)
api_addr = "https://0.0.0.0:8200"

# Cluster address (HTTPS)
cluster_addr = "https://0.0.0.0:8201"

# Telemetry
telemetry {
  disable_hostname = false
  prometheus_retention_time = "30s"
}

# Log level
log_level = "info"

# Default lease TTL and max
default_lease_ttl = "24h"
max_lease_ttl = "720h"  # 30 days

