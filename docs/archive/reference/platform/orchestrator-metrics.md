# Orchestrator Metrics

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


Lightweight, in-process counters expose orchestration health for alerts and compliance remediation.

## Endpoint
- `GET /metrics` on orchestrator (dev: `http://localhost:8012/metrics`).
- Response fields:
  - `queued`, `running`, `completed`, `failed`: counts across all operations.
  - `last_duration_ms`, `avg_duration_ms`, `total_duration_ms`, `samples`: overall timing in milliseconds.
  - `by_type`: per operation type (keys: `automated_response`, `compliance_remediation`) with the same counters/timers.
  - `uptime_seconds`: process uptime.

## How it is updated
- `mark_queued` when an orchestration request is accepted.
- `mark_started` when execution begins; `mark_completed` or `mark_failed` on finish.
- Durations are wall-clock from start to finish using the orchestrator process clock.

## Suggested alerts/SLOs (tune per environment)
- Failures: alert if `failed` increases by >5 over 5 minutes or if failure rate >5% of samples.
- Stuck runs: alert if `running` remains >0 for >5 minutes without `completed` changing.
- Latency: p95 completion < 5s for automated_response; < 15s for compliance_remediation. Use `avg_duration_ms` as a coarse guard rail; refine with logs until a metrics backend is added.
- Backpressure: alert if `queued` > 50 for >2 minutes.

## Next steps (optional enhancements)
- Add per-tenant counts in `by_type` for isolation checks.
- Add structured log lines with `op`, `tenant_id`, `status`, `duration_ms` for easier scraping by log-based monitors.
- Emit Prometheus format if/when we add a metrics backend.
