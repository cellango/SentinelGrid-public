#!/bin/bash
# Setup Chocolatey package for SentinelGrid agents
# This script creates a Chocolatey package structure

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHOCO_DIR="${CHOCO_DIR:-${SCRIPT_DIR}/../../chocolatey-packages}"
CDN_URL="${CDN_URL:-https://agents.sentinelgrid.ai}"
SENTINELGRID_VERSION="${SENTINELGRID_VERSION:-1.0.0}"

echo "=========================================="
echo "Setting up Chocolatey Package"
echo "=========================================="
echo "Package Directory: ${CHOCO_DIR}"
echo "CDN URL: ${CDN_URL}"
echo ""

# Create package structure
mkdir -p "${CHOCO_DIR}/sentinelgrid-agent"

# Create Chocolatey package files
cat > "${CHOCO_DIR}/sentinelgrid-agent/sentinelgrid-agent.nuspec" <<EOF
<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://schemas.microsoft.com/packaging/2010/07/nuspec.xsd">
  <metadata>
    <id>sentinelgrid-agent</id>
    <version>${SENTINELGRID_VERSION}</version>
    <title>SentinelGrid Endpoint Protection Agent</title>
    <authors>SentinelGrid</authors>
    <owners>SentinelGrid</owners>
    <summary>SentinelGrid Endpoint Protection Agent for Windows</summary>
    <description>
      SentinelGrid Endpoint Protection Agent provides host-based intrusion detection,
      file integrity monitoring, configuration assessment, and vulnerability detection.
      Powered by Wazuh.
    </description>
    <projectUrl>https://sentinelgrid.ai</projectUrl>
    <tags>security monitoring endpoint protection wazuh</tags>
    <licenseUrl>https://sentinelgrid.ai/license</licenseUrl>
    <requireLicenseAcceptance>false</requireLicenseAcceptance>
    <releaseNotes>Initial release based on Wazuh ${WAZUH_VERSION:-4.8.0}</releaseNotes>
  </metadata>
  <files>
    <file src="tools\**" target="tools" />
  </files>
</package>
EOF

# Create install script
mkdir -p "${CHOCO_DIR}/sentinelgrid-agent/tools"
cat > "${CHOCO_DIR}/sentinelgrid-agent/tools/chocolateyinstall.ps1" <<'EOF'
$ErrorActionPreference = 'Stop'

$packageName = 'sentinelgrid-agent'
$url = '${CDN_URL}/v${SENTINELGRID_VERSION}/windows/sentinelgrid-agent-${SENTINELGRID_VERSION}-1.msi'
$checksum = 'PLACEHOLDER_SHA256'
$checksumType = 'sha256'

$packageArgs = @{
  packageName   = $packageName
  fileType      = 'MSI'
  url           = $url
  checksum      = $checksum
  checksumType  = $checksumType
  silentArgs    = '/quiet /norestart'
  validExitCodes= @(0, 3010, 1641)
}

Install-ChocolateyPackage @packageArgs
EOF

# Replace placeholders in install script
sed -i.bak "s|\${CDN_URL}|${CDN_URL}|g" "${CHOCO_DIR}/sentinelgrid-agent/tools/chocolateyinstall.ps1"
sed -i.bak "s|\${SENTINELGRID_VERSION}|${SENTINELGRID_VERSION}|g" "${CHOCO_DIR}/sentinelgrid-agent/tools/chocolateyinstall.ps1"
rm -f "${CHOCO_DIR}/sentinelgrid-agent/tools/chocolateyinstall.ps1.bak"

# Create uninstall script
cat > "${CHOCO_DIR}/sentinelgrid-agent/tools/chocolateyuninstall.ps1" <<'EOF'
$ErrorActionPreference = 'Stop'

$packageName = 'sentinelgrid-agent'

$packageArgs = @{
  packageName   = $packageName
  fileType      = 'MSI'
  silentArgs    = '/quiet /norestart'
  validExitCodes= @(0, 3010, 1641)
}

$uninstalled = $false
[array]$key = Get-UninstallRegistryKey -SoftwareName "SentinelGrid Agent*"

if ($key.Count -eq 1) {
  $key | ForEach-Object {
    $packageArgs['file'] = "$($_.UninstallString)"
    
    if ($packageArgs['file'] -like '*msiexec.exe*') {
      $packageArgs['file'] = ''
      $packageArgs['silentArgs'] = "/x $($_.PSChildName) $($packageArgs['silentArgs'])"
    }
    
    Uninstall-ChocolateyPackage @packageArgs
  }
} elseif ($key.Count -eq 0) {
  Write-Warning "$packageName has already been uninstalled by other means."
} elseif ($key.Count -gt 1) {
  Write-Warning "$key.Count matches found!"
  Write-Warning "To prevent accidental data loss, no programs will be uninstalled."
  Write-Warning "Please alert package maintainer the following keys were matched:"
  $key | ForEach-Object {Write-Warning "- $($_.DisplayName)"}
}
EOF

# Create README
cat > "${CHOCO_DIR}/sentinelgrid-agent/README.md" <<EOF
# SentinelGrid Agent Chocolatey Package

Chocolatey package for installing SentinelGrid Endpoint Protection Agent on Windows.

## Installation

\`\`\`powershell
# Install from Chocolatey community repository (after publishing)
choco install sentinelgrid-agent

# Or install from local package
choco install sentinelgrid-agent --source="'.;https://community.chocolatey.org/api/v2'"
\`\`\`

## Configuration

\`\`\`powershell
# Configure with tenant token
& "C:\Program Files (x86)\ossec-agent\agent-auth.exe" -m manager.sentinelgrid.ai -A YOUR_TENANT_TOKEN

# Start service
Start-Service -Name "SentinelGrid Agent"
\`\`\`

## Update

\`\`\`powershell
choco upgrade sentinelgrid-agent
\`\`\`

## Uninstall

\`\`\`powershell
choco uninstall sentinelgrid-agent
\`\`\`

## Building Package

\`\`\`powershell
# Update version and checksum
# Build package
choco pack sentinelgrid-agent.nuspec

# Test installation
choco install sentinelgrid-agent --source="'.;https://community.chocolatey.org/api/v2'" -y

# Publish to Chocolatey community repository
choco push sentinelgrid-agent.${SENTINELGRID_VERSION}.nupkg --source="https://push.chocolatey.org/"
\`\`\`
EOF

echo ""
echo "=========================================="
echo "✅ Chocolatey package setup complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Update SHA256 checksum in chocolateyinstall.ps1"
echo "2. Build package: choco pack sentinelgrid-agent.nuspec"
echo "3. Test installation locally"
echo "4. Publish to Chocolatey community repository"

