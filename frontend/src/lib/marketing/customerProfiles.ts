export type CustomerProfile = {
  key: string;
  label: string;
  companyType: string;
  companySize: string;
  role: string;
  packageFit: string;
  headline: string;
  summary: string;
  primaryChallenge: string;
  deploymentPath: string;
  firstWeekOutcome: string;
  outcomeHighlight: string;
  measurableOutcome: string;
  proofPoints: string[];
  storyQuote: string;
  storyQuoteLabel: string;
};

export const customerProfiles: CustomerProfile[] = [
  {
    key: "b2b_saas",
    label: "B2B SaaS team under customer review pressure",
    companyType: "B2B SaaS",
    companySize: "120-250 employees",
    role: "Security lead who also owns trust and customer review prep",
    packageFit: "Protect + Defend + Comply",
    headline: "Replace spreadsheet evidence and disconnected security tools with one operating record.",
    summary:
      "This team needs cloud and identity visibility, faster incident follow-up, and customer-ready evidence without buying a separate GRC stack first.",
    primaryChallenge:
      "Customer questionnaires, audit prep, and day-to-day response work were being rebuilt in different tools and documents.",
    deploymentPath:
      "Connect AWS plus Microsoft 365 / Entra first, then turn the same findings into evidence workflows and review-ready exports.",
    firstWeekOutcome:
      "AWS and Microsoft 365 are connected, one prioritized finding is assigned, and the same operating record can feed an audit export or customer review packet.",
    outcomeHighlight: "Shorter path from detection to customer-facing evidence",
    measurableOutcome: "One operating record supports both remediation and trust follow-up.",
    proofPoints: [
      "Audit-facing exports from live detections",
      "Access review and evidence workflows built into the same platform",
      "Trust-center artifacts without rebuilding the story in slides",
    ],
    storyQuote:
      "We needed security work that could survive contact with a customer questionnaire without rewriting the whole story every time.",
    storyQuoteLabel: "Representative security lead, B2B SaaS, 120-250 employees",
  },
  {
    key: "lean_it_security",
    label: "Lean IT-led security team",
    companyType: "Cloud-first SMB",
    companySize: "50-150 employees",
    role: "IT or operations owner carrying security alongside other responsibilities",
    packageFit: "Protect + Defend",
    headline: "Stop living across cloud consoles, identity reports, endpoint tools, and ticket queues.",
    summary:
      "This team needs immediate visibility, guided remediation, and an easier way to explain priorities without building a formal SOC.",
    primaryChallenge:
      "The team was switching between admin consoles and point tools but still lacked one clean list of what mattered most.",
    deploymentPath:
      "Use the default SMB rollout path, then add endpoint telemetry and response workflows once the first queue is healthy.",
    firstWeekOutcome:
      "The team sees one queue item with identity, cloud, and response context instead of three separate admin screens and starts from a guided response recommendation.",
    outcomeHighlight: "Faster time to first action with less dashboard switching",
    measurableOutcome: "One prioritized queue item replaces three disconnected admin views.",
    proofPoints: [
      "One queue for cloud, identity, endpoint, posture, and AI risk",
      "Built-in ownership, SLAs, and downstream ticketing",
      "Predictable package pricing instead of point-tool sprawl",
    ],
    storyQuote:
      "The bar was simple: tell us what matters first and give us a response path we can actually run without building a SOC.",
    storyQuoteLabel: "Representative IT and security owner, cloud-first SMB, 50-150 employees",
  },
  {
    key: "ai_using_product_team",
    label: "AI-using product team with security and policy pressure",
    companyType: "Modern software or services company",
    companySize: "100-300 employees",
    role: "Security or platform owner supporting both infrastructure and AI application rollout",
    packageFit: "Protect + Defend + AI Shield",
    headline: "Handle AI runtime security in the same operator flow as the rest of the platform.",
    summary:
      "This team does not want a separate AI dashboard, separate response model, or separate trust narrative for prompt injection, data leakage, and policy misuse.",
    primaryChallenge:
      "The company was about to add AI security, but doing it with another detached tool would have created another review, another workflow, and another report stream.",
    deploymentPath:
      "Bring AI Shield into the same queue and response workflow already used for cloud, identity, and endpoint work, then layer in Comply only if governance evidence is part of the deal.",
    firstWeekOutcome:
      "AI events land in the same queue, the same response packs are available, and leadership gets an AI governance summary without creating a parallel workflow.",
    outcomeHighlight: "AI risk becomes part of normal security operations instead of a side program",
    measurableOutcome: "AI incidents and governance reporting run on the same platform record.",
    proofPoints: [
      "AI incidents promoted into the main incident model",
      "AI-specific response packs on the same playbook surface",
      "Controlled launch scope for the supported provider path",
    ],
    storyQuote:
      "If AI security meant another dashboard and another board deck, we were going to lose the operational argument before we started.",
    storyQuoteLabel:
      "Representative platform and security owner, modern software company, 100-300 employees",
  },
];
