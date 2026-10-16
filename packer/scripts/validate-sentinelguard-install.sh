#!/usr/bin/env bash
# Validate SentinelGuard install inside a baked image. Intended as a post-provision check.
set -euo pipefail

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

service_name="${SENTINEL_GUARD_SERVICE_NAME:-sentinelguard}"
config_path="${SENTINEL_GUARD_CONFIG_PATH:-/etc/sentinelguard/config.yaml}"
install_dir="${SENTINEL_GUARD_INSTALL_DIR:-/opt/sentinelguard}"
wazuh_alert_path="${SENTINEL_GUARD_WAZUH_ALERT_PATH:-/var/ossec/logs/alerts/alerts.json}"

log "Checking SentinelGuard install (service=${service_name}, config=${config_path})"

if [[ ! -d "$install_dir" ]]; then
    log "ERROR: install dir missing at $install_dir"
    exit 1
fi

bin_path="$(find "$install_dir" -maxdepth 3 -type f -perm -111 -name 'sentinelguard*' | head -n1 || true)"
if [[ -z "$bin_path" ]]; then
    log "ERROR: no sentinelguard binary found under $install_dir"
    exit 1
fi
log "Found binary at $bin_path"

if [[ ! -f "$config_path" ]]; then
    log "ERROR: config missing at $config_path"
    exit 1
fi

if ! grep -q "tenant_id" "$config_path"; then
    log "ERROR: config missing tenant_id"
    exit 1
fi
if ! grep -q "ingest_url" "$config_path"; then
    log "ERROR: config missing ingest_url"
    exit 1
fi
log "Config present and includes tenant_id/ingest_url placeholders"

if [[ -n "$wazuh_alert_path" ]]; then
    if [[ ! -f "$wazuh_alert_path" ]]; then
        log "WARN: wazuh alert path $wazuh_alert_path not found (ensure Wazuh outputs JSON alerts here)"
    else
        if sudo -u sentinelguard test -r "$wazuh_alert_path"; then
            log "Wazuh alert path is readable by sentinelguard user"
        else
            log "WARN: sentinelguard user cannot read $wazuh_alert_path"
        fi
    fi
fi

if command -v systemctl >/dev/null 2>&1; then
    if systemctl cat "${service_name}" >/dev/null 2>&1; then
        log "Systemd unit ${service_name}.service is present"
        if systemctl is-enabled "${service_name}" >/dev/null 2>&1; then
            log "Service is enabled (expected on first boot)"
        else
            log "WARN: service is not enabled; enable with: systemctl enable ${service_name}"
        fi
    else
        log "ERROR: systemd unit ${service_name}.service not found"
        exit 1
    fi
else
    log "systemd not available; skipping service validation"
fi

log "SentinelGuard validation finished"
