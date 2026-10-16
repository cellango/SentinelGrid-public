# Install SentinelGrid Endpoint Protection Agent (Windows)
# This script installs the agent and configures it with a tenant token

$ErrorActionPreference = "Stop"
$LogFile = "C:\Windows\Temp\sentinelgrid-agent-install.log"

function Write-Log {
    param([string]$Message)
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogMessage = "[$Timestamp] $Message"
    Write-Host $LogMessage
    Add-Content -Path $LogFile -Value $LogMessage
}

Write-Log "Installing SentinelGrid Endpoint Protection Agent..."

$TenantToken = $env:SENTINELGRID_TENANT_TOKEN
$ManagerHost = $env:SENTINELGRID_MANAGER_HOST
if (-not $ManagerHost) { $ManagerHost = "manager.sentinelgrid.ai" }
$ManagerPort = $env:SENTINELGRID_MANAGER_PORT
if (-not $ManagerPort) { $ManagerPort = "1514" }
$AgentVersion = $env:SENTINELGRID_AGENT_VERSION
if (-not $AgentVersion) { $AgentVersion = "1.0.0" }
$CDNUrl = $env:SENTINELGRID_CDN_URL
if (-not $CDNUrl) { $CDNUrl = "https://agents.sentinelgrid.ai" }

# Download and install agent
$InstallerUrl = "$CDNUrl/v$AgentVersion/windows/sentinelgrid-agent-$AgentVersion-1.msi"
$InstallerPath = "$env:TEMP\sentinelgrid-agent.msi"

Write-Log "Downloading agent from: $InstallerUrl"
try {
    Invoke-WebRequest -Uri $InstallerUrl -OutFile $InstallerPath -UseBasicParsing
} catch {
    Write-Log "ERROR: Failed to download agent installer: $_"
    exit 1
}

Write-Log "Installing agent..."
try {
    Start-Process -FilePath "msiexec.exe" -ArgumentList "/i `"$InstallerPath`" /quiet /norestart" -Wait -NoNewWindow
} catch {
    Write-Log "ERROR: Failed to install agent: $_"
    exit 1
}

# Configure agent if token provided
if ($TenantToken) {
    Write-Log "Configuring agent with tenant token..."
    
    $AgentAuthPath = "C:\Program Files (x86)\ossec-agent\agent-auth.exe"
    if (Test-Path $AgentAuthPath) {
        try {
            & $AgentAuthPath -m $ManagerHost -p $ManagerPort -A $TenantToken
            Write-Log "Agent configured successfully"
        } catch {
            Write-Log "WARNING: Agent authentication failed. Token may be invalid or manager unreachable."
            Write-Log "Agent will need to be configured manually after deployment."
        }
    } else {
        Write-Log "WARNING: agent-auth.exe not found. Agent will need to be configured manually."
    }
} else {
    Write-Log "No tenant token provided. Agent will need to be configured manually after deployment."
}

# Start service
Write-Log "Starting SentinelGrid agent service..."
try {
    $ServiceName = "SentinelGrid Agent"
    if (-not (Get-Service -Name $ServiceName -ErrorAction SilentlyContinue)) {
        $ServiceName = "ossec-agent"
    }
    
    if (Get-Service -Name $ServiceName -ErrorAction SilentlyContinue) {
        Start-Service -Name $ServiceName
        Set-Service -Name $ServiceName -StartupType Automatic
        Write-Log "Agent service started and enabled"
    } else {
        Write-Log "WARNING: Agent service not found. Service will need to be started manually."
    }
} catch {
    Write-Log "WARNING: Failed to start agent service: $_"
}

Write-Log "SentinelGrid agent installation complete!"
Write-Log "NOTE: Agent will be configured and started on first boot if tenant token is provided via user-data."

