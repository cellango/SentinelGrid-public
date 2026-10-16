-- Seed initial scanner registry entries for orchestrator
INSERT INTO scanner_registry (id, name, version, image_digest, parser, default_limits, metadata, active)
VALUES
    ('prowler', 'prowler', 'latest', 'toniblyx/prowler:latest', 'prowler', '{"timeout_seconds": 900, "cpus": 1, "memory": "512m"}', '{"type":"cloud","network_mode":"none","read_only_rootfs":true}', true),
    ('trivy', 'trivy', 'latest', 'aquasec/trivy:latest', 'trivy', '{"timeout_seconds": 900, "cpus": 1, "memory": "512m"}', '{"type":"cloud","network_mode":"none","read_only_rootfs":true}', true),
    ('gitleaks', 'gitleaks', 'latest', 'zricethezav/gitleaks:latest', 'gitleaks', '{"timeout_seconds": 600, "cpus": 1, "memory": "512m"}', '{"type":"git","network_mode":"none","read_only_rootfs":true}', true),
    ('checkov', 'checkov', 'latest', 'bridgecrew/checkov:latest', 'checkov', '{"timeout_seconds": 900, "cpus": 1, "memory": "512m"}', '{"type":"git","network_mode":"none","read_only_rootfs":true}', true),
    ('zap', 'zap', 'stable', 'ghcr.io/zaproxy/zaproxy:stable', 'zap', '{"timeout_seconds": 1800, "cpus": 2, "memory": "1g"}', '{"type":"app","network_mode":"bridge","read_only_rootfs":false,"workdir":"/zap/wrk"}', true),
    ('semgrep', 'semgrep', 'latest', 'returntocorp/semgrep:latest', 'semgrep', '{"timeout_seconds": 900, "cpus": 1, "memory": "512m"}', '{"type":"app","network_mode":"none","read_only_rootfs":true}', true)
ON CONFLICT (id) DO UPDATE
SET version = EXCLUDED.version,
    image_digest = EXCLUDED.image_digest,
    parser = EXCLUDED.parser,
    default_limits = EXCLUDED.default_limits,
    metadata = EXCLUDED.metadata,
    active = true,
    updated_at = now();
