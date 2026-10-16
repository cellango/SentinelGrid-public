#!/bin/bash
#
# Generate Secure Vault Root Token
#
# This script generates a cryptographically secure root token for HashiCorp Vault.
# The token is 256 bits (64 hex characters) - suitable for production use.
#
# SECURITY: Store the generated token securely. See VAULT_ROOT_TOKEN_SECURITY.md
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}╔════════════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                                                                                ║${NC}"
echo -e "${CYAN}║         ${BLUE}Generate Secure Vault Root Token${CYAN}                                    ║${NC}"
echo -e "${CYAN}║                                                                                ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Generate 256-bit random token (64 hex characters)
ROOT_TOKEN=$(openssl rand -hex 32)

echo -e "${GREEN}✅ Generated secure Vault root token${NC}"
echo ""
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}Root Token:${NC}"
echo -e "${GREEN}$ROOT_TOKEN${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo -e "${RED}🚨 CRITICAL SECURITY WARNINGS 🚨${NC}"
echo ""
echo -e "${YELLOW}This token has UNLIMITED ACCESS to ALL secrets in Vault.${NC}"
echo -e "${YELLOW}Store it with EXTREME CARE.${NC}"
echo ""

echo -e "${CYAN}✅ DO:${NC}"
echo -e "  ${GREEN}•${NC} Store in AWS Secrets Manager"
echo -e "  ${GREEN}•${NC} Store in encrypted password manager (1Password, Bitwarden)"
echo -e "  ${GREEN}•${NC} Store in encrypted file (GPG, age)"
echo -e "  ${GREEN}•${NC} Share only with authorized personnel"
echo -e "  ${GREEN}•${NC} Add to .env.production (gitignored)"
echo ""

echo -e "${RED}❌ DO NOT:${NC}"
echo -e "  ${RED}•${NC} Commit to git"
echo -e "  ${RED}•${NC} Share via email/Slack/unencrypted channels"
echo -e "  ${RED}•${NC} Store in plain text files"
echo -e "  ${RED}•${NC} Store in source code"
echo -e "  ${RED}•${NC} Log or print in scripts"
echo ""

echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}Next Steps:${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo -e "${YELLOW}1.${NC} Store token securely (choose one):"
echo ""
echo -e "   ${CYAN}Option A:${NC} Add to .env.production (gitignored)"
echo -e "   ${BLUE}   echo 'VAULT_ROOT_TOKEN=$ROOT_TOKEN' >> .env.production${NC}"
echo ""
echo -e "   ${CYAN}Option B:${NC} Store in AWS Secrets Manager"
echo -e "   ${BLUE}   aws secretsmanager create-secret \\${NC}"
echo -e "   ${BLUE}     --name sentinelgrid/vault/root-token \\${NC}"
echo -e "   ${BLUE}     --secret-string \"$ROOT_TOKEN\"${NC}"
echo ""
echo -e "   ${CYAN}Option C:${NC} Store in password manager"
echo -e "   ${BLUE}   Copy token above and paste into 1Password/Bitwarden${NC}"
echo ""

echo -e "${YELLOW}2.${NC} Set environment variable:"
echo -e "   ${BLUE}   export VAULT_ROOT_TOKEN=\"$ROOT_TOKEN\"${NC}"
echo ""

echo -e "${YELLOW}3.${NC} Verify token works:"
echo -e "   ${BLUE}   export VAULT_ADDR=https://localhost:8200${NC}"
echo -e "   ${BLUE}   export VAULT_SKIP_VERIFY=true${NC}  # Skip cert verification for self-signed cert"
echo -e "   ${BLUE}   export VAULT_TOKEN=\"$ROOT_TOKEN\"${NC}"
echo -e "   ${BLUE}   vault status${NC}"
echo ""

echo -e "${YELLOW}4.${NC} Use token in scripts:"
echo -e "   ${BLUE}   VAULT_ROOT_TOKEN=\"$ROOT_TOKEN\" bash backend/scripts/init_complete_stack.sh${NC}"
echo ""

echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${RED}  ⚠️  TOKEN GENERATED - STORE SECURELY BEFORE PROCEEDING  ⚠️${NC}"
echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Optionally write to file (user must confirm)
read -p "$(echo -e ${YELLOW}Write token to .env.production? [y/N]: ${NC})" write_file

if [[ "$write_file" =~ ^[Yy]$ ]]; then
    ENV_FILE=".env.production"
    
    # Check if file exists
    if [ -f "$ENV_FILE" ]; then
        read -p "$(echo -e ${YELLOW}$ENV_FILE exists. Append? [y/N]: ${NC})" append
        if [[ "$append" =~ ^[Yy]$ ]]; then
            echo "" >> "$ENV_FILE"
            echo "# Vault Root Token (generated $(date -u +"%Y-%m-%d %H:%M:%S UTC"))" >> "$ENV_FILE"
            echo "VAULT_ROOT_TOKEN=$ROOT_TOKEN" >> "$ENV_FILE"
            echo -e "${GREEN}✅ Token appended to $ENV_FILE${NC}"
        else
            echo -e "${YELLOW}⏭️  Skipped writing to file${NC}"
        fi
    else
        echo "# Vault Root Token (generated $(date -u +"%Y-%m-%d %H:%M:%S UTC"))" > "$ENV_FILE"
        echo "VAULT_ROOT_TOKEN=$ROOT_TOKEN" >> "$ENV_FILE"
        echo -e "${GREEN}✅ Token written to $ENV_FILE${NC}"
        echo -e "${YELLOW}⚠️  Verify $ENV_FILE is in .gitignore${NC}"
    fi
else
    echo -e "${YELLOW}⏭️  Token not written to file. Store manually.${NC}"
fi

echo ""
echo -e "${GREEN}✅ Token generation complete!${NC}"
echo ""

