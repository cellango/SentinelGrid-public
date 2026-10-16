#!/usr/bin/env bash
set -euo pipefail

# Installer for SentinelGuard EDR sidecars.
# Defaults: Wazuh + OpenEDR enabled, Velociraptor opt-in.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HEALTH_CHECK="${SCRIPT_DIR}/sidecar-health.sh"

WAZUH_ENABLED="${EDR_WAZUH_ENABLED:-true}"
OPENEDR_ENABLED="${EDR_OPENEDR_ENABLED:-true}"
VELOCI_ENABLED="${EDR_VELOCIRAPTOR_ENABLED:-false}"

CONFIG_PATH="${EDR_CONFIG_PATH:-/etc/sentinelguard/edr-agent.config.yaml}"
STATE_DIR="${EDR_STATE_DIR:-/var/lib/sentinelguard}"

log() { echo "[$(date -Is)] $*"; }
die() { echo "ERROR: $*" >&2; exit 1; }

require_binary() {
  local bin="$1" name="$2"
  if [[ ! -x "$bin" ]]; then
    die "Expected ${name} binary at ${bin}. Set EDR_${name^^}_BINARY or install the sidecar."
  fi
}

write_unit() {
  local name="$1" bin="$2" config="$3" health="$4" restart_sec="$5"
  local unit="/etc/systemd/system/sentinelguard-${name}.service"
  cat > "$unit" <<EOF
[Unit]
Description=SentinelGuard ${name} sidecar
After=network.target

[Service]
ExecStart=${bin} --config ${config}
EOF
  if [[ -n "$health" ]]; then
    cat >> "$unit" <<EOF
ExecStartPre=${HEALTH_CHECK} "${health}" "${name}" 5 2
EOF
  fi
  cat >> "$unit" <<EOF
Restart=on-failure
RestartSec=${restart_sec}
StartLimitIntervalSec=120
StartLimitBurst=5
User=root
KillSignal=SIGTERM
TimeoutStopSec=20

[Install]
WantedBy=multi-user.target
EOF
  log "Wrote systemd unit ${unit}"
}

install_sidecar() {
  local key="$1" enabled="$2" bin="$3" config="$4" health="$5"
  if [[ "${enabled}" != "true" ]]; then
    log "Skipping ${key} (disabled)"
    return
  fi
  require_binary "$bin" "$key"
  if [[ ! -f "$config" ]]; then
    log "Config ${config} missing for ${key}; creating placeholder"
    mkdir -p "$(dirname "$config")"
    cat > "$config" <<EOF
# TODO: populate ${key} config
EOF
  fi
  write_unit "$key" "$bin" "$config" "$health" "${EDR_RESTART_BACKOFF_SECONDS:-10}"
  systemctl daemon-reload
  systemctl enable --now "sentinelguard-${key}.service"
}

log "Creating state dir at ${STATE_DIR}"
mkdir -p "${STATE_DIR}/spool"

install_sidecar "wazuh" "$WAZUH_ENABLED" "${EDR_WAZUH_BINARY:-/usr/bin/wazuh-agentd}" "${EDR_WAZUH_CONFIG_PATH:-/var/ossec/etc/ossec.conf}" "${EDR_WAZUH_HEALTH_ENDPOINT:-}"
install_sidecar "openedr" "$OPENEDR_ENABLED" "${EDR_OPENEDR_BINARY:-/opt/openedr/bin/openedr}" "${EDR_OPENEDR_CONFIG_PATH:-/etc/openedr/config.yaml}" "${EDR_OPENEDR_HEALTH_ENDPOINT:-}"
install_sidecar "velociraptor" "$VELOCI_ENABLED" "${EDR_VELOCIRAPTOR_BINARY:-/usr/local/bin/velociraptor}" "${EDR_VELOCIRAPTOR_CONFIG_PATH:-/etc/velociraptor/client.config.yaml}" "${EDR_VELOCIRAPTOR_HEALTH_ENDPOINT:-}"

log "Installation complete. Verify health endpoints and ingest connectivity before rollout."
