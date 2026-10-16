package providers

import (
	"context"
	"fmt"
	"sentinelgrid-ai-shield/gateway/pkg/types"
	"sort"
	"strings"
)

// Provider interface for LLM providers
type Provider interface {
	Name() string
	ChatCompletion(ctx context.Context, req *types.ChatCompletionRequest, orgID string) (*types.ChatCompletionResponse, error)
	Completion(ctx context.Context, req *types.CompletionRequest, orgID string) (*types.CompletionResponse, error)
	Embeddings(ctx context.Context, req *types.EmbeddingRequest, orgID string) (*types.EmbeddingResponse, error)
}

type Capabilities struct {
	ChatCompletions bool
	Completions     bool
	Embeddings      bool
	LaunchReady     bool
}

type UnsupportedProviderError struct {
	Model              string
	Provider           string
	SupportedProviders []string
}

func (e *UnsupportedProviderError) Error() string {
	if e.Provider == "" {
		return fmt.Sprintf(
			"model %q is not mapped to a launch-supported provider; supported providers: %s",
			e.Model,
			strings.Join(e.SupportedProviders, ", "),
		)
	}

	return fmt.Sprintf(
		"provider %q for model %q is not launch-supported; supported providers: %s",
		e.Provider,
		e.Model,
		strings.Join(e.SupportedProviders, ", "),
	)
}

func launchUnsupportedProviderError(provider, model string) error {
	return &UnsupportedProviderError{
		Model:              model,
		Provider:           provider,
		SupportedProviders: []string{"openai"},
	}
}

// Router selects appropriate provider based on model
type Router struct {
	providers     map[string]Provider
	capabilities  map[string]Capabilities
	disabledOrder []string
}

func NewRouter(keyFetcher *KeyFetcherService) *Router {
	return &Router{
		providers: map[string]Provider{
			"openai":    NewOpenAIProvider(keyFetcher),
			"anthropic": NewAnthropicProvider(),
			"local":     NewLocalProvider(),
		},
		capabilities: map[string]Capabilities{
			"openai": {
				ChatCompletions: true,
				Completions:     true,
				Embeddings:      true,
				LaunchReady:     true,
			},
			"anthropic": {
				ChatCompletions: true,
				Completions:     false,
				Embeddings:      false,
				LaunchReady:     false,
			},
			"local": {
				ChatCompletions: true,
				Completions:     true,
				Embeddings:      false,
				LaunchReady:     false,
			},
		},
		disabledOrder: []string{"anthropic", "local"},
	}
}

func (r *Router) SelectProvider(model string) (Provider, error) {
	providerName := detectProvider(model)
	if providerName == "" {
		return nil, &UnsupportedProviderError{
			Model:              model,
			SupportedProviders: r.SupportedProviders(),
		}
	}

	caps, ok := r.capabilities[providerName]
	if !ok || !caps.LaunchReady {
		return nil, &UnsupportedProviderError{
			Model:              model,
			Provider:           providerName,
			SupportedProviders: r.SupportedProviders(),
		}
	}

	provider, ok := r.providers[providerName]
	if !ok {
		return nil, fmt.Errorf("provider %q not configured", providerName)
	}

	return provider, nil
}

func (r *Router) SupportedProviders() []string {
	supported := make([]string, 0, len(r.capabilities))
	for name, caps := range r.capabilities {
		if caps.LaunchReady {
			supported = append(supported, name)
		}
	}
	sort.Strings(supported)
	return supported
}

func (r *Router) DisabledProviders() []string {
	return append([]string(nil), r.disabledOrder...)
}

func detectProvider(model string) string {
	normalized := strings.ToLower(strings.TrimSpace(model))
	switch {
	case normalized == "":
		return ""
	case strings.HasPrefix(normalized, "gpt"),
		strings.HasPrefix(normalized, "o1"),
		strings.HasPrefix(normalized, "o3"),
		strings.HasPrefix(normalized, "text-embedding"),
		strings.HasPrefix(normalized, "omni"):
		return "openai"
	case strings.HasPrefix(normalized, "claude"):
		return "anthropic"
	case strings.HasPrefix(normalized, "llama"),
		strings.HasPrefix(normalized, "mistral"),
		strings.HasPrefix(normalized, "mixtral"),
		strings.HasPrefix(normalized, "qwen"),
		strings.HasPrefix(normalized, "gemma"),
		strings.HasPrefix(normalized, "local"):
		return "local"
	default:
		return ""
	}
}
