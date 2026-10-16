package providers

import (
	"context"
	"fmt"

	"sentinelgrid-ai-shield/gateway/pkg/types"
)

type LocalProvider struct {
}

func NewLocalProvider() *LocalProvider {
	return &LocalProvider{}
}

func (p *LocalProvider) Name() string {
	return "local"
}

func (p *LocalProvider) ChatCompletion(ctx context.Context, req *types.ChatCompletionRequest, orgID string) (*types.ChatCompletionResponse, error) {
	model := ""
	if req != nil {
		model = req.Model
	}
	return nil, launchUnsupportedProviderError(p.Name(), model)
}

func (p *LocalProvider) Completion(ctx context.Context, req *types.CompletionRequest, orgID string) (*types.CompletionResponse, error) {
	model := ""
	if req != nil {
		model = req.Model
	}
	return nil, launchUnsupportedProviderError(p.Name(), model)
}

func (p *LocalProvider) Embeddings(ctx context.Context, req *types.EmbeddingRequest, orgID string) (*types.EmbeddingResponse, error) {
	return nil, fmt.Errorf("local provider embeddings not yet implemented")
}
