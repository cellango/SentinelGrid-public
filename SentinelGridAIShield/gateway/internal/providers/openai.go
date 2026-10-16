package providers

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"time"

	"sentinelgrid-ai-shield/gateway/pkg/types"
)

type OpenAIProvider struct {
	baseURL    string
	client     *http.Client
	keyFetcher *KeyFetcherService
}

func NewOpenAIProvider(keyFetcher *KeyFetcherService) *OpenAIProvider {
	baseURL := os.Getenv("OPENAI_BASE_URL")
	if baseURL == "" {
		baseURL = "https://api.openai.com/v1"
	}

	return &OpenAIProvider{
		baseURL:    baseURL,
		client:     &http.Client{Timeout: 120 * time.Second},
		keyFetcher: keyFetcher,
	}
}

func (p *OpenAIProvider) Name() string {
	return "openai"
}

func (p *OpenAIProvider) ChatCompletion(ctx context.Context, req *types.ChatCompletionRequest, orgID string) (*types.ChatCompletionResponse, error) {
	// Fetch API key from customer's vault
	apiKey, err := p.keyFetcher.FetchProviderKey(ctx, orgID, "openai")
	if err != nil {
		return nil, fmt.Errorf("failed to fetch OpenAI key: %w", err)
	}

	data, err := json.Marshal(req)
	if err != nil {
		return nil, err
	}

	url := fmt.Sprintf("%s/chat/completions", p.baseURL)
	httpReq, err := http.NewRequestWithContext(ctx, "POST", url, bytes.NewReader(data))
	if err != nil {
		return nil, err
	}

	httpReq.Header.Set("Content-Type", "application/json")
	httpReq.Header.Set("Authorization", fmt.Sprintf("Bearer %s", apiKey))

	resp, err := p.client.Do(httpReq)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 400 {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("OpenAI error: %s", string(body))
	}

	var result types.ChatCompletionResponse
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, err
	}

	return &result, nil
}

func (p *OpenAIProvider) Completion(ctx context.Context, req *types.CompletionRequest, orgID string) (*types.CompletionResponse, error) {
	// Fetch API key from customer's vault
	apiKey, err := p.keyFetcher.FetchProviderKey(ctx, orgID, "openai")
	if err != nil {
		return nil, fmt.Errorf("failed to fetch OpenAI key: %w", err)
	}

	data, err := json.Marshal(req)
	if err != nil {
		return nil, err
	}

	url := fmt.Sprintf("%s/completions", p.baseURL)
	httpReq, err := http.NewRequestWithContext(ctx, "POST", url, bytes.NewReader(data))
	if err != nil {
		return nil, err
	}

	httpReq.Header.Set("Content-Type", "application/json")
	httpReq.Header.Set("Authorization", fmt.Sprintf("Bearer %s", apiKey))

	resp, err := p.client.Do(httpReq)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var result types.CompletionResponse
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, err
	}

	return &result, nil
}

func (p *OpenAIProvider) Embeddings(ctx context.Context, req *types.EmbeddingRequest, orgID string) (*types.EmbeddingResponse, error) {
	// Fetch API key from customer's vault
	apiKey, err := p.keyFetcher.FetchProviderKey(ctx, orgID, "openai")
	if err != nil {
		return nil, fmt.Errorf("failed to fetch OpenAI key: %w", err)
	}

	data, err := json.Marshal(req)
	if err != nil {
		return nil, err
	}

	url := fmt.Sprintf("%s/embeddings", p.baseURL)
	httpReq, err := http.NewRequestWithContext(ctx, "POST", url, bytes.NewReader(data))
	if err != nil {
		return nil, err
	}

	httpReq.Header.Set("Content-Type", "application/json")
	httpReq.Header.Set("Authorization", fmt.Sprintf("Bearer %s", apiKey))

	resp, err := p.client.Do(httpReq)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var result types.EmbeddingResponse
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, err
	}

	return &result, nil
}

