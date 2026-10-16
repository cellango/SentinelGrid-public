package agent

import (
	"bytes"
	"context"
	"crypto/tls"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
)

// Batch mirrors the ingest payload expected by the server.
type Batch struct {
	TenantID string                   `json:"tenant_id"`
	AgentID  string                   `json:"agent_id"`
	Events   []map[string]interface{} `json:"events"`
}

// Agent wraps ingestion, buffering, and optional embedding fan-out.
type Agent struct {
	cfg        Config
	client     *http.Client
	queue      *diskQueue
	embedSender *embedSender
}

func NewAgent(cfg Config) (*Agent, error) {
	queue, err := newDiskQueue(cfg.BufferDir)
	if err != nil {
		return nil, err
	}

	httpClient := &http.Client{
		Transport: &http.Transport{
			TLSClientConfig: &tls.Config{InsecureSkipVerify: cfg.SkipTLSVerify}, // #nosec G402
		},
		Timeout: cfg.RequestTimeout,
	}

	var es *embedSender
	if cfg.EmbeddingURL != "" {
		es = &embedSender{
			url:    cfg.EmbeddingURL,
			client: httpClient,
		}
	}

	return &Agent{
		cfg:        cfg,
		client:     httpClient,
		queue:      queue,
		embedSender: es,
	}, nil
}

// Run reads Wazuh alerts, maps to ECS, retries any buffered batches, and ships to ingest.
func (a *Agent) Run(ctx context.Context) error {
	if !a.cfg.Sidecars.Wazuh.Enabled {
		log.Printf("wazuh sidecar disabled; skipping Wazuh alert ingestion")
		return nil
	}
	if err := a.retryBuffered(ctx); err != nil {
		log.Printf("warn: retry buffered failed: %v", err)
	}

	events, err := readWazuhAlerts(a.cfg.WazuhAlertPath, a.cfg.MaxEventBytes, a.cfg.TenantID, a.cfg.AgentID)
	if err != nil {
		return fmt.Errorf("read wazuh alerts: %w", err)
	}
	if len(events) == 0 {
		log.Printf("no events read from %s", a.cfg.WazuhAlertPath)
		return nil
	}

	batches := splitIntoBatches(events, a.cfg.BatchSize)
	for _, evts := range batches {
		batch := Batch{
			TenantID: a.cfg.TenantID,
			AgentID:  a.cfg.AgentID,
			Events:   evts,
		}
		if err := a.sendBatch(ctx, batch); err != nil {
			log.Printf("ingest failed, buffering batch (%d events): %v", len(evts), err)
			if err := a.queue.enqueue(batch); err != nil {
				return fmt.Errorf("buffer batch: %w", err)
			}
		} else if a.embedSender != nil {
			a.embedSender.sendAsync(evts)
		}
	}
	return nil
}

func (a *Agent) retryBuffered(ctx context.Context) error {
	pending, err := a.queue.list()
	if err != nil {
		return err
	}
	for _, item := range pending {
		if err := a.sendBatch(ctx, item.Batch); err != nil {
			return fmt.Errorf("retry buffered batch %s: %w", item.Path, err)
		}
		if err := a.queue.delete(item.Path); err != nil {
			log.Printf("warn: failed to delete buffered batch %s: %v", item.Path, err)
		}
	}
	return nil
}

func (a *Agent) sendBatch(ctx context.Context, batch Batch) error {
	body := new(bytes.Buffer)
	if err := json.NewEncoder(body).Encode(batch); err != nil {
		return fmt.Errorf("encode batch: %w", err)
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, a.cfg.IngestURL, body)
	if err != nil {
		return fmt.Errorf("create request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")
	if a.cfg.AuthToken != "" {
		req.Header.Set("Authorization", "Bearer "+a.cfg.AuthToken)
	}

	resp, err := a.client.Do(req)
	if err != nil {
		return fmt.Errorf("post ingest: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		b, _ := io.ReadAll(io.LimitReader(resp.Body, 2048))
		return fmt.Errorf("ingest returned %d: %s", resp.StatusCode, string(b))
	}
	return nil
}

func splitIntoBatches(events []map[string]interface{}, batchSize int) [][]map[string]interface{} {
	if batchSize <= 0 {
		return [][]map[string]interface{}{events}
	}
	var result [][]map[string]interface{}
	for i := 0; i < len(events); i += batchSize {
		end := i + batchSize
		if end > len(events) {
			end = len(events)
		}
		result = append(result, events[i:end])
	}
	return result
}
