# Vault Server Configuration - HTTP Only (for testing)
# This is a temporary config to test if certificate issues are causing the problem

ui = true

storage "file" {
  path = "/vault/file"
}

listener "tcp" {
  address     = "0.0.0.0:8202"
  tls_disable = 1  # Disable TLS for testing
}

# API address (HTTP)
api_addr = "http://0.0.0.0:8202"

# Cluster address (HTTP)
cluster_addr = "http://0.0.0.0:8201"

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

