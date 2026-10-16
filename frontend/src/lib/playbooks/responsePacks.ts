import type { Incident } from '@/lib/api/incidents';
import type { Playbook } from '@/lib/api/playbooks';
import type { Alert } from '@/lib/api/siem';
import type { CanonicalStoryDomain } from '@/lib/security/story';

export interface ResponsePackDefinition {
  id: string;
  label: string;
  summary: string;
  operatorGoal: string;
  recommendedOwner: string;
  recommendedSla: string;
  storyDomains: CanonicalStoryDomain[];
  operatorRoute: string;
  operatorRouteLabel: string;
  attackPatterns: string[];
  playbookKeys: string[];
  signalCategories: string[];
  findingTypes?: string[];
  keywords: string[];
  mitreTactics?: string[];
  firstMoves: string[];
  successChecks: string[];
}

export interface MatchedResponsePack {
  pack: ResponsePackDefinition;
  score: number;
  reasons: string[];
  playbooks: Playbook[];
  primaryPlaybook?: Playbook;
}

export const RESPONSE_PACKS: ResponsePackDefinition[] = [
  {
    id: 'account_takeover',
    label: 'Account takeover containment',
    summary: 'Contain risky sign-ins, session abuse, password-spray activity, and MFA bypass attempts before they turn into broader identity compromise.',
    operatorGoal: 'Confirm the identity blast radius, contain live access, and hand off owner actions in one flow.',
    recommendedOwner: 'Identity admin or help desk lead',
    recommendedSla: '4 hour containment target',
    storyDomains: ['identity', 'endpoint', 'security'],
    operatorRoute: '/dashboard/iam/people',
    operatorRouteLabel: 'Open identity workbench',
    attackPatterns: ['account takeover', 'password spray', 'mfa fatigue', 'suspicious login'],
    playbookKeys: ['ACCOUNT-COMPROMISE', 'PASSWORD-SPRAY', 'MFA-BYPASS', 'SUSPICIOUS-LOGIN', 'SUSPICIOUS_LOGIN_BASIC'],
    signalCategories: ['identity', 'iam', 'authentication', 'access', 'suspicious_login'],
    keywords: ['account compromise', 'suspicious login', 'impossible travel', 'password spray', 'mfa fatigue', 'session hijack', 'risky sign-in'],
    mitreTactics: ['Credential Access', 'Initial Access', 'Persistence'],
    firstMoves: [
      'Validate the impacted identity, session history, and recently elevated access.',
      'Require credential reset or revoke the active session if the account is still exposed.',
      'Assign ownership and confirm downstream ticket routing before the case stalls.',
    ],
    successChecks: [
      'The risky identity has a named owner and an SLA.',
      'Live sessions are revoked or the identity is otherwise contained.',
      'Follow-up review is scheduled for related admin roles and affected apps.',
    ],
  },
  {
    id: 'phishing_mailbox_compromise',
    label: 'Mailbox compromise response',
    summary: 'Handle phishing-driven mailbox compromise, malicious inbox rules, and email-delivered credential theft with a repeatable SMB play.',
    operatorGoal: 'Contain the mailbox, scope message spread, and coordinate user follow-up quickly.',
    recommendedOwner: 'Email admin or help desk lead',
    recommendedSla: 'Same-day containment target',
    storyDomains: ['identity', 'application', 'security'],
    operatorRoute: '/dashboard/alerts',
    operatorRouteLabel: 'Open email-driven alerts',
    attackPatterns: ['phishing', 'mailbox compromise', 'malicious inbox rule', 'credential theft'],
    playbookKeys: ['PHISH-USER', 'PHISH-GATEWAY'],
    signalCategories: ['email', 'phishing', 'identity', 'application'],
    keywords: ['phish', 'mailbox', 'inbox rule', 'oauth consent', 'email compromise', 'malicious email'],
    mitreTactics: ['Initial Access', 'Collection'],
    firstMoves: [
      'Confirm the affected mailbox, forwarding rules, and high-risk message activity.',
      'Isolate the compromised user path by rotating credentials and reviewing granted apps.',
      'Coordinate user communications and ticket handoff while preserving evidence.',
    ],
    successChecks: [
      'The compromised mailbox path is contained.',
      'Forwarding or rule abuse is reviewed and cleaned up.',
      'The user-facing follow-up and downstream ticket are already assigned.',
    ],
  },
  {
    id: 'ransomware_containment',
    label: 'Ransomware containment',
    summary: 'Drive a fast endpoint-led response for ransomware behaviors, malware execution, beaconing, or an EDR control gap.',
    operatorGoal: 'Isolate the endpoint path, preserve evidence, and move from triage into containment without delay.',
    recommendedOwner: 'Endpoint lead or MSP operator',
    recommendedSla: '2 hour containment target',
    storyDomains: ['endpoint', 'identity', 'security'],
    operatorRoute: '/dashboard/endpoint-protection',
    operatorRouteLabel: 'Open endpoint coverage',
    attackPatterns: ['ransomware', 'malware', 'beaconing', 'agent offline'],
    playbookKeys: ['MALWARE-CONTAIN', 'ENDPOINT-ISOLATE', 'AGENT-OFFLINE', 'C2/BEACON'],
    signalCategories: ['endpoint', 'malware', 'ransomware', 'edr', 'host'],
    keywords: ['ransomware', 'encryption', 'beacon', 'malware', 'endpoint isolate', 'edr offline', 'lateral movement'],
    mitreTactics: ['Execution', 'Impact', 'Command and Control'],
    firstMoves: [
      'Identify the affected host and any linked identities before containment starts.',
      'Isolate or contain the endpoint path and escalate when an agent or control is offline.',
      'Capture analyst notes and ownership so containment does not remain tribal knowledge.',
    ],
    successChecks: [
      'The endpoint path is isolated or otherwise contained.',
      'Owner, SLA, and downstream ticket are set for follow-through.',
      'Related identities or additional hosts are reviewed before closing the incident.',
    ],
  },
  {
    id: 'cloud_exposure',
    label: 'Cloud exposure hardening',
    summary: 'Use one saved response pack for public storage, internet-exposed data paths, disabled logging, and high-risk cloud misconfigurations.',
    operatorGoal: 'Reduce exposure fast, record the owner, and keep the fix tied to the same evidence story.',
    recommendedOwner: 'Cloud platform owner',
    recommendedSla: '24 hour remediation target',
    storyDomains: ['cloud', 'security'],
    operatorRoute: '/dashboard/cloud-security',
    operatorRouteLabel: 'Open cloud posture',
    attackPatterns: ['public storage', 'public database', 'logging disabled', 'privileged pod'],
    playbookKeys: ['CLOUD-PUBLIC-STORAGE', 'DB-PUBLIC-EXPOSED', 'LOGGING-DISABLED', 'K8S-PRIV-POD'],
    signalCategories: ['cloud', 'storage', 'database', 'kubernetes', 'network', 'data'],
    keywords: ['public bucket', 'public storage', 'public database', 'logging disabled', 'privileged pod', 'internet exposed'],
    mitreTactics: ['Discovery', 'Collection'],
    firstMoves: [
      'Confirm the exposed resource, tenant owner, and any linked identity or ticket context.',
      'Prioritize public data paths and disabled telemetry before lower-risk posture gaps.',
      'Create a fix owner and due date so posture findings become actual operator work.',
    ],
    successChecks: [
      'The exposed cloud path has an owner and due date.',
      'A direct remediation path or ticket is already open.',
      'Supporting evidence is ready for trust or audit follow-up if needed.',
    ],
  },
  {
    id: 'secret_exposure',
    label: 'Secret and code exposure',
    summary: 'Respond to leaked secrets, high-risk IaC findings, and application-side exposure without splitting the operator story across tools.',
    operatorGoal: 'Contain exposed credentials, route code or IaC fixes, and preserve one evidence trail.',
    recommendedOwner: 'AppSec or platform engineering lead',
    recommendedSla: '1 business day remediation target',
    storyDomains: ['application', 'cloud', 'security'],
    operatorRoute: '/dashboard/scans',
    operatorRouteLabel: 'Open scanning and fixes',
    attackPatterns: ['secret exposure', 'high-risk IaC', 'code leak', 'build pipeline risk'],
    playbookKeys: ['SECRET-EXPOSURE', 'IAC-HIGH-RISK', 'SAST-HIGH'],
    signalCategories: ['application', 'repo', 'secret', 'iac', 'code'],
    keywords: ['secret exposure', 'hardcoded secret', 'repository leak', 'iac risk', 'pipeline secret', 'sast high'],
    mitreTactics: ['Credential Access', 'Initial Access'],
    firstMoves: [
      'Confirm which secret, repo, or build path is exposed and who owns the fix.',
      'Rotate or revoke exposed credentials before backlog cleanup begins.',
      'Send the right engineering handoff with evidence already attached.',
    ],
    successChecks: [
      'Exposed secrets are rotated or revoked.',
      'The engineering owner has a routed task with linked evidence.',
      'Residual scanning work is tracked to closure, not left as a note.',
    ],
  },
  {
    id: 'ai_prompt_injection_containment',
    label: 'AI prompt injection containment',
    summary: 'Respond to prompt injection, jailbreak, and guardrail-bypass activity before unsafe prompts turn into tool execution or data exposure.',
    operatorGoal: 'Confirm the risky prompt path, review downstream tool exposure, and contain repeated abuse quickly.',
    recommendedOwner: 'AI app owner or security lead',
    recommendedSla: '4 hour containment target',
    storyDomains: ['ai', 'application', 'security'],
    operatorRoute: '/dashboard/ai-security/events',
    operatorRouteLabel: 'Review AI runtime events',
    attackPatterns: ['prompt injection', 'jailbreak', 'guardrail bypass', 'unsafe prompt'],
    playbookKeys: ['AI-PROMPT-INJECTION', 'AI-JAILBREAK-BURST'],
    signalCategories: ['prompt_injection', 'jailbreak', 'guardrail_bypass'],
    findingTypes: ['prompt_injection'],
    keywords: ['prompt injection', 'jailbreak', 'unsafe prompt', 'guardrail bypass', 'adversarial prompt', 'system prompt'],
    mitreTactics: ['Initial Access', 'Execution'],
    firstMoves: [
      'Confirm the AI app, user path, and the exact prompt or conversation that triggered the finding.',
      'Review whether tools, retrieval, or downstream actions were reachable from the abused prompt path.',
      'Route the case to the AI owner with containment guidance before the same prompt pattern is reused.',
    ],
    successChecks: [
      'The risky prompt path has a named owner and a due date.',
      'Any exposed tool or downstream execution path is contained or explicitly reviewed.',
      'The operator story shows the prompt context, owner handoff, and follow-up action.',
    ],
  },
  {
    id: 'ai_data_leakage_response',
    label: 'AI data leakage response',
    summary: 'Use one saved motion for sensitive data exposure, secret leakage, and policy misses that let customer data reach external models.',
    operatorGoal: 'Confirm what data left the boundary, contain the prompt path, and capture the evidence for policy and trust follow-up.',
    recommendedOwner: 'AI app owner or privacy lead',
    recommendedSla: 'Same-day review target',
    storyDomains: ['ai', 'application', 'security'],
    operatorRoute: '/dashboard/compliance/ai-activity',
    operatorRouteLabel: 'Review AI activity evidence',
    attackPatterns: ['sensitive data exposure', 'secret leakage', 'pii leakage', 'external llm exposure'],
    playbookKeys: ['AI-DATA-LEAK'],
    signalCategories: ['sensitive_data_exposure', 'data_leak', 'secret_exposure', 'pii_exposure'],
    findingTypes: ['sensitive_data_exposure'],
    keywords: ['sensitive data', 'data leak', 'secret material', 'customer data', 'pii', 'credential leak', 'model output'],
    mitreTactics: ['Collection', 'Exfiltration'],
    firstMoves: [
      'Confirm which AI app, provider, and user path sent sensitive data outside the expected boundary.',
      'Contain the prompt path or provider route before the same data class is sent again.',
      'Attach the evidence trail so policy owners, privacy, and customer-trust teams can reuse the same story.',
    ],
    successChecks: [
      'The exposed AI path has a named owner and a due date.',
      'The affected prompt or provider route is contained, blocked, or otherwise reviewed.',
      'Evidence is ready for downstream trust, audit, or customer security-review follow-up.',
    ],
  },
  {
    id: 'ai_policy_and_tool_misuse',
    label: 'AI policy and tool misuse',
    summary: 'Handle blocked policy violations, unsafe tool actions, and model misuse with one operator pack tied to the AI control plane.',
    operatorGoal: 'Decide whether the policy is correct, whether the app is misconfigured, and who owns the fix before violations become normal noise.',
    recommendedOwner: 'AI platform owner or security lead',
    recommendedSla: '1 business day remediation target',
    storyDomains: ['ai', 'application', 'security'],
    operatorRoute: '/dashboard/ai-security/policies',
    operatorRouteLabel: 'Open AI policy controls',
    attackPatterns: ['policy violation', 'unsafe tool action', 'tool misuse', 'model abuse'],
    playbookKeys: ['AI-POLICY-VIOLATION', 'AI-UNSAFE-TOOL-ACTION', 'AI-TOOL-CALL-ANOMALY'],
    signalCategories: ['policy_violation', 'unsafe_tool_action', 'tool_call_anomaly'],
    findingTypes: ['policy_violation'],
    keywords: ['policy violation', 'unsafe tool', 'tool misuse', 'tool call', 'guardrail policy', 'blocked model', 'unapproved action'],
    mitreTactics: ['Defense Evasion', 'Execution'],
    firstMoves: [
      'Confirm whether the event represents a true policy violation, an unsafe tool call, or a guardrail tuning gap.',
      'Review the app policy and owner workflow before operators normalize the same blocked behavior.',
      'Capture the policy decision, owner, and follow-up task in the same story used for the rest of the platform.',
    ],
    successChecks: [
      'The violated policy or unsafe tool path has an explicit owner.',
      'The fix is routed as a policy change, app change, or operator exception rather than a vague note.',
      'The same issue can be tracked across runtime events, incidents, and leadership reporting.',
    ],
  },
];

type ResponsePackContext = {
  categories: string[];
  findingTypes: string[];
  domains: Set<CanonicalStoryDomain>;
  text: string;
  playbookTokens: string[];
  mitreTokens: string[];
};

function normalizeToken(value: unknown): string {
  if (value == null) return '';
  return String(value)
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, ' ')
    .trim();
}

function uniqueStrings(values: Array<string | undefined | null>): string[] {
  return Array.from(new Set(values.map((value) => normalizeToken(value)).filter(Boolean)));
}

function playbookSearchText(playbook: Playbook): string {
  return uniqueStrings([
    playbook.id,
    playbook.name,
    playbook.playbook_key,
    playbook.category,
    ...(playbook.tags || []),
  ]).join(' ');
}

function matchPackPlaybooks(pack: ResponsePackDefinition, playbooks: Playbook[]): Playbook[] {
  return playbooks
    .filter((playbook) => {
      const searchText = playbookSearchText(playbook);
      return pack.playbookKeys.some((token) => searchText.includes(normalizeToken(token)));
    })
    .sort((left, right) => {
      const leftPrimary = normalizeToken(left.playbook_key || left.name);
      const rightPrimary = normalizeToken(right.playbook_key || right.name);
      const leftRank = pack.playbookKeys.findIndex((token) => leftPrimary.includes(normalizeToken(token)));
      const rightRank = pack.playbookKeys.findIndex((token) => rightPrimary.includes(normalizeToken(token)));
      const normalizedLeftRank = leftRank === -1 ? Number.MAX_SAFE_INTEGER : leftRank;
      const normalizedRightRank = rightRank === -1 ? Number.MAX_SAFE_INTEGER : rightRank;
      return normalizedLeftRank - normalizedRightRank;
    });
}

function scorePack(pack: ResponsePackDefinition, context: ResponsePackContext): { score: number; reasons: string[] } {
  let score = 0;
  const reasons: string[] = [];

  const findingTypeMatch = pack.findingTypes?.find((token) =>
    context.findingTypes.some((candidate) => candidate.includes(normalizeToken(token)))
  );
  if (findingTypeMatch) {
    score += 5;
    reasons.push(`${findingTypeMatch.replace(/_/g, ' ')} finding`);
  }

  const playbookMatch = pack.playbookKeys.find((token) =>
    context.playbookTokens.some((candidate) => candidate.includes(normalizeToken(token)))
  );
  if (playbookMatch) {
    score += 6;
    reasons.push(`${playbookMatch.toLowerCase().replace(/-/g, ' ')} mapping`);
  }

  const categoryMatch = pack.signalCategories.find((token) =>
    context.categories.some((candidate) => candidate.includes(normalizeToken(token)))
  );
  if (categoryMatch) {
    score += 3;
    reasons.push(`${categoryMatch.replace(/_/g, ' ')} signal`);
  }

  const keywordMatches = pack.keywords.filter((keyword) => context.text.includes(normalizeToken(keyword)));
  if (keywordMatches.length > 0) {
    score += Math.min(3, keywordMatches.length);
    reasons.push(`${keywordMatches[0]} indicator`);
  }

  const domainMatch = pack.storyDomains.find((domain) => context.domains.has(domain));
  if (domainMatch) {
    score += 2;
    reasons.push(`${domainMatch} context`);
  }

  const tacticMatch = pack.mitreTactics?.find((tactic) =>
    context.mitreTokens.some((candidate) => candidate.includes(normalizeToken(tactic)))
  );
  if (tacticMatch) {
    score += 1;
    reasons.push(`${tacticMatch.toLowerCase()} tactic`);
  }

  return {
    score,
    reasons: Array.from(new Set(reasons)).slice(0, 3),
  };
}

function buildAlertContext(alert: Alert): ResponsePackContext {
  const rawPayload = alert.raw_payload || {};
  const alternatePlaybooks = Array.isArray(rawPayload.recommended_playbooks)
    ? rawPayload.recommended_playbooks.map((item: any) => item?.id || item?.key || item?.name || item)
    : [];
  const findingType = rawPayload.finding?.type || rawPayload.sg?.finding_type;

  return {
    categories: uniqueStrings([
      alert.category,
      rawPayload.category,
      rawPayload.alert_type,
      rawPayload.sg?.category,
      findingType,
    ]),
    findingTypes: uniqueStrings([findingType]),
    domains: new Set(alert.story_domains || []),
    text: uniqueStrings([
      alert.title,
      alert.description,
      alert.source,
      alert.user_identifier,
      alert.asset_id,
      alert.mitre_tactic,
      alert.mitre_technique,
      rawPayload.reason,
      rawPayload.summary,
      rawPayload.title,
      rawPayload.event_type,
      rawPayload.violation_reason,
      rawPayload.ai?.app_id,
      rawPayload.ai?.provider,
      rawPayload.ai?.model,
      rawPayload.ai?.violation_reason,
      findingType,
      ...(alert.entities || []).map((entity) => entity.label),
      ...(alert.evidence || []).map((item) => item.title),
      ...alternatePlaybooks,
    ]).join(' '),
    playbookTokens: uniqueStrings([
      alert.recommended_playbook,
      alert.recommended_playbook_id,
      alert.recommended_playbook_key,
      rawPayload.recommended_playbook,
      rawPayload.recommended_playbook_id,
      rawPayload.recommended_playbook_key,
      rawPayload.playbook_id,
      rawPayload.sg?.playbook_id,
      ...alternatePlaybooks,
    ]),
    mitreTokens: uniqueStrings([alert.mitre_tactic, alert.mitre_technique, ...(alert.mitre_tactics || []), ...(alert.mitre_techniques || [])]),
  };
}

function buildIncidentContext(incident: Incident): ResponsePackContext {
  const rawPayload = incident.raw_payload || {};
  const relatedTitles = (incident.related_detections || []).flatMap((item) => [item.id, item.title]);
  const findingType = rawPayload.finding?.type || rawPayload.sg?.finding_type;

  return {
    categories: uniqueStrings([
      incident.source,
      rawPayload.category,
      rawPayload.incident_type,
      rawPayload.sg?.category,
      rawPayload.alert_type,
      findingType,
    ]),
    findingTypes: uniqueStrings([findingType]),
    domains: new Set(incident.story_domains || []),
    text: uniqueStrings([
      incident.title,
      incident.description,
      rawPayload.summary,
      rawPayload.reason,
      rawPayload.event_type,
      rawPayload.violation_reason,
      rawPayload.ai?.app_id,
      rawPayload.ai?.provider,
      rawPayload.ai?.model,
      rawPayload.ai?.violation_reason,
      findingType,
      incident.assigned_to,
      incident.recommended_playbook,
      incident.recommended_playbook_key,
      ...(incident.entities || []).map((entity) => entity.label),
      ...(incident.evidence || []).map((item) => item.title),
      ...relatedTitles,
    ]).join(' '),
    playbookTokens: uniqueStrings([
      incident.recommended_playbook,
      incident.recommended_playbook_id,
      incident.recommended_playbook_key,
      rawPayload.recommended_playbook,
      rawPayload.recommended_playbook_id,
      rawPayload.recommended_playbook_key,
      rawPayload.playbook_id,
      rawPayload.sg?.playbook_id,
    ]),
    mitreTokens: uniqueStrings([...(incident.mitre_tactics || []), ...(incident.mitre_techniques || [])]),
  };
}

function matchPacks(context: ResponsePackContext, playbooks: Playbook[]): MatchedResponsePack[] {
  return RESPONSE_PACKS.map((pack) => {
    const playbookMatches = matchPackPlaybooks(pack, playbooks);
    const match = scorePack(pack, context);
    if (playbookMatches.length > 0) {
      match.score += 1;
    }
    return {
      pack,
      score: match.score,
      reasons: match.reasons,
      playbooks: playbookMatches,
      primaryPlaybook: playbookMatches[0],
    };
  })
    .filter((item) => item.score >= 3)
    .sort((left, right) => {
      if (right.score !== left.score) {
        return right.score - left.score;
      }
      return right.playbooks.length - left.playbooks.length;
    });
}

export function getResponsePackById(id?: string | null): ResponsePackDefinition | undefined {
  if (!id) return undefined;
  return RESPONSE_PACKS.find((pack) => pack.id === id);
}

export function getResponsePackPlaybooks(packId: string, playbooks: Playbook[]): Playbook[] {
  const pack = getResponsePackById(packId);
  if (!pack) return [];
  return matchPackPlaybooks(pack, playbooks);
}

export function matchResponsePacksForAlert(alert: Alert, playbooks: Playbook[] = []): MatchedResponsePack[] {
  return matchPacks(buildAlertContext(alert), playbooks);
}

export function matchResponsePacksForIncident(incident: Incident, playbooks: Playbook[] = []): MatchedResponsePack[] {
  return matchPacks(buildIncidentContext(incident), playbooks);
}
