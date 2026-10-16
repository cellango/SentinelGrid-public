package agent

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"time"
)

// diskQueue persists batches on disk so they can be retried after failures or restarts.
type diskQueue struct {
	dir string
}

type queuedBatch struct {
	Path  string
	Batch Batch
}

func newDiskQueue(dir string) (*diskQueue, error) {
	if dir == "" {
		return nil, fmt.Errorf("buffer dir required")
	}
	if err := os.MkdirAll(dir, 0o750); err != nil {
		return nil, fmt.Errorf("create buffer dir: %w", err)
	}
	return &diskQueue{dir: dir}, nil
}

func (q *diskQueue) enqueue(batch Batch) error {
	body, err := json.Marshal(batch)
	if err != nil {
		return fmt.Errorf("encode batch: %w", err)
	}
	tmp := filepath.Join(q.dir, fmt.Sprintf("batch-%d.tmp", time.Now().UnixNano()))
	final := filepath.Join(q.dir, fmt.Sprintf("batch-%d.json", time.Now().UnixNano()))
	if err := os.WriteFile(tmp, body, 0o640); err != nil {
		return fmt.Errorf("write temp batch: %w", err)
	}
	return os.Rename(tmp, final)
}

func (q *diskQueue) list() ([]queuedBatch, error) {
	glob := filepath.Join(q.dir, "batch-*.json")
	paths, err := filepath.Glob(glob)
	if err != nil {
		return nil, fmt.Errorf("list buffer dir: %w", err)
	}
	sort.Strings(paths)
	out := make([]queuedBatch, 0, len(paths))
	for _, p := range paths {
		body, err := os.ReadFile(p)
		if err != nil {
			return nil, fmt.Errorf("read batch %s: %w", p, err)
		}
		var b Batch
		if err := json.Unmarshal(body, &b); err != nil {
			return nil, fmt.Errorf("decode batch %s: %w", p, err)
		}
		out = append(out, queuedBatch{Path: p, Batch: b})
	}
	return out, nil
}

func (q *diskQueue) delete(path string) error {
	if path == "" {
		return nil
	}
	return os.Remove(path)
}
