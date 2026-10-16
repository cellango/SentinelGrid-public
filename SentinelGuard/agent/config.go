package agent

import (
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"
)

// Config defines how the SentinelGuard sidecar agent runs.
type Config struct {
	TenantID             string
	AgentID              string
	IngestURL            string
	AuthToken            string
	WazuhAlertPath       string
	BufferDir            string
	BatchSize            int
	SkipTLSVerify        bool
	EmbeddingURL         string
	EmbeddingSeverityMin int
	EmbeddingCategories  []string
	RequestTimeout       time.Duration
	MaxEventBytes        int
	Sidecars             SidecarConfig
}

// SidecarConfig bundles enablement and runtime details per EDR source.
type SidecarConfig struct {
	Wazuh        SidecarSettings
	OpenEDR      SidecarSettings
	Velociraptor SidecarSettings
}

// SidecarSettings captures binary/config/health/transport for a sidecar.
type SidecarSettings struct {
	Enabled        bool
	Binary         string
	ConfigPath     string
	HealthEndpoint string
	Transport      SidecarTransport
}

// SidecarTransport models how the sidecar talks to ingest.
type SidecarTransport struct {
	IngestURL string
	MTLSCert  string
	MTLSKey   string
	Token     string
}

// FromEnv builds a Config using environment variables with sensible defaults for local dev.
func FromEnv() Config {
	return Config{
		TenantID:             getenv("SENTINEL_GUARD_TENANT_ID", "tenant-dev"),
		AgentID:              getenv("SENTINEL_GUARD_AGENT_ID", "dev-agent"),
		IngestURL:            getenv("SENTINEL_GUARD_INGEST_URL", "http://localhost:8085/ingest"),
		AuthToken:            os.Getenv("SENTINEL_GUARD_AUTH_TOKEN"),
		WazuhAlertPath:       getenv("SENTINEL_GUARD_WAZUH_ALERT_PATH", "/var/ossec/logs/alerts/alerts.json"),
		BufferDir:            getenv("SENTINEL_GUARD_BUFFER_DIR", defaultBufferDir()),
		BatchSize:            atoiDefault(os.Getenv("SENTINEL_GUARD_BATCH_SIZE"), 50),
		SkipTLSVerify:        getenv("SENTINEL_GUARD_TLS_VERIFY", "true") == "false",
		EmbeddingURL:         os.Getenv("SENTINEL_GUARD_EMBEDDING_URL"),
		EmbeddingSeverityMin: atoiDefault(os.Getenv("SENTINEL_GUARD_EMBED_SEVERITY_MIN"), 50),
		EmbeddingCategories:  parseList(os.Getenv("SENTINEL_GUARD_EMBED_CATEGORIES")),
		RequestTimeout:       time.Duration(atoiDefault(os.Getenv("SENTINEL_GUARD_HTTP_TIMEOUT_SECONDS"), 10)) * time.Second,
		MaxEventBytes:        atoiDefault(os.Getenv("SENTINEL_GUARD_MAX_EVENT_BYTES"), 262144), // 256KB safety cap
		Sidecars: SidecarConfig{
			Wazuh: SidecarSettings{
				Enabled:        parseBoolDefault(os.Getenv("EDR_WAZUH_ENABLED"), true),
				Binary:         getenv("EDR_WAZUH_BINARY", "/usr/bin/wazuh-agentd"),
				ConfigPath:     getenv("EDR_WAZUH_CONFIG_PATH", "/var/ossec/etc/ossec.conf"),
				HealthEndpoint: getenv("EDR_WAZUH_HEALTH_ENDPOINT", "http://localhost:55000"),
				Transport: SidecarTransport{
					IngestURL: getenv("EDR_WAZUH_INGEST_URL", getenv("SENTINEL_GUARD_INGEST_URL", "http://localhost:8085/ingest")),
					MTLSCert:  os.Getenv("EDR_WAZUH_MTLS_CERT"),
					MTLSKey:   os.Getenv("EDR_WAZUH_MTLS_KEY"),
					Token:     getenv("EDR_WAZUH_TOKEN", os.Getenv("SENTINEL_GUARD_AUTH_TOKEN")),
				},
			},
			OpenEDR: SidecarSettings{
				Enabled:        parseBoolDefault(os.Getenv("EDR_OPENEDR_ENABLED"), true),
				Binary:         getenv("EDR_OPENEDR_BINARY", "/opt/openedr/bin/openedr"),
				ConfigPath:     getenv("EDR_OPENEDR_CONFIG_PATH", "/etc/openedr/config.yaml"),
				HealthEndpoint: getenv("EDR_OPENEDR_HEALTH_ENDPOINT", "http://localhost:8040/health"),
				Transport: SidecarTransport{
					IngestURL: getenv("EDR_OPENEDR_INGEST_URL", getenv("SENTINEL_GUARD_INGEST_URL", "http://localhost:8085/ingest")),
					MTLSCert:  os.Getenv("EDR_OPENEDR_MTLS_CERT"),
					MTLSKey:   os.Getenv("EDR_OPENEDR_MTLS_KEY"),
					Token:     getenv("EDR_OPENEDR_TOKEN", os.Getenv("SENTINEL_GUARD_AUTH_TOKEN")),
				},
			},
			Velociraptor: SidecarSettings{
				Enabled:        parseBoolDefault(os.Getenv("EDR_VELOCIRAPTOR_ENABLED"), false),
				Binary:         getenv("EDR_VELOCIRAPTOR_BINARY", "/usr/local/bin/velociraptor"),
				ConfigPath:     getenv("EDR_VELOCIRAPTOR_CONFIG_PATH", "/etc/velociraptor/client.config.yaml"),
				HealthEndpoint: getenv("EDR_VELOCIRAPTOR_HEALTH_ENDPOINT", "http://localhost:8001/server.health"),
				Transport: SidecarTransport{
					IngestURL: getenv("EDR_VELOCIRAPTOR_INGEST_URL", getenv("SENTINEL_GUARD_INGEST_URL", "http://localhost:8085/ingest")),
					MTLSCert:  os.Getenv("EDR_VELOCIRAPTOR_MTLS_CERT"),
					MTLSKey:   os.Getenv("EDR_VELOCIRAPTOR_MTLS_KEY"),
					Token:     os.Getenv("EDR_VELOCIRAPTOR_TOKEN"),
				},
			},
		},
	}
}

func defaultBufferDir() string {
	if dir := os.Getenv("SENTINEL_GUARD_STATE_DIR"); dir != "" {
		return filepath.Join(dir, "spool")
	}
	return "/var/lib/sentinelguard/spool"
}

func atoiDefault(value string, def int) int {
	if value == "" {
		return def
	}
	if v, err := strconv.Atoi(value); err == nil {
		return v
	}
	return def
}

func getenv(key, def string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return def
}

func parseList(raw string) []string {
	if raw == "" {
		return nil
	}
	parts := strings.Split(raw, ",")
	out := make([]string, 0, len(parts))
	for _, p := range parts {
		if v := strings.TrimSpace(p); v != "" {
			out = append(out, v)
		}
	}
	return out
}

func parseBoolDefault(raw string, def bool) bool {
	if raw == "" {
		return def
	}
	switch strings.ToLower(raw) {
	case "1", "true", "yes", "on":
		return true
	case "0", "false", "no", "off":
		return false
	default:
		return def
	}
}
