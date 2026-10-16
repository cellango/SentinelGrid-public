package httpapi

import (
	"errors"
	"fmt"
	"strings"
	"time"

	"sentinelgrid-ai-shield/gateway/internal/providers"
	"sentinelgrid-ai-shield/gateway/internal/telemetry"
	"sentinelgrid-ai-shield/gateway/pkg/types"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/rs/zerolog/log"
)

func (h *Handler) ChatCompletions(c *gin.Context) {
	var req types.ChatCompletionRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(400, types.ErrorResponse{
			Error: types.ErrorDetail{
				Message: "Invalid request body",
				Type:    "invalid_request_error",
			},
		})
		return
	}

	authCtx, statusCode, authErr := h.resolveAuthorizedContext(c)
	if authErr != nil {
		c.JSON(statusCode, authErr)
		return
	}

	orgID := authCtx.OrgID
	realm := authCtx.Realm
	appID := authCtx.AppID
	userID := req.User

	// Extract prompt text for guardrails
	promptText := extractPromptFromMessages(req.Messages)

	// Run input guardrails (simplified for now - real impl would call services API)
	evalResult := h.Policy.EvaluateInput(orgID, appID, promptText)

	// Check if blocked
	if evalResult.Decision == "blocked" {
		// Emit telemetry for blocked request
		event := telemetry.AiEvent{
			ID:                       uuid.New().String(),
			TenantID:                 orgID,
			Realm:                    realm,
			AppID:                    appID,
			UserID:                   userID,
			Model:                    req.Model,
			Provider:                 "blocked",
			HasPII:                   evalResult.Risk.HasPII,
			HasSecrets:               evalResult.Risk.HasSecrets,
			PromptInjectionSuspected: evalResult.Risk.PromptInjectionSuspected,
			PolicyDecision:           "blocked",
			ViolationReason:          evalResult.Reason,
			PromptPreview:            truncate(promptText, 200),
			CreatedAt:                time.Now(),
		}
		_ = h.Telemetry.WriteAiEvent(event)

		c.JSON(403, types.ErrorResponse{
			Error: types.ErrorDetail{
				Message: fmt.Sprintf("Request blocked by policy: %s", evalResult.Reason),
				Type:    "policy_violation",
			},
		})
		return
	}

	// Route to appropriate provider
	provider, err := h.Providers.SelectProvider(req.Model)
	if err != nil {
		var unsupportedErr *providers.UnsupportedProviderError
		if errors.As(err, &unsupportedErr) {
			c.JSON(400, types.ErrorResponse{
				Error: types.ErrorDetail{
					Message: unsupportedErr.Error(),
					Type:    "invalid_request_error",
					Code:    "provider_not_supported",
				},
			})
			return
		}

		log.Error().Err(err).Msg("Provider selection failed")
		c.JSON(500, types.ErrorResponse{
			Error: types.ErrorDetail{
				Message: "Failed to select provider",
				Type:    "provider_error",
			},
		})
		return
	}

	// Call provider
	resp, err := provider.ChatCompletion(c.Request.Context(), &req, orgID)
	if err != nil {
		_ = h.Telemetry.WriteAiEvent(telemetry.AiEvent{
			ID:                       uuid.New().String(),
			TenantID:                 orgID,
			Realm:                    realm,
			AppID:                    appID,
			UserID:                   userID,
			Model:                    req.Model,
			Provider:                 provider.Name(),
			HasPII:                   evalResult.Risk.HasPII,
			HasSecrets:               evalResult.Risk.HasSecrets,
			PromptInjectionSuspected: evalResult.Risk.PromptInjectionSuspected,
			PolicyDecision:           "provider_error",
			ViolationReason:          truncate(err.Error(), 200),
			PromptPreview:            truncate(promptText, 200),
			CreatedAt:                time.Now(),
		})
		log.Error().Err(err).Msg("Provider call failed")
		c.JSON(500, types.ErrorResponse{
			Error: types.ErrorDetail{
				Message: "Failed to complete request",
				Type:    "provider_error",
			},
		})
		return
	}

	// Extract response text for output guardrails
	responseText := ""
	if len(resp.Choices) > 0 {
		responseText = resp.Choices[0].Message.Content
	}

	// Run output guardrails (simplified)
	outputEval := h.Policy.EvaluateOutput(orgID, appID, responseText)

	// Emit telemetry for successful request
	event := telemetry.AiEvent{
		ID:                       uuid.New().String(),
		TenantID:                 orgID,
		Realm:                    realm,
		AppID:                    appID,
		UserID:                   userID,
		Model:                    req.Model,
		Provider:                 provider.Name(),
		HasPII:                   evalResult.Risk.HasPII || outputEval.Risk.HasPII,
		HasSecrets:               evalResult.Risk.HasSecrets || outputEval.Risk.HasSecrets,
		PromptInjectionSuspected: evalResult.Risk.PromptInjectionSuspected,
		PolicyDecision:           "allowed",
		TokensIn:                 resp.Usage.PromptTokens,
		TokensOut:                resp.Usage.CompletionTokens,
		PromptPreview:            truncate(promptText, 200),
		ResponsePreview:          truncate(responseText, 200),
		CreatedAt:                time.Now(),
	}
	_ = h.Telemetry.WriteAiEvent(event)

	c.JSON(200, resp)
}

func extractPromptFromMessages(messages []types.ChatMessage) string {
	var parts []string
	for _, msg := range messages {
		parts = append(parts, msg.Content)
	}
	return strings.Join(parts, "\n")
}

func truncate(s string, maxLen int) string {
	if len(s) <= maxLen {
		return s
	}
	return s[:maxLen] + "..."
}
