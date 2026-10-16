# Vault Server Configuration - Development with Persistent Storage
# Uses file storage backend for persistence, but HTTP (no TLS) for dev simplicity

ui = true

# File storage backend - data persists in volume
storage "file" {
  path = "/vault/file"
}

# HTTP listener (no TLS for dev simplicity)
listener "tcp" {
  address     = "0.0.0.0:8200"
  tls_disable = 1  # Disable TLS for dev
}

# API address (HTTP)
api_addr = "http://0.0.0.0:8200"

# Log level
log_level = "info"

# Default lease TTL and max
default_lease_ttl = "24h"
max_lease_ttl = "720h"  # 30 days

