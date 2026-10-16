-- Migration: V2 - Add trigger fields to playbooks
ALTER TABLE playbooks
ADD COLUMN IF NOT EXISTS trigger_conditions JSONB;

ALTER TABLE playbooks
ADD COLUMN IF NOT EXISTS auto_trigger_enabled BOOLEAN DEFAULT false;

ALTER TABLE playbooks
ADD COLUMN IF NOT EXISTS trigger_priority INTEGER DEFAULT 0;
