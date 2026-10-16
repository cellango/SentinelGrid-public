#!/bin/bash
# Generate GPG keys for package signing
# This script generates GPG keys for signing APT and YUM packages

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KEYS_DIR="${SCRIPT_DIR}/../gpg-keys"
KEY_NAME="SentinelGrid Package Signing Key"
KEY_EMAIL="packages@sentinelgrid.ai"
KEY_EXPIRY="2y"  # Key expires in 2 years

echo "=========================================="
echo "Generating GPG Keys for Package Signing"
echo "=========================================="
echo ""

# Check if GPG is available
if ! command -v gpg &> /dev/null; then
    echo "❌ GPG not found. Please install gnupg first."
    exit 1
fi

# Create keys directory
mkdir -p "$KEYS_DIR"

# Check if key already exists
if [ -f "$KEYS_DIR/sentinelgrid-package-key.asc" ]; then
    echo "⚠️  GPG key already exists: $KEYS_DIR/sentinelgrid-package-key.asc"
    read -p "Generate new key? (y/N): " -r
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Skipping key generation"
        exit 0
    fi
fi

# Generate key batch file
cat > "$KEYS_DIR/key-batch.txt" <<EOF
%no-protection
Key-Type: RSA
Key-Length: 4096
Subkey-Type: RSA
Subkey-Length: 4096
Name-Real: ${KEY_NAME}
Name-Email: ${KEY_EMAIL}
Expire-Date: ${KEY_EXPIRY}
EOF

echo "Generating GPG key..."
echo "This may take a few minutes..."

# Generate key
gpg --batch --gen-key "$KEYS_DIR/key-batch.txt" || {
    echo "❌ Failed to generate GPG key"
    exit 1
}

# Get key ID
KEY_ID=$(gpg --list-keys --keyid-format LONG "${KEY_EMAIL}" | grep -E "^pub" | sed -n 's/.*\/\([A-F0-9]*\).*/\1/p' | head -1)

if [ -z "$KEY_ID" ]; then
    echo "❌ Failed to get key ID"
    exit 1
fi

echo "✅ GPG key generated: ${KEY_ID}"

# Export public key
gpg --armor --export "$KEY_ID" > "$KEYS_DIR/sentinelgrid-package-key.asc"
echo "✅ Public key exported: $KEYS_DIR/sentinelgrid-package-key.asc"

# Export public key for APT
cp "$KEYS_DIR/sentinelgrid-package-key.asc" "$KEYS_DIR/gpg.key"
echo "✅ APT GPG key: $KEYS_DIR/gpg.key"

# Export public key for YUM
cp "$KEYS_DIR/sentinelgrid-package-key.asc" "$KEYS_DIR/RPM-GPG-KEY-sentinelgrid"
echo "✅ YUM GPG key: $KEYS_DIR/RPM-GPG-KEY-sentinelgrid"

# Export private key (encrypted, for backup)
gpg --armor --export-secret-keys "$KEY_ID" | gpg --symmetric --cipher-algo AES256 --output "$KEYS_DIR/sentinelgrid-package-key-private.asc.gpg"
echo "✅ Private key backup (encrypted): $KEYS_DIR/sentinelgrid-package-key-private.asc.gpg"

# Clean up batch file
rm -f "$KEYS_DIR/key-batch.txt"

echo ""
echo "=========================================="
echo "✅ GPG key generation complete!"
echo "=========================================="
echo "Key ID: ${KEY_ID}"
echo "Public Key: $KEYS_DIR/sentinelgrid-package-key.asc"
echo ""
echo "Next steps:"
echo "1. Copy gpg.key to apt-repo/ and yum-repo/ directories"
echo "2. Update repository configurations to use this key"
echo "3. Keep private key secure and backed up"

