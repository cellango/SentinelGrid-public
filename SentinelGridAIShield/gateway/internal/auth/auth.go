package auth

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"os"
	"time"
)

var (
	ErrMissingAPIKey = errors.New("missing API key")
	ErrInvalidAPIKey = errors.New("invalid API key")
)

const defaultInternalServiceToken = "internal-service-token-change-in-production"

// Service handles authentication and authorization
type Service struct {
	servicesURL string
	client      *http.Client
}

func NewService(servicesURL string) *Service {
	return &Service{
		servicesURL: servicesURL,
		client:      &http.Client{Timeout: 10 * time.Second},
	}
}

type APIKeyValidationResult struct {
	Valid   bool   `json:"valid"`
	OrgID   string `json:"org_id"`
	AppID   string `json:"app_id"`
	Realm   string `json:"realm"`
	AppName string `json:"app_name"`
}

// ValidateAPIKey validates an API key and returns org/app context
func (s *Service) ValidateAPIKey(apiKey string) (orgID string, appID string, realm string, err error) {
	if apiKey == "" {
		return "", "", "", ErrMissingAPIKey
	}

	requestBody, err := json.Marshal(map[string]string{"api_key": apiKey})
	if err != nil {
		return "", "", "", fmt.Errorf("failed to encode API key validation request: %w", err)
	}

	req, err := http.NewRequest(
		http.MethodPost,
		fmt.Sprintf("%s/internal/auth/validate-api-key", s.servicesURL),
		bytes.NewReader(requestBody),
	)
	if err != nil {
		return "", "", "", fmt.Errorf("failed to create API key validation request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", fmt.Sprintf("Bearer %s", s.internalToken()))

	resp, err := s.client.Do(req)
	if err != nil {
		return "", "", "", fmt.Errorf("failed to validate API key: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode == http.StatusUnauthorized {
		return "", "", "", ErrInvalidAPIKey
	}
	if resp.StatusCode >= http.StatusBadRequest {
		return "", "", "", fmt.Errorf("API key validation returned status %d", resp.StatusCode)
	}

	var result APIKeyValidationResult
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return "", "", "", fmt.Errorf("failed to decode API key validation response: %w", err)
	}
	if !result.Valid || result.OrgID == "" || result.AppID == "" {
		return "", "", "", ErrInvalidAPIKey
	}

	return result.OrgID, result.AppID, result.Realm, nil
}

func (s *Service) ValidateInternalServiceToken(token string) error {
	if token == "" || token != s.internalToken() {
		return fmt.Errorf("invalid internal service token")
	}
	return nil
}

func (s *Service) internalToken() string {
	token := os.Getenv("INTERNAL_SERVICE_TOKEN")
	if token == "" {
		token = defaultInternalServiceToken
	}
	return token
}
