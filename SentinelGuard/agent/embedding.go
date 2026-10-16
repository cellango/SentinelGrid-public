package agent

import (
	"bytes"
	"encoding/json"
	"log"
	"net/http"
	"strings"
	"time"
)

// embedSender is a lightweight hook to forward summarized events for embeddings.
type embedSender struct {
	url    string
	client *http.Client
}

func (e *embedSender) sendAsync(events []map[string]interface{}) {
	summaries := make([]map[string]interface{}, 0, len(events))
	for _, evt := range events {
		summaries = append(summaries, map[string]interface{}{
			"summary": summarize(evt),
			"time":    time.Now().UTC().Format(time.RFC3339Nano),
		})
	}
	go e.post(summaries)
}

func (e *embedSender) post(payload interface{}) {
	body, err := json.Marshal(payload)
	if err != nil {
		return
	}
	req, err := http.NewRequest(http.MethodPost, e.url, bytes.NewReader(body))
	if err != nil {
		return
	}
	req.Header.Set("Content-Type", "application/json")
	resp, err := e.client.Do(req)
	if err != nil {
		log.Printf("warn: embedding send failed: %v", err)
		return
	}
	resp.Body.Close()
	if resp.StatusCode >= 300 {
		log.Printf("warn: embedding service returned %d", resp.StatusCode)
	}
}

func summarize(evt map[string]interface{}) string {
	var parts []string
	if v, ok := lookupString(evt, "rule.name"); ok {
		parts = append(parts, v)
	}
	if v, ok := lookupString(evt, "event.action"); ok {
		parts = append(parts, v)
	}
	if v, ok := lookupString(evt, "process.name"); ok {
		parts = append(parts, "process="+v)
	}
	if v, ok := lookupString(evt, "file.path"); ok {
		parts = append(parts, "file="+v)
	}
	if len(parts) == 0 {
		return "sentinelguard event"
	}
	return strings.Join(parts, " | ")
}

func lookupString(evt map[string]interface{}, path string) (string, bool) {
	parts := strings.Split(path, ".")
	curr := evt
	for i, p := range parts {
		val, ok := curr[p]
		if !ok {
			return "", false
		}
		if i == len(parts)-1 {
			if s, ok := val.(string); ok && s != "" {
				return s, true
			}
			return "", false
		}
		next, ok := val.(map[string]interface{})
		if !ok {
			return "", false
		}
		curr = next
	}
	return "", false
}
