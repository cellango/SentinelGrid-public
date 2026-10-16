package httpapi

import (
	"errors"
	"net/http"
	"strings"

	"sentinelgrid-ai-shield/gateway/internal/auth"
	"sentinelgrid-ai-shield/gateway/pkg/types"

	"github.com/gin-gonic/gin"
)

type authorizedContext struct {
	OrgID string
	AppID string
	Realm string
}

func (h *Handler) resolveAuthorizedContext(c *gin.Context) (*authorizedContext, int, *types.ErrorResponse) {
	apiKey, err := extractBearerToken(c.GetHeader("Authorization"))
	if err != nil {
		return nil, http.StatusUnauthorized, &types.ErrorResponse{
			Error: types.ErrorDetail{
				Message: err.Error(),
				Type:    "authentication_error",
			},
		}
	}

	orgID, appID, realm, err := h.Auth.ValidateAPIKey(apiKey)
	if err != nil {
		if errors.Is(err, auth.ErrMissingAPIKey) || errors.Is(err, auth.ErrInvalidAPIKey) {
			return nil, http.StatusUnauthorized, &types.ErrorResponse{
				Error: types.ErrorDetail{
					Message: "Invalid API key",
					Type:    "authentication_error",
				},
			}
		}
		return nil, http.StatusBadGateway, &types.ErrorResponse{
			Error: types.ErrorDetail{
				Message: "Failed to validate API key",
				Type:    "service_unavailable",
			},
		}
	}

	if realm == "" {
		realm = appID
	}

	if tenantHeader := c.GetHeader("X-Tenant-ID"); tenantHeader != "" && tenantHeader != orgID {
		return nil, http.StatusForbidden, spoofingError("tenant")
	}
	if appHeader := c.GetHeader("X-App-ID"); appHeader != "" && appHeader != appID {
		return nil, http.StatusForbidden, spoofingError("app")
	}
	if realmHeader := c.GetHeader("X-Realm"); realmHeader != "" && realmHeader != realm {
		return nil, http.StatusForbidden, spoofingError("realm")
	}

	return &authorizedContext{
		OrgID: orgID,
		AppID: appID,
		Realm: realm,
	}, http.StatusOK, nil
}

func spoofingError(scope string) *types.ErrorResponse {
	return &types.ErrorResponse{
		Error: types.ErrorDetail{
			Message: "Cross-tenant spoof attempt blocked",
			Type:    "authorization_error",
			Code:    scope + "_mismatch",
		},
	}
}

func extractBearerToken(authorization string) (string, error) {
	if authorization == "" {
		return "", auth.ErrMissingAPIKey
	}
	if !strings.HasPrefix(authorization, "Bearer ") {
		return "", auth.ErrMissingAPIKey
	}
	token := strings.TrimSpace(strings.TrimPrefix(authorization, "Bearer "))
	if token == "" {
		return "", auth.ErrMissingAPIKey
	}
	return token, nil
}
