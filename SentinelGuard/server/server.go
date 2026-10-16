package server

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"net/http"
	"strings"
	"sync"

	"github.com/go-chi/chi/v5"

	"sentinelguard/rationalizer"
)

// IngestRequest represents a batch sent from an endpoint agent.
type IngestRequest struct {
	TenantID        string                   `json:"tenant_id"`
	AgentID         string                   `json:"agent_id"`
	Events          []map[string]interface{} `json:"events"`
	EDRSource       string                   `json:"edr_source,omitempty"`
	SidecarEnabled  *bool                    `json:"sidecar_enabled,omitempty"`
}

// Store abstracts persistence (e.g., OpenSearch). Makes testing easy.
type Store interface {
	SaveBatch(ctx context.Context, tenantID, agentID string, events []map[string]interface{}) error
	Health() error
}

// InMemoryStore is a simple map-backed store for tests/dev.
type InMemoryStore struct {
	mu   sync.Mutex
	data map[string][]map[string]interface{}
}

func NewInMemoryStore() *InMemoryStore {
	return &InMemoryStore{data: make(map[string][]map[string]interface{})}
}

func (s *InMemoryStore) SaveBatch(_ context.Context, tenantID, agentID string, events []map[string]interface{}) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	key := tenantID + "::" + agentID
	s.data[key] = append(s.data[key], events...)
	return nil
}

func (s *InMemoryStore) Health() error { return nil }

// NewStoreFromConfig instantiates the requested store implementation.
func NewStoreFromConfig(cfg ServerConfig) (Store, error) {
	switch strings.ToLower(cfg.StoreKind) {
	case "memory":
		return NewInMemoryStore(), nil
	case "", "opensearch":
		return NewOpenSearchStore(cfg.OpenSearch)
	default:
		return nil, fmt.Errorf("unknown store kind: %s", cfg.StoreKind)
	}
}

// Router builds the HTTP router with handlers using the provided Store.
func Router(store Store, cfg RouterConfig, embedCfg EmbeddingConfig) http.Handler {
	r := chi.NewRouter()
	embedder := newEmbedClient(embedCfg)

	r.Get("/health", func(w http.ResponseWriter, _ *http.Request) {
		if err := store.Health(); err != nil {
			http.Error(w, "store unhealthy", http.StatusServiceUnavailable)
			return
		}
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{"status":"ok","service":"sentinelguard-server"}`))
	})

	ingestHandler := func(defaultEDRSource string, defaultSidecar bool) http.HandlerFunc {
		return func(w http.ResponseWriter, r *http.Request) {
		if cfg.MaxBodyBytes > 0 {
			r.Body = http.MaxBytesReader(w, r.Body, cfg.MaxBodyBytes)
		}
		if cfg.BearerToken != "" {
			if !authorize(r.Header.Get("Authorization"), cfg.BearerToken) {
				http.Error(w, "unauthorized", http.StatusUnauthorized)
				return
			}
		}

		var req IngestRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			http.Error(w, "invalid JSON", http.StatusBadRequest)
			return
		}
		if req.EDRSource == "" {
			req.EDRSource = defaultEDRSource
		}
		if req.SidecarEnabled == nil && defaultSidecar {
			val := true
			req.SidecarEnabled = &val
		}
		if err := validateIngest(req); err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}
		if len(cfg.AllowedTenants) > 0 {
			if _, ok := cfg.AllowedTenants[req.TenantID]; !ok {
				http.Error(w, "tenant not allowed", http.StatusForbidden)
				return
			}
		}
		if cfg.MaxBatchEvents > 0 && len(req.Events) > cfg.MaxBatchEvents {
			http.Error(w, fmt.Sprintf("too many events; max %d", cfg.MaxBatchEvents), http.StatusRequestEntityTooLarge)
			return
		}

		// Dedupe/optimize before persistence.
		events, dropped := dedupeEvents(req.TenantID, req.AgentID, req.Events)
		if dropped > 0 {
			log.Printf("dedupe: dropped=%d retained=%d tenant=%s agent=%s", dropped, len(events), req.TenantID, req.AgentID)
		}

		// Optional request timeout guard for downstream store.
		var cancel func()
		if cfg.RequestTimeout > 0 {
			var ctx context.Context
			ctx, cancel = context.WithTimeout(r.Context(), cfg.RequestTimeout)
			r = r.WithContext(ctx)
		}
		if cancel != nil {
			defer cancel()
		}

		// Enrich events with edr_source/sidecar flags when provided
		if req.EDRSource != "" || req.SidecarEnabled != nil {
			for i := range events {
				if req.EDRSource != "" {
					if _, ok := events[i]["edr_source"]; !ok {
						events[i]["edr_source"] = req.EDRSource
					}
				}
				if req.SidecarEnabled != nil {
					if _, ok := events[i]["sidecar_enabled"]; !ok {
						events[i]["sidecar_enabled"] = *req.SidecarEnabled
					}
				}
			}
		}

		if err := store.SaveBatch(r.Context(), req.TenantID, req.AgentID, events); err != nil {
			log.Printf("save batch error: %v", err)
			http.Error(w, "failed to persist", http.StatusInternalServerError)
			return
		}
		log.Printf("ingested tenant=%s agent=%s events=%d payload=%v", req.TenantID, req.AgentID, len(events), events)

		// Fire-and-forget embedding summaries (if configured)
		if embedder != nil {
			summaries := rationalizer.Rationalize(req.Events, rationalizer.Config{
				SeverityMin:       embedCfg.SeverityMin,
				CategoryAllowlist: embedCfg.CategoryAllowlist,
				DedupeWindowSecs:  embedCfg.DedupeWindowSecs,
				TruncateMessage:   embedCfg.TruncateMessage,
				TruncateCommand:   embedCfg.TruncateCommand,
			}, rationalizer.Meta{
				TenantID: req.TenantID,
				AgentID:  req.AgentID,
				Source:   "sentinelguard",
			})
			go embedder.send(summaries)
		}

		w.WriteHeader(http.StatusAccepted)
		_, _ = w.Write([]byte(`{"status":"queued"}`))
		}
	}

	// Default ingest (agent-provided)
	r.Post("/ingest", ingestHandler("", false))
	// Sidecar-specific ingest paths set default edr_source and sidecar flag
	r.Post("/ingest/openedr", ingestHandler("sentinelguard-openedr", true))
	r.Post("/ingest/velociraptor", ingestHandler("sentinelguard-velociraptor", true))

	return r
}

func validateIngest(req IngestRequest) error {
	if req.TenantID == "" {
		return errors.New("tenant_id is required")
	}
	if req.AgentID == "" {
		return errors.New("agent_id is required")
	}
	if len(req.Events) == 0 {
		return errors.New("events is required")
	}
	return nil
}

func authorize(header, expectedToken string) bool {
	if header == "" {
		return false
	}
	const prefix = "Bearer "
	if strings.HasPrefix(header, prefix) {
		return strings.TrimSpace(strings.TrimPrefix(header, prefix)) == expectedToken
	}
	return strings.TrimSpace(header) == expectedToken
}

// dedupeEvents removes duplicate events in a batch based on a deterministic hash of tenant, agent, host, rule/action/timestamp.
func dedupeEvents(tenantID, agentID string, events []map[string]interface{}) ([]map[string]interface{}, int) {
	seen := make(map[string]struct{}, len(events))
	unique := make([]map[string]interface{}, 0, len(events))
	dropped := 0
	for _, evt := range events {
		id := deterministicID(tenantID, agentID, evt)
		if _, ok := seen[id]; ok {
			dropped++
			continue
		}
		seen[id] = struct{}{}
		unique = append(unique, evt)
	}
	return unique, dropped
}
