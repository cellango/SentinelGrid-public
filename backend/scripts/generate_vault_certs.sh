#!/bin/bash
#
# Generate Self-Signed Certificates for Vault (Development)
#
# Creates self-signed certificates for Vault TLS in development.
# For production, use proper CA-signed certificates.
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CERTS_DIR="$PROJECT_ROOT/infra/vault/certs"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}Generating self-signed certificates for Vault...${NC}"
echo ""

# Create certs directory
mkdir -p "$CERTS_DIR"

# Generate private key
echo -e "${YELLOW}[1/3] Generating private key...${NC}"
openssl genrsa -out "$CERTS_DIR/vault.key" 2048
echo -e "${GREEN}✅ Private key generated${NC}"

# Generate certificate signing request
echo -e "${YELLOW}[2/3] Generating certificate signing request...${NC}"
openssl req -new -key "$CERTS_DIR/vault.key" -out "$CERTS_DIR/vault.csr" \
    -subj "/C=US/ST=CA/L=San Francisco/O=SentinelGrid/OU=Dev/CN=localhost" \
    -addext "subjectAltName=DNS:localhost,DNS:vault,DNS:*.localhost,IP:127.0.0.1,IP:0.0.0.0"
echo -e "${GREEN}✅ CSR generated${NC}"

# Generate self-signed certificate (valid for 10 years)
echo -e "${YELLOW}[3/3] Generating self-signed certificate...${NC}"
openssl x509 -req -days 3650 -in "$CERTS_DIR/vault.csr" -signkey "$CERTS_DIR/vault.key" \
    -out "$CERTS_DIR/vault.crt" \
    -extensions v3_req -extfile <(
        echo "[v3_req]"
        echo "subjectAltName=DNS:localhost,DNS:vault,DNS:*.localhost,IP:127.0.0.1,IP:0.0.0.0"
    )
echo -e "${GREEN}✅ Certificate generated${NC}"

# Set permissions
chmod 600 "$CERTS_DIR/vault.key"
chmod 644 "$CERTS_DIR/vault.crt"

# Clean up CSR
rm -f "$CERTS_DIR/vault.csr"

echo ""
echo -e "${GREEN}✅ Certificates generated successfully!${NC}"
echo ""
echo -e "${BLUE}Certificate files:${NC}"
echo -e "  ${YELLOW}Private Key:${NC}   $CERTS_DIR/vault.key"
echo -e "  ${YELLOW}Certificate:${NC}   $CERTS_DIR/vault.crt"
echo ""
echo -e "${BLUE}Certificate Details:${NC}"
openssl x509 -in "$CERTS_DIR/vault.crt" -text -noout | grep -E "Subject:|Issuer:|Not Before|Not After" | head -4
echo ""
echo -e "${YELLOW}⚠️  Note: These are self-signed certificates for development only.${NC}"
echo -e "${YELLOW}   For production, use proper CA-signed certificates.${NC}"
echo ""

