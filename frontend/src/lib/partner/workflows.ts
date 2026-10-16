export type PartnerDeliveryMode = "advisory" | "co_managed" | "partner_led";

export const partnerDeliveryModes = [
  {
    id: "advisory" as PartnerDeliveryMode,
    label: "Advisory",
    summary: "Partner monitors, recommends, and reports. Customer owns approvals and remediation.",
    partnerOwns: ["Health review", "Prioritization", "Reporting"],
    customerOwns: ["Approvals", "Remediation execution", "Final risk decisions"],
  },
  {
    id: "co_managed" as PartnerDeliveryMode,
    label: "Co-Managed",
    summary: "Partner drives daily triage and coordination. Customer retains approval control for sensitive actions.",
    partnerOwns: ["Daily triage", "Incident coordination", "Ticket routing"],
    customerOwns: ["Sensitive approvals", "Shared ownership", "Business-impact decisions"],
  },
  {
    id: "partner_led" as PartnerDeliveryMode,
    label: "Partner-Led",
    summary: "Partner runs the operating queue inside agreed guardrails while the customer retains oversight.",
    partnerOwns: ["Queue ownership", "Routine remediation", "Reporting cadence"],
    customerOwns: ["Oversight", "Exceptions", "Delegation policy"],
  },
];

export const partnerWorkflowStages = [
  {
    title: "Cross-tenant review",
    description: "Start in the partner console to identify critical tenants, SLA drift, and customers that need attention today.",
  },
  {
    title: "Explicit tenant context",
    description: "Enter tenant context deliberately before taking tenant-scoped actions, notes, or ticket updates.",
  },
  {
    title: "Delegated response",
    description: "Run partner-approved work, request customer approval for sensitive changes, and keep the audit trail intact.",
  },
  {
    title: "Client reporting",
    description: "Turn the same incident, compliance, and trust evidence into customer updates and service reviews.",
  },
];

export const partnerOperatingRules = [
  "Cross-tenant views stay summary-oriented and read-heavy.",
  "Tenant-scoped writes only happen after explicit tenant-context entry.",
  "Sensitive actions follow the tenant delivery mode and approval policy.",
  "Audit history records both the actor and the tenant context for partner actions.",
];
