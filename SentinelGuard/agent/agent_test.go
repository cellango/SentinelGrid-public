package agent

import (
	"context"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"
)

type fakeEmbedSender struct {
	sent [][]map[string]interface{}
}

func (f *fakeEmbedSender) sendAsync(events []map[string]interface{}) {
	f.sent = append(f.sent, events)
}

// wire agent with injected queue/client/embedSender for testing sendBatch behavior
func TestAgentSendBatchSuccess(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			t.Fatalf("expected POST, got %s", r.Method)
		}
		w.WriteHeader(http.StatusAccepted)
	}))
	defer srv.Close()

	cfg := Config{
		TenantID:    "tenant-1",
		AgentID:     "agent-1",
		IngestURL:   srv.URL,
		AuthToken:   "token",
		BufferDir:   t.TempDir(),
		RequestTimeout: 5 * time.Second,
		Sidecars: SidecarConfig{
			Wazuh: SidecarSettings{Enabled: true},
		},
	}

	a, err := NewAgent(cfg)
	if err != nil {
		t.Fatalf("new agent: %v", err)
	}

	batch := Batch{
		TenantID: "tenant-1",
		AgentID:  "agent-1",
		Events:   []map[string]interface{}{{"foo": "bar"}},
	}
	if err := a.sendBatch(context.Background(), batch); err != nil {
		t.Fatalf("sendBatch failed: %v", err)
	}
}

func TestSplitIntoBatches(t *testing.T) {
	events := []map[string]interface{}{
		{"id": 1}, {"id": 2}, {"id": 3},
	}
	batches := splitIntoBatches(events, 2)
	if len(batches) != 2 {
		t.Fatalf("expected 2 batches, got %d", len(batches))
	}
	if len(batches[0]) != 2 || len(batches[1]) != 1 {
		t.Fatalf("unexpected batch sizes: %#v", batches)
	}
}

func TestSendBatchHTTPErrorBuffers(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		http.Error(w, "boom", http.StatusBadRequest)
	}))
	defer srv.Close()

	cfg := Config{
		TenantID:    "tenant-1",
		AgentID:     "agent-1",
		IngestURL:   srv.URL,
		BufferDir:   t.TempDir(),
		Sidecars: SidecarConfig{Wazuh: SidecarSettings{Enabled: true}},
	}
	a, err := NewAgent(cfg)
	if err != nil {
		t.Fatalf("new agent: %v", err)
	}

	err = a.Run(context.Background())
	if err == nil {
		t.Fatalf("expected error due to missing wazuh alerts file")
	}

	// Directly exercise sendBatch with bad response
	batch := Batch{
		TenantID: "tenant-1",
		AgentID:  "agent-1",
		Events:   []map[string]interface{}{{"foo": "bar"}},
	}
	if err := a.sendBatch(context.Background(), batch); err == nil {
		t.Fatalf("expected sendBatch error from 400 response")
	}
}

// Ensure Wazuh disabled short-circuits Run without error.
func TestRunSkipsWhenWazuhDisabled(t *testing.T) {
	cfg := Config{
		BufferDir: t.TempDir(),
		Sidecars: SidecarConfig{Wazuh: SidecarSettings{Enabled: false}},
	}
	a, err := NewAgent(cfg)
	if err != nil {
		t.Fatalf("new agent: %v", err)
	}
	if err := a.Run(context.Background()); err != nil {
		t.Fatalf("expected nil when wazuh disabled, got %v", err)
	}
}
