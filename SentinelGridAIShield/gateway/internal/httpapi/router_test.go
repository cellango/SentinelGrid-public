package httpapi

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
)

func newMockServicesServer() *httptest.Server {
	return httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch {
		case r.Method == http.MethodPost && r.URL.Path == "/internal/auth/validate-api-key":
			if r.Header.Get("Authorization") != "Bearer internal-service-token-change-in-production" {
				http.Error(w, `{"detail":"invalid internal service token"}`, http.StatusForbidden)
				return
			}
			var payload map[string]string
			_ = json.NewDecoder(r.Body).Decode(&payload)
			if payload["api_key"] != "valid-api-key" {
				http.Error(w, `{"detail":"invalid api key"}`, http.StatusUnauthorized)
				return
			}
			_ = json.NewEncoder(w).Encode(map[string]any{
				"valid":  true,
				"org_id": "11111111-1111-1111-1111-111111111111",
				"app_id": "22222222-2222-2222-2222-222222222222",
				"realm":  "prod",
			})
		case r.Method == http.MethodGet && r.URL.Path == "/internal/provider-keys/11111111-1111-1111-1111-111111111111/openai":
			if r.Header.Get("Authorization") != "Bearer internal-service-token-change-in-production" {
				http.Error(w, `{"detail":"invalid internal service token"}`, http.StatusForbidden)
				return
			}
			_ = json.NewEncoder(w).Encode(map[string]any{
				"success":         true,
				"key":             "sk-test-openai-key",
				"key_fingerprint": "abcd1234abcd1234",
				"message":         "ok",
			})
		default:
			http.NotFound(w, r)
		}
	}))
}

func newTestRouter(t *testing.T) (*gin.Engine, *httptest.Server) {
	t.Helper()
	gin.SetMode(gin.TestMode)
	router := gin.New()
	services := newMockServicesServer()
	SetupRoutes(router, services.URL, "stdout")
	return router, services
}

func TestHealthEndpoint(t *testing.T) {
	router, services := newTestRouter(t)
	defer services.Close()

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/health", nil)
	router.ServeHTTP(w, req)

	assert.Equal(t, 200, w.Code)

	var response map[string]interface{}
	err := json.Unmarshal(w.Body.Bytes(), &response)
	assert.NoError(t, err)
	assert.Equal(t, "healthy", response["status"])
	assert.Equal(t, []interface{}{"openai"}, response["supported_providers"])
	assert.Equal(t, []interface{}{"anthropic", "local"}, response["disabled_providers"])
}

func TestChatCompletionsEndpoint(t *testing.T) {
	router, services := newTestRouter(t)
	defer services.Close()

	requestBody := map[string]interface{}{
		"model": "gpt-4",
		"messages": []map[string]string{
			{"role": "user", "content": "Hello"},
		},
	}

	body, _ := json.Marshal(requestBody)
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("POST", "/v1/chat/completions", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer valid-api-key")

	router.ServeHTTP(w, req)

	assert.Equal(t, 500, w.Code)
}

func TestInvalidRequestBody(t *testing.T) {
	router, services := newTestRouter(t)
	defer services.Close()

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("POST", "/v1/chat/completions", bytes.NewReader([]byte("invalid")))
	req.Header.Set("Content-Type", "application/json")

	router.ServeHTTP(w, req)

	assert.Equal(t, 400, w.Code)
}

func TestChatCompletionsRejectsUnsupportedProvider(t *testing.T) {
	router, services := newTestRouter(t)
	defer services.Close()

	requestBody := map[string]interface{}{
		"model": "claude-sonnet-4-20250514",
		"messages": []map[string]string{
			{"role": "user", "content": "Hello"},
		},
	}

	body, _ := json.Marshal(requestBody)
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("POST", "/v1/chat/completions", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer valid-api-key")

	router.ServeHTTP(w, req)

	assert.Equal(t, 400, w.Code)
	assert.Contains(t, w.Body.String(), "not launch-supported")
	assert.Contains(t, w.Body.String(), "openai")
}

func TestCompletionsRejectsUnsupportedProvider(t *testing.T) {
	router, services := newTestRouter(t)
	defer services.Close()

	requestBody := map[string]interface{}{
		"model":  "local-llama3",
		"prompt": "Hello",
	}

	body, _ := json.Marshal(requestBody)
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("POST", "/v1/completions", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer valid-api-key")

	router.ServeHTTP(w, req)

	assert.Equal(t, 400, w.Code)
	assert.Contains(t, w.Body.String(), "not launch-supported")
}

func TestEmbeddingsRejectsUnknownModel(t *testing.T) {
	router, services := newTestRouter(t)
	defer services.Close()

	requestBody := map[string]interface{}{
		"model": "mystery-model",
		"input": []string{"hello world"},
	}

	body, _ := json.Marshal(requestBody)
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("POST", "/v1/embeddings", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer valid-api-key")

	router.ServeHTTP(w, req)

	assert.Equal(t, 400, w.Code)
	assert.Contains(t, w.Body.String(), "launch-supported provider")
}

func TestChatCompletionsRejectsInvalidAPIKey(t *testing.T) {
	router, services := newTestRouter(t)
	defer services.Close()

	requestBody := map[string]interface{}{
		"model": "gpt-4",
		"messages": []map[string]string{
			{"role": "user", "content": "Hello"},
		},
	}

	body, _ := json.Marshal(requestBody)
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("POST", "/v1/chat/completions", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer invalid-api-key")

	router.ServeHTTP(w, req)

	assert.Equal(t, 401, w.Code)
	assert.Contains(t, w.Body.String(), "Invalid API key")
}

func TestChatCompletionsRejectsTenantSpoofAttempt(t *testing.T) {
	router, services := newTestRouter(t)
	defer services.Close()

	requestBody := map[string]interface{}{
		"model": "gpt-4",
		"messages": []map[string]string{
			{"role": "user", "content": "Hello"},
		},
	}

	body, _ := json.Marshal(requestBody)
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("POST", "/v1/chat/completions", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer valid-api-key")
	req.Header.Set("X-Tenant-ID", "33333333-3333-3333-3333-333333333333")

	router.ServeHTTP(w, req)

	assert.Equal(t, 403, w.Code)
	assert.Contains(t, w.Body.String(), "Cross-tenant spoof attempt blocked")
}

func TestRefreshConfigRequiresInternalToken(t *testing.T) {
	router, services := newTestRouter(t)
	defer services.Close()

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/admin/config/refresh", nil)
	router.ServeHTTP(w, req)
	assert.Equal(t, 403, w.Code)

	w = httptest.NewRecorder()
	req, _ = http.NewRequest("GET", "/admin/config/refresh", nil)
	req.Header.Set("Authorization", "Bearer internal-service-token-change-in-production")
	router.ServeHTTP(w, req)
	assert.Equal(t, 200, w.Code)
}
