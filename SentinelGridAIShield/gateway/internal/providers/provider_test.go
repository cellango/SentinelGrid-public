package providers

import (
	"context"
	"errors"
	"testing"

	"sentinelgrid-ai-shield/gateway/pkg/types"

	"github.com/stretchr/testify/assert"
)

func TestAnthropicProviderRejectsDirectCalls(t *testing.T) {
	provider := NewAnthropicProvider()

	_, err := provider.ChatCompletion(context.Background(), &types.ChatCompletionRequest{Model: "claude-sonnet-4"}, "org-123")

	var unsupportedErr *UnsupportedProviderError
	assert.True(t, errors.As(err, &unsupportedErr))
	assert.Equal(t, "anthropic", unsupportedErr.Provider)
	assert.Equal(t, []string{"openai"}, unsupportedErr.SupportedProviders)
}

func TestLocalProviderRejectsDirectCalls(t *testing.T) {
	provider := NewLocalProvider()

	_, err := provider.Completion(context.Background(), &types.CompletionRequest{Model: "local-llama3"}, "org-123")

	var unsupportedErr *UnsupportedProviderError
	assert.True(t, errors.As(err, &unsupportedErr))
	assert.Equal(t, "local", unsupportedErr.Provider)
	assert.Equal(t, []string{"openai"}, unsupportedErr.SupportedProviders)
}
