/**
 * Universal command palette for route jump, entity search, saved shortcuts, and AI fallback.
 */

'use client';

import { useState, useRef, useEffect, useCallback, useDeferredValue, useMemo } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import clsx from 'clsx';
import {
  ArrowTopRightOnSquareIcon,
  BookmarkIcon,
  ClockIcon,
  MagnifyingGlassIcon,
  SparklesIcon,
} from '@heroicons/react/24/outline';
import { BookmarkIcon as BookmarkSolidIcon } from '@heroicons/react/24/solid';
import AgentBadge, { type AgentId } from '@/components/ui/AgentBadge';
import { sendDashboardChat, getChatSuggestions, type ChatMessage } from '@/lib/api/dashboard-chat';
import { listAlerts, type Alert } from '@/lib/api/siem';
import { listIncidents, type Incident } from '@/lib/api/incidents';
import { listDetectionRules, type DetectionRule } from '@/lib/api/detections';
import { listReports, type Report } from '@/lib/api/reports';
import { getPolicies, type Policy } from '@/lib/api/iam-portal';
import { getIAMUsers, type UserInfo as IAMUserInfo } from '@/lib/api/iam-portal';
import { getPeopleAccessSnapshot, type PeopleAccessSnapshot } from '@/lib/api/dashboard';
import { useAuth } from '@/lib/providers/AuthProvider';
import { OPEN_COMMAND_PALETTE_EVENT, type OpenCommandPaletteDetail } from '@/lib/command-palette';
import { getPlanTierRank, type PlanTier } from '@/lib/product/catalog';
import {
  buildAlertGraphHref,
  buildEntityGraphHref,
  buildIncidentGraphHref,
} from '@/lib/security/graph-context';

interface CommandPaletteProps {
  tenantId?: string;
  dashboardContext?: Record<string, unknown>;
}

type QuickActionCategory = 'investigate' | 'report' | 'action' | 'query';
type ChatSourceTone = 'knowledge_base' | 'live_compliance_status' | 'proposed_agent_action' | 'general';
type PaletteGroupId =
  | 'saved'
  | 'recent'
  | 'commands'
  | 'jump'
  | 'graph'
  | 'alerts'
  | 'incidents'
  | 'people'
  | 'rules'
  | 'policies'
  | 'reports'
  | 'ai';
type PaletteAction = 'navigate' | 'command' | 'ai';
type PaletteResultKind =
  | 'saved'
  | 'recent'
  | 'command'
  | 'route'
  | 'graph'
  | 'alert'
  | 'incident'
  | 'person'
  | 'rule'
  | 'policy'
  | 'report'
  | 'ai';

interface QuickAction {
  command: string;
  label: string;
  description: string;
  agent: AgentId;
  category: QuickActionCategory;
}

interface RouteShortcut {
  id: string;
  title: string;
  subtitle: string;
  href: string;
  workflow: 'Detect' | 'Respond' | 'Govern' | 'Admin';
  keywords: string[];
  adminOnly?: boolean;
  minPlanTier?: PlanTier;
}

interface PaletteResult {
  id: string;
  key: string;
  group: PaletteGroupId;
  kind: PaletteResultKind;
  action: PaletteAction;
  title: string;
  subtitle: string;
  href?: string;
  query?: string;
  command?: string;
  agent?: AgentId;
  metaLabel?: string;
  accentTone?: 'critical' | 'high' | 'medium' | 'low' | 'neutral' | 'success';
  pinnable?: boolean;
  searchTerms?: string[];
}

interface StoredPaletteItem {
  id: string;
  key: string;
  group: PaletteGroupId;
  kind: PaletteResultKind;
  title: string;
  subtitle: string;
  href?: string;
  command?: string;
  agent?: AgentId;
  metaLabel?: string;
}

const SAVED_SHORTCUTS_KEY = 'sg_command_palette_saved';
const RECENT_ITEMS_KEY = 'sg_command_palette_recent';
const PLAN_TIER_OVERRIDE_KEY = 'plan_tier_override';
const PLAN_TIER_KEY = 'plan_tier';
const ADMIN_ROLES = ['admin', 'tenant_admin', 'TENANT_ADMIN', 'soc_manager', 'SOC_MANAGER'];
const CHAT_SOURCE_LABELS: Record<ChatSourceTone, string> = {
  knowledge_base: 'Knowledge base',
  live_compliance_status: 'Live compliance status',
  proposed_agent_action: 'Proposed agent action',
  general: 'AI assistant',
};
const CHAT_SOURCE_CLASSNAMES: Record<ChatSourceTone, string> = {
  knowledge_base: 'border-sky-500/30 bg-sky-500/10 text-sky-200',
  live_compliance_status: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-200',
  proposed_agent_action: 'border-amber-500/30 bg-amber-500/10 text-amber-200',
  general: 'border-border-faint bg-surface-card text-text-muted',
};
const GROUP_ORDER: PaletteGroupId[] = [
  'saved',
  'recent',
  'commands',
  'jump',
  'graph',
  'alerts',
  'incidents',
  'people',
  'rules',
  'policies',
  'reports',
  'ai',
];
const GROUP_TITLES: Record<PaletteGroupId, string> = {
  saved: 'Saved quick actions',
  recent: 'Recent items',
  commands: 'Quick actions',
  jump: 'Jump to',
  graph: 'Graph pivots',
  alerts: 'Alerts',
  incidents: 'Incidents',
  people: 'People',
  rules: 'Detection rules',
  policies: 'Policies',
  reports: 'Reports',
  ai: 'Ask SentinelGrid AI',
};
const DEFAULT_SUGGESTIONS = [
  'What is my current security posture?',
  'Show critical incidents from the last 24h',
  'Which SOC 2 criteria need attention?',
  'List dormant admin accounts',
  'Summarize cloud misconfigurations',
  'What attack paths exist in my environment?',
  'Show me all resources accessible by this compromised identity',
  'Trace the blast radius from this incident',
  'Which workloads are reachable from this exposed asset?',
];
const QUICK_ACTIONS: QuickAction[] = [
  { command: '/investigate', label: 'Investigate', description: 'Deep-dive into an incident or alert.', agent: 'incident_agent', category: 'investigate' },
  { command: '/posture', label: 'Posture Check', description: 'Get the current security posture summary.', agent: 'orchestrator', category: 'query' },
  { command: '/compliance', label: 'Compliance Status', description: 'Review SOC 2 and ISO 27001 coverage.', agent: 'compliance_agent', category: 'report' },
  { command: '/identity', label: 'Identity Audit', description: 'Check IAM risks and dormant accounts.', agent: 'iam_agent', category: 'query' },
  { command: '/graph', label: 'Relationship Query', description: 'Ask who can reach an identity, host, or cloud resource.', agent: 'orchestrator', category: 'query' },
  { command: '/threats', label: 'Threat Summary', description: 'Summarize active threats and attack paths.', agent: 'siem_agent', category: 'query' },
  { command: '/remediate', label: 'Remediate', description: 'Plan or trigger a remediation workflow.', agent: 'remediation_agent', category: 'action' },
  { command: '/report', label: 'Generate Report', description: 'Prepare an audit or executive report.', agent: 'reporting_agent', category: 'report' },
  { command: '/cloud', label: 'Cloud Security', description: 'Review AWS, Azure, and GCP findings.', agent: 'cloud_posture_agent', category: 'query' },
];
const ROUTE_SHORTCUTS: RouteShortcut[] = [
  {
    id: 'route-now',
    title: 'Now',
    subtitle: 'Open the prioritized cross-domain queue.',
    href: '/dashboard/now',
    workflow: 'Detect',
    keywords: ['dashboard', 'home', 'queue', 'now'],
  },
  {
    id: 'route-alerts',
    title: 'Alert Queue',
    subtitle: 'Triage incoming alerts and validate signal quality.',
    href: '/dashboard/alerts',
    workflow: 'Detect',
    keywords: ['alerts', 'detections', 'queue', 'triage'],
  },
  {
    id: 'route-incidents',
    title: 'Incident Queue',
    subtitle: 'Review active incidents and case ownership.',
    href: '/dashboard/incidents',
    workflow: 'Detect',
    keywords: ['incidents', 'cases', 'queue', 'response'],
  },
  {
    id: 'route-security-graph',
    title: 'Security Graph',
    subtitle: 'Pivot through attack paths and entity relationships.',
    href: '/dashboard/security-graph',
    workflow: 'Detect',
    keywords: ['graph', 'attack path', 'blast radius', 'entities'],
  },
  {
    id: 'route-telemetry',
    title: 'Telemetry Search',
    subtitle: 'Search logs, investigate activity, and trace events.',
    href: '/dashboard/log-management',
    workflow: 'Detect',
    keywords: ['telemetry', 'logs', 'events', 'search'],
  },
  {
    id: 'route-detection-rules',
    title: 'Detection Coverage',
    subtitle: 'Review rule coverage and tune detections.',
    href: '/dashboard/siem/detection-rules',
    workflow: 'Detect',
    keywords: ['detections', 'rules', 'coverage', 'siem'],
    minPlanTier: 'protect_defend',
  },
  {
    id: 'route-war-room',
    title: 'War Room',
    subtitle: 'Coordinate the active response and shared timeline.',
    href: '/dashboard/war-room',
    workflow: 'Respond',
    keywords: ['war room', 'response', 'coordination', 'timeline'],
  },
  {
    id: 'route-playbooks',
    title: 'Response Playbooks',
    subtitle: 'Run response packs and approvals.',
    href: '/dashboard/playbooks',
    workflow: 'Respond',
    keywords: ['playbooks', 'automation', 'response', 'soar'],
    minPlanTier: 'protect_defend',
  },
  {
    id: 'route-people',
    title: 'People & Access',
    subtitle: 'Review identities, workforce apps, and admin exposure.',
    href: '/dashboard/iam/people',
    workflow: 'Respond',
    keywords: ['people', 'identities', 'users', 'access', 'mfa'],
  },
  {
    id: 'route-policies',
    title: 'Policies',
    subtitle: 'Manage sign-on, access, approval, and authorization policies.',
    href: '/dashboard/iam/policies',
    workflow: 'Respond',
    keywords: ['policies', 'authorization', 'sign-on', 'approval', 'access rules'],
  },
  {
    id: 'route-posture',
    title: 'Cloud Posture',
    subtitle: 'Prioritize posture gaps and misconfigurations.',
    href: '/dashboard/posture',
    workflow: 'Govern',
    keywords: ['posture', 'cloud', 'misconfigurations', 'risk'],
  },
  {
    id: 'route-compliance',
    title: 'Compliance',
    subtitle: 'Translate operational work into control coverage.',
    href: '/dashboard/compliance',
    workflow: 'Govern',
    keywords: ['compliance', 'controls', 'soc 2', 'audit'],
    minPlanTier: 'protect_defend_comply',
  },
  {
    id: 'route-reports',
    title: 'Reports',
    subtitle: 'Generate customer-facing and audit-ready exports.',
    href: '/dashboard/compliance/reports',
    workflow: 'Govern',
    keywords: ['reports', 'exports', 'trust center', 'evidence'],
    minPlanTier: 'protect_defend_comply',
  },
  {
    id: 'route-ai-governance',
    title: 'AI Governance',
    subtitle: 'Review AI activity, evidence, and governance posture.',
    href: '/dashboard/ai-governance',
    workflow: 'Govern',
    keywords: ['ai governance', 'ai activity', 'ai risk', 'ai reports'],
    minPlanTier: 'protect_defend_comply',
  },
  {
    id: 'route-settings',
    title: 'Usage & Billing',
    subtitle: 'Review usage, billing, and subscription settings.',
    href: '/dashboard/settings/usage',
    workflow: 'Admin',
    keywords: ['settings', 'usage', 'billing', 'subscription'],
  },
];
function normalizeSearchValue(value: string) {
  return value.trim().toLowerCase().replace(/\s+/g, ' ');
}

function parseStoredItems(value: string | null): StoredPaletteItem[] {
  if (!value) {
    return [];
  }

  try {
    const parsed = JSON.parse(value);
    if (!Array.isArray(parsed)) {
      return [];
    }

    return parsed.filter((item): item is StoredPaletteItem => {
      return (
        typeof item === 'object' &&
        item !== null &&
        typeof item.id === 'string' &&
        typeof item.key === 'string' &&
        typeof item.group === 'string' &&
        typeof item.kind === 'string' &&
        typeof item.title === 'string' &&
        typeof item.subtitle === 'string'
      );
    });
  } catch {
    return [];
  }
}

function upsertStoredItems(items: StoredPaletteItem[], nextItem: StoredPaletteItem, limit: number) {
  return [nextItem, ...items.filter((item) => item.key !== nextItem.key)].slice(0, limit);
}

function buildStoredItem(result: PaletteResult, kindOverride?: PaletteResultKind): StoredPaletteItem {
  return {
    id: result.id,
    key: result.key,
    group: result.group,
    kind: kindOverride || result.kind,
    title: result.title,
    subtitle: result.subtitle,
    href: result.href,
    command: result.command,
    agent: result.agent,
    metaLabel: result.metaLabel,
  };
}

function scoreMatch(query: string, values: string[]) {
  const normalizedQuery = normalizeSearchValue(query);
  if (!normalizedQuery) {
    return 0;
  }

  const tokens = normalizedQuery.split(' ').filter(Boolean);
  let bestScore = 0;

  values.forEach((value, index) => {
    const normalizedValue = normalizeSearchValue(value);
    if (!normalizedValue) {
      return;
    }

    if (!tokens.every((token) => normalizedValue.includes(token))) {
      return;
    }

    let score = 45 - index * 2;
    if (normalizedValue === normalizedQuery) {
      score = 120 - index * 2;
    } else if (normalizedValue.startsWith(normalizedQuery)) {
      score = 100 - index * 2;
    } else if (tokens.some((token) => normalizedValue.startsWith(token))) {
      score = 72 - index * 2;
    }

    bestScore = Math.max(bestScore, score);
  });

  return bestScore;
}

function isRelationshipQuery(query: string) {
  const normalized = normalizeSearchValue(query);
  if (!normalized) {
    return false;
  }

  return [
    'graph',
    'attack path',
    'blast radius',
    'reachable',
    'relationship',
    'lateral movement',
    'pivot',
    'compromised identity',
    'exposed asset',
    'accessible by',
  ].some((pattern) => normalized.includes(pattern));
}

function limitPerGroup(results: Array<PaletteResult & { score: number }>, maxPerGroup: number) {
  const groupCounts = new Map<PaletteGroupId, number>();

  return results.filter((result) => {
    const currentCount = groupCounts.get(result.group) || 0;
    if (currentCount >= maxPerGroup) {
      return false;
    }

    groupCounts.set(result.group, currentCount + 1);
    return true;
  });
}

function groupResults(results: PaletteResult[]) {
  const grouped = new Map<PaletteGroupId, PaletteResult[]>();

  results.forEach((result) => {
    const existing = grouped.get(result.group) || [];
    existing.push(result);
    grouped.set(result.group, existing);
  });

  return GROUP_ORDER
    .filter((group) => grouped.has(group))
    .map((group) => ({
      id: group,
      title: GROUP_TITLES[group],
      items: grouped.get(group) || [],
    }))
    .filter((group) => group.items.length > 0);
}

function severityTone(value?: string | null): PaletteResult['accentTone'] {
  switch ((value || '').toLowerCase()) {
    case 'critical':
      return 'critical';
    case 'high':
      return 'high';
    case 'medium':
      return 'medium';
    case 'low':
      return 'low';
    case 'completed':
    case 'ready':
    case 'enabled':
    case 'active':
      return 'success';
    default:
      return 'neutral';
  }
}

function formatPolicyTypeLabel(value: string) {
  switch (value) {
    case 'signon':
      return 'Sign-on';
    case 'access':
      return 'Access';
    case 'approval':
      return 'Approval';
    case 'sod':
      return 'SoD';
    case 'authorization':
      return 'Authorization';
    default:
      return value;
  }
}

function formatReportStatus(value?: string) {
  const normalized = (value || '').toLowerCase();
  if (!normalized) {
    return 'Unknown';
  }

  return normalized
    .split('_')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

function accentClassName(tone: PaletteResult['accentTone']) {
  switch (tone) {
    case 'critical':
      return 'border-rose-400/30 bg-rose-500/10 text-rose-200';
    case 'high':
      return 'border-orange-400/30 bg-orange-500/10 text-orange-200';
    case 'medium':
      return 'border-amber-400/30 bg-amber-500/10 text-amber-200';
    case 'low':
      return 'border-sky-400/30 bg-sky-500/10 text-sky-200';
    case 'success':
      return 'border-emerald-400/30 bg-emerald-500/10 text-emerald-200';
    default:
      return 'border-border-faint bg-surface-hover text-text-muted';
  }
}

export default function CommandPalette({ tenantId, dashboardContext }: CommandPaletteProps) {
  const router = useRouter();
  const pathname = usePathname();
  const { user, planTier } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const deferredInput = useDeferredValue(input);
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [activeAgent, setActiveAgent] = useState<AgentId | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [people, setPeople] = useState<IAMUserInfo[]>([]);
  const [rules, setRules] = useState<DetectionRule[]>([]);
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [reports, setReports] = useState<Report[]>([]);
  const [peopleSnapshot, setPeopleSnapshot] = useState<PeopleAccessSnapshot | null>(null);
  const [savedShortcuts, setSavedShortcuts] = useState<StoredPaletteItem[]>([]);
  const [recentItems, setRecentItems] = useState<StoredPaletteItem[]>([]);
  const [suggestions, setSuggestions] = useState<string[]>(DEFAULT_SUGGESTIONS);
  const [catalogStatus, setCatalogStatus] = useState<'idle' | 'loading' | 'ready'>('idle');
  const [catalogError, setCatalogError] = useState<string | null>(null);
  const [activeIndex, setActiveIndex] = useState(0);
  const [tierOverride, setTierOverride] = useState<string | null>(null);

  const inputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const previousPathnameRef = useRef(pathname);
  const dashboardContextRef = useRef<Record<string, unknown>>(dashboardContext || {});
  const userRoles = user?.roles || [];
  const hasAdminRole = userRoles.some((role) => ADMIN_ROLES.includes(role));
  const effectivePlanTier =
    tierOverride ||
    (typeof window !== 'undefined' ? window.localStorage.getItem(PLAN_TIER_KEY) : null) ||
    planTier;
  const currentPlanRank = getPlanTierRank(effectivePlanTier || 'protect');

  useEffect(() => {
    dashboardContextRef.current = dashboardContext || {};
  }, [dashboardContext]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    setTierOverride(window.localStorage.getItem(PLAN_TIER_OVERRIDE_KEY));
    setSavedShortcuts(parseStoredItems(window.localStorage.getItem(SAVED_SHORTCUTS_KEY)));
    setRecentItems(parseStoredItems(window.localStorage.getItem(RECENT_ITEMS_KEY)));
  }, []);

  const persistSavedShortcuts = useCallback((items: StoredPaletteItem[]) => {
    setSavedShortcuts(items);
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(SAVED_SHORTCUTS_KEY, JSON.stringify(items));
    }
  }, []);

  const persistRecentItems = useCallback((items: StoredPaletteItem[]) => {
    setRecentItems(items);
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(RECENT_ITEMS_KEY, JSON.stringify(items));
    }
  }, []);

  const recordRecentItem = useCallback(
    (result: PaletteResult) => {
      const nextRecent = upsertStoredItems(recentItems, buildStoredItem(result, 'recent'), 8);
      persistRecentItems(nextRecent);
    },
    [persistRecentItems, recentItems]
  );

  const toggleSavedShortcut = useCallback(
    (result: PaletteResult) => {
      const alreadySaved = savedShortcuts.some((item) => item.key === result.key);
      if (alreadySaved) {
        persistSavedShortcuts(savedShortcuts.filter((item) => item.key !== result.key));
        return;
      }

      const nextSaved = upsertStoredItems(savedShortcuts, buildStoredItem(result, 'saved'), 8);
      persistSavedShortcuts(nextSaved);
    },
    [persistSavedShortcuts, savedShortcuts]
  );

  const handleInputChange = useCallback((value: string) => {
    setInput(value);
  }, []);

  const handleClose = useCallback(() => {
    setIsOpen(false);
    setInput('');
    setActiveIndex(0);
  }, []);

  const handleNewChat = useCallback(() => {
    setMessages([]);
    setConversationId(null);
    setActiveAgent(null);
    setInput('');
    requestAnimationFrame(() => inputRef.current?.focus());
  }, []);

  const loadWorkspaceResults = useCallback(async () => {
    if (!tenantId) {
      return;
    }

    setCatalogStatus('loading');
    setCatalogError(null);

    const [
      alertsResult,
      incidentsResult,
      peopleCatalogResult,
      rulesResult,
      policiesResult,
      reportsResult,
      peopleResult,
      suggestionsResult,
    ] =
      await Promise.allSettled([
        listAlerts({ limit: 25, offset: 0 }),
        listIncidents({ limit: 25, offset: 0 }),
        getIAMUsers(),
        listDetectionRules(),
        getPolicies(),
        listReports({ limit: 25 }),
        getPeopleAccessSnapshot(tenantId),
        getChatSuggestions(dashboardContextRef.current, tenantId),
      ]);

    if (alertsResult.status === 'fulfilled') {
      setAlerts(alertsResult.value.alerts || []);
    }
    if (incidentsResult.status === 'fulfilled') {
      setIncidents(incidentsResult.value.items || []);
    }
    if (peopleCatalogResult.status === 'fulfilled') {
      setPeople(peopleCatalogResult.value || []);
    }
    if (rulesResult.status === 'fulfilled') {
      setRules(rulesResult.value || []);
    }
    if (policiesResult.status === 'fulfilled') {
      setPolicies(policiesResult.value || []);
    }
    if (reportsResult.status === 'fulfilled') {
      setReports(reportsResult.value || []);
    }
    if (peopleResult.status === 'fulfilled') {
      setPeopleSnapshot(peopleResult.value);
    }
    if (suggestionsResult.status === 'fulfilled' && suggestionsResult.value.length > 0) {
      setSuggestions(suggestionsResult.value);
    }

    const successes = [
      alertsResult,
      incidentsResult,
      peopleCatalogResult,
      rulesResult,
      policiesResult,
      reportsResult,
      peopleResult,
    ].filter((result) => result.status === 'fulfilled').length;

    if (successes === 0) {
      setCatalogError('Workspace search results could not be loaded right now.');
    }

    setCatalogStatus('ready');
  }, [tenantId]);

  const handleSend = useCallback(
    async (messageOverride?: string) => {
      const trimmedMessage = (messageOverride || input).trim();
      if (!trimmedMessage || isLoading || !tenantId) {
        return;
      }

      const matchedAction = QUICK_ACTIONS.find((action) => trimmedMessage.startsWith(action.command));
      if (matchedAction) {
        setActiveAgent(matchedAction.agent);
      }

      const userMessage: ChatMessage = {
        role: 'user',
        content: trimmedMessage,
        timestamp: new Date().toISOString(),
      };

      setMessages((previousMessages) => [...previousMessages, userMessage]);
      setInput('');
      setIsLoading(true);
      setActiveIndex(0);

      try {
        const response = await sendDashboardChat(
          {
            message: userMessage.content,
            active_agent: matchedAction?.agent,
            context: {
              page: 'command_palette',
              active_agent: matchedAction?.agent,
              dashboard_data: {
                ...dashboardContextRef.current,
                active_agent: matchedAction?.agent,
                route: pathname,
              },
            },
            conversation_id: conversationId || undefined,
          },
          tenantId
        );

        if (response.conversation_id && !conversationId) {
          setConversationId(response.conversation_id);
        }

        setMessages((previousMessages) => [
          ...previousMessages,
          {
            role: 'assistant',
            content: response.reply,
            timestamp: new Date().toISOString(),
            answer_type: response.answer_type,
            source_kind: response.source_kind,
            module: response.module,
            retrieval_categories: response.retrieval_categories,
            sources: response.sources,
            actions: response.actions,
          },
        ]);
      } catch {
        setMessages((previousMessages) => [
          ...previousMessages,
          {
            role: 'assistant',
            content: 'I encountered an error processing your request. Please try again.',
            timestamp: new Date().toISOString(),
          },
        ]);
      } finally {
        setActiveAgent(null);
        setIsLoading(false);
      }
    },
    [conversationId, input, isLoading, pathname, tenantId]
  );

  useEffect(() => {
    const handleGlobalKey = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        setIsOpen((previousState) => !previousState);
      }
    };

    const handleOpenEvent = (event: Event) => {
      const detail = (event as CustomEvent<OpenCommandPaletteDetail>).detail;
      setIsOpen(true);
      handleInputChange(detail?.query || '');
    };

    document.addEventListener('keydown', handleGlobalKey);
    window.addEventListener(OPEN_COMMAND_PALETTE_EVENT, handleOpenEvent as EventListener);
    return () => {
      document.removeEventListener('keydown', handleGlobalKey);
      window.removeEventListener(OPEN_COMMAND_PALETTE_EVENT, handleOpenEvent as EventListener);
    };
  }, [handleInputChange]);

  useEffect(() => {
    if (!isOpen || catalogStatus !== 'idle') {
      return;
    }

    void loadWorkspaceResults();
  }, [catalogStatus, isOpen, loadWorkspaceResults]);

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    requestAnimationFrame(() => inputRef.current?.focus());
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) {
      previousPathnameRef.current = pathname;
      return;
    }

    if (previousPathnameRef.current === pathname) {
      return;
    }

    setIsOpen(false);
    setInput('');
    setActiveIndex(0);
    previousPathnameRef.current = pathname;
  }, [pathname, isOpen]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const visibleRouteShortcuts = ROUTE_SHORTCUTS.filter((shortcut) => {
    if (shortcut.adminOnly && !hasAdminRole) {
      return false;
    }

    if (!shortcut.minPlanTier) {
      return true;
    }

    return currentPlanRank >= getPlanTierRank(shortcut.minPlanTier);
  }).map<PaletteResult>((shortcut) => {
    const isPeopleRoute = shortcut.href === '/dashboard/iam/people' && peopleSnapshot;
    const subtitle = isPeopleRoute
      ? `${peopleSnapshot.users_total} identities · ${peopleSnapshot.mfa_missing_count} missing MFA · ${peopleSnapshot.dormant_accounts_count} dormant accounts.`
      : shortcut.subtitle;

    return {
      id: shortcut.id,
      key: `route:${shortcut.href}`,
      group: 'jump',
      kind: 'route',
      action: 'navigate',
      title: shortcut.title,
      subtitle,
      href: shortcut.href,
      metaLabel: shortcut.workflow,
      accentTone: 'neutral',
      pinnable: true,
      searchTerms: shortcut.keywords,
    };
  });

  const alertResults = alerts.map<PaletteResult>((alert) => ({
    id: alert.id,
    key: `alert:${alert.id}`,
    group: 'alerts',
    kind: 'alert',
    action: 'navigate',
    title: alert.title,
    subtitle: `${alert.status} alert${alert.description ? ` · ${alert.description}` : ''}`,
    href: `/dashboard/alerts/${encodeURIComponent(alert.id)}`,
    metaLabel: alert.severity.toUpperCase(),
    accentTone: severityTone(alert.severity),
    pinnable: true,
    searchTerms: [
      alert.id,
      alert.title,
      alert.description || '',
      alert.status,
      alert.severity,
      alert.source,
      alert.user_identifier || '',
      alert.asset_id || '',
    ],
  }));

  const incidentResults = incidents.map<PaletteResult>((incident) => ({
    id: incident.id,
    key: `incident:${incident.id}`,
    group: 'incidents',
    kind: 'incident',
    action: 'navigate',
    title: incident.title,
    subtitle: `${incident.status} incident${incident.description ? ` · ${incident.description}` : ''}`,
    href: `/dashboard/incidents/${encodeURIComponent(incident.id)}`,
    metaLabel: (incident.severity || incident.status || 'incident').toUpperCase(),
    accentTone: severityTone(incident.severity || incident.status),
    pinnable: true,
    searchTerms: [
      incident.id,
      incident.title,
      incident.description || '',
      incident.status,
      incident.severity || '',
      incident.phase || '',
      incident.assigned_to || '',
    ],
  }));

  const ruleResults = rules.map<PaletteResult>((rule) => ({
    id: rule.id,
    key: `rule:${rule.id}`,
    group: 'rules',
    kind: 'rule',
    action: 'navigate',
    title: rule.name,
    subtitle: `${rule.category} detection rule · ${rule.description}`,
    href: `/dashboard/siem/detection-rules/${encodeURIComponent(rule.id)}`,
    metaLabel: rule.is_enabled ? 'ENABLED' : 'DISABLED',
    accentTone: rule.is_enabled ? 'success' : 'neutral',
    pinnable: true,
    searchTerms: [
      rule.id,
      rule.rule_key,
      rule.name,
      rule.description,
      rule.category,
      rule.alert_type,
      rule.severity,
    ],
  }));

  const policyResults = policies.map<PaletteResult>((policy) => ({
    id: policy.id,
    key: `policy:${policy.id}`,
    group: 'policies',
    kind: 'policy',
    action: 'navigate',
    title: policy.display_name,
    subtitle: `${formatPolicyTypeLabel(policy.policy_type)} policy${policy.description ? ` · ${policy.description}` : ''}`,
    href: `/dashboard/iam/policies?tab=${encodeURIComponent(policy.policy_type)}`,
    metaLabel: formatPolicyTypeLabel(policy.policy_type),
    accentTone: policy.is_active ? 'success' : 'neutral',
    pinnable: true,
    searchTerms: [
      policy.id,
      policy.name,
      policy.display_name,
      policy.description || '',
      policy.policy_type,
      policy.scope,
      policy.scope_id || '',
    ],
  }));

  const reportResults = reports.map<PaletteResult>((report) => ({
    id: report.id,
    key: `report:${report.id}`,
    group: 'reports',
    kind: 'report',
    action: 'navigate',
    title: report.name,
    subtitle: `${formatReportStatus(report.status)} report · Opens the reports workspace`,
    href: '/dashboard/compliance/reports',
    metaLabel: formatReportStatus(report.status),
    accentTone: severityTone(report.status),
    pinnable: true,
    searchTerms: [
      report.id,
      report.name,
      report.format,
      report.status,
      report.generated_by || '',
      report.date_range_start || '',
      report.date_range_end || '',
    ],
  }));

  const peopleResults = people.map<PaletteResult>((person) => {
    const displayName =
      `${person.first_name || ''} ${person.last_name || ''}`.trim() || person.username;

    return {
      id: person.user_id,
      key: `person:${person.user_id}`,
      group: 'people',
      kind: 'person',
      action: 'navigate',
      title: displayName,
      subtitle: [
        person.email || person.username,
        person.department || person.team || 'Directory profile',
        person.is_privileged ? 'Privileged' : person.enabled ? 'Active' : 'Disabled',
      ].join(' · '),
      href: `/dashboard/iam/people?user_id=${encodeURIComponent(person.user_id)}${
        person.email ? `&email=${encodeURIComponent(person.email)}` : ''
      }`,
      metaLabel: person.is_privileged ? 'PRIVILEGED' : 'USER',
      accentTone: person.is_privileged ? 'high' : person.enabled ? 'success' : 'neutral',
      pinnable: true,
      searchTerms: [
        person.user_id,
        person.username,
        person.email || '',
        person.first_name || '',
        person.last_name || '',
        person.department || '',
        person.team || '',
        person.location || '',
        person.employee_type || '',
      ],
    };
  });

  const trimmedQuery = deferredInput.trim();
  const isCommandQuery = trimmedQuery.startsWith('/');

  const graphResults = useMemo(() => {
    if (!trimmedQuery || isCommandQuery || !isRelationshipQuery(trimmedQuery)) {
      return [] as Array<PaletteResult & { score: number }>;
    }

    const scoreGraphCandidate = (result: PaletteResult) =>
      scoreMatch(trimmedQuery, [result.title, result.subtitle, ...(result.searchTerms || [])]);

    const personGraphResults = peopleResults
      .map((result) => ({ result, score: scoreGraphCandidate(result) }))
      .filter((entry) => entry.score > 0)
      .sort((left, right) => right.score - left.score)
      .slice(0, 2)
      .map(({ result, score }) => ({
        id: `graph-person:${result.id}`,
        key: `graph-person:${result.id}`,
        group: 'graph' as const,
        kind: 'graph' as const,
        action: 'navigate' as const,
        title: `Graph access for ${result.title}`,
        subtitle: `Pivot from ${result.title} into relationship and blast-radius context.`,
        href: buildEntityGraphHref({
          entityType: 'identity',
          entityId: result.id,
          entityLabel: result.title,
          entityDomain: 'identity',
          title: `${result.title} access graph`,
          severity: result.accentTone === 'high' ? 'high' : 'medium',
          summary: result.subtitle,
          sourceLabel: 'People & Access',
          sourceHref: result.href,
        }),
        metaLabel: 'GRAPH',
        accentTone: result.accentTone,
        pinnable: true,
        searchTerms: [result.title, result.subtitle, 'graph', 'identity', 'blast radius'],
        score: score + 30,
      }));

    const alertGraphResults = alertResults
      .map((result) => ({ result, score: scoreGraphCandidate(result) }))
      .filter((entry) => entry.score > 0)
      .sort((left, right) => right.score - left.score)
      .slice(0, 1)
      .map(({ result, score }) => ({
        id: `graph-alert:${result.id}`,
        key: `graph-alert:${result.id}`,
        group: 'graph' as const,
        kind: 'graph' as const,
        action: 'navigate' as const,
        title: `Graph context for ${result.title}`,
        subtitle: 'Open the alert in graph view and inspect linked entities and evidence.',
        href: buildAlertGraphHref(result.id, {
          sourceLabel: 'Alert queue',
          sourceHref: result.href,
        }),
        metaLabel: 'GRAPH',
        accentTone: result.accentTone,
        pinnable: true,
        searchTerms: [result.title, result.subtitle, 'graph', 'alert', 'attack path'],
        score: score + 24,
      }));

    const incidentGraphResults = incidentResults
      .map((result) => ({ result, score: scoreGraphCandidate(result) }))
      .filter((entry) => entry.score > 0)
      .sort((left, right) => right.score - left.score)
      .slice(0, 1)
      .map(({ result, score }) => ({
        id: `graph-incident:${result.id}`,
        key: `graph-incident:${result.id}`,
        group: 'graph' as const,
        kind: 'graph' as const,
        action: 'navigate' as const,
        title: `Graph blast radius for ${result.title}`,
        subtitle: 'Open the incident graph and inspect cross-domain blast radius.',
        href: buildIncidentGraphHref(result.id, {
          sourceLabel: 'Incident queue',
          sourceHref: result.href,
        }),
        metaLabel: 'GRAPH',
        accentTone: result.accentTone,
        pinnable: true,
        searchTerms: [result.title, result.subtitle, 'graph', 'incident', 'blast radius'],
        score: score + 26,
      }));

    const genericGraphResult: Array<PaletteResult & { score: number }> =
      personGraphResults.length > 0 || alertGraphResults.length > 0 || incidentGraphResults.length > 0
        ? []
        : [
            {
              id: 'graph-workspace',
              key: 'graph-workspace',
              group: 'graph',
              kind: 'graph',
              action: 'navigate',
              title: 'Open Security Graph workspace',
              subtitle: 'Start from the graph and explore attack paths, entity pivots, and blast radius manually.',
              href: '/dashboard/security-graph',
              metaLabel: 'GRAPH',
              accentTone: 'neutral',
              pinnable: true,
              searchTerms: ['graph', 'attack path', 'blast radius', 'reachable'],
              score: 20,
            },
          ];

    return [...personGraphResults, ...incidentGraphResults, ...alertGraphResults, ...genericGraphResult];
  }, [alertResults, incidentResults, isCommandQuery, peopleResults, trimmedQuery]);

  const commandResults = QUICK_ACTIONS.map<PaletteResult>((action) => ({
    id: action.command,
    key: `command:${action.command}`,
    group: 'commands',
    kind: 'command',
    action: 'command',
    title: action.label,
    subtitle: action.description,
    command: action.command,
    agent: action.agent,
    metaLabel: action.command,
    accentTone: 'neutral',
    pinnable: true,
    searchTerms: [action.command, action.label, action.description, action.category],
  }));

  const savedResults = savedShortcuts.map<PaletteResult>((item) => ({
    ...item,
    action: item.command ? 'command' : item.href ? 'navigate' : 'ai',
    group: 'saved',
    kind: 'saved',
    accentTone: 'neutral',
    pinnable: true,
    query: item.command,
  }));

  const recentResults = recentItems.map<PaletteResult>((item) => ({
    ...item,
    action: item.command ? 'command' : item.href ? 'navigate' : 'ai',
    group: 'recent',
    kind: 'recent',
    accentTone: 'neutral',
    pinnable: true,
    query: item.command,
  }));

  const commandQuery = isCommandQuery ? trimmedQuery.slice(1) : '';
  const searchableResults = [
    ...visibleRouteShortcuts,
    ...alertResults,
    ...incidentResults,
    ...peopleResults,
    ...ruleResults,
    ...policyResults,
    ...reportResults,
  ];

  const filteredCommandResults = isCommandQuery
    ? commandResults.filter((result) => scoreMatch(commandQuery, result.searchTerms || []) > 0)
    : [];
  const matchedWorkspaceResults =
    trimmedQuery && !isCommandQuery
      ? limitPerGroup(
          [...graphResults, ...searchableResults]
            .map((result) => ({
              ...result,
              score:
                typeof (result as { score?: number }).score === 'number'
                  ? (result as { score: number }).score
                  : scoreMatch(trimmedQuery, [
                      result.title,
                      result.subtitle,
                      ...(result.searchTerms || []),
                    ]),
            }))
            .filter((result) => result.score > 0)
            .sort((left, right) => right.score - left.score),
          4
        )
      : [];

  const aiFallbackResult: PaletteResult | null =
    trimmedQuery && !isCommandQuery
      ? {
          id: `ai:${trimmedQuery}`,
          key: `ai:${trimmedQuery}`,
          group: 'ai',
          kind: 'ai',
          action: 'ai',
          title: `Ask SentinelGrid AI about "${trimmedQuery}"`,
          subtitle: 'Use the AI assistant when a route or entity result is not enough.',
          query: trimmedQuery,
          metaLabel: 'AI',
          accentTone: 'neutral',
          pinnable: false,
        }
      : null;

  const browseStateResults =
    trimmedQuery === '' && messages.length === 0
      ? [
          ...savedResults,
          ...recentResults,
          ...commandResults.slice(0, 4),
          ...visibleRouteShortcuts.slice(0, 6),
          ...suggestions.slice(0, 4).map<PaletteResult>((suggestion) => ({
            id: `suggestion:${suggestion}`,
            key: `suggestion:${suggestion}`,
            group: 'ai',
            kind: 'ai',
            action: 'ai',
            title: suggestion,
            subtitle: 'Run this as an AI query.',
            query: suggestion,
            metaLabel: 'AI',
            accentTone: 'neutral',
            pinnable: false,
          })),
        ]
      : [];

  const currentResultGroups = groupResults(
    isCommandQuery
      ? filteredCommandResults
      : trimmedQuery
        ? [...matchedWorkspaceResults, ...(aiFallbackResult ? [aiFallbackResult] : [])]
        : browseStateResults
  );
  const flatResults = currentResultGroups.flatMap((group) => group.items);
  const shouldShowResults =
    trimmedQuery.length > 0 ||
    (messages.length === 0 && currentResultGroups.length > 0);

  useEffect(() => {
    setActiveIndex(0);
  }, [trimmedQuery, isOpen]);

  useEffect(() => {
    if (activeIndex < flatResults.length) {
      return;
    }

    setActiveIndex(0);
  }, [activeIndex, flatResults.length]);

  const handleResultSelect = useCallback(
    async (result: PaletteResult) => {
      if (result.action === 'navigate' && result.href) {
        recordRecentItem(result);
        setInput('');
        setIsOpen(false);
        router.push(result.href);
        return;
      }

      if (result.action === 'command' && result.command) {
        recordRecentItem(result);
        setInput(`${result.command} `);
        requestAnimationFrame(() => inputRef.current?.focus());
        return;
      }

      if (result.action === 'ai' && result.query) {
        await handleSend(result.query);
      }
    },
    [handleSend, recordRecentItem, router]
  );

  const handleKeyDown = async (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Escape') {
      event.preventDefault();
      if (trimmedQuery) {
        setInput('');
        return;
      }

      handleClose();
      return;
    }

    if (event.key === 'ArrowDown' && flatResults.length > 0) {
      event.preventDefault();
      setActiveIndex((previousIndex) => (previousIndex + 1) % flatResults.length);
      return;
    }

    if (event.key === 'ArrowUp' && flatResults.length > 0) {
      event.preventDefault();
      setActiveIndex((previousIndex) => (previousIndex - 1 + flatResults.length) % flatResults.length);
      return;
    }

    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      if (flatResults.length > 0) {
        await handleResultSelect(flatResults[activeIndex] || flatResults[0]);
        return;
      }

      await handleSend();
    }
  };

  if (!isOpen) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-[60]" role="dialog" aria-modal="true" aria-label="Universal search and command palette">
      <div
        className="absolute inset-0 bg-surface-overlay-strong backdrop-blur-sm"
        onClick={handleClose}
        aria-hidden="true"
      />

      <div className="absolute inset-x-4 top-[8vh] mx-auto flex max-h-[78vh] max-w-4xl flex-col overflow-hidden rounded-2xl border border-border-faint bg-surface-card shadow-2xl animate-in fade-in zoom-in-95 duration-200">
        <div className="border-b border-border-faint px-4 py-3">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-primary/20 to-secondary/20">
              <MagnifyingGlassIcon className="h-4 w-4 text-primary" aria-hidden="true" />
            </div>
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(event) => handleInputChange(event.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Search alerts, incidents, rules, people, policies, and reports. Type / for quick actions."
              className="flex-1 bg-transparent text-sm text-text-main placeholder:text-text-muted outline-none"
              disabled={isLoading}
              aria-label="Search SentinelGrid workspace"
              aria-controls="command-palette-results"
              aria-activedescendant={flatResults[activeIndex]?.key}
            />
            {activeAgent && <AgentBadge agentId={activeAgent} variant="pill" />}
            <div className="flex items-center gap-1.5">
              {messages.length > 0 && (
                <button
                  onClick={handleNewChat}
                  className="rounded border border-border-faint px-2 py-1 text-[10px] font-medium text-text-muted transition-colors hover:border-border-muted hover:text-text-main"
                >
                  New chat
                </button>
              )}
              <kbd className="hidden rounded border border-border-faint bg-surface-hover px-1.5 py-0.5 text-[10px] font-mono text-text-muted sm:inline-flex">
                ESC
              </kbd>
            </div>
          </div>
          <div className="mt-2 flex items-center justify-between gap-3 text-[11px] text-text-muted">
            <p>
              {trimmedQuery
                ? 'Arrow keys move through results. Enter opens the active result.'
                : 'Pinned actions, recent items, and live workspace results are available from anywhere in the dashboard.'}
            </p>
            {catalogStatus === 'loading' && <p>Loading workspace results…</p>}
          </div>
        </div>

        {shouldShowResults ? (
          <div id="command-palette-results" className="max-h-[56vh] overflow-y-auto px-4 py-4" role="listbox" aria-label="Command palette results">
            {catalogError && trimmedQuery && (
              <div className="mb-4 rounded-lg border border-rose-400/20 bg-rose-500/10 px-3 py-2 text-xs text-rose-200">
                {catalogError}
              </div>
            )}
            {currentResultGroups.length === 0 && (
              <div className="rounded-xl border border-border-faint bg-surface-hover px-4 py-6 text-center">
                <p className="text-sm font-medium text-text-main">No matching results.</p>
                <p className="mt-2 text-xs text-text-muted">
                  {isCommandQuery
                    ? 'Press Enter to send the command text to AI, or continue typing to filter saved actions.'
                    : 'Press Enter to ask SentinelGrid AI instead.'}
                </p>
              </div>
            )}
            {currentResultGroups.map((group) => (
              <section key={group.id} className="mb-5 last:mb-0">
                <div className="mb-2 flex items-center gap-2">
                  {group.id === 'saved' && <BookmarkIcon className="h-4 w-4 text-text-muted" aria-hidden="true" />}
                  {group.id === 'recent' && <ClockIcon className="h-4 w-4 text-text-muted" aria-hidden="true" />}
                  {group.id === 'ai' && <SparklesIcon className="h-4 w-4 text-text-muted" aria-hidden="true" />}
                  <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-text-muted">
                    {group.title}
                  </p>
                </div>
                <div className="space-y-2">
                  {group.items.map((result) => {
                    const flattenedIndex = flatResults.findIndex((item) => item.key === result.key);
                    const isActive = activeIndex === flattenedIndex;
                    const isSaved = savedShortcuts.some((item) => item.key === result.key);

                    return (
                      <div
                        key={result.key}
                        id={result.key}
                        role="option"
                        aria-selected={isActive}
                        className={clsx(
                          'flex min-h-[56px] items-start gap-2 rounded-xl border px-3 py-3 transition-colors',
                          isActive
                            ? 'border-primary/40 bg-primary/10'
                            : 'border-border-faint bg-surface-card hover:border-border-muted hover:bg-surface-hover'
                        )}
                      >
                        <button
                          type="button"
                          onClick={() => void handleResultSelect(result)}
                          className="flex min-h-[44px] flex-1 items-start gap-3 text-left"
                        >
                          <div className={clsx('mt-0.5 rounded-md border px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.06em]', accentClassName(result.accentTone))}>
                            {result.metaLabel || group.title}
                          </div>
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center gap-2">
                              <p className="truncate text-sm font-medium text-text-main">{result.title}</p>
                              {result.action === 'navigate' && (
                                <ArrowTopRightOnSquareIcon className="h-3.5 w-3.5 flex-shrink-0 text-text-muted" aria-hidden="true" />
                              )}
                              {result.agent && <AgentBadge agentId={result.agent} variant="inline" />}
                            </div>
                            <p className="mt-1 line-clamp-2 text-xs text-text-muted">{result.subtitle}</p>
                          </div>
                        </button>
                        {result.pinnable && (
                          <button
                            type="button"
                            onClick={(event) => {
                              event.stopPropagation();
                              toggleSavedShortcut(result);
                            }}
                            className="mt-0.5 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-md text-text-muted transition-colors hover:bg-surface-hover hover:text-text-main"
                            aria-label={isSaved ? `Remove ${result.title} from saved quick actions` : `Save ${result.title} as a quick action`}
                          >
                            {isSaved ? (
                              <BookmarkSolidIcon className="h-4 w-4" aria-hidden="true" />
                            ) : (
                              <BookmarkIcon className="h-4 w-4" aria-hidden="true" />
                            )}
                          </button>
                        )}
                      </div>
                    );
                  })}
                </div>
              </section>
            ))}
          </div>
        ) : messages.length > 0 ? (
          <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
            {messages.map((message, index) => (
              <div
                key={`${message.role}-${index}`}
                className={clsx('flex', message.role === 'user' ? 'justify-end' : 'justify-start')}
              >
                <div
                  className={clsx(
                    'max-w-[85%] rounded-2xl border px-4 py-2.5 text-sm',
                    message.role === 'user'
                      ? 'border-primary/20 bg-primary/15 text-text-main'
                      : 'border-border-faint bg-surface-hover text-text-main'
                  )}
                >
                  {message.role === 'assistant' && message.answer_type && (
                    <div className="mb-2 flex flex-wrap items-center gap-2">
                      <span
                        className={clsx(
                          'rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase',
                          CHAT_SOURCE_CLASSNAMES[(message.answer_type as ChatSourceTone) || 'general'] ||
                            CHAT_SOURCE_CLASSNAMES.general
                        )}
                      >
                        {CHAT_SOURCE_LABELS[(message.answer_type as ChatSourceTone) || 'general'] ||
                          CHAT_SOURCE_LABELS.general}
                      </span>
                      {message.module === 'compliance' && message.retrieval_categories?.length ? (
                        <span className="text-[10px] text-text-muted">
                          {message.retrieval_categories.join(', ')}
                        </span>
                      ) : null}
                    </div>
                  )}
                  <div className="whitespace-pre-wrap">{message.content}</div>
                  {message.role === 'assistant' && message.actions?.length ? (
                    <div className="mt-3 space-y-1">
                      {message.actions.slice(0, 2).map((action) => (
                        <div
                          key={`${action.action}-${action.recommendation_id || action.label}`}
                          className="rounded-lg border border-border-faint bg-surface-card px-3 py-2 text-xs text-text-muted"
                        >
                          <span className="font-medium text-text-main">{action.label}</span>
                          {action.requires_approval ? <span className="ml-2 text-amber-300">Approval required</span> : null}
                        </div>
                      ))}
                    </div>
                  ) : null}
                  <time className="mt-1 block text-right text-[10px] text-text-muted" dateTime={message.timestamp}>
                    {message.timestamp
                      ? new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                      : ''}
                  </time>
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="flex justify-start">
                <div className="flex items-center gap-2 rounded-2xl border border-border-faint bg-surface-hover px-4 py-3">
                  {activeAgent && <AgentBadge agentId={activeAgent} variant="inline" />}
                  <div className="flex gap-1">
                    <div className="h-1.5 w-1.5 animate-bounce rounded-full bg-primary" />
                    <div className="h-1.5 w-1.5 animate-bounce rounded-full bg-primary" style={{ animationDelay: '0.15s' }} />
                    <div className="h-1.5 w-1.5 animate-bounce rounded-full bg-primary" style={{ animationDelay: '0.3s' }} />
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        ) : (
          <div className="px-4 py-6">
            <div className="rounded-xl border border-border-faint bg-surface-hover px-4 py-6 text-center">
              <p className="text-sm font-medium text-text-main">No workspace results are ready yet.</p>
              <p className="mt-2 text-xs text-text-muted">
                Start with <code className="rounded bg-surface-card px-1 py-0.5 font-mono">/</code> for quick actions or ask the AI assistant a direct question.
              </p>
              <div className="mt-4 grid gap-2 sm:grid-cols-2">
                {suggestions.slice(0, 4).map((suggestion) => (
                  <button
                    key={suggestion}
                    onClick={() => void handleSend(suggestion)}
                    className="min-h-[44px] rounded-lg border border-border-faint px-3 py-2.5 text-left text-xs text-text-muted transition-colors hover:border-border-muted hover:bg-surface-card hover:text-text-main"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
