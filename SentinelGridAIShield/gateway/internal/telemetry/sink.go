package telemetry

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"os"

	"github.com/rs/zerolog/log"
)

type Sink interface {
	WriteAiEvent(event AiEvent) error
	WriteAiToolCall(call AiToolCall) error
}

// StdoutSink writes telemetry to stdout as JSON
type StdoutSink struct{}

func NewStdoutSink() *StdoutSink {
	return &StdoutSink{}
}

func (s *StdoutSink) WriteAiEvent(event AiEvent) error {
	data, err := json.Marshal(event)
	if err != nil {
		return fmt.Errorf("failed to marshal event: %w", err)
	}
	fmt.Fprintln(os.Stdout, string(data))
	return nil
}

func (s *StdoutSink) WriteAiToolCall(call AiToolCall) error {
	data, err := json.Marshal(call)
	if err != nil {
		return fmt.Errorf("failed to marshal tool call: %w", err)
	}
	fmt.Fprintln(os.Stdout, string(data))
	return nil
}

// HTTPSink sends telemetry to services API via HTTP
type HTTPSink struct {
	baseURL string
	client  *http.Client
}

func NewHTTPSink(baseURL string) *HTTPSink {
	return &HTTPSink{
		baseURL: baseURL,
		client:  &http.Client{},
	}
}

func (s *HTTPSink) WriteAiEvent(event AiEvent) error {
	data, err := json.Marshal(event)
	if err != nil {
		return fmt.Errorf("failed to marshal event: %w", err)
	}

	url := fmt.Sprintf("%s/api/v1/telemetry/events", s.baseURL)
	req, err := http.NewRequest(http.MethodPost, url, bytes.NewReader(data))
	if err != nil {
		return fmt.Errorf("failed to create telemetry event request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", fmt.Sprintf("Bearer %s", internalServiceToken()))
	req.Header.Set("X-Tenant-ID", event.TenantID)

	resp, err := s.client.Do(req)
	if err != nil {
		log.Error().Err(err).Msg("Failed to send telemetry event")
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 400 {
		log.Warn().Int("status", resp.StatusCode).Msg("Telemetry event failed")
	}

	return nil
}

func (s *HTTPSink) WriteAiToolCall(call AiToolCall) error {
	data, err := json.Marshal(call)
	if err != nil {
		return fmt.Errorf("failed to marshal tool call: %w", err)
	}

	url := fmt.Sprintf("%s/api/v1/telemetry/tool-calls", s.baseURL)
	req, err := http.NewRequest(http.MethodPost, url, bytes.NewReader(data))
	if err != nil {
		return fmt.Errorf("failed to create telemetry tool call request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", fmt.Sprintf("Bearer %s", internalServiceToken()))
	req.Header.Set("X-Tenant-ID", call.OrgID)

	resp, err := s.client.Do(req)
	if err != nil {
		log.Error().Err(err).Msg("Failed to send telemetry tool call")
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 400 {
		log.Warn().Int("status", resp.StatusCode).Msg("Telemetry tool call failed")
	}

	return nil
}

// NewSink creates appropriate sink based on mode
func NewSink(mode, servicesURL string) Sink {
	if mode == "http" {
		return NewHTTPSink(servicesURL)
	}
	return NewStdoutSink()
}

func internalServiceToken() string {
	token := os.Getenv("INTERNAL_SERVICE_TOKEN")
	if token == "" {
		token = "internal-service-token-change-in-production"
	}
	return token
}
