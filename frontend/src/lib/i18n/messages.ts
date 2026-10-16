/**
 * Internationalization Message Catalog
 * Central message definitions for all user-facing strings.
 * Structure: namespace.key = message string.
 *
 * Usage:
 *   import { t } from '@/lib/i18n';
 *   t('nav.dashboard')  // "Dashboard"
 *   t('incidents.empty') // "No open incidents"
 */

export const messages = {
  en: {
    // ── Navigation ────────────────────────────────────────────────
    'nav.dashboard': 'Dashboard',
    'nav.warRoom': 'War Room',
    'nav.alerts': 'Alert Queue',
    'nav.incidents': 'Incident Queue',
    'nav.securityGraph': 'Security Graph',
    'nav.telemetry': 'Telemetry Search',
    'nav.playbooks': 'Response Playbooks',
    'nav.detectionRules': 'Detection Coverage',
    'nav.people': 'People & Access',
    'nav.posture': 'Cloud Posture',
    'nav.compliance': 'Compliance',
    'nav.reports': 'Reports',
    'nav.aiGovernance': 'AI Governance',
    'nav.partnerConsole': 'Partner Console',

    // ── Common actions ────────────────────────────────────────────
    'action.save': 'Save',
    'action.cancel': 'Cancel',
    'action.delete': 'Delete',
    'action.edit': 'Edit',
    'action.close': 'Close',
    'action.search': 'Search',
    'action.filter': 'Filter',
    'action.export': 'Export',
    'action.refresh': 'Refresh',
    'action.viewAll': 'View all',
    'action.investigate': 'Investigate',
    'action.resolve': 'Resolve',
    'action.dismiss': 'Dismiss',
    'action.assign': 'Assign',
    'action.retry': 'Retry',

    // ── Empty states ──────────────────────────────────────────────
    'empty.noData': 'No data yet',
    'empty.noDataDesc': 'Data will appear here once your systems are connected and generating findings.',
    'empty.noIncidents': 'No open incidents',
    'empty.noIncidentsDesc': 'Your environment is clear. We\'ll alert you immediately if an incident is detected.',
    'empty.noAlerts': 'No active alerts',
    'empty.noAlertsDesc': 'All clear. Detection rules are monitoring your environment around the clock.',
    'empty.noResults': 'No results found',
    'empty.noResultsDesc': 'Try adjusting your search terms or filters to find what you\'re looking for.',
    'empty.error': 'Something went wrong',
    'empty.errorDesc': 'We couldn\'t load this data. Please try refreshing the page.',

    // ── Severity ──────────────────────────────────────────────────
    'severity.critical': 'Critical',
    'severity.high': 'High',
    'severity.medium': 'Medium',
    'severity.low': 'Low',
    'severity.info': 'Info',

    // ── Status ────────────────────────────────────────────────────
    'status.open': 'Open',
    'status.investigating': 'Investigating',
    'status.resolved': 'Resolved',
    'status.closed': 'Closed',
    'status.falsePositive': 'False Positive',
    'status.acknowledged': 'Acknowledged',
    'status.healthy': 'Healthy',
    'status.degraded': 'Degraded',
    'status.critical': 'Critical',

    // ── Time ──────────────────────────────────────────────────────
    'time.justNow': 'Just now',
    'time.minutesAgo': '{count} minutes ago',
    'time.hoursAgo': '{count} hours ago',
    'time.daysAgo': '{count} days ago',
    'time.today': 'Today',
    'time.yesterday': 'Yesterday',

    // ── Dashboard ─────────────────────────────────────────────────
    'dashboard.securityPulse': 'Security Pulse',
    'dashboard.postureScore': 'Posture Score',
    'dashboard.openIncidents': 'Open Incidents',
    'dashboard.activeAlerts': 'Active Alerts',
    'dashboard.complianceScore': 'Compliance Score',
    'dashboard.recommendations': 'Recommendations',

    // ── War Room ──────────────────────────────────────────────────
    'warRoom.title': 'War Room',
    'warRoom.subtitle': 'Your single prioritized queue — address the most urgent items first.',
    'warRoom.urgent': '{count} urgent',
    'warRoom.whyNow': 'Why now',

    // ── Compliance ────────────────────────────────────────────────
    'compliance.heatmap': 'Compliance Heatmap',
    'compliance.compliant': 'Compliant',
    'compliance.partial': 'Partial',
    'compliance.nonCompliant': 'Non-Compliant',
    'compliance.notAssessed': 'Not Assessed',

    // ── AI ─────────────────────────────────────────────────────────
    'ai.commandPalette': 'AI Command Palette',
    'ai.askAnything': 'Ask anything, or type / for commands...',
    'ai.newChat': 'New chat',
    'ai.governance': 'AI Governance',
    'ai.shadowAi': 'Shadow AI',
    'ai.policyViolations': 'Policy Violations',

    // ── Partner ───────────────────────────────────────────────────
    'partner.console': 'Partner Console',
    'partner.managedTenants': 'Managed Tenants',
    'partner.switchTenant': 'Switch to Tenant',
  },
} as const;

export type Locale = keyof typeof messages;

export const DEFAULT_LOCALE: Locale = 'en';

export type MessageKey = keyof typeof messages.en;
