package rationalizer

import (
	"strings"
	"time"
)

// Config controls which events are eligible to be embedded.
type Config struct {
	SeverityMin       int
	CategoryAllowlist map[string]struct{}
	DedupeWindowSecs  int
	TruncateMessage   int
	TruncateCommand   int
}

// Meta carries contextual identifiers for summaries.
type Meta struct {
	TenantID string
	AgentID  string
	Source   string
}

// Summary represents the payload sent to the embedding service.
type Summary struct {
	TenantID  string                 `json:"tenant_id"`
	Source    string                 `json:"source"`
	AgentID   string                 `json:"agent_id,omitempty"`
	HostID    string                 `json:"host_id,omitempty"`
	OSID      string                 `json:"os_id,omitempty"`
	Timestamp string                 `json:"@timestamp,omitempty"`
	Summary   string                 `json:"summary,omitempty"`
	Fields    map[string]interface{} `json:"fields,omitempty"`
}

// Rationalize filters and summarizes events for embedding.
func Rationalize(events []map[string]interface{}, cfg Config, meta Meta) []Summary {
	if meta.Source == "" {
		meta.Source = "sentinelguard"
	}
	dedupeWindow := time.Duration(cfg.DedupeWindowSecs) * time.Second
	fingerprints := make(map[string]time.Time)
	var out []Summary
	for _, evt := range events {
		if !passesSeverity(evt, cfg.SeverityMin) {
			continue
		}
		if !passesCategory(evt, cfg.CategoryAllowlist) {
			continue
		}
		if dedupeWindow > 0 {
			fp, ts := fingerprint(evt)
			if ts.IsZero() {
				ts = time.Now().UTC()
			}
			if seenAt, ok := fingerprints[fp]; ok {
				if ts.Sub(seenAt) <= dedupeWindow {
					continue
				}
			}
			fingerprints[fp] = ts
		}
		summary := summarizeEvent(evt, cfg)
		if summary == "" {
			continue
		}
		out = append(out, Summary{
			TenantID:  meta.TenantID,
			Source:    meta.Source,
			AgentID:   meta.AgentID,
			HostID:    stringField(evt, "host.id"),
			OSID:      stringField(evt, "_id"),
			Timestamp: timestampField(evt),
			Summary:   summary,
			Fields: map[string]interface{}{
				"rule.name":           stringField(evt, "rule.name"),
				"rule.description":    stringField(evt, "rule.description"),
				"event.action":        stringField(evt, "event.action"),
				"event.category":      field(evt, "event.category"),
				"event.type":          field(evt, "event.type"),
				"process.name":        stringField(evt, "process.name"),
				"process.command":     truncate(stringField(evt, "process.command_line"), cfg.TruncateCommand),
				"file.path":           stringField(evt, "file.path"),
				"user.name":           stringField(evt, "user.name"),
				"message":             truncate(stringField(evt, "message"), cfg.TruncateMessage),
				"agent.id":            stringField(evt, "agent.id"),
				"host.name":           stringField(evt, "host.name"),
				"sentinelguard.trace": stringField(evt, "sentinelgrid.trace_id"),
			},
		})
	}
	return out
}

func passesSeverity(evt map[string]interface{}, min int) bool {
	if min <= 0 {
		return true
	}
	severity := numericSeverity(evt)
	return severity >= min
}

func numericSeverity(evt map[string]interface{}) int {
	switch v := field(evt, "event.severity").(type) {
	case float64:
		return int(v)
	case int:
		return v
	case int32:
		return int(v)
	case int64:
		return int(v)
	case string:
		return 0
	default:
		return 0
	}
}

func passesCategory(evt map[string]interface{}, allow map[string]struct{}) bool {
	if len(allow) == 0 {
		return true
	}
	val := field(evt, "event.category")
	switch v := val.(type) {
	case string:
		_, ok := allow[v]
		return ok
	case []interface{}:
		for _, item := range v {
			if s, ok := item.(string); ok {
				if _, allowed := allow[s]; allowed {
					return true
				}
			}
		}
	}
	return false
}

func summarizeEvent(evt map[string]interface{}, cfg Config) string {
	parts := []string{
		stringField(evt, "rule.name"),
		stringField(evt, "event.action"),
		stringField(evt, "event.category"),
		stringField(evt, "process.name"),
		stringField(evt, "file.path"),
		truncate(stringField(evt, "message"), minPositive(cfg.TruncateMessage, 200)),
	}
	var out string
	for _, p := range parts {
		if p != "" {
			if out != "" {
				out += " | "
			}
			out += p
		}
	}
	return out
}

func stringField(evt map[string]interface{}, path string) string {
	if v := field(evt, path); v != nil {
		if s, ok := v.(string); ok {
			return s
		}
	}
	return ""
}

func field(evt map[string]interface{}, path string) interface{} {
	parts := strings.Split(path, ".")
	curr := evt
	for i, p := range parts {
		val, ok := curr[p]
		if !ok {
			return nil
		}
		if i == len(parts)-1 {
			return val
		}
		next, ok := val.(map[string]interface{})
		if !ok {
			return nil
		}
		curr = next
	}
	return nil
}

func timestampField(evt map[string]interface{}) string {
	if ts := stringField(evt, "@timestamp"); ts != "" {
		return ts
	}
	return time.Now().UTC().Format(time.RFC3339Nano)
}

func truncate(s string, max int) string {
	if max <= 0 || len(s) <= max {
		return s
	}
	return s[:max]
}

func minPositive(values ...int) int {
	min := 0
	for _, v := range values {
		if v <= 0 {
			continue
		}
		if min == 0 || v < min {
			min = v
		}
	}
	return min
}

func fingerprint(evt map[string]interface{}) (string, time.Time) {
	ts := time.Now().UTC()
	if v := stringField(evt, "@timestamp"); v != "" {
		if parsed, err := time.Parse(time.RFC3339Nano, v); err == nil {
			ts = parsed
		}
	}
	parts := []string{
		stringField(evt, "organization.id"),
		stringField(evt, "tenant_id"),
		stringField(evt, "agent.id"),
		stringField(evt, "host.id"),
		stringField(evt, "rule.id"),
		stringField(evt, "event.action"),
		truncate(stringField(evt, "message"), 128),
	}
	return strings.Join(parts, "|"), ts
}
