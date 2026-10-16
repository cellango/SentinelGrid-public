package server

import (
	"os"
	"strconv"
	"strings"
	"time"
)

// RouterConfig controls HTTP handler behavior such as auth and limits.
type RouterConfig struct {
	BearerToken      string
	AllowedTenants   map[string]struct{}
	MaxBatchEvents   int
	MaxBodyBytes     int64
	RequestTimeout   time.Duration
	DisableAuthCheck bool
}

// OpenSearchConfig holds connection details for the OpenSearch-backed store.
type OpenSearchConfig struct {
	Addresses          []string
	Username           string
	Password           string
	Index              string
	InsecureSkipVerify bool
	Timeout            time.Duration
	MaxBatchSize       int
}

// EmbeddingConfig controls optional embedding fan-out.
type EmbeddingConfig struct {
	URL               string
	SeverityMin       int
	Categories        []string
	CategoryAllowlist map[string]struct{}
	DedupeWindowSecs  int
	TruncateMessage   int
	TruncateCommand   int
}

// ServerConfig bundles routing and storage configuration.
type ServerConfig struct {
	Router     RouterConfig
	StoreKind  string // "opensearch" (default) or "memory"
	OpenSearch OpenSearchConfig
	Embedding  EmbeddingConfig
}

// LoadServerConfigFromEnv builds ServerConfig from environment variables with sane defaults.
func LoadServerConfigFromEnv() ServerConfig {
	storeKind := strings.ToLower(getenv("EDR_STORE", "opensearch"))

	router := RouterConfig{
		BearerToken:    os.Getenv("INGEST_BEARER_TOKEN"),
		AllowedTenants: parseAllowedTenants(os.Getenv("TENANT_ALLOWLIST")),
		MaxBatchEvents: atoiDefault(os.Getenv("MAX_EVENTS_PER_BATCH"), 500),
		MaxBodyBytes:   int64(atoiDefault(os.Getenv("MAX_BODY_BYTES"), 5*1024*1024)), // 5MB
		RequestTimeout: time.Duration(atoiDefault(os.Getenv("INGEST_REQUEST_TIMEOUT_SECONDS"), 10)) * time.Second,
	}

	openSearch := OpenSearchConfig{
		Addresses:          parseAddresses(getenv("OPENSEARCH_URLS", getenv("OPENSEARCH_URL", "http://localhost:9200"))),
		Username:           os.Getenv("OPENSEARCH_USERNAME"),
		Password:           os.Getenv("OPENSEARCH_PASSWORD"),
		Index:              getenv("OPENSEARCH_INDEX", "sentinelguard-events"),
		InsecureSkipVerify: strings.ToLower(os.Getenv("OPENSEARCH_INSECURE_SKIP_VERIFY")) == "true",
		Timeout:            time.Duration(atoiDefault(os.Getenv("OPENSEARCH_TIMEOUT_SECONDS"), 5)) * time.Second,
		MaxBatchSize:       atoiDefault(os.Getenv("OPENSEARCH_MAX_BATCH_SIZE"), 1000),
	}

	embedding := EmbeddingConfig{
		URL:              os.Getenv("EMBEDDING_URL"),
		SeverityMin:      atoiDefault(os.Getenv("EMBEDDING_SEVERITY_MIN"), 50), // ECS severity 0-100
		DedupeWindowSecs: atoiDefault(os.Getenv("EMBEDDING_DEDUPE_WINDOW_SECS"), 600),
		TruncateMessage:  atoiDefault(os.Getenv("EMBEDDING_TRUNCATE_MESSAGE"), 512),
		TruncateCommand:  atoiDefault(os.Getenv("EMBEDDING_TRUNCATE_COMMAND"), 512),
	}
	if raw := os.Getenv("EMBEDDING_CATEGORIES"); raw != "" {
		embedding.Categories = parseList(raw)
		embedding.CategoryAllowlist = make(map[string]struct{}, len(embedding.Categories))
		for _, c := range embedding.Categories {
			embedding.CategoryAllowlist[c] = struct{}{}
		}
	}

	return ServerConfig{
		Router:     router,
		StoreKind:  storeKind,
		OpenSearch: openSearch,
		Embedding:  embedding,
	}
}

func parseAllowedTenants(raw string) map[string]struct{} {
	if raw == "" {
		return nil
	}
	items := strings.Split(raw, ",")
	result := make(map[string]struct{}, len(items))
	for _, item := range items {
		val := strings.TrimSpace(item)
		if val != "" {
			result[val] = struct{}{}
		}
	}
	return result
}

func parseAddresses(raw string) []string {
	parts := strings.Split(raw, ",")
	addresses := make([]string, 0, len(parts))
	for _, p := range parts {
		if trimmed := strings.TrimSpace(p); trimmed != "" {
			addresses = append(addresses, trimmed)
		}
	}
	return addresses
}

func parseList(raw string) []string {
	parts := strings.Split(raw, ",")
	out := make([]string, 0, len(parts))
	for _, p := range parts {
		if v := strings.TrimSpace(p); v != "" {
			out = append(out, v)
		}
	}
	return out
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
