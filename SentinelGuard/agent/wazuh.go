package agent

import (
	"bufio"
	"encoding/json"
	"fmt"
	"os"
	"strings"
	"time"
)

// readWazuhAlerts reads newline-delimited Wazuh alerts and maps them to ECS.
func readWazuhAlerts(path string, maxBytes int, tenantID, agentID string) ([]map[string]interface{}, error) {
	file, err := os.Open(path)
	if err != nil {
		return nil, fmt.Errorf("open alerts file: %w", err)
	}
	defer file.Close()

	events := make([]map[string]interface{}, 0, 50)
	scanner := bufio.NewScanner(file)
	if maxBytes > 0 {
		buf := make([]byte, 0, maxBytes)
		scanner.Buffer(buf, maxBytes)
	}

	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" {
			continue
		}
		var raw map[string]interface{}
		if err := json.Unmarshal([]byte(line), &raw); err != nil {
			// Skip malformed lines but keep going; Wazuh can emit partials during rotation.
			continue
		}
		ecs := mapWazuhToECS(raw, tenantID, agentID)
		events = append(events, ecs)
	}
	if err := scanner.Err(); err != nil {
		return nil, fmt.Errorf("scan alerts: %w", err)
	}
	return events, nil
}

func mapWazuhToECS(raw map[string]interface{}, tenantID, agentID string) map[string]interface{} {
	evt := copyMap(raw)

	ensureField(evt, "organization.id", tenantID)
	ensureField(evt, "agent.id", agentID)
	ensureField(evt, "agent.type", "sentinelguard")
	ensureField(evt, "event.module", "sentinelguard")
	ensureField(evt, "event.dataset", "sentinelguard.wazuh")

	if ts, ok := evt["@timestamp"]; !ok || ts == "" {
		if v, ok := raw["timestamp"].(string); ok && v != "" {
			ensureField(evt, "@timestamp", v)
		} else {
			ensureField(evt, "@timestamp", time.Now().UTC().Format(time.RFC3339Nano))
		}
	}

	if rule, ok := raw["rule"].(map[string]interface{}); ok {
		if id, ok := rule["id"]; ok {
			ensureField(evt, "rule.id", id)
		}
		if name, ok := rule["description"]; ok {
			ensureField(evt, "rule.name", name)
		}
	}

	if agent, ok := raw["agent"].(map[string]interface{}); ok {
		if hid, ok := agent["id"]; ok {
			ensureField(evt, "host.id", hid)
		}
		if hname, ok := agent["name"]; ok {
			ensureField(evt, "host.name", hname)
		}
		if hv, ok := agent["version"]; ok {
			ensureField(evt, "host.os.version", hv)
		}
	}

	return evt
}

func copyMap(in map[string]interface{}) map[string]interface{} {
	out := make(map[string]interface{}, len(in))
	for k, v := range in {
		out[k] = v
	}
	return out
}
