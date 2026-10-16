package providers

import (
	"context"
	"fmt"

	"sentinelgrid-ai-shield/gateway/pkg/types"
)

type AnthropicProvider struct {
}

func NewAnthropicProvider() *AnthropicProvider {
	return &AnthropicProvider{}
}

func (p *AnthropicProvider) Name() string {
	return "anthropic"
}

func (p *AnthropicProvider) ChatCompletion(ctx context.Context, req *types.ChatCompletionRequest, orgID string) (*types.ChatCompletionResponse, error) {
	model := ""
	if req != nil {
		model = req.Model
	}
	return nil, launchUnsupportedProviderError(p.Name(), model)
}

func (p *AnthropicProvider) Completion(ctx context.Context, req *types.CompletionRequest, orgID string) (*types.CompletionResponse, error) {
	return nil, fmt.Errorf("anthropic provider does not support completions")
}

func (p *AnthropicProvider) Embeddings(ctx context.Context, req *types.EmbeddingRequest, orgID string) (*types.EmbeddingResponse, error) {
	return nil, fmt.Errorf("anthropic provider does not support embeddings")
}
