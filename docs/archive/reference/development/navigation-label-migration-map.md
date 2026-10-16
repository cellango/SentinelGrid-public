# Dashboard Navigation Migration Map

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


## Section-Level Mapping

| Previous Sidebar Section | Current Home | Notes |
| --- | --- | --- |
| Prioritize | Detect | Queue-first detection work now lives under a single workflow label. |
| Investigate | Detect | Graph, telemetry, scans, and detection coverage now sit with the rest of the detection workflow. |
| Respond | Respond | Kept as a primary workflow. |
| Harden | Respond or Govern | Identity response tasks moved to `Respond`; posture moved to `Govern`. |
| Prove & Report | Govern | Compliance, reporting, and AI governance now sit under a single governance workflow. |
| Operate Platform | Header user menu | Admin and internal-only destinations are still available, but removed from the primary sidebar scan path. |

## Destination-Level Mapping

| Previous Label | Current Home |
| --- | --- |
| Now | Detect |
| Alert Queue | Detect |
| Incident Queue | Detect |
| Security Graph | Detect |
| Telemetry Search | Detect |
| Detection Coverage | Detect |
| Identity Events | Detect |
| Exposure Scans | Detect |
| Pen Tests | Detect |
| War Room | Respond |
| Response Playbooks | Respond |
| People & Access | Respond |
| Privileged Access | Respond |
| Access Reviews | Respond |
| Cloud Posture | Govern |
| Compliance | Govern |
| Reports | Govern |
| AI Activity | Govern |
| AI Governance | Govern |
| IAM Reports | Govern |
| Partner Console | Header user menu > Admin |
| Revenue & Activation | Header user menu > Admin as `Platform Operations` |
| Settings | Header user menu > Workspace as `Usage & Billing` |
| Configure | Header user menu > Workspace as `Resume Setup` |

## Support Notes

- Canonical primary workflows are now `Detect`, `Respond`, and `Govern`.
- Secondary admin destinations are intentionally still reachable, but they no longer compete with operator workflows in the sidebar.
- Support docs and release notes should refer to `Platform Operations` instead of `Revenue & Activation` when pointing users to the admin menu.
