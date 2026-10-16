export interface TrustArtifactDefinition {
  id: string;
  templateKey: string;
  templateName: string;
  title: string;
  audience: string;
  summary: string;
  delivery: string;
  refreshCadence: string;
  sections: string[];
}

export const TRUST_ARTIFACTS: TrustArtifactDefinition[] = [
  {
    id: "customer_security_review",
    templateKey: "smb_customer_security_review_pack",
    templateName: "SMB Customer Security Review Pack",
    title: "Customer Security Review Pack",
    audience: "Prospects, customers, and procurement teams",
    summary:
      "A concise trust-facing export that turns live detections, criteria coverage, and control checks into a readable security review packet.",
    delivery: "Generate as PDF or CSV and share with an expiring link from the compliance reports view.",
    refreshCadence: "Refresh before customer reviews, renewals, or security questionnaires.",
    sections: [
      "Security review overview",
      "Priority criteria snapshot",
      "Top detection sources",
    ],
  },
  {
    id: "audit_readiness",
    templateKey: "smb_audit_readiness_pack",
    templateName: "SMB Audit Readiness Pack",
    title: "Audit Readiness Pack",
    audience: "Auditors, internal compliance owners, and customer trust teams",
    summary:
      "An auditor-friendly view of readiness, priority criteria, mapped detections, and control checks tied back to live platform activity.",
    delivery: "Generate on demand as PDF or CSV for audit prep and evidence handoff.",
    refreshCadence: "Use monthly, before audits, or after material remediation work.",
    sections: [
      "Audit readiness overview",
      "Priority SOC 2 criteria",
      "Key detections feeding audit evidence",
      "Control checks feeding audit evidence",
    ],
  },
  {
    id: "evidence_attachment",
    templateKey: "smb_evidence_attachment_export",
    templateName: "SMB Evidence Attachment Export",
    title: "Evidence Attachment Export",
    audience: "Auditors, customers requesting proof, and internal control owners",
    summary:
      "An evidence-oriented export that highlights criteria requiring updates and the supporting signals that can be attached to audit or questionnaire workflows.",
    delivery: "Generate as PDF or CSV when an auditor or customer asks for supporting evidence.",
    refreshCadence: "Refresh whenever evidence coverage changes or a review packet is sent.",
    sections: [
      "Evidence coverage overview",
      "Criteria requiring evidence updates",
      "Mapped detections",
      "Mapped control checks",
    ],
  },
];

export const TRUST_ARTIFACT_TEMPLATE_KEYS = new Set(
  TRUST_ARTIFACTS.map((artifact) => artifact.templateKey)
);

export function slugifyTemplateName(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .replace(/&/g, "and")
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
}

export function isTrustArtifactTemplateKey(value?: string | null): boolean {
  return Boolean(value && TRUST_ARTIFACT_TEMPLATE_KEYS.has(value));
}
