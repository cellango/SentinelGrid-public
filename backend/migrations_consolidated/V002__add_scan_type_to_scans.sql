-- Ensure scans tables carry scan_type (scanner type) column for orchestrator UI/API

ALTER TABLE IF EXISTS orchestration.scans
  ADD COLUMN IF NOT EXISTS scan_type text;

ALTER TABLE IF EXISTS public.scans
  ADD COLUMN IF NOT EXISTS scan_type text;
