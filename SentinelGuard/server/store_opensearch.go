package server

import (
	"bytes"
	"context"
	"crypto/tls"
	"crypto/sha1" // #nosec G505
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"strings"
	"time"

	opensearch "github.com/opensearch-project/opensearch-go/v2"
)

// OpenSearchStore persists events into an OpenSearch index using the bulk API.
type OpenSearchStore struct {
	client *opensearch.Client
	index  string
	max    int
}

func NewOpenSearchStore(cfg OpenSearchConfig) (*OpenSearchStore, error) {
	if len(cfg.Addresses) == 0 {
		return nil, errors.New("opensearch address is required")
	}

	httpClient := &http.Client{
		Transport: &http.Transport{
			TLSClientConfig: &tls.Config{InsecureSkipVerify: cfg.InsecureSkipVerify}, // #nosec G402
		},
		Timeout: cfg.Timeout,
	}

	client, err := opensearch.NewClient(opensearch.Config{
		Addresses: cfg.Addresses,
		Username:  cfg.Username,
		Password:  cfg.Password,
		Transport: httpClient.Transport,
	})
	if err != nil {
		return nil, fmt.Errorf("opensearch client init: %w", err)
	}

	return &OpenSearchStore{
		client: client,
		index:  cfg.Index,
		max:    cfg.MaxBatchSize,
	}, nil
}

func (s *OpenSearchStore) SaveBatch(ctx context.Context, tenantID, agentID string, events []map[string]interface{}) error {
	if len(events) == 0 {
		return nil
	}
	if s.max > 0 && len(events) > s.max {
		return fmt.Errorf("batch too large: %d (max %d)", len(events), s.max)
	}

	var buf bytes.Buffer
	now := time.Now().UTC().Format(time.RFC3339Nano)

	for _, evt := range events {
		ensureField(evt, "organization.id", tenantID)
		ensureField(evt, "agent.id", agentID)
		ensureField(evt, "agent.type", "sentinelguard")
		if _, ok := evt["@timestamp"]; !ok {
			evt["@timestamp"] = now
		}
		id := deterministicID(tenantID, agentID, evt)
		meta := map[string]map[string]string{"index": {"_index": s.index, "_id": id}}
		if err := writeJSONLine(&buf, meta); err != nil {
			return err
		}
		if err := writeJSONLine(&buf, evt); err != nil {
			return err
		}
	}

	resp, err := s.client.Bulk(bytes.NewReader(buf.Bytes()), s.client.Bulk.WithContext(ctx))
	if err != nil {
		return fmt.Errorf("opensearch bulk: %w", err)
	}
	defer resp.Body.Close()

	if resp.IsError() {
		return fmt.Errorf("opensearch bulk response error: %s", resp.String())
	}

	var bulkResp struct {
		Errors bool `json:"errors"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&bulkResp); err != nil {
		return fmt.Errorf("decode bulk response: %w", err)
	}
	if bulkResp.Errors {
		return errors.New("opensearch bulk reported item errors")
	}
	return nil
}

func (s *OpenSearchStore) Health() error {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	resp, err := s.client.Cluster.Health(
		s.client.Cluster.Health.WithContext(ctx),
	)
	if err != nil {
		return fmt.Errorf("opensearch health: %w", err)
	}
	defer resp.Body.Close()
	if resp.IsError() {
		return fmt.Errorf("opensearch cluster health error: %s", resp.String())
	}
	return nil
}

func writeJSONLine(buf *bytes.Buffer, v interface{}) error {
	b, err := json.Marshal(v)
	if err != nil {
		return fmt.Errorf("marshal bulk item: %w", err)
	}
	if _, err := buf.Write(b); err != nil {
		return fmt.Errorf("write bulk item: %w", err)
	}
	if err := buf.WriteByte('\n'); err != nil {
		return fmt.Errorf("write bulk newline: %w", err)
	}
	return nil
}

// ensureField sets a dotted path inside a map, creating intermediate maps when needed.
func ensureField(dst map[string]interface{}, path string, value interface{}) {
	parts := strings.Split(path, ".")
	curr := dst
	for i, p := range parts {
		if i == len(parts)-1 {
			curr[p] = value
			return
		}
		next, ok := curr[p].(map[string]interface{})
		if !ok {
			next = make(map[string]interface{})
			curr[p] = next
		}
		curr = next
	}
}

func deterministicID(tenantID, agentID string, evt map[string]interface{}) string {
	hostID := stringValue(evt, "host.id")
	ruleID := stringValue(evt, "rule.id")
	action := stringValue(evt, "event.action")
	ts := fmt.Sprintf("%v", evt["@timestamp"])
	parts := []string{tenantID, agentID, hostID, ruleID, action, ts}
	h := sha1.Sum([]byte(strings.Join(parts, "|"))) // #nosec G401
	return fmt.Sprintf("%x", h[:])
}

func stringValue(evt map[string]interface{}, path string) string {
	parts := strings.Split(path, ".")
	curr := evt
	for i, p := range parts {
		val, ok := curr[p]
		if !ok {
			return ""
		}
		if i == len(parts)-1 {
			if s, ok := val.(string); ok {
				return s
			}
			return ""
		}
		next, ok := val.(map[string]interface{})
		if !ok {
			return ""
		}
		curr = next
	}
	return ""
}
