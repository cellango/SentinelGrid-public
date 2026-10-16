# Posture Management & Security Score (Customer Guide)

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


This document explains how SentinelGrid computes the Security Score shown in the posture dashboard. It covers inputs, calculations, data sources, and how to interpret the results.

## What the Security Score represents
- A 0–100 score summarizing your current security posture.
- Broken down by domain (Cloud, App, Identity, Endpoint; Data/AI reserved for future use).
- Adjusted by data coverage and penalized for open critical/high incidents.
- Snapshots are stored to show trends over time.

## Inputs
- **Posture findings**: Open or in-progress findings pulled from connected scanners and cloud posture sources (table `posture_findings`).
- **Domain mapping**: Each finding is mapped to a domain using the `posture_domain_mapping` table (seeded defaults include cloud posture scanners→cloud/identity, application security scanners→app, endpoint/edr categories→endpoint, ai→ai).
- **Severity weights**: Weighted by `posture_severity_weight` (defaults: critical=40, high=20, medium=5, low=1, info=0) with overrides supported in the DB.
- **Coverage signals** (last 7 days):
  - Cloud: distinct cloud accounts with recent findings ÷ total accounts.
  - App: distinct repos scanned by application security pipelines (static code analysis, IaC security, secret scanning, container/image scanning, dynamic app testing) ÷ total repos.
  - Endpoint: active agents (last_seen) ÷ total agents.
- **Incident context**: Open critical/high incidents from the `incidents` table.

## How the score is computed
1) **Risk per finding**: severity weight × asset multiplier (if criticality/data_classification present in the finding/asset metadata).
2) **Domain aggregation**: For each domain:
   - `risk` = sum of finding risks.
   - `open` = count of open/in-progress findings.
   - Domain score = `round(100 * (1 - min(1, risk / max(20, open*20))))`.
3) **Coverage adjustment**: Domain scores are multiplied by coverage (0–1) to produce `score_adjusted`; coverage details are exposed.
4) **Overall score (weighted)**: Weighted average of domain scores (adjusted when present):
   - Weights: Cloud 3.0, App 3.0, Identity 2.0, Endpoint 1.0, Data 1.0, AI 1.0.
5) **Incident penalty**: Subtract up to 20 points based on open incidents: `(criticals * 5) + (highs * 3)`, capped at 20.
6) **Top risks**: The five highest-weight findings (severity × asset context) are returned to highlight what’s pulling the score down.
7) **Snapshots**: Each run saves a snapshot (`posture_score_snapshot` + `posture_domain_score_snapshot`) for history and trend charts.
8) **Fallback**: If posture tables are unavailable (e.g., air-gapped demo), the service returns a static placeholder score so the UI can render.

## Data sources by domain
- **Cloud**: Cloud posture scanner findings, cloud account inventory, recent cloud scans.
- **App**: Application security pipelines (static code analysis, IaC security, secret scanning, container/image scanning, dynamic app testing).
- **Identity**: IAM-related findings (mapped via category/service keywords).
- **Endpoint**: Endpoint/EDR categories and active agent telemetry.
- **AI/Data**: Reserved for future AI/data posture; currently minimal influence unless mapped.

## Interpreting the score
- **High score (80–100)**: Low weighted risk and good coverage; few or no critical/high incidents.
- **Mid score (60–79)**: Moderate risk or gaps in coverage; open medium/high issues to review.
- **Low score (<60)**: High weighted risk, poor coverage, or open critical incidents; prioritize top risks and improve coverage.
- **Coverage matters**: Even with few findings, low coverage drags adjusted scores toward 0, reflecting limited visibility.
- **Incidents matter**: Open critical/high incidents apply an explicit penalty on the overall score.

## Improving your score
- Close or remediate high/critical findings (especially the top risks).
- Increase coverage: connect all cloud accounts, scan all key repos, and ensure agents are active.
- Reduce open critical/high incidents or close them in the incident queue.
- Keep domain mappings and severity weights tuned to match your risk model (via DB config tables).
- **Vulnerabilities specifically**:
  - App and image scanners (static code analysis, IaC security, secret scanning, container/image scanning, dynamic testing) and cloud misconfig findings are treated as posture findings; critical/high vulns carry higher severity weight, increasing domain risk.
  - To lift scores: prioritize remediating critical/high vulns, fix misconfigs flagged by cloud scanners, and re-run scans to update posture. Expanding scan coverage (more repos/images/cloud accounts) improves the coverage multiplier so fixed vulns raise the adjusted score faster.

## Remediation playbook
1) **Prioritize by impact**  
   - Work the top risks first (critical/high, exposed assets, sensitive data).  
   - Use domain scores to focus: e.g., low App score → address repo/image findings; low Cloud score → fix misconfigs on high-value accounts.

2) **Close the incident penalty loop**  
   - Resolve or close critical/high incidents in the incident queue; each open critical/high can subtract from the overall score.

3) **Improve coverage before rescoring**  
   - Cloud: onboard all accounts; ensure cloud posture scans cover them.  
   - App: run application security scans (static code, IaC, secrets, container/image, dynamic app testing) on all key repos/images; ensure CI jobs report back.  
   - Endpoint: deploy/activate agents everywhere; stale or offline agents drag endpoint coverage.

4) **Remediate and verify**  
   - Apply fixes, then re-run scans to refresh `posture_findings`; the score updates after rescans land.  
   - For noise/false positives, mark resolved in the scanner (or suppress in code) to keep findings out of `posture_findings`.

5) **Harden by domain**  
   - Identity: enforce MFA, least privilege, rotate keys, remove dormant accounts.  
   - Cloud: fix high-severity misconfigs (public buckets, wide-open security groups, missing encryption), enable logging.  
   - App: fix code/IaC secrets and critical vulns; add pre-merge scanning gates for critical/high.  
   - Endpoint: ensure EDR agents healthy and reporting; patch critical CVEs on endpoints.  
   - AI/Data (future domains): apply model guardrails and data access controls as they come online.

6) **Tune and align**  
   - Adjust severity weights and domain mappings in the DB if your risk model differs (e.g., weight endpoint higher).  
   - Define SLAs by severity (e.g., critical in 24h, high in 3d) and track burn-down against top risks.

7) **Automate workflow**  
   - Create tickets for critical/high findings; integrate with Jira/ServiceNow if used.  
   - Schedule periodic scans and posture refresh (snapshots already stored for trends).

## Where this runs
- Service: `backend/services/orchestrator/app/services/posture_scoring.py`.
- API: `/orchestrator/tenant/{tenant_id}/posture-score` (proxied by API Gateway).
