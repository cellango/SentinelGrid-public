#!/bin/bash
# Simple Vault persistence test

set -e

VAULT_ADDR="http://localhost:8210"
COMPOSE_FILE="docker-compose.dev.yml"

echo "🧪 Simple Vault Persistence Test"
echo ""

# Get tokens from container
UNSEAL_KEY=$(docker exec vault cat /vault/file/.vault_unseal_key 2>/dev/null || echo "")
ROOT_TOKEN=$(docker exec vault cat /vault/file/.vault_root_token 2>/dev/null || echo "")

if [ -z "$UNSEAL_KEY" ] || [ -z "$ROOT_TOKEN" ]; then
    echo "⚠️  Vault not initialized. Please run: ./backend/scripts/init_vault_prod.sh"
    exit 1
fi

# Unseal
echo "🔓 Unsealing Vault..."
docker exec vault sh -c "export VAULT_ADDR=http://127.0.0.1:8200 && vault operator unseal $UNSEAL_KEY" >/dev/null 2>&1

# Store test secret
TEST_VALUE="test-$(date +%s)"
echo "💾 Storing test secret: $TEST_VALUE"
docker exec -e VAULT_ADDR=http://127.0.0.1:8200 -e VAULT_TOKEN="$ROOT_TOKEN" vault vault kv put sentinelgrid/test/persistence value="$TEST_VALUE" >/dev/null 2>&1

# Restart
echo "🔄 Restarting container..."
docker-compose -f "$COMPOSE_FILE" restart vault >/dev/null 2>&1
sleep 8

# Unseal again
echo "🔓 Unsealing after restart..."
docker exec vault sh -c "export VAULT_ADDR=http://127.0.0.1:8200 && vault operator unseal $UNSEAL_KEY" >/dev/null 2>&1
sleep 2

# Verify
RETRIEVED=$(docker exec -e VAULT_ADDR=http://127.0.0.1:8200 -e VAULT_TOKEN="$ROOT_TOKEN" vault vault kv get -format=json sentinelgrid/test/persistence 2>/dev/null | grep -o '"value":"[^"]*' | cut -d'"' -f4 || echo "")

if [ "$TEST_VALUE" = "$RETRIEVED" ]; then
    echo "✅✅✅ SUCCESS! Secret persisted: $RETRIEVED"
    exit 0
else
    echo "❌ FAILED! Expected: $TEST_VALUE, Got: $RETRIEVED"
    exit 1
fi
