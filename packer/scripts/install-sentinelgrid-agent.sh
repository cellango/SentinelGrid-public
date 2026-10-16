#!/bin/bash
# Install SentinelGrid Endpoint Protection Agent
# This script installs the agent and configures it with a tenant token

set -e

TENANT_TOKEN="${SENTINELGRID_TENANT_TOKEN:-}"
MANAGER_HOST="${SENTINELGRID_MANAGER_HOST:-manager.sentinelgrid.ai}"
MANAGER_PORT="${SENTINELGRID_MANAGER_PORT:-1514}"
AGENT_VERSION="${SENTINELGRID_AGENT_VERSION:-1.0.0}"
CDN_URL="${SENTINELGRID_CDN_URL:-https://agents.sentinelgrid.ai}"

# Ensure we're using SentinelGrid rebranded agents, not upstream Wazuh
# All downloads should come from SentinelGrid CDN

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

log "Installing SentinelGrid Endpoint Protection Agent..."

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    VERSION=$VERSION_ID
elif [ -f /etc/redhat-release ]; then
    OS="rhel"
    VERSION=$(cat /etc/redhat-release | sed 's/.*release \([0-9]\+\).*/\1/')
else
    log "ERROR: Unsupported operating system"
    exit 1
fi

log "Detected OS: $OS $VERSION"

# Install based on OS
case $OS in
    "amzn"|"amazon")
        log "Installing via YUM (Amazon Linux)..."
        
        # Add repository
        curl -fsSL ${CDN_URL}/yum/RPM-GPG-KEY-sentinelgrid | rpm --import -
        cat > /etc/yum.repos.d/sentinelgrid.repo <<EOF
[sentinelgrid]
name=SentinelGrid Agent Repository
baseurl=${CDN_URL}/yum/\$releasever/\$basearch
enabled=1
gpgcheck=1
gpgkey=${CDN_URL}/yum/RPM-GPG-KEY-sentinelgrid
repo_gpgcheck=1
EOF
        
        yum install -y sentinelgrid-agent || {
            log "Repository not available, installing from package..."
            yum install -y wget
            wget -O /tmp/sentinelgrid-agent.rpm ${CDN_URL}/v${AGENT_VERSION}/linux/rpm/sentinelgrid-agent-${AGENT_VERSION}-1.x86_64.rpm
            yum localinstall -y /tmp/sentinelgrid-agent.rpm
        }
        ;;
    
    "ubuntu"|"debian")
        log "Installing via APT (Debian/Ubuntu)..."
        
        # Add repository (SentinelGrid rebranded agents)
        curl -fsSL ${CDN_URL}/apt/gpg.key | apt-key add -
        echo "deb [arch=amd64] ${CDN_URL}/apt stable main" | tee /etc/apt/sources.list.d/sentinelgrid.list
        
        apt-get update -qq
        # Try repository first, fallback to direct download
        apt-get install -y sentinelgrid-agent || {
            log "Repository not available, installing from package..."
            apt-get install -y wget
            # Download SentinelGrid rebranded agent (not upstream Wazuh)
            wget -O /tmp/sentinelgrid-agent.deb ${CDN_URL}/v${AGENT_VERSION}/linux/deb/sentinelgrid-agent_${AGENT_VERSION}-1_amd64.deb
            dpkg -i /tmp/sentinelgrid-agent.deb || apt-get install -f -y
        }
        ;;
    
    "rhel"|"centos")
        log "Installing via YUM (RHEL/CentOS)..."
        
        # Add repository
        curl -fsSL ${CDN_URL}/yum/RPM-GPG-KEY-sentinelgrid | rpm --import -
        cat > /etc/yum.repos.d/sentinelgrid.repo <<EOF
[sentinelgrid]
name=SentinelGrid Agent Repository
baseurl=${CDN_URL}/yum/\$releasever/\$basearch
enabled=1
gpgcheck=1
gpgkey=${CDN_URL}/yum/RPM-GPG-KEY-sentinelgrid
repo_gpgcheck=1
EOF
        
        yum install -y sentinelgrid-agent || {
            log "Repository not available, installing from package..."
            yum install -y wget
            wget -O /tmp/sentinelgrid-agent.rpm ${CDN_URL}/v${AGENT_VERSION}/linux/rpm/sentinelgrid-agent-${AGENT_VERSION}-1.x86_64.rpm
            yum localinstall -y /tmp/sentinelgrid-agent.rpm
        }
        ;;
    
    *)
        log "ERROR: Unsupported OS: $OS"
        exit 1
        ;;
esac

# Configure agent if token provided
if [ -n "$TENANT_TOKEN" ]; then
    log "Configuring agent with tenant token..."
    
    # Find agent-auth binary
    if [ -f /var/ossec/bin/agent-auth ]; then
        /var/ossec/bin/agent-auth \
            -m "$MANAGER_HOST" \
            -p "$MANAGER_PORT" \
            -A "$TENANT_TOKEN" || {
            log "WARNING: Agent authentication failed. Token may be invalid or manager unreachable."
            log "Agent will need to be configured manually after deployment."
        }
    else
        log "WARNING: agent-auth binary not found. Agent will need to be configured manually."
    fi
else
    log "No tenant token provided. Agent will need to be configured manually after deployment."
fi

# Enable and start service
log "Enabling SentinelGrid agent service..."
if command -v systemctl &> /dev/null; then
    systemctl enable sentinelgrid-agent 2>/dev/null || systemctl enable ossec-agentd 2>/dev/null || true
    # Don't start during build - will start on first boot
    # systemctl start sentinelgrid-agent
else
    log "WARNING: systemctl not found. Service will need to be started manually."
fi

log "SentinelGrid agent installation complete!"
log "NOTE: Agent will be configured and started on first boot if tenant token is provided via user-data."

