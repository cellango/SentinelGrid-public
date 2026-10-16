package server

import (
	"bytes"
	"encoding/json"
	"log"
	"net/http"
	"time"

	"sentinelguard/rationalizer"
)

// embedClient sends summaries to the embedding service.
type embedClient struct {
	url    string
	client *http.Client
}

func newEmbedClient(cfg EmbeddingConfig) *embedClient {
	if cfg.URL == "" {
		return nil
	}
	return &embedClient{
		url: cfg.URL,
		client: &http.Client{
			Timeout: 5 * time.Second,
		},
	}
}

func (c *embedClient) send(summaries []rationalizer.Summary) {
	if c == nil || len(summaries) == 0 {
		return
	}
	body, err := json.Marshal(summaries)
	if err != nil {
		log.Printf("embedding marshal error: %v", err)
		return
	}
	req, err := http.NewRequest(http.MethodPost, c.url, bytes.NewReader(body))
	if err != nil {
		log.Printf("embedding request build error: %v", err)
		return
	}
	req.Header.Set("Content-Type", "application/json")
	resp, err := c.client.Do(req)
	if err != nil {
		log.Printf("embedding send error: %v", err)
		return
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 300 {
		log.Printf("embedding service returned %d", resp.StatusCode)
	}
}
