-- Backfill playbook.category using category_filter for existing records.
-- This is a data-only migration to enable UI category chips for playbooks.

-- Array-style category_filter (e.g., ["identity","cloud"])
UPDATE playbooks
SET category = category_filter->>0
WHERE (category IS NULL OR category = '')
  AND jsonb_typeof(category_filter) = 'array'
  AND (category_filter != '[]'::jsonb);

-- Object-style category_filter (e.g., {"categories":["identity","cloud"]})
UPDATE playbooks
SET category = category_filter->'categories'->>0
WHERE (category IS NULL OR category = '')
  AND jsonb_typeof(category_filter) = 'object'
  AND category_filter ? 'categories';
