-- Move detections, alerts, incidents, and tickets into security_ops schema.
-- Assumes V117 (schemas/roles) is applied and search_path will be adjusted in services.

ALTER TABLE IF EXISTS detection_bindings SET SCHEMA security_ops;
ALTER TABLE IF EXISTS detection_deduplication SET SCHEMA security_ops;
ALTER TABLE IF EXISTS detection_playbook_mappings SET SCHEMA security_ops;
ALTER TABLE IF EXISTS detection_rule_executions SET SCHEMA security_ops;
ALTER TABLE IF EXISTS detection_rule_versions SET SCHEMA security_ops;
ALTER TABLE IF EXISTS detection_rules SET SCHEMA security_ops;
ALTER TABLE IF EXISTS detection_suppression_events SET SCHEMA security_ops;
ALTER TABLE IF EXISTS detection_suppression_rules SET SCHEMA security_ops;

ALTER TABLE IF EXISTS alerts SET SCHEMA security_ops;
ALTER TABLE IF EXISTS alert_ai_analysis SET SCHEMA security_ops;
ALTER TABLE IF EXISTS alert_playbook_triggers SET SCHEMA security_ops;
ALTER TABLE IF EXISTS alert_triage_feedback SET SCHEMA security_ops;

ALTER TABLE IF EXISTS incidents SET SCHEMA security_ops;
ALTER TABLE IF EXISTS incident_actions SET SCHEMA security_ops;
ALTER TABLE IF EXISTS incident_ai_summaries SET SCHEMA security_ops;
ALTER TABLE IF EXISTS incident_alerts SET SCHEMA security_ops;
ALTER TABLE IF EXISTS incident_evidence SET SCHEMA security_ops;
ALTER TABLE IF EXISTS incident_lifecycle SET SCHEMA security_ops;
ALTER TABLE IF EXISTS incident_observables SET SCHEMA security_ops;
ALTER TABLE IF EXISTS incident_timeline SET SCHEMA security_ops;

ALTER TABLE IF EXISTS tickets SET SCHEMA security_ops;
ALTER TABLE IF EXISTS ticket_alerts SET SCHEMA security_ops;
ALTER TABLE IF EXISTS ticket_ai_enrichments SET SCHEMA security_ops;
ALTER TABLE IF EXISTS ticket_vulnerabilities SET SCHEMA security_ops;
