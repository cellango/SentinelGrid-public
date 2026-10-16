package telemetry

import (
	"time"
)

// AiEvent represents a single LLM interaction
type AiEvent struct {
	ID                      string    `json:"id"`
	TenantID                string    `json:"tenant_id"`
	Realm                   string    `json:"realm,omitempty"`
	AppID                   string    `json:"ai_app_id"`
	UserID                  string    `json:"user_id,omitempty"`
	Provider                string    `json:"provider"`
	Model                   string    `json:"model"`
	HasPII                  bool      `json:"has_pii"`
	HasSecrets              bool      `json:"has_secrets"`
	PromptInjectionSuspected bool     `json:"prompt_injection_suspected"`
	PolicyDecision          string    `json:"policy_decision"` // allowed, blocked, modified
	ViolationReason         string    `json:"violation_reason,omitempty"`
	TokensIn                int       `json:"tokens_in"`
	TokensOut               int       `json:"tokens_out"`
	PromptPreview           string    `json:"prompt_preview,omitempty"`
	ResponsePreview         string    `json:"response_preview,omitempty"`
	CreatedAt               time.Time `json:"created_at"`
}

// AiToolCall represents an agent tool invocation
type AiToolCall struct {
	ID              string    `json:"id"`
	OrgID           string    `json:"org_id"`
	AppID           string    `json:"ai_app_id"`
	AgentID         string    `json:"agent_id,omitempty"`
	UserID          string    `json:"user_id,omitempty"`
	ToolName        string    `json:"tool_name"`
	Action          string    `json:"action,omitempty"`
	Allowed         bool      `json:"allowed"`
	PolicyViolated  bool      `json:"policy_violated"`
	ViolationReason string    `json:"violation_reason,omitempty"`
	CreatedAt       time.Time `json:"created_at"`
}

// RiskFlags represents detected risks in a prompt/response
type RiskFlags struct {
	HasPII                  bool `json:"has_pii"`
	HasSecrets              bool `json:"has_secrets"`
	PromptInjectionSuspected bool `json:"prompt_injection_suspected"`
	ToxicOutput             bool `json:"toxic_output"`
}

// PolicyDecision represents the result of policy evaluation
type PolicyDecision struct {
	Decision string    `json:"decision"` // allowed, blocked, modified
	Risk     RiskFlags `json:"risk"`
	Reason   string    `json:"reason,omitempty"`
}
