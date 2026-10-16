package httpapi

import (
	"errors"
	"time"

	"sentinelgrid-ai-shield/gateway/internal/providers"
	"sentinelgrid-ai-shield/gateway/internal/telemetry"
	"sentinelgrid-ai-shield/gateway/pkg/types"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/rs/zerolog/log"
)

func (h *Handler) Completions(c *gin.Context) {
	var req types.CompletionRequest
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

	// Run guardrails
	evalResult := h.Policy.EvaluateInput(orgID, appID, req.Prompt)
	if evalResult.Decision == "blocked" {
		event := telemetry.AiEvent{
			ID:              uuid.New().String(),
			TenantID:        orgID,
			Realm:           realm,
			AppID:           appID,
			UserID:          userID,
			Model:           req.Model,
			Provider:        "blocked",
			PolicyDecision:  "blocked",
			ViolationReason: evalResult.Reason,
			PromptPreview:   truncate(req.Prompt, 200),
			CreatedAt:       time.Now(),
		}
		_ = h.Telemetry.WriteAiEvent(event)

		c.JSON(403, types.ErrorResponse{
			Error: types.ErrorDetail{
				Message: "Request blocked by policy",
				Type:    "policy_violation",
			},
		})
		return
	}

	// Route to provider
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
	resp, err := provider.Completion(c.Request.Context(), &req, orgID)
	if err != nil {
		_ = h.Telemetry.WriteAiEvent(telemetry.AiEvent{
			ID:              uuid.New().String(),
			TenantID:        orgID,
			Realm:           realm,
			AppID:           appID,
			UserID:          userID,
			Model:           req.Model,
			Provider:        provider.Name(),
			PolicyDecision:  "provider_error",
			ViolationReason: truncate(err.Error(), 200),
			PromptPreview:   truncate(req.Prompt, 200),
			CreatedAt:       time.Now(),
		})
		c.JSON(500, types.ErrorResponse{
			Error: types.ErrorDetail{
				Message: "Failed to complete request",
				Type:    "provider_error",
			},
		})
		return
	}

	// Emit telemetry
	event := telemetry.AiEvent{
		ID:             uuid.New().String(),
		TenantID:       orgID,
		Realm:          realm,
		AppID:          appID,
		UserID:         userID,
		Model:          req.Model,
		Provider:       provider.Name(),
		PolicyDecision: "allowed",
		TokensIn:       resp.Usage.PromptTokens,
		TokensOut:      resp.Usage.CompletionTokens,
		PromptPreview:  truncate(req.Prompt, 200),
		CreatedAt:      time.Now(),
	}
	_ = h.Telemetry.WriteAiEvent(event)

	c.JSON(200, resp)
}

func (h *Handler) Embeddings(c *gin.Context) {
	var req types.EmbeddingRequest
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

	// Route to provider (no guardrails for embeddings typically)
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
	resp, err := provider.Embeddings(c.Request.Context(), &req, orgID)
	if err != nil {
		_ = h.Telemetry.WriteAiEvent(telemetry.AiEvent{
			ID:              uuid.New().String(),
			TenantID:        orgID,
			Realm:           realm,
			AppID:           appID,
			UserID:          req.User,
			Model:           req.Model,
			Provider:        provider.Name(),
			PolicyDecision:  "provider_error",
			ViolationReason: truncate(err.Error(), 200),
			CreatedAt:       time.Now(),
		})
		c.JSON(500, types.ErrorResponse{
			Error: types.ErrorDetail{
				Message: "Failed to complete request",
				Type:    "provider_error",
			},
		})
		return
	}

	c.JSON(200, resp)
}
