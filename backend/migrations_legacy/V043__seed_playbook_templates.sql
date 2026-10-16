-- Migration: 043 - Seed Playbook Templates
-- Purpose: Mark builtin playbooks as templates for clone-and-edit in the no-code editor.

-- Mark built-in playbooks as templates and set template_key where possible
UPDATE playbooks
SET
    is_template = COALESCE(is_template, true),
    template_key = COALESCE(template_key, key)
WHERE is_builtin = true
   OR (key IS NOT NULL AND key <> '');

-- Ensure requires_approval has a default (column already exists in initial schema)
UPDATE playbooks
SET requires_approval = COALESCE(requires_approval, false)
WHERE requires_approval IS NULL;
