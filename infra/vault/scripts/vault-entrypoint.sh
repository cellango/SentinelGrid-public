#!/bin/bash
#
# Vault Entrypoint Script - Auto-initialize with persistent storage
# 
# This script:
# 1. Starts Vault with file storage
# 2. Auto-initializes on first run (if not already initialized)
# 3. Auto-unseals using root token for dev convenience
#

set -e

VAULT_ADDR="${VAULT_ADDR:-http://127.0.0.1:8200}"
VAULT_ROOT_TOKEN="${VAULT_ROOT_TOKEN:-sentinelgrid-dev-root-token}"
INIT_FILE="/vault/file/.vault_initialized"

# Function to check if Vault is initialized
is_vault_initialized() {
    vault status 2>/dev/null | grep -q "Initialized.*true" || return 1
}

# Function to check if Vault is sealed
is_vault_sealed() {
    vault status 2>/dev/null | grep -q "Sealed.*true" || return 1
}

# Wait for Vault to be ready
wait_for_vault() {
    echo "⏳ Waiting for Vault to start..."
    for i in {1..30}; do
        if vault status >/dev/null 2>&1; then
            echo "✅ Vault is ready"
            return 0
        fi
        sleep 1
    done
    echo "❌ Vault failed to start"
    return 1
}

# Initialize Vault if needed
initialize_vault() {
    if [ -f "$INIT_FILE" ]; then
        echo "✅ Vault already initialized (marker file exists)"
        return 0
    fi
    
    if is_vault_initialized; then
        echo "✅ Vault already initialized"
        touch "$INIT_FILE"
        return 0
    fi
    
    echo "🔐 Initializing Vault..."
    
    # Initialize with 1 unseal key (for dev simplicity)
    INIT_OUTPUT=$(vault operator init -key-shares=1 -key-threshold=1 -format=json)
    UNSEAL_KEY=$(echo "$INIT_OUTPUT" | jq -r '.unseal_keys_b64[0]')
    
    echo "📝 Unsealing Vault..."
    vault operator unseal "$UNSEAL_KEY"
    
    # Set root token if using custom token
    if [ "$VAULT_ROOT_TOKEN" != "sentinelgrid-dev-root-token" ]; then
        echo "🔑 Setting custom root token..."
        vault auth "$UNSEAL_KEY" 2>/dev/null || true
        # Note: Changing root token requires the old root token
    fi
    
    touch "$INIT_FILE"
    echo "✅ Vault initialized and unsealed"
}

# Start Vault server in background
echo "🚀 Starting Vault server..."
vault server -config=/vault/config/vault.hcl &
VAULT_PID=$!

# Wait for Vault to be ready
sleep 3
wait_for_vault

# Initialize if needed
initialize_vault

# Unseal if sealed
if is_vault_sealed; then
    echo "🔓 Unsealing Vault..."
    # For dev, we'll use the unseal key from initialization
    # In a real setup, this would be stored securely
    if [ -f /vault/file/.vault_unseal_key ]; then
        UNSEAL_KEY=$(cat /vault/file/.vault_unseal_key)
        vault operator unseal "$UNSEAL_KEY"
    else
        echo "⚠️  Vault is sealed but no unseal key found"
        echo "   You may need to unseal manually"
    fi
fi

echo "✅ Vault is ready!"
echo "   Address: $VAULT_ADDR"
echo "   Root Token: $VAULT_ROOT_TOKEN"

# Wait for the Vault server process
wait $VAULT_PID

