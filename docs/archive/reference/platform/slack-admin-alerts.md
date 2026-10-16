# SentinelGrid Admin Slack Alerts

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


Purpose: any infrastructure problem should notify the SentinelGrid Admin Slack channel.

- Channel: create or reuse a private `#sentinelgrid-admin` channel and keep on-call engineers in it.
- Webhook: add a Slack app → Incoming Webhooks → allow posting to `#sentinelgrid-admin`; copy the webhook URL.
- Env var: store the webhook URL as `SLACK_ADMIN_WEBHOOK_URL` in the runtime environment (docker-compose `.env`, secrets manager, or CI/CD variables).
- CLI helper: use `scripts/notify_slack_admin.sh "Infra alert: <details>"` to push a message. The script fails fast if the webhook is missing.
- Automation: wire health checks and infra monitors to call the script (or reuse the same webhook) so outages, restarts, and certificate/Keycloak issues reach the channel immediately.

Placement rule reminder: docs live under `docs/` (only `README.md` in repo root); scripts live in `scripts/`.
