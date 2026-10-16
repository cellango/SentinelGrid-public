#!/bin/bash
# Setup APT repository for SentinelGrid agents
# This script creates a Debian/Ubuntu APT repository structure

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${REPO_DIR:-${SCRIPT_DIR}/../../apt-repo}"
CDN_URL="${CDN_URL:-https://agents.sentinelgrid.ai}"
GPG_KEY_ID="${GPG_KEY_ID:-}"
SENTINELGRID_VERSION="${SENTINELGRID_VERSION:-1.0.0}"

echo "=========================================="
echo "Setting up APT Repository"
echo "=========================================="
echo "Repository Directory: ${REPO_DIR}"
echo "CDN URL: ${CDN_URL}"
echo ""

# Create repository structure
mkdir -p "${REPO_DIR}"/{dists,pool,conf}

# Create distributions directory structure
for dist in "stable" "testing"; do
    for arch in "amd64" "arm64"; do
        mkdir -p "${REPO_DIR}/dists/${dist}/main/binary-${arch}"
    done
done

# Create repository configuration
cat > "${REPO_DIR}/conf/distributions" <<EOF
Origin: SentinelGrid
Label: SentinelGrid Agent Repository
Suite: stable
Codename: stable
Version: ${SENTINELGRID_VERSION}
Architectures: amd64 arm64
Components: main
Description: SentinelGrid Endpoint Protection Agent Repository
SignWith: ${GPG_KEY_ID:-default}

Origin: SentinelGrid
Label: SentinelGrid Agent Repository (Testing)
Suite: testing
Codename: testing
Version: ${SENTINELGRID_VERSION}
Architectures: amd64 arm64
Components: main
Description: SentinelGrid Endpoint Protection Agent Repository (Testing)
SignWith: ${GPG_KEY_ID:-default}
EOF

echo "✅ Repository structure created"

# Create Release file template
cat > "${REPO_DIR}/conf/options" <<EOF
ask-passphrase
basedir ${REPO_DIR}
EOF

# Create repository index script
cat > "${REPO_DIR}/update-repo.sh" <<'SCRIPT'
#!/bin/bash
# Update APT repository index

set -e

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CDN_URL="${CDN_URL:-https://agents.sentinelgrid.ai}"

echo "Updating APT repository index..."

# Check if reprepro is installed
if ! command -v reprepro &> /dev/null; then
    echo "❌ reprepro not found. Installing..."
    sudo apt-get update
    sudo apt-get install -y reprepro gnupg
fi

# Add packages from pool
for deb_file in "${REPO_DIR}/pool"/*.deb; do
    if [ -f "$deb_file" ]; then
        echo "Adding: $(basename $deb_file)"
        reprepro -b "${REPO_DIR}" includedeb stable "$deb_file" || \
        reprepro -b "${REPO_DIR}" includedeb testing "$deb_file" || true
    fi
done

# Update repository
reprepro -b "${REPO_DIR}" export stable
reprepro -b "${REPO_DIR}" export testing

echo "✅ Repository index updated"
SCRIPT

chmod +x "${REPO_DIR}/update-repo.sh"

# Create installation instructions
cat > "${REPO_DIR}/INSTALL.md" <<EOF
# Installing SentinelGrid Agent via APT

## Add Repository

\`\`\`bash
# Import GPG key (if available)
curl -fsSL ${CDN_URL}/apt/gpg.key | sudo apt-key add -

# Add repository
echo "deb [arch=amd64] ${CDN_URL}/apt stable main" | sudo tee /etc/apt/sources.list.d/sentinelgrid.list

# Update package list
sudo apt-get update
\`\`\`

## Install Agent

\`\`\`bash
sudo apt-get install sentinelgrid-agent
\`\`\`

## Configure Agent

\`\`\`bash
# Configure with tenant token
sudo /var/ossec/bin/agent-auth -m manager.sentinelgrid.ai -A YOUR_TENANT_TOKEN

# Start service
sudo systemctl enable sentinelgrid-agent
sudo systemctl start sentinelgrid-agent
\`\`\`

## Update Agent

\`\`\`bash
sudo apt-get update
sudo apt-get upgrade sentinelgrid-agent
\`\`\`
EOF

echo ""
echo "=========================================="
echo "✅ APT repository setup complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Add DEB packages to: ${REPO_DIR}/pool/"
echo "2. Run: ${REPO_DIR}/update-repo.sh"
echo "3. Upload repository to CDN: ${CDN_URL}/apt/"
echo "4. Configure GPG signing (if needed)"

