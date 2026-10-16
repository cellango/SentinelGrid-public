export type NistFramework = 'NIST SP 800-53' | 'NIST CSF';

export type NistControlInfo = {
  id: string;
  framework: NistFramework;
  title: string;
  summary: string;
  family?: string;
};

const NIST_800_53: Record<string, Omit<NistControlInfo, 'id'>> = {
  'AC-2': {
    framework: 'NIST SP 800-53',
    family: 'Access Control (AC)',
    title: 'Account Management',
    summary:
      'Organizations manage information system accounts through their lifecycle (create/enable/modify/disable/remove), define who can create accounts, and review accounts/privileges regularly to reduce the risk of unauthorized access.',
  },
  'AC-5': {
    framework: 'NIST SP 800-53',
    family: 'Access Control (AC)',
    title: 'Separation of Duties',
    summary:
      'Organizations separate duties and responsibilities among individuals to reduce the risk of fraud, abuse, or errors (e.g., no single person can both approve and execute sensitive changes).',
  },
  'AC-6': {
    framework: 'NIST SP 800-53',
    family: 'Access Control (AC)',
    title: 'Least Privilege',
    summary:
      'Users and processes are granted only the access needed to perform authorized tasks. Privileges are limited, time-bound where possible, and reviewed to reduce the impact of account compromise.',
  },
  'AC-7': {
    framework: 'NIST SP 800-53',
    family: 'Access Control (AC)',
    title: 'Unsuccessful Logon Attempts',
    summary:
      'Systems enforce controls after repeated failed logon attempts (e.g., lockouts, delays, or additional verification) to help detect and slow password guessing and credential stuffing.',
  },
  'IA-2': {
    framework: 'NIST SP 800-53',
    family: 'Identification and Authentication (IA)',
    title: 'Identification and Authentication (Organizational Users)',
    summary:
      'Users are uniquely identified and authenticated before being granted access. This commonly includes MFA and strong authentication policies for privileged and remote access.',
  },
  'IA-4': {
    framework: 'NIST SP 800-53',
    family: 'Identification and Authentication (IA)',
    title: 'Identifier Management',
    summary:
      'Organizations manage unique identifiers (usernames, service identities) to ensure identities are unambiguous, appropriately assigned, and maintained throughout their lifecycle.',
  },
  'IA-5': {
    framework: 'NIST SP 800-53',
    family: 'Identification and Authentication (IA)',
    title: 'Authenticator Management',
    summary:
      'Organizations manage authenticators (passwords, keys, tokens) including creation, distribution, rotation, revocation, and complexity requirements to reduce credential compromise.',
  },
  'IR-4': {
    framework: 'NIST SP 800-53',
    family: 'Incident Response (IR)',
    title: 'Incident Handling',
    summary:
      'Organizations establish and execute incident handling procedures, including preparation, detection/analysis, containment, eradication, and recovery—coordinating across people, process, and technology.',
  },
  'IR-5': {
    framework: 'NIST SP 800-53',
    family: 'Incident Response (IR)',
    title: 'Incident Monitoring',
    summary:
      'Organizations monitor and track incidents and related information to support effective response, ensure follow-through, and identify patterns or recurring issues.',
  },
  'IR-6': {
    framework: 'NIST SP 800-53',
    family: 'Incident Response (IR)',
    title: 'Incident Reporting',
    summary:
      'Incidents are reported to appropriate internal and external stakeholders (e.g., security leadership, legal/compliance, regulators) according to policy and severity.',
  },
  'AU-6': {
    framework: 'NIST SP 800-53',
    family: 'Audit and Accountability (AU)',
    title: 'Audit Review, Analysis, and Reporting',
    summary:
      'Organizations review and analyze audit logs to identify suspicious activity, investigate events, and report findings—supporting detection and incident response.',
  },
  'CA-7': {
    framework: 'NIST SP 800-53',
    family: 'Assessment, Authorization, and Monitoring (CA)',
    title: 'Continuous Monitoring',
    summary:
      'Organizations continuously monitor security controls and system changes to maintain awareness of security posture and detect deviations that increase risk.',
  },
  'CM-7': {
    framework: 'NIST SP 800-53',
    family: 'Configuration Management (CM)',
    title: 'Least Functionality',
    summary:
      'Systems are configured to provide only essential capabilities and services, reducing attack surface by disabling unnecessary features and software.',
  },
  'RA-3': {
    framework: 'NIST SP 800-53',
    family: 'Risk Assessment (RA)',
    title: 'Risk Assessment',
    summary:
      'Organizations conduct risk assessments to identify threats, vulnerabilities, likelihood, and impact, informing prioritization of controls and response activities.',
  },
  'SI-3': {
    framework: 'NIST SP 800-53',
    family: 'System and Information Integrity (SI)',
    title: 'Malicious Code Protection',
    summary:
      'Organizations deploy protections to detect, prevent, and eradicate malicious code (e.g., antivirus/EDR, scanning, update mechanisms) across endpoints and systems.',
  },
  'SI-4': {
    framework: 'NIST SP 800-53',
    family: 'System and Information Integrity (SI)',
    title: 'System Monitoring',
    summary:
      'Organizations monitor systems and communications to detect attacks, indicators of compromise, and unauthorized activity—often leveraging SIEM, EDR, and network telemetry.',
  },
};

const NIST_CSF: Record<string, Omit<NistControlInfo, 'id'>> = {
  'PR.AC': {
    framework: 'NIST CSF',
    title: 'Identity Management, Authentication and Access Control',
    summary:
      'Identities and credentials are managed, access is provisioned based on roles, and authentication/authorization controls are enforced to prevent unauthorized access.',
  },
  'PR.DS': {
    framework: 'NIST CSF',
    title: 'Data Security',
    summary:
      'Data is protected in transit and at rest, integrity is maintained, and sensitive data handling (classification, retention, disposal) reduces the risk of leakage or tampering.',
  },
  'PR.IP': {
    framework: 'NIST CSF',
    title: 'Information Protection Processes and Procedures',
    summary:
      'Policies, processes, and procedures are maintained to manage protection activities, including change management, secure configurations, and operational resilience.',
  },
  'DE.CM': {
    framework: 'NIST CSF',
    title: 'Security Continuous Monitoring',
    summary:
      'Systems and networks are monitored to detect cybersecurity events and verify the effectiveness of protective measures, enabling faster detection and response.',
  },
  'RS.MI': {
    framework: 'NIST CSF',
    title: 'Mitigation',
    summary:
      'Response activities contain and mitigate incidents to reduce impact—such as isolating hosts, disabling compromised accounts, blocking indicators, and applying patches.',
  },
  'RS.CO': {
    framework: 'NIST CSF',
    title: 'Communications',
    summary:
      'Response communications are coordinated with stakeholders (internal and external) to ensure timely escalation, accurate updates, and consistent incident handling.',
  },
};

export function getNistControlInfo(controlId: string): NistControlInfo {
  const normalized = (controlId || '').trim().toUpperCase();
  const known = NIST_800_53[normalized] || NIST_CSF[normalized];
  if (known) return { id: normalized, ...known };

  // Best-effort classification for unknown controls
  const isCsf = normalized.includes('.');
  if (isCsf) {
    return {
      id: normalized,
      framework: 'NIST CSF',
      title: 'NIST CSF Category',
      summary:
        'A NIST Cybersecurity Framework (CSF) category/subcategory mapping. Use this as a governance reference to understand how the playbook supports your security program.',
    };
  }
  return {
    id: normalized || controlId,
    framework: 'NIST SP 800-53',
    title: 'NIST SP 800-53 Control',
    summary:
      'A NIST SP 800-53 control mapping. Use this as a governance reference to understand which security requirements this playbook helps satisfy.',
  };
}

