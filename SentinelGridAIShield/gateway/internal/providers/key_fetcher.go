package providers

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"sync"
	"time"
)

// KeyFetcherService fetches provider API keys from Services API
// Keys are cached for 5 minutes to reduce latency
type KeyFetcherService struct {
	servicesURL string
	client      *http.Client
	cache       *keyCache
}

// keyCache stores provider keys with TTL
type keyCache struct {
	mu    sync.RWMutex
	items map[string]*cacheEntry
}

type cacheEntry struct {
	key       string
	expiresAt time.Time
}

// ProviderCredentialConfig holds configuration from Services API
type ProviderCredentialConfig struct {
	ID              string    `json:"id"`
	OrgID           string    `json:"org_id"`
	Provider        string    `json:"provider"`
	AccessMethod    string    `json:"access_method"`
	VaultType       string    `json:"vault_type"`
	LastValidated   time.Time `json:"last_validated"`
	ValidationError string    `json:"validation_error"`
}

// KeyFetchResponse from Services API
type KeyFetchResponse struct {
	Success        bool   `json:"success"`
	Key            string `json:"key"`
	KeyFingerprint string `json:"key_fingerprint"`
	Message        string `json:"message"`
}

// NewKeyFetcherService creates a new key fetcher
func NewKeyFetcherService(servicesURL string) *KeyFetcherService {
	return &KeyFetcherService{
		servicesURL: servicesURL,
		client:      &http.Client{Timeout: 10 * time.Second},
		cache: &keyCache{
			items: make(map[string]*cacheEntry),
		},
	}
}

// FetchProviderKey retrieves API key for a provider from customer's vault
// Implements caching with 5-minute TTL to reduce latency
func (s *KeyFetcherService) FetchProviderKey(ctx context.Context, orgID, provider string) (string, error) {
	cacheKey := fmt.Sprintf("%s:%s", orgID, provider)

	// Check cache first
	if cachedKey := s.cache.get(cacheKey); cachedKey != "" {
		return cachedKey, nil
	}

	// Cache miss - fetch from Services API
	key, err := s.fetchFromServicesAPI(ctx, orgID, provider)
	if err != nil {
		return "", fmt.Errorf("failed to fetch provider key: %w", err)
	}

	// Cache the key for 5 minutes
	s.cache.set(cacheKey, key, 5*time.Minute)

	return key, nil
}

// fetchFromServicesAPI calls the Services API to get the provider key
func (s *KeyFetcherService) fetchFromServicesAPI(ctx context.Context, orgID, provider string) (string, error) {
	// Build request URL
	url := fmt.Sprintf("%s/internal/provider-keys/%s/%s", s.servicesURL, orgID, provider)

	// Create request
	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return "", fmt.Errorf("failed to create request: %w", err)
	}

	// Add internal service token (should be set via env var)
	internalToken := os.Getenv("INTERNAL_SERVICE_TOKEN")
	if internalToken == "" {
		internalToken = "internal-service-token-change-in-production"
	}
	req.Header.Set("Authorization", fmt.Sprintf("Bearer %s", internalToken))

	// Make request
	resp, err := s.client.Do(req)
	if err != nil {
		return "", fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	// Check status
	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return "", fmt.Errorf("services API returned %d: %s", resp.StatusCode, string(body))
	}

	// Parse response
	var keyResp KeyFetchResponse
	if err := json.NewDecoder(resp.Body).Decode(&keyResp); err != nil {
		return "", fmt.Errorf("failed to decode response: %w", err)
	}

	if !keyResp.Success {
		return "", fmt.Errorf("key fetch failed: %s", keyResp.Message)
	}

	if keyResp.Key == "" {
		return "", fmt.Errorf("services API returned empty key")
	}

	return keyResp.Key, nil
}

// GetProviderConfig fetches provider configuration without the key
func (s *KeyFetcherService) GetProviderConfig(ctx context.Context, orgID, provider string) (*ProviderCredentialConfig, error) {
	url := fmt.Sprintf("%s/api/v1/provider-credentials?org_id=%s&provider=%s", s.servicesURL, orgID, provider)

	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return nil, err
	}
	req.Header.Set("Authorization", fmt.Sprintf("Bearer %s", s.internalToken()))
	req.Header.Set("X-Tenant-ID", orgID)

	resp, err := s.client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("failed to get config: status %d", resp.StatusCode)
	}

	var configs []ProviderCredentialConfig
	if err := json.NewDecoder(resp.Body).Decode(&configs); err != nil {
		return nil, err
	}

	if len(configs) == 0 {
		return nil, fmt.Errorf("no configuration found for %s/%s", orgID, provider)
	}

	return &configs[0], nil
}

func (s *KeyFetcherService) internalToken() string {
	token := os.Getenv("INTERNAL_SERVICE_TOKEN")
	if token == "" {
		token = "internal-service-token-change-in-production"
	}
	return token
}

// InvalidateCache removes a key from cache (useful after key rotation)
func (s *KeyFetcherService) InvalidateCache(orgID, provider string) {
	cacheKey := fmt.Sprintf("%s:%s", orgID, provider)
	s.cache.delete(cacheKey)
}

// keyCache methods

func (c *keyCache) get(key string) string {
	c.mu.RLock()
	defer c.mu.RUnlock()

	entry, exists := c.items[key]
	if !exists {
		return ""
	}

	// Check if expired
	if time.Now().After(entry.expiresAt) {
		// Don't delete here (would need write lock), just return empty
		return ""
	}

	return entry.key
}

func (c *keyCache) set(key, value string, ttl time.Duration) {
	c.mu.Lock()
	defer c.mu.Unlock()

	c.items[key] = &cacheEntry{
		key:       value,
		expiresAt: time.Now().Add(ttl),
	}
}

func (c *keyCache) delete(key string) {
	c.mu.Lock()
	defer c.mu.Unlock()

	delete(c.items, key)
}

// cleanupExpired removes expired entries (call periodically)
func (c *keyCache) cleanupExpired() {
	c.mu.Lock()
	defer c.mu.Unlock()

	now := time.Now()
	for key, entry := range c.items {
		if now.After(entry.expiresAt) {
			delete(c.items, key)
		}
	}
}

// StartCleanupWorker starts a background worker to cleanup expired cache entries
func (s *KeyFetcherService) StartCleanupWorker(ctx context.Context) {
	ticker := time.NewTicker(1 * time.Minute)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			s.cache.cleanupExpired()
		}
	}
}
