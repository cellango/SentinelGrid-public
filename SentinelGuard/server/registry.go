package server

import (
	"crypto/rand"
	"encoding/hex"
	"errors"
	"sync"
	"time"
)

// Agent represents a registered sidecar/endpoint.
type Agent struct {
	TenantID string
	AgentID  string
	HostID   string
	Token    string
	IssuedAt time.Time
	Expires  time.Time
}

// Registry tracks registered agents and validates tokens.
type Registry interface {
	Register(agent Agent) (Agent, error)
	ValidateToken(token string) (*Agent, bool)
}

// MemoryRegistry is an in-memory Registry implementation for dev/testing.
type MemoryRegistry struct {
	mu     sync.RWMutex
	tokens map[string]Agent
}

func NewMemoryRegistry() *MemoryRegistry {
	return &MemoryRegistry{
		tokens: make(map[string]Agent),
	}
}

func (r *MemoryRegistry) Register(agent Agent) (Agent, error) {
	if agent.TenantID == "" || agent.AgentID == "" || agent.HostID == "" {
		return Agent{}, errors.New("tenant_id, agent_id, and host_id are required")
	}
	if agent.Token == "" {
		agent.Token = randomToken()
	}
	if agent.IssuedAt.IsZero() {
		agent.IssuedAt = time.Now().UTC()
	}
	r.mu.Lock()
	defer r.mu.Unlock()
	r.tokens[agent.Token] = agent
	return agent, nil
}

func (r *MemoryRegistry) ValidateToken(token string) (*Agent, bool) {
	if token == "" {
		return nil, false
	}
	r.mu.RLock()
	defer r.mu.RUnlock()
	agent, ok := r.tokens[token]
	if !ok {
		return nil, false
	}
	if !agent.Expires.IsZero() && time.Now().UTC().After(agent.Expires) {
		return nil, false
	}
	return &agent, true
}

func randomToken() string {
	b := make([]byte, 16)
	if _, err := rand.Read(b); err != nil {
		return ""
	}
	return hex.EncodeToString(b)
}
