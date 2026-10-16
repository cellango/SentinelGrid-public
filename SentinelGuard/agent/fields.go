package agent

import "strings"

// ensureField sets a dotted path inside a map, creating intermediate maps when needed.
func ensureField(dst map[string]interface{}, path string, value interface{}) {
	parts := strings.Split(path, ".")
	curr := dst
	for i, p := range parts {
		if i == len(parts)-1 {
			curr[p] = value
			return
		}
		next, ok := curr[p].(map[string]interface{})
		if !ok {
			next = make(map[string]interface{})
			curr[p] = next
		}
		curr = next
	}
}
