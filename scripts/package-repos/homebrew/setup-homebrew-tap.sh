#!/bin/bash
# Setup Homebrew tap for SentinelGrid agents
# This script creates a Homebrew tap repository structure

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TAP_DIR="${TAP_DIR:-${SCRIPT_DIR}/../../homebrew-tap}"
CDN_URL="${CDN_URL:-https://agents.sentinelgrid.ai}"
SENTINELGRID_VERSION="${SENTINELGRID_VERSION:-1.0.0}"

echo "=========================================="
echo "Setting up Homebrew Tap"
echo "=========================================="
echo "Tap Directory: ${TAP_DIR}"
echo "CDN URL: ${CDN_URL}"
echo ""

# Create tap structure
mkdir -p "${TAP_DIR}"/{Formula,Casks}

# Create Homebrew formula
cat > "${TAP_DIR}/Formula/sentinelgrid-agent.rb" <<EOF
class SentinelgridAgent < Formula
  desc "SentinelGrid Endpoint Protection Agent"
  homepage "https://sentinelgrid.ai"
  version "${SENTINELGRID_VERSION}"
  license "GPL-2.0"

  if Hardware::CPU.intel?
    url "${CDN_URL}/v${SENTINELGRID_VERSION}/macos/sentinelgrid-agent-${SENTINELGRID_VERSION}-1.pkg"
    sha256 "PLACEHOLDER_SHA256_INTEL"
  else
    url "${CDN_URL}/v${SENTINELGRID_VERSION}/macos/sentinelgrid-agent-${SENTINELGRID_VERSION}-1-arm64.pkg"
    sha256 "PLACEHOLDER_SHA256_ARM64"
  end

  def install
    # Extract PKG
    system "pkgutil", "--expand", "#{cached_download}", "#{buildpath}/extracted"
    
    # Install files
    system "sudo", "installer", "-pkg", "#{cached_download}", "-target", "/"
  end

  def post_install
    ohai "SentinelGrid Agent installed!"
    ohai "Configure with: sudo /var/ossec/bin/agent-auth -m manager.sentinelgrid.ai -A YOUR_TENANT_TOKEN"
    ohai "Start service: sudo launchctl load /Library/LaunchDaemons/com.sentinelgrid.agent.plist"
  end

  test do
    system "#{bin}/sentinelgrid-agent", "--version"
  end
end
EOF

# Create Cask (alternative to Formula)
cat > "${TAP_DIR}/Casks/sentinelgrid-agent.rb" <<EOF
cask "sentinelgrid-agent" do
  version "${SENTINELGRID_VERSION}"
  sha256 "PLACEHOLDER_SHA256"

  url "${CDN_URL}/v${version}/macos/sentinelgrid-agent-${version}-1.pkg"
  name "SentinelGrid Agent"
  desc "SentinelGrid Endpoint Protection Agent"
  homepage "https://sentinelgrid.ai"

  pkg "sentinelgrid-agent-${version}-1.pkg"

  uninstall pkgutil: "com.sentinelgrid.agent"

  zap trash: [
    "/var/ossec",
    "~/Library/Preferences/com.sentinelgrid.agent.plist"
  ]
end
EOF

# Create README
cat > "${TAP_DIR}/README.md" <<EOF
# SentinelGrid Homebrew Tap

Homebrew tap for installing SentinelGrid Endpoint Protection Agent on macOS.

## Installation

\`\`\`bash
# Add tap
brew tap sentinelgrid/agents

# Install agent
brew install sentinelgrid-agent

# Or using cask
brew install --cask sentinelgrid-agent
\`\`\`

## Configuration

\`\`\`bash
# Configure with tenant token
sudo /var/ossec/bin/agent-auth -m manager.sentinelgrid.ai -A YOUR_TENANT_TOKEN

# Start service
sudo launchctl load /Library/LaunchDaemons/com.sentinelgrid.agent.plist
\`\`\`

## Update

\`\`\`bash
brew update
brew upgrade sentinelgrid-agent
\`\`\`

## Uninstall

\`\`\`bash
brew uninstall sentinelgrid-agent
\`\`\`
EOF

echo ""
echo "=========================================="
echo "✅ Homebrew tap setup complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Update SHA256 checksums in Formula files"
echo "2. Create GitHub repository: homebrew-agents"
echo "3. Push to GitHub: git push origin main"
echo "4. Users can install with: brew tap sentinelgrid/agents"

