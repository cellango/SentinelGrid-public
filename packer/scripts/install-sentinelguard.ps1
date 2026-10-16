# Install SentinelGuard (Go agent) sidecar. Optional; skips when disabled.
$ErrorActionPreference = "Stop"
$LogFile = "C:\Windows\Temp\sentinelguard-install.log"

function Write-Log {
    param([string]$Message)
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $Line = "[$Timestamp] $Message"
    Write-Host $Line
    Add-Content -Path $LogFile -Value $Line
}

$enabled = $env:SENTINEL_GUARD_ENABLED
if (-not $enabled -or $enabled.ToLower() -ne "true") {
    Write-Log "SentinelGuard disabled; skipping install."
    exit 0
}

$packageUrl = $env:SENTINEL_GUARD_PACKAGE_URL
$packagePath = $env:SENTINEL_GUARD_PACKAGE_PATH
if (-not $packagePath -or $packagePath -eq "") { $packagePath = "$env:TEMP\sentinelguard.zip" }
$installDir = $env:SENTINEL_GUARD_INSTALL_DIR
if (-not $installDir -or $installDir -eq "") { $installDir = "C:\Program Files\SentinelGuard" }
$configPath = $env:SENTINEL_GUARD_CONFIG_PATH
if (-not $configPath -or $configPath -eq "") { $configPath = "C:\ProgramData\SentinelGuard\config.yaml" }
$configTemplate = $env:SENTINEL_GUARD_CONFIG_TEMPLATE
if (-not $configTemplate -or $configTemplate -eq "") { $configTemplate = "C:\Windows\Temp\sentinelguard.config.tmpl" }
$serviceName = $env:SENTINEL_GUARD_SERVICE_NAME
if (-not $serviceName -or $serviceName -eq "") { $serviceName = "SentinelGuard" }

$tenantId = $env:SENTINEL_GUARD_TENANT_ID
$agentId = $env:SENTINEL_GUARD_AGENT_ID
$ingestUrl = $env:SENTINEL_GUARD_INGEST_URL
$tlsVerify = $env:SENTINEL_GUARD_TLS_VERIFY
if (-not $tlsVerify -or $tlsVerify -eq "") { $tlsVerify = "true" }
$authToken = $env:SENTINEL_GUARD_AUTH_TOKEN
$wazuhAlertPath = $env:SENTINEL_GUARD_WAZUH_ALERT_PATH
$guardVersion = $env:SENTINEL_GUARD_VERSION

Write-Log "Installing SentinelGuard (enabled=$enabled)"

if (-not $packageUrl -and -not (Test-Path $packagePath)) {
    Write-Log "ERROR: Provide SENTINEL_GUARD_PACKAGE_URL or pre-upload package to $packagePath"
    exit 1
}

if ($packageUrl) {
    Write-Log "Downloading package from $packageUrl"
    Invoke-WebRequest -Uri $packageUrl -OutFile $packagePath -UseBasicParsing
}

Write-Log "Expanding package to $installDir"
New-Item -ItemType Directory -Path $installDir -Force | Out-Null
Expand-Archive -Path $packagePath -DestinationPath $installDir -Force

$bin = Get-ChildItem -Path $installDir -Recurse -Filter "sentinelguard*.exe" | Select-Object -First 1
if (-not $bin) {
    Write-Log "ERROR: No sentinelguard executable found under $installDir"
    exit 1
}

$configDir = Split-Path $configPath -Parent
New-Item -ItemType Directory -Path $configDir -Force | Out-Null

if (Test-Path $configTemplate) {
    Write-Log "Rendering config from template $configTemplate"
    $templateContent = Get-Content $configTemplate -Raw
    $rendered = $templateContent `
        -replace '\$\{SENTINEL_GUARD_TENANT_ID\}', $tenantId `
        -replace '\$\{SENTINEL_GUARD_AGENT_ID\}', $agentId `
        -replace '\$\{SENTINEL_GUARD_INGEST_URL\}', $ingestUrl `
        -replace '\$\{SENTINEL_GUARD_TLS_VERIFY\}', $tlsVerify `
        -replace '\$\{SENTINEL_GUARD_AUTH_TOKEN\}', $authToken `
        -replace '\$\{SENTINEL_GUARD_WAZUH_ALERT_PATH\}', $wazuhAlertPath `
        -replace '\$\{SENTINEL_GUARD_VERSION\}', $guardVersion
    $rendered | Out-File -FilePath $configPath -Encoding ASCII
} else {
    Write-Log "Writing default config to $configPath"
    @"
tenant_id: "$tenantId"
agent_id: "$agentId"
ingest_url: "$ingestUrl"
tls_verify: $tlsVerify
auth_token: "$authToken"
wazuh_alert_path: "$wazuhAlertPath"
version: "$guardVersion"
"@ | Out-File -FilePath $configPath -Encoding ASCII
}

Write-Log "Creating Windows service $serviceName"
$binaryWithArgs = "`"$($bin.FullName)`" --config `"$configPath`""
if (Get-Service -Name $serviceName -ErrorAction SilentlyContinue) {
    Set-Service -Name $serviceName -StartupType Automatic
} else {
    New-Service -Name $serviceName -BinaryPathName $binaryWithArgs -StartupType Automatic -ErrorAction Stop
}

# Do not start service during bake; allow first-boot start to avoid noisy failures during imaging.
Write-Log "SentinelGuard installation complete."
