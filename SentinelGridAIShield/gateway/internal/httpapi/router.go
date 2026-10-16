package httpapi

import (
	"net/http"
	"strings"

	"sentinelgrid-ai-shield/gateway/internal/auth"
	"sentinelgrid-ai-shield/gateway/internal/guardrails"
	"sentinelgrid-ai-shield/gateway/internal/policy"
	"sentinelgrid-ai-shield/gateway/internal/providers"
	"sentinelgrid-ai-shield/gateway/internal/telemetry"

	"github.com/gin-gonic/gin"
)

type Handler struct {
	Auth       *auth.Service
	Policy     *policy.Engine
	Providers  *providers.Router
	Guardrails *guardrails.Client
	Telemetry  telemetry.Sink
}

func SetupRoutes(router *gin.Engine, servicesURL, telemetryMode string) {
	// Initialize components
	guardrailsClient := guardrails.NewClient(servicesURL)
	telemetrySink := telemetry.NewSink(telemetryMode, servicesURL)
	authService := auth.NewService(servicesURL)
	keyFetcher := providers.NewKeyFetcherService(servicesURL)
	providerRouter := providers.NewRouter(keyFetcher)
	policyEngine := policy.NewEngine(guardrailsClient)

	handler := &Handler{
		Auth:       authService,
		Policy:     policyEngine,
		Providers:  providerRouter,
		Guardrails: guardrailsClient,
		Telemetry:  telemetrySink,
	}

	// Health check
	router.GET("/health", handler.Health)

	// OpenAI-compatible endpoints (v1 prefix)
	v1 := router.Group("/v1")
	{
		v1.POST("/chat/completions", handler.ChatCompletions)
		v1.POST("/completions", handler.Completions)
		v1.POST("/embeddings", handler.Embeddings)
	}

	// Admin endpoints (internal)
	admin := router.Group("/admin")
	{
		admin.GET("/config/refresh", handler.RefreshConfig)
	}
}

func (h *Handler) Health(c *gin.Context) {
	c.JSON(200, gin.H{
		"status":              "healthy",
		"service":             "sentinelgrid-ai-shield-gateway",
		"supported_providers": h.Providers.SupportedProviders(),
		"disabled_providers":  h.Providers.DisabledProviders(),
	})
}

func (h *Handler) RefreshConfig(c *gin.Context) {
	token := c.GetHeader("Authorization")
	if strings.HasPrefix(token, "Bearer ") {
		token = strings.TrimSpace(strings.TrimPrefix(token, "Bearer "))
	}
	if token == "" {
		token = c.GetHeader("X-Internal-Service-Token")
	}
	if err := h.Auth.ValidateInternalServiceToken(token); err != nil {
		c.JSON(http.StatusForbidden, gin.H{
			"error": gin.H{
				"message": "invalid internal service token",
				"type":    "authentication_error",
			},
		})
		return
	}

	c.JSON(200, gin.H{
		"status": "config refreshed",
	})
}
