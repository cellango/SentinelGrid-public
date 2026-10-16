#!/bin/bash
# Install SentinelGuard (Go agent) sidecar. Optional; skips when disabled.
set -euo pipefail

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

enabled="${SENTINEL_GUARD_ENABLED:-false}"
if [[ "${enabled,,}" != "true" && "${enabled}" != "1" ]]; then
    log "SentinelGuard disabled; skipping install."
    exit 0
fi

pkg_url="${SENTINEL_GUARD_PACKAGE_URL:-}"
pkg_path="${SENTINEL_GUARD_PACKAGE:-/tmp/sentinelguard.tgz}"
install_dir="${SENTINEL_GUARD_INSTALL_DIR:-/opt/sentinelguard}"
config_path="${SENTINEL_GUARD_CONFIG_PATH:-/etc/sentinelguard/config.yaml}"
config_template="${SENTINEL_GUARD_CONFIG_TEMPLATE:-/tmp/sentinelguard.config.tmpl}"
service_name="${SENTINEL_GUARD_SERVICE_NAME:-sentinelguard}"

tenant_id="${SENTINEL_GUARD_TENANT_ID:-}"
agent_id="${SENTINEL_GUARD_AGENT_ID:-}"
ingest_url="${SENTINEL_GUARD_INGEST_URL:-}"
tls_verify="${SENTINEL_GUARD_TLS_VERIFY:-true}"
auth_token="${SENTINEL_GUARD_AUTH_TOKEN:-}"
wazuh_alert_path="${SENTINEL_GUARD_WAZUH_ALERT_PATH:-/var/ossec/logs/alerts/alerts.json}"
version="${SENTINEL_GUARD_VERSION:-}"

log "Installing SentinelGuard (enabled=${enabled})"

mkdir -p "$(dirname "$pkg_path")"
mkdir -p "$install_dir"

if [[ -n "$pkg_url" ]]; then
    log "Downloading SentinelGuard package from $pkg_url"
    curl -fsSL "$pkg_url" -o "$pkg_path"
fi

if [[ ! -f "$pkg_path" ]]; then
    log "ERROR: SentinelGuard package not found at $pkg_path (provide SENTINEL_GUARD_PACKAGE_URL or pre-upload the artifact)."
    exit 1
fi

log "Extracting package to $install_dir"
tar -xzf "$pkg_path" -C "$install_dir"

bin_path="$(find "$install_dir" -maxdepth 3 -type f -perm -111 | head -n1 || true)"
if [[ -z "$bin_path" ]]; then
    log "ERROR: No executable found in $install_dir after extraction."
    exit 1
fi
chmod +x "$bin_path"

log "Creating sentinelguard service user (if missing)"
if ! id -u sentinelguard >/dev/null 2>&1; then
    useradd --system --no-create-home --shell /usr/sbin/nologin sentinelguard
fi
chown -R sentinelguard:sentinelguard "$install_dir" || true

log "Writing config to $config_path"
mkdir -p "$(dirname "$config_path")"
if command -v envsubst >/dev/null 2>&1 && [[ -f "$config_template" ]]; then
    envsubst < "$config_template" > "$config_path"
else
    cat > "$config_path" <<EOF
tenant_id: "${tenant_id}"
agent_id: "${agent_id}"
ingest_url: "${ingest_url}"
tls_verify: ${tls_verify}
auth_token: "${auth_token}"
wazuh_alert_path: "${wazuh_alert_path}"
version: "${version}"
EOF
fi
chmod 640 "$config_path"
chown sentinelguard:sentinelguard "$config_path" || true

if command -v systemctl >/dev/null 2>&1; then
    log "Creating systemd unit ${service_name}.service"
    cat > "/etc/systemd/system/${service_name}.service" <<EOF
[Unit]
Description=SentinelGuard agent
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=sentinelguard
Group=sentinelguard
ExecStart=${bin_path} --config ${config_path}
Restart=always
RestartSec=5
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOF
    systemctl daemon-reload
    systemctl enable "${service_name}" || true
    # Do not start during bake; will start on first boot.
else
    log "systemd not available; install completed without service registration."
fi

log "SentinelGuard installation complete."
