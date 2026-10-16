package policy

import (
	"context"

	"sentinelgrid-ai-shield/gateway/internal/guardrails"
	"sentinelgrid-ai-shield/gateway/internal/telemetry"
)

// Engine evaluates policies and applies guardrails
type Engine struct {
	guardrails *guardrails.Client
}

func NewEngine(guardrailsClient *guardrails.Client) *Engine {
	return &Engine{
		guardrails: guardrailsClient,
	}
}

// EvaluateInput runs input guardrails and returns policy decision
func (e *Engine) EvaluateInput(orgID, appID, text string) telemetry.PolicyDecision {
	ctx := context.Background()
	
	var risk telemetry.RiskFlags

	// Check for PII
	piiResult, _ := e.guardrails.ScanPII(ctx, text)
	if piiResult != nil {
		risk.HasPII = piiResult.HasPII
	}

	// Check for secrets
	secretsResult, _ := e.guardrails.ScanSecrets(ctx, text)
	if secretsResult != nil {
		risk.HasSecrets = secretsResult.HasSecrets
	}

	// Check for prompt injection
	injectionResult, _ := e.guardrails.ScanInjection(ctx, text)
	if injectionResult != nil {
		risk.PromptInjectionSuspected = injectionResult.IsSuspicious
	}

	// Make policy decision (simplified - real impl would check org/app policies)
	decision := "allowed"
	reason := ""

	// Block if secrets detected (always block secrets by default)
	if risk.HasSecrets {
		decision = "blocked"
		reason = "Secrets detected in prompt"
	}

	// Block if clear prompt injection
	if risk.PromptInjectionSuspected && injectionResult.Score > 0.8 {
		decision = "blocked"
		reason = "Prompt injection detected"
	}

	return telemetry.PolicyDecision{
		Decision: decision,
		Risk:     risk,
		Reason:   reason,
	}
}

// EvaluateOutput runs output guardrails
func (e *Engine) EvaluateOutput(orgID, appID, text string) telemetry.PolicyDecision {
	ctx := context.Background()
	
	var risk telemetry.RiskFlags

	// Check for PII in output
	piiResult, _ := e.guardrails.ScanPII(ctx, text)
	if piiResult != nil {
		risk.HasPII = piiResult.HasPII
	}

	// Check for secrets in output
	secretsResult, _ := e.guardrails.ScanSecrets(ctx, text)
	if secretsResult != nil {
		risk.HasSecrets = secretsResult.HasSecrets
	}

	return telemetry.PolicyDecision{
		Decision: "allowed",
		Risk:     risk,
		Reason:   "",
	}
}

