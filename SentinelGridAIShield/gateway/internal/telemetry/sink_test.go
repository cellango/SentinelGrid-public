package telemetry

import (
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
)

func TestStdoutSink(t *testing.T) {
	sink := NewStdoutSink()
	
	event := AiEvent{
		ID:             "test-123",
		TenantID:       "tenant-123",
		Realm:          "demo",
		AppID:          "app-123",
		Provider:       "openai",
		Model:          "gpt-4",
		PolicyDecision: "allowed",
		TokensIn:       10,
		TokensOut:      20,
		CreatedAt:      time.Now(),
	}
	
	err := sink.WriteAiEvent(event)
	assert.NoError(t, err)
}

func TestHTTPSink(t *testing.T) {
	sink := NewHTTPSink("http://localhost:9999")
	
	event := AiEvent{
		ID:             "test-123",
		TenantID:       "tenant-123",
		Realm:          "demo",
		AppID:          "app-123",
		Provider:       "openai",
		Model:          "gpt-4",
		PolicyDecision: "allowed",
		CreatedAt:      time.Now(),
	}
	
	// Should not panic even if service unavailable
	err := sink.WriteAiEvent(event)
	// Error is expected since mock service doesn't exist
	assert.Error(t, err)
}

func TestNewSink(t *testing.T) {
	stdoutSink := NewSink("stdout", "http://localhost:8000")
	assert.IsType(t, &StdoutSink{}, stdoutSink)
	
	httpSink := NewSink("http", "http://localhost:8000")
	assert.IsType(t, &HTTPSink{}, httpSink)
}
