/**
 * Agent Badge — Multi-Agent Transparency
 * Shows which AI agent performed an automated action.
 * Builds trust by making AI actions visible and traceable.
 */

'use client';

import clsx from 'clsx';

// ── Agent registry ─────────────────────────────────────────────────────

export type AgentId =
  | 'orchestrator'
  | 'siem_agent'
  | 'iam_agent'
  | 'compliance_agent'
  | 'cloud_posture_agent'
  | 'incident_agent'
  | 'detection_agent'
  | 'remediation_agent'
  | 'ai_shield_agent'
  | 'reporting_agent';

interface AgentInfo {
  label: string;
  shortLabel: string;
  color: string;
  icon: string; // SVG path
}

const AGENTS: Record<AgentId, AgentInfo> = {
  orchestrator: {
    label: 'Orchestrator',
    shortLabel: 'ORCH',
    color: 'bg-primary/15 border-primary/40 text-primary',
    icon: 'M4.5 12a7.5 7.5 0 0015 0m-15 0a7.5 7.5 0 1115 0m-15 0H3m16.5 0H21m-1.5 0H12m-8.457 3.077l1.41-.513m14.095-5.13l1.41-.513M5.106 17.785l1.15-.964m11.49-9.642l1.149-.964M7.501 19.795l.75-1.3m7.5-12.99l.75-1.3m-6.063 16.658l.26-1.477m2.605-14.772l.26-1.477m0 17.726l-.26-1.477M10.698 4.614l-.26-1.477M16.5 19.794l-.75-1.299M7.5 4.205L12 12m6.894 5.785l-1.149-.964M6.256 7.178l-1.15-.964m15.352 8.864l-1.41-.513M4.954 9.435l-1.41-.514M12.002 12l-3.75 6.495',
  },
  siem_agent: {
    label: 'SIEM Agent',
    shortLabel: 'SIEM',
    color: 'bg-blue-500/15 border-blue-500/40 text-blue-300',
    icon: 'M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126z',
  },
  iam_agent: {
    label: 'IAM Agent',
    shortLabel: 'IAM',
    color: 'bg-violet-500/15 border-violet-500/40 text-violet-300',
    icon: 'M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952 4.125 4.125 0 00-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 018.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0111.964-3.07M12 6.375a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm8.25 2.25a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z',
  },
  compliance_agent: {
    label: 'Compliance Agent',
    shortLabel: 'COMP',
    color: 'bg-emerald-500/15 border-emerald-500/40 text-emerald-300',
    icon: 'M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z',
  },
  cloud_posture_agent: {
    label: 'Cloud Posture Agent',
    shortLabel: 'CLOUD',
    color: 'bg-sky-500/15 border-sky-500/40 text-sky-300',
    icon: 'M2.25 15a4.5 4.5 0 004.5 4.5H18a3.75 3.75 0 001.332-7.257 3 3 0 00-3.758-3.848 5.25 5.25 0 00-10.233 2.33A4.502 4.502 0 002.25 15z',
  },
  incident_agent: {
    label: 'Incident Agent',
    shortLabel: 'INC',
    color: 'bg-rose-500/15 border-rose-500/40 text-rose-300',
    icon: 'M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z',
  },
  detection_agent: {
    label: 'Detection Agent',
    shortLabel: 'DET',
    color: 'bg-amber-500/15 border-amber-500/40 text-amber-300',
    icon: 'M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z',
  },
  remediation_agent: {
    label: 'Remediation Agent',
    shortLabel: 'REM',
    color: 'bg-teal-500/15 border-teal-500/40 text-teal-300',
    icon: 'M11.42 15.17l-5.657-5.657a8 8 0 1111.314 0l-5.657 5.657z',
  },
  ai_shield_agent: {
    label: 'AI Shield Agent',
    shortLabel: 'AI',
    color: 'bg-fuchsia-500/15 border-fuchsia-500/40 text-fuchsia-300',
    icon: 'M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z',
  },
  reporting_agent: {
    label: 'Reporting Agent',
    shortLabel: 'RPT',
    color: 'bg-indigo-500/15 border-indigo-500/40 text-indigo-300',
    icon: 'M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z',
  },
};

// ── Badge variants ─────────────────────────────────────────────────────

interface AgentBadgeProps {
  agentId: AgentId;
  action?: string;
  timestamp?: string;
  variant?: 'inline' | 'pill' | 'card';
  className?: string;
}

export default function AgentBadge({
  agentId,
  action,
  timestamp,
  variant = 'pill',
  className,
}: AgentBadgeProps) {
  const agent = AGENTS[agentId];
  if (!agent) return null;

  if (variant === 'inline') {
    return (
      <span
        className={clsx('inline-flex items-center gap-1 text-xs', className)}
        title={`Automated by ${agent.label}`}
      >
        <svg className="w-3 h-3 text-text-muted" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24" aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round" d={agent.icon} />
        </svg>
        <span className="text-text-muted">{agent.shortLabel}</span>
      </span>
    );
  }

  if (variant === 'card') {
    return (
      <div
        className={clsx('flex items-center gap-3 p-3 rounded-lg border', agent.color, className)}
        role="status"
        aria-label={`Automated by ${agent.label}${action ? `: ${action}` : ''}`}
      >
        <div className="w-8 h-8 rounded-md bg-primary-ghost flex items-center justify-center flex-shrink-0">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" d={agent.icon} />
          </svg>
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-xs font-semibold">{agent.label}</p>
          {action && <p className="text-[10px] opacity-80 truncate">{action}</p>}
        </div>
        {timestamp && (
          <time className="text-[10px] opacity-60 flex-shrink-0" dateTime={timestamp}>
            {new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </time>
        )}
      </div>
    );
  }

  // Default: pill
  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-medium border',
        agent.color,
        className
      )}
      title={`Automated by ${agent.label}${action ? `: ${action}` : ''}`}
      role="status"
    >
      <svg className="w-3 h-3" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24" aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" d={agent.icon} />
      </svg>
      {agent.shortLabel}
      {action && <span className="opacity-70">· {action}</span>}
    </span>
  );
}

export { AGENTS };
