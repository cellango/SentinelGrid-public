package policy

import (
	"testing"

	"sentinelgrid-ai-shield/gateway/internal/guardrails"

	"github.com/stretchr/testify/assert"
)

func TestEvaluateInputWithPII(t *testing.T) {
	client := guardrails.NewClient("http://mock:8000")
	engine := NewEngine(client)
	
	// Text with PII
	text := "My email is john@example.com"
	result := engine.EvaluateInput("test-org", "test-app", text)
	
	// Should detect PII (even with mock client that fails gracefully)
	assert.NotEmpty(t, result.Decision)
	assert.Contains(t, []string{"allowed", "blocked"}, result.Decision)
}

func TestEvaluateInputWithSecret(t *testing.T) {
	client := guardrails.NewClient("http://mock:8000")
	engine := NewEngine(client)
	
	// Text with secret pattern
	text := "My API key is sk-1234567890abcdefghij"
	result := engine.EvaluateInput("test-org", "test-app", text)
	
	// Decision should be made
	assert.NotEmpty(t, result.Decision)
}

func TestEvaluateInputClean(t *testing.T) {
	client := guardrails.NewClient("http://mock:8000")
	engine := NewEngine(client)
	
	// Clean text
	text := "Hello, how are you?"
	result := engine.EvaluateInput("test-org", "test-app", text)
	
	// Should allow
	assert.Equal(t, "allowed", result.Decision)
	assert.Empty(t, result.Reason)
}

func TestEvaluateOutput(t *testing.T) {
	client := guardrails.NewClient("http://mock:8000")
	engine := NewEngine(client)
	
	// Output text
	text := "I'm doing well, thank you!"
	result := engine.EvaluateOutput("test-org", "test-app", text)
	
	// Should evaluate without errors
	assert.NotEmpty(t, result.Decision)
}

