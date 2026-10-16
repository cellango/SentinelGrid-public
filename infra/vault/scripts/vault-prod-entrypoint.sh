#!/bin/sh
#
# Vault Production Entrypoint Script
# 
# This script:
# 1. Starts Vault with file storage (production mode)
# 2. Auto-initializes on first run (if not already initialized)
# 3. Auto-unseals using stored unseal key
# 4. Persists initialization data in the file storage volume
#

set -e

VAULT_ADDR="${VAULT_ADDR:-https://127.0.0.1:8200}"
VAULT_SKIP_VERIFY="${VAULT_SKIP_VERIFY:-true}"  # Skip TLS verification for self-signed certs
export VAULT_ADDR
export VAULT_SKIP_VERIFY

VAULT_ROOT_TOKEN="${VAULT_ROOT_TOKEN:-}"
UNSEAL_KEY_FILE="/vault/file/.vault_unseal_key"
ROOT_TOKEN_FILE="/vault/file/.vault_root_token"
INIT_FILE="/vault/file/.vault_initialized"
VAULT_CONFIG="/vault/config/vault.hcl"

if [ "$VAULT_ROOT_TOKEN" = "sentinelgrid-prod-root-token-change-me" ]; then
    echo "❌ VAULT_ROOT_TOKEN is using a retired placeholder value"
    exit 1
fi

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
    echo "⏳ Waiting for Vault server to start..."
    max_attempts=30
    attempt=0
    
    # Ensure environment variables are set for HTTPS
    export VAULT_ADDR
    export VAULT_SKIP_VERIFY
    
    while [ $attempt -lt $max_attempts ]; do
        # Check if port is listening using nc (netcat)
        if command -v nc >/dev/null 2>&1; then
            if nc -z 127.0.0.1 8200 2>/dev/null; then
                # Port is open, try vault status with HTTPS
                STATUS_OUTPUT=$(vault status 2>&1)
                STATUS_EXIT=$?
                # Vault returns exit code 2 when sealed; treat that as "responding" so we can unseal next
                if [ $STATUS_EXIT -eq 0 ] || [ $STATUS_EXIT -eq 2 ]; then
                    echo "✅ Vault server is responding (exit=${STATUS_EXIT})"
                    return 0
                fi
            fi
        else
            # Fallback: just try vault status (will fail gracefully if not ready)
            STATUS_OUTPUT=$(vault status 2>&1)
            STATUS_EXIT=$?
            if [ $STATUS_EXIT -eq 0 ] || [ $STATUS_EXIT -eq 2 ]; then
                echo "✅ Vault server is responding (exit=${STATUS_EXIT})"
                return 0
            fi
        fi
        attempt=$((attempt + 1))
        if [ $((attempt % 5)) -eq 0 ]; then
            echo "   Still waiting... (${attempt}/${max_attempts})"
        fi
        sleep 1
    done
    
    echo "❌ Vault server failed to start or respond"
    return 1
}

# Initialize Vault if needed
initialize_vault() {
    # Check if already initialized by Vault itself
    if is_vault_initialized; then
        echo "✅ Vault is already initialized"
        # Ensure marker file exists
        touch "$INIT_FILE"
        
        # Restore unseal key and root token if they exist
        if [ -f "$UNSEAL_KEY_FILE" ]; then
            echo "📋 Found stored unseal key"
        fi
        if [ -f "$ROOT_TOKEN_FILE" ]; then
            echo "📋 Found stored root token"
            # Use stored token if available
            export VAULT_TOKEN=$(cat "$ROOT_TOKEN_FILE")
        fi
        return 0
    fi
    
    # Check marker file (may exist even if Vault reset)
    if [ -f "$INIT_FILE" ]; then
        echo "⚠️  Marker file exists but Vault not initialized"
        echo "   This may indicate Vault data was reset"
        rm -f "$INIT_FILE"
    fi
    
    echo "🔐 Initializing Vault for the first time..."
    
    # Initialize with 1 unseal key and 1 threshold (for simplicity)
    # In production, you'd use 5 keys with 3 threshold
    # Ensure VAULT_ADDR and VAULT_SKIP_VERIFY are set for HTTPS
    export VAULT_ADDR
    export VAULT_SKIP_VERIFY
    INIT_OUTPUT=$(vault operator init -key-shares=1 -key-threshold=1 -format=json 2>&1)
    INIT_EXIT_CODE=$?
    
    if [ $INIT_EXIT_CODE -ne 0 ]; then
        echo "❌ Failed to initialize Vault"
        echo "$INIT_OUTPUT"
        return 1
    fi
    
    # Extract unseal key and root token from JSON
    # Since jq is not available in Vault container, use grep/sed combination
    # JSON format: {"unseal_keys_b64":["BASE64KEY"],"root_token":"TOKEN"}
    
    # Extract unseal key - look for the pattern "unseal_keys_b64":["KEY"]
    # The key is between the quotes after the opening bracket
    UNSEAL_KEY=$(echo "$INIT_OUTPUT" | grep -o '"unseal_keys_b64"[[:space:]]*:[[:space:]]*\[[[:space:]]*"[^"]*"' | sed 's/.*"\([^"]*\)"$/\1/')
    
    # Extract root token - look for "root_token":"TOKEN"
    ROOT_TOKEN=$(echo "$INIT_OUTPUT" | grep -o '"root_token"[[:space:]]*:[[:space:]]*"[^"]*"' | sed 's/.*"\([^"]*\)"$/\1/')
    
    # Alternative method if the above doesn't work (for multiline JSON)
    if [ -z "$UNSEAL_KEY" ] || [ "$UNSEAL_KEY" = "null" ]; then
        # Read JSON line by line, find unseal_keys_b64 array, get next line which has the key
        UNSEAL_KEY=$(echo "$INIT_OUTPUT" | awk '/unseal_keys_b64/ {found=1; next} found && /"/ {gsub(/[^A-Za-z0-9+\/=]/, "", $0); print; exit}')
    fi
    
    if [ -z "$ROOT_TOKEN" ] || [ "$ROOT_TOKEN" = "null" ]; then
        # Try extracting token that starts with hvs. (Vault token format)
        ROOT_TOKEN=$(echo "$INIT_OUTPUT" | grep -o 'hvs\.[A-Za-z0-9]\{20,\}' | head -1)
    fi
    
    # Final validation
    if [ -z "$UNSEAL_KEY" ] || [ "$UNSEAL_KEY" = "null" ] || [ ${#UNSEAL_KEY} -lt 20 ]; then
        echo "❌ Failed to extract unseal key"
        echo "Debug: Init output snippet (first 300 chars):"
        echo "$INIT_OUTPUT" | head -c 300
        echo ""
        echo "Full output saved to /tmp/vault_init_debug.txt"
        echo "$INIT_OUTPUT" > /tmp/vault_init_debug.txt
        return 1
    fi
    
    if [ -z "$ROOT_TOKEN" ] || [ "$ROOT_TOKEN" = "null" ] || [ ${#ROOT_TOKEN} -lt 20 ]; then
        echo "❌ Failed to extract root token"
        return 1
    fi
    
    echo "✅ Extracted unseal key (${#UNSEAL_KEY} chars) and root token (${#ROOT_TOKEN} chars)"
    
    # Store unseal key and root token securely in the volume
    echo "$UNSEAL_KEY" > "$UNSEAL_KEY_FILE"
    chmod 600 "$UNSEAL_KEY_FILE"
    echo "$ROOT_TOKEN" > "$ROOT_TOKEN_FILE"
    chmod 600 "$ROOT_TOKEN_FILE"
    
    echo "💾 Stored unseal key and root token in persistent storage"
    
    # Unseal Vault
    echo "🔓 Unsealing Vault..."
    vault operator unseal "$UNSEAL_KEY"
    
    # Set token for subsequent operations
    export VAULT_TOKEN="$ROOT_TOKEN"
    
    # If custom root token is provided and different, we'd need to use the original token
    # to change it, which is complex. For now, just use what Vault generated.
    if [ -n "$VAULT_ROOT_TOKEN" ] && [ "$VAULT_ROOT_TOKEN" != "$ROOT_TOKEN" ]; then
        echo "⚠️  Note: Vault generated root token: $ROOT_TOKEN"
        echo "   To use custom token, set VAULT_ROOT_TOKEN to this value or change it via Vault API"
    fi
    
    # Create marker file
    touch "$INIT_FILE"
    echo "✅ Vault initialized and unsealed"
}

# Unseal Vault if sealed
unseal_vault() {
    if ! is_vault_sealed; then
        echo "✅ Vault is already unsealed"
        return 0
    fi
    
    echo "🔓 Vault is sealed, unsealing..."
    
    if [ ! -f "$UNSEAL_KEY_FILE" ]; then
        echo "❌ Unseal key file not found: $UNSEAL_KEY_FILE"
        echo "   Cannot unseal Vault automatically"
        echo "   You will need to unseal manually"
        return 1
    fi
    
    UNSEAL_KEY=$(cat "$UNSEAL_KEY_FILE")
    export VAULT_ADDR
    export VAULT_SKIP_VERIFY
    vault operator unseal "$UNSEAL_KEY"
    
    # Set token if available
    if [ -f "$ROOT_TOKEN_FILE" ]; then
        export VAULT_TOKEN=$(cat "$ROOT_TOKEN_FILE")
    fi
    
    echo "✅ Vault unsealed"
}

# Start Vault server in background
echo "🚀 Starting Vault server in production mode..."
echo "   Config: $VAULT_CONFIG"
echo "   Storage: /vault/file (persistent)"
echo "   Address: $VAULT_ADDR"
echo "   TLS: Enabled (skip verify: $VAULT_SKIP_VERIFY)"

vault server -config="$VAULT_CONFIG" &
VAULT_PID=$!

# Wait for Vault to be ready
sleep 3
wait_for_vault || {
    echo "❌ Vault failed to start"
    kill $VAULT_PID 2>/dev/null || true
    exit 1
}

# Ensure environment is set for all vault commands
export VAULT_ADDR
export VAULT_SKIP_VERIFY

# Initialize if needed
initialize_vault || {
    echo "❌ Failed to initialize Vault"
    kill $VAULT_PID 2>/dev/null || true
    exit 1
}

# Unseal if sealed
unseal_vault || {
    echo "⚠️  Warning: Vault may not be unsealed"
}

# Verify Vault is ready (ensure env vars are set)
export VAULT_ADDR
export VAULT_SKIP_VERIFY
if is_vault_initialized && ! is_vault_sealed; then
    echo ""
    echo "✅ Vault is ready and operational!"
    echo "   Address: $VAULT_ADDR"
    if [ -f "$ROOT_TOKEN_FILE" ]; then
        echo "   Root Token: $(cat $ROOT_TOKEN_FILE)"
    fi
    echo "   Storage: Persistent (survives container restarts)"
    echo ""
else
    echo "⚠️  Warning: Vault may not be fully operational"
    vault status
fi

# Wait for the Vault server process
wait $VAULT_PID
