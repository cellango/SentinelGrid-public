#!/bin/bash
#
# Export Vault Credentials for Secure Physical Storage
#
# This script extracts Vault root token and unseal keys and formats them
# for secure offline storage in a physical vault or safe.
#
# Usage: ./scripts/export_vault_credentials.sh [output-file]
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
OUTPUT_FILE="${1:-$PROJECT_ROOT/vault-credentials-secure.txt}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                                                        ║${NC}"
echo -e "${CYAN}║     ${BLUE}Vault Credentials Export for Physical Storage${CYAN}      ║${NC}"
echo -e "${CYAN}║                                                        ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if vault container is running
if ! docker ps --format '{{.Names}}' | grep -q "^vault$"; then
    echo -e "${RED}❌ Error: vault container is not running${NC}"
    echo -e "${YELLOW}   Start it with: docker-compose -f docker-compose.vault.yml up -d vault${NC}"
    exit 1
fi

# Extract credentials
echo -e "${YELLOW}[1/3] Extracting Vault credentials...${NC}"
ROOT_TOKEN=$(docker exec vault cat /vault/file/.vault_root_token 2>/dev/null || echo "")
UNSEAL_KEY=$(docker exec vault cat /vault/file/.vault_unseal_key 2>/dev/null || echo "")

if [ -z "$ROOT_TOKEN" ] || [ -z "$UNSEAL_KEY" ]; then
    echo -e "${RED}❌ Error: Could not extract credentials${NC}"
    echo -e "${YELLOW}   Make sure Vault is initialized${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Credentials extracted${NC}"

# Get additional information
VAULT_ADDR="https://localhost:8210"
TIMESTAMP=$(date -u +"%Y-%m-%d %H:%M:%S UTC")
HOSTNAME=$(hostname)
CLUSTER_ID=$(docker exec vault sh -c 'export VAULT_ADDR=https://127.0.0.1:8200 && export VAULT_SKIP_VERIFY=true && vault status 2>/dev/null | grep "Cluster ID" | awk "{print \$3}"' || echo "N/A")

# Create secure output file
echo -e "${YELLOW}[2/3] Creating secure credentials file...${NC}"

cat > "$OUTPUT_FILE" <<EOF
╔════════════════════════════════════════════════════════════════════════════╗
║                                                                            ║
║                  VAULT PRODUCTION CREDENTIALS                              ║
║                  STORE THIS IN A PHYSICAL SAFE/VAULT                       ║
║                                                                            ║
║  ⚠️  SECURITY WARNING: This file contains sensitive credentials            ║
║      Store this document in a secure physical location                     ║
║      Do not store digitally or share via unsecured channels                ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝

Export Date:     $TIMESTAMP
Vault Address:   $VAULT_ADDR
Host Machine:    $HOSTNAME
Cluster ID:      $CLUSTER_ID

────────────────────────────────────────────────────────────────────────────

ROOT TOKEN
────────────────────────────────────────────────────────────────────────────

The root token provides full administrative access to Vault.
Keep this secure and limit access to authorized personnel only.

Root Token: $ROOT_TOKEN

Usage:
  export VAULT_ADDR=$VAULT_ADDR
  export VAULT_SKIP_VERIFY=true
  export VAULT_TOKEN=$ROOT_TOKEN
  vault status

────────────────────────────────────────────────────────────────────────────

UNSEAL KEY
────────────────────────────────────────────────────────────────────────────

The unseal key is required to unseal Vault after container restarts.
Vault will be sealed on restart for security.

Unseal Key: $UNSEAL_KEY

Usage (if Vault becomes sealed):
  docker exec vault sh -c "export VAULT_ADDR=https://127.0.0.1:8200 && export VAULT_SKIP_VERIFY=true && vault operator unseal $UNSEAL_KEY"

────────────────────────────────────────────────────────────────────────────

ADDITIONAL INFORMATION
────────────────────────────────────────────────────────────────────────────

Container Name:  vault
Port:            8210 (HTTPS)
Storage:         Persistent (Docker volume: vault_prod_data)
TLS:             Enabled (self-signed certificate)

Access from host:
  export VAULT_ADDR=$VAULT_ADDR
  export VAULT_SKIP_VERIFY=true
  export VAULT_TOKEN=$ROOT_TOKEN

Access from container:
  docker exec -it vault sh
  export VAULT_ADDR=https://127.0.0.1:8200
  export VAULT_SKIP_VERIFY=true
  export VAULT_TOKEN=$ROOT_TOKEN

────────────────────────────────────────────────────────────────────────────

SECURITY NOTES
────────────────────────────────────────────────────────────────────────────

1. Store this document in a physical safe or secure location
2. Limit access to authorized personnel only
3. Consider storing root token and unseal key in separate locations
4. Rotate credentials periodically (recommended every 90 days)
5. Never commit this file to version control
6. Destroy this file after transferring to secure storage

────────────────────────────────────────────────────────────────────────────

EOF

# Set secure permissions
chmod 600 "$OUTPUT_FILE"

echo -e "${GREEN}✅ Credentials file created: $OUTPUT_FILE${NC}"

# Print to console (masked)
echo -e "${YELLOW}[3/3] Credentials Summary:${NC}"
echo ""
echo -e "  ${BLUE}Root Token:${NC} ${ROOT_TOKEN:0:20}...${ROOT_TOKEN: -8}"
echo -e "  ${BLUE}Unseal Key:${NC} ${UNSEAL_KEY:0:20}...${UNSEAL_KEY: -8}"
echo ""

echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                        ║${NC}"
echo -e "${GREEN}║          ${CYAN}✅ Credentials Exported Successfully${GREEN}                 ║${NC}"
echo -e "${GREEN}║                                                        ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}📄 Full credentials saved to:${NC} $OUTPUT_FILE"
echo ""
echo -e "${RED}⚠️  SECURITY REMINDER:${NC}"
echo -e "   1. Print this file for physical storage"
echo -e "   2. Store in a secure physical vault/safe"
echo -e "   3. Delete the digital file after printing: ${CYAN}rm $OUTPUT_FILE${NC}"
echo -e "   4. Consider splitting root token and unseal key into separate documents"
echo ""

