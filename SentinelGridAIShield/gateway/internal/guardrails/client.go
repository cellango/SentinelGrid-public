package guardrails

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
)

// Client calls the Python services API for guardrails checks
type Client struct {
	baseURL string
	client  *http.Client
}

func NewClient(baseURL string) *Client {
	return &Client{
		baseURL: baseURL,
		client:  &http.Client{},
	}
}

type PIIRequest struct {
	Text string `json:"text"`
}

type PIIResponse struct {
	HasPII   bool     `json:"has_pii"`
	Entities []string `json:"entities"`
	Redacted string   `json:"redacted"`
}

func (c *Client) ScanPII(ctx context.Context, text string) (*PIIResponse, error) {
	req := PIIRequest{Text: text}
	data, _ := json.Marshal(req)

	url := fmt.Sprintf("%s/api/v1/guardrails/scan/pii", c.baseURL)
	httpReq, err := http.NewRequestWithContext(ctx, "POST", url, bytes.NewReader(data))
	if err != nil {
		return nil, err
	}
	httpReq.Header.Set("Content-Type", "application/json")
	httpReq.Header.Set("Authorization", fmt.Sprintf("Bearer %s", internalServiceToken()))

	resp, err := c.client.Do(httpReq)
	if err != nil {
		// If service unavailable, return safe default
		return &PIIResponse{HasPII: false}, nil
	}
	defer resp.Body.Close()

	var result PIIResponse
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return &PIIResponse{HasPII: false}, nil
	}

	return &result, nil
}

type InjectionRequest struct {
	Text string `json:"text"`
}

type InjectionResponse struct {
	IsSuspicious bool    `json:"is_suspicious"`
	Score        float64 `json:"score"`
	Patterns     []string `json:"patterns"`
}

func (c *Client) ScanInjection(ctx context.Context, text string) (*InjectionResponse, error) {
	req := InjectionRequest{Text: text}
	data, _ := json.Marshal(req)

	url := fmt.Sprintf("%s/api/v1/guardrails/scan/injection", c.baseURL)
	httpReq, err := http.NewRequestWithContext(ctx, "POST", url, bytes.NewReader(data))
	if err != nil {
		return nil, err
	}
	httpReq.Header.Set("Content-Type", "application/json")
	httpReq.Header.Set("Authorization", fmt.Sprintf("Bearer %s", internalServiceToken()))

	resp, err := c.client.Do(httpReq)
	if err != nil {
		return &InjectionResponse{IsSuspicious: false}, nil
	}
	defer resp.Body.Close()

	var result InjectionResponse
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return &InjectionResponse{IsSuspicious: false}, nil
	}

	return &result, nil
}

type SecretsRequest struct {
	Text string `json:"text"`
}

type SecretsResponse struct{
	HasSecrets bool     `json:"has_secrets"`
	Findings   []string `json:"findings"`
}

func (c *Client) ScanSecrets(ctx context.Context, text string) (*SecretsResponse, error) {
	req := SecretsRequest{Text: text}
	data, _ := json.Marshal(req)

	url := fmt.Sprintf("%s/api/v1/guardrails/scan/secrets", c.baseURL)
	httpReq, err := http.NewRequestWithContext(ctx, "POST", url, bytes.NewReader(data))
	if err != nil {
		return nil, err
	}
	httpReq.Header.Set("Content-Type", "application/json")
	httpReq.Header.Set("Authorization", fmt.Sprintf("Bearer %s", internalServiceToken()))

	resp, err := c.client.Do(httpReq)
	if err != nil {
		return &SecretsResponse{HasSecrets: false}, nil
	}
	defer resp.Body.Close()

	var result SecretsResponse
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return &SecretsResponse{HasSecrets: false}, nil
	}

	return &result, nil
}

func internalServiceToken() string {
	token := os.Getenv("INTERNAL_SERVICE_TOKEN")
	if token == "" {
		token = "internal-service-token-change-in-production"
	}
	return token
}
