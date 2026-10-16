#!/bin/bash
# Setup YUM repository for SentinelGrid agents
# This script creates a RHEL/CentOS/Amazon Linux YUM repository structure

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${REPO_DIR:-${SCRIPT_DIR}/../../yum-repo}"
CDN_URL="${CDN_URL:-https://agents.sentinelgrid.ai}"
GPG_KEY_ID="${GPG_KEY_ID:-}"
SENTINELGRID_VERSION="${SENTINELGRID_VERSION:-1.0.0}"

echo "=========================================="
echo "Setting up YUM Repository"
echo "=========================================="
echo "Repository Directory: ${REPO_DIR}"
echo "CDN URL: ${CDN_URL}"
echo ""

# Create repository structure
mkdir -p "${REPO_DIR}"/{7,8,9,2023}/{x86_64,noarch}
mkdir -p "${REPO_DIR}/repodata"

# Create repository metadata script
cat > "${REPO_DIR}/update-repo.sh" <<'SCRIPT'
#!/bin/bash
# Update YUM repository metadata

set -e

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CDN_URL="${CDN_URL:-https://agents.sentinelgrid.ai}"

echo "Updating YUM repository metadata..."

# Check if createrepo is installed
if ! command -v createrepo &> /dev/null && ! command -v createrepo_c &> /dev/null; then
    echo "❌ createrepo not found. Installing..."
    if command -v yum &> /dev/null; then
        sudo yum install -y createrepo
    elif command -v dnf &> /dev/null; then
        sudo dnf install -y createrepo
    else
        echo "⚠️  Please install createrepo manually"
        exit 1
    fi
fi

CREATEREPO_CMD="createrepo"
if command -v createrepo_c &> /dev/null; then
    CREATEREPO_CMD="createrepo_c"
fi

# Update metadata for each distribution
for dist in 7 8 9 2023; do
    if [ -d "${REPO_DIR}/${dist}" ]; then
        echo "Updating metadata for RHEL/CentOS ${dist}..."
        
        for arch in x86_64 noarch; do
            if [ -d "${REPO_DIR}/${dist}/${arch}" ]; then
                echo "  Processing ${arch}..."
                $CREATEREPO_CMD --update "${REPO_DIR}/${dist}/${arch}"
            fi
        done
    fi
done

echo "✅ Repository metadata updated"
SCRIPT

chmod +x "${REPO_DIR}/update-repo.sh"

# Create repository configuration files
cat > "${REPO_DIR}/sentinelgrid.repo" <<EOF
[sentinelgrid]
name=SentinelGrid Agent Repository
baseurl=${CDN_URL}/yum/\$releasever/\$basearch
enabled=1
gpgcheck=1
gpgkey=${CDN_URL}/yum/RPM-GPG-KEY-sentinelgrid
repo_gpgcheck=1
EOF

# Create GPG key placeholder
cat > "${REPO_DIR}/RPM-GPG-KEY-sentinelgrid" <<EOF
-----BEGIN PGP PUBLIC KEY BLOCK-----
# Placeholder - Replace with actual GPG public key
# To generate: gpg --armor --export <key-id> > RPM-GPG-KEY-sentinelgrid
-----END PGP PUBLIC KEY BLOCK-----
EOF

# Create installation instructions
cat > "${REPO_DIR}/INSTALL.md" <<EOF
# Installing SentinelGrid Agent via YUM

## RHEL/CentOS 7/8/9

\`\`\`bash
# Import GPG key
sudo rpm --import ${CDN_URL}/yum/RPM-GPG-KEY-sentinelgrid

# Add repository
sudo curl -o /etc/yum.repos.d/sentinelgrid.repo ${CDN_URL}/yum/sentinelgrid.repo

# Install agent
sudo yum install -y sentinelgrid-agent
\`\`\`

## Amazon Linux 2023

\`\`\`bash
# Import GPG key
sudo rpm --import ${CDN_URL}/yum/RPM-GPG-KEY-sentinelgrid

# Add repository
sudo curl -o /etc/yum.repos.d/sentinelgrid.repo ${CDN_URL}/yum/sentinelgrid.repo

# Install agent
sudo dnf install -y sentinelgrid-agent
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
sudo yum update sentinelgrid-agent
# or
sudo dnf update sentinelgrid-agent
\`\`\`
EOF

echo ""
echo "=========================================="
echo "✅ YUM repository setup complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Add RPM packages to: ${REPO_DIR}/<version>/<arch>/"
echo "2. Run: ${REPO_DIR}/update-repo.sh"
echo "3. Upload repository to CDN: ${CDN_URL}/yum/"
echo "4. Configure GPG signing (if needed)"

