package server

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestIngestWithTenantPersists(t *testing.T) {
	store := NewInMemoryStore()
	router := Router(store, RouterConfig{MaxBatchEvents: 10}, EmbeddingConfig{})

	payload := map[string]interface{}{
		"tenant_id": "tenant-123",
		"agent_id":  "agent-abc",
		"events": []map[string]interface{}{
			{"@timestamp": "2024-01-01T00:00:00Z", "event": map[string]interface{}{"type": "test"}},
		},
	}
	body, _ := json.Marshal(payload)
	req := httptest.NewRequest(http.MethodPost, "/ingest", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")

	rr := httptest.NewRecorder()
	router.ServeHTTP(rr, req)

	if rr.Code != http.StatusAccepted {
		t.Fatalf("expected 202, got %d, body=%s", rr.Code, rr.Body.String())
	}

	// Verify the data is persisted in the in-memory store
	store.mu.Lock()
	defer store.mu.Unlock()
	key := "tenant-123::agent-abc"
	events := store.data[key]
	if len(events) != 1 {
		t.Fatalf("expected 1 event stored, got %d", len(events))
	}
	if events[0]["@timestamp"] != "2024-01-01T00:00:00Z" {
		t.Fatalf("unexpected event content: %+v", events[0])
	}
}

func TestIngestOpenEDRAddsSourceAndSidecar(t *testing.T) {
	store := NewInMemoryStore()
	router := Router(store, RouterConfig{}, EmbeddingConfig{})

	payload := map[string]interface{}{
		"tenant_id": "tenant-123",
		"agent_id":  "agent-abc",
		"events": []map[string]interface{}{
			{"@timestamp": "2024-01-01T00:00:00Z", "event": map[string]interface{}{"type": "process"}},
		},
	}
	body, _ := json.Marshal(payload)
	req := httptest.NewRequest(http.MethodPost, "/ingest/openedr", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")

	rr := httptest.NewRecorder()
	router.ServeHTTP(rr, req)

	if rr.Code != http.StatusAccepted {
		t.Fatalf("expected 202, got %d, body=%s", rr.Code, rr.Body.String())
	}

	store.mu.Lock()
	defer store.mu.Unlock()
	key := "tenant-123::agent-abc"
	events := store.data[key]
	if len(events) != 1 {
		t.Fatalf("expected 1 event stored, got %d", len(events))
	}
	if got := events[0]["edr_source"]; got != "sentinelguard-openedr" {
		t.Fatalf("expected edr_source sentinelguard-openedr, got %v", got)
	}
	if got := events[0]["sidecar_enabled"]; got != true {
		t.Fatalf("expected sidecar_enabled true, got %v", got)
	}
}

func TestIngestVelociraptorAddsSourceAndSidecar(t *testing.T) {
	store := NewInMemoryStore()
	router := Router(store, RouterConfig{}, EmbeddingConfig{})

	payload := map[string]interface{}{
		"tenant_id": "tenant-789",
		"agent_id":  "agent-hunt",
		"events": []map[string]interface{}{
			{"@timestamp": "2024-01-01T00:00:00Z", "event": map[string]interface{}{"type": "hunt"}},
		},
	}
	body, _ := json.Marshal(payload)
	req := httptest.NewRequest(http.MethodPost, "/ingest/velociraptor", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")

	rr := httptest.NewRecorder()
	router.ServeHTTP(rr, req)

	if rr.Code != http.StatusAccepted {
		t.Fatalf("expected 202, got %d, body=%s", rr.Code, rr.Body.String())
	}

	store.mu.Lock()
	defer store.mu.Unlock()
	key := "tenant-789::agent-hunt"
	events := store.data[key]
	if len(events) != 1 {
		t.Fatalf("expected 1 event stored, got %d", len(events))
	}
	if got := events[0]["edr_source"]; got != "sentinelguard-velociraptor" {
		t.Fatalf("expected edr_source sentinelguard-velociraptor, got %v", got)
	}
	if got := events[0]["sidecar_enabled"]; got != true {
		t.Fatalf("expected sidecar_enabled true, got %v", got)
	}
}

func TestIngestAuthAndTenantAllowlist(t *testing.T) {
	store := NewInMemoryStore()
	router := Router(store, RouterConfig{
		BearerToken:    "secret",
		AllowedTenants: map[string]struct{}{"tenant-allowed": {}},
		MaxBatchEvents: 5,
	}, EmbeddingConfig{})

	payload := map[string]interface{}{
		"tenant_id": "tenant-allowed",
		"agent_id":  "agent-abc",
		"events":    []map[string]interface{}{{"@timestamp": "2024-01-01T00:00:00Z"}},
	}
	body, _ := json.Marshal(payload)
	req := httptest.NewRequest(http.MethodPost, "/ingest", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer secret")
	rr := httptest.NewRecorder()
	router.ServeHTTP(rr, req)

	if rr.Code != http.StatusAccepted {
		t.Fatalf("expected 202, got %d", rr.Code)
	}

	req2 := httptest.NewRequest(http.MethodPost, "/ingest", bytes.NewReader(body))
	req2.Header.Set("Content-Type", "application/json")
	rr2 := httptest.NewRecorder()
	router.ServeHTTP(rr2, req2)
	if rr2.Code != http.StatusUnauthorized {
		t.Fatalf("expected 401 when auth missing, got %d", rr2.Code)
	}

	payload["tenant_id"] = "tenant-blocked"
	body, _ = json.Marshal(payload)
	req3 := httptest.NewRequest(http.MethodPost, "/ingest", bytes.NewReader(body))
	req3.Header.Set("Content-Type", "application/json")
	req3.Header.Set("Authorization", "Bearer secret")
	rr3 := httptest.NewRecorder()
	router.ServeHTTP(rr3, req3)
	if rr3.Code != http.StatusForbidden {
		t.Fatalf("expected 403 for blocked tenant, got %d", rr3.Code)
	}
}

func TestIngestRejectsLargeBatch(t *testing.T) {
	store := NewInMemoryStore()
	router := Router(store, RouterConfig{MaxBatchEvents: 1}, EmbeddingConfig{})

	payload := map[string]interface{}{
		"tenant_id": "tenant-123",
		"agent_id":  "agent-abc",
		"events": []map[string]interface{}{
			{"@timestamp": "2024-01-01T00:00:00Z"},
			{"@timestamp": "2024-01-01T00:00:01Z"},
		},
	}
	body, _ := json.Marshal(payload)
	req := httptest.NewRequest(http.MethodPost, "/ingest", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	rr := httptest.NewRecorder()
	router.ServeHTTP(rr, req)

	if rr.Code != http.StatusRequestEntityTooLarge {
		t.Fatalf("expected 413, got %d", rr.Code)
	}
}
