/**
 * Rich Empty State Component
 * Illustrated empty states for common scenarios.
 * Replaces plain "No data" text with contextual illustrations and CTAs.
 */

'use client';

import clsx from 'clsx';

type EmptyStateVariant =
  | 'no-data'
  | 'no-incidents'
  | 'no-alerts'
  | 'no-results'
  | 'no-connection'
  | 'secure'
  | 'coming-soon'
  | 'error';

interface EmptyStateProps {
  variant?: EmptyStateVariant;
  title?: string;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
  secondaryAction?: {
    label: string;
    onClick: () => void;
  };
  className?: string;
  compact?: boolean;
}

// ── SVG Illustrations ──────────────────────────────────────────────────

function NoDataIllustration() {
  return (
    <svg width="120" height="120" viewBox="0 0 120 120" fill="none" className="text-text-muted/30">
      <rect x="20" y="30" width="80" height="60" rx="8" stroke="currentColor" strokeWidth="2" strokeDasharray="4 4" />
      <line x1="40" y1="50" x2="80" y2="50" stroke="currentColor" strokeWidth="2" strokeLinecap="round" opacity="0.4" />
      <line x1="40" y1="60" x2="70" y2="60" stroke="currentColor" strokeWidth="2" strokeLinecap="round" opacity="0.3" />
      <line x1="40" y1="70" x2="60" y2="70" stroke="currentColor" strokeWidth="2" strokeLinecap="round" opacity="0.2" />
      <circle cx="90" cy="30" r="15" stroke="oklch(0.82 0.15 192)" strokeWidth="2" opacity="0.3" />
      <path d="M85 30l4 4 6-8" stroke="oklch(0.82 0.15 192)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" opacity="0.3" />
    </svg>
  );
}

function SecureIllustration() {
  return (
    <svg width="120" height="120" viewBox="0 0 120 120" fill="none">
      <path d="M60 20L30 35V55C30 75 42 93 60 100C78 93 90 75 90 55V35L60 20Z" stroke="oklch(0.65 0.2 145)" strokeWidth="2" fill="oklch(0.65 0.2 145 / 0.08)" />
      <path d="M50 60L56 66L72 50" stroke="oklch(0.65 0.2 145)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="60" cy="58" r="22" stroke="oklch(0.65 0.2 145)" strokeWidth="1" opacity="0.2" strokeDasharray="3 3" />
    </svg>
  );
}

function NoConnectionIllustration() {
  return (
    <svg width="120" height="120" viewBox="0 0 120 120" fill="none" className="text-text-muted/30">
      <circle cx="40" cy="60" r="18" stroke="currentColor" strokeWidth="2" />
      <circle cx="80" cy="60" r="18" stroke="currentColor" strokeWidth="2" />
      <line x1="58" y1="54" x2="62" y2="66" stroke="oklch(0.7 0.2 25)" strokeWidth="2.5" strokeLinecap="round" />
      <line x1="62" y1="54" x2="58" y2="66" stroke="oklch(0.7 0.2 25)" strokeWidth="2.5" strokeLinecap="round" />
      <circle cx="40" cy="60" r="5" fill="currentColor" opacity="0.2" />
      <circle cx="80" cy="60" r="5" fill="currentColor" opacity="0.2" />
    </svg>
  );
}

function NoResultsIllustration() {
  return (
    <svg width="120" height="120" viewBox="0 0 120 120" fill="none" className="text-text-muted/30">
      <circle cx="52" cy="52" r="25" stroke="currentColor" strokeWidth="2" />
      <line x1="70" y1="70" x2="95" y2="95" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
      <line x1="42" y1="47" x2="62" y2="47" stroke="currentColor" strokeWidth="2" strokeLinecap="round" opacity="0.3" />
      <line x1="42" y1="55" x2="55" y2="55" stroke="currentColor" strokeWidth="2" strokeLinecap="round" opacity="0.2" />
    </svg>
  );
}

function ErrorIllustration() {
  return (
    <svg width="120" height="120" viewBox="0 0 120 120" fill="none">
      <circle cx="60" cy="60" r="35" stroke="oklch(0.7 0.2 25)" strokeWidth="2" opacity="0.3" />
      <line x1="48" y1="48" x2="72" y2="72" stroke="oklch(0.7 0.2 25)" strokeWidth="3" strokeLinecap="round" />
      <line x1="72" y1="48" x2="48" y2="72" stroke="oklch(0.7 0.2 25)" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}

function ComingSoonIllustration() {
  return (
    <svg width="120" height="120" viewBox="0 0 120 120" fill="none">
      <rect x="30" y="25" width="60" height="70" rx="8" stroke="oklch(0.82 0.15 192)" strokeWidth="2" opacity="0.3" />
      <path d="M48 50L54 56L68 42" stroke="oklch(0.82 0.15 192)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" opacity="0.5" />
      <line x1="45" y1="68" x2="75" y2="68" stroke="oklch(0.82 0.15 192)" strokeWidth="2" strokeLinecap="round" opacity="0.2" />
      <line x1="45" y1="76" x2="65" y2="76" stroke="oklch(0.82 0.15 192)" strokeWidth="2" strokeLinecap="round" opacity="0.15" />
      <circle cx="85" cy="30" r="12" fill="oklch(0.82 0.15 192 / 0.1)" stroke="oklch(0.82 0.15 192)" strokeWidth="1.5" opacity="0.4" />
      <path d="M82 27v6l4 2" stroke="oklch(0.82 0.15 192)" strokeWidth="1.5" strokeLinecap="round" opacity="0.4" />
    </svg>
  );
}

// ── Variant config ────────────────────────────────────────────────────

const VARIANT_CONFIG: Record<EmptyStateVariant, {
  illustration: () => JSX.Element;
  defaultTitle: string;
  defaultDescription: string;
}> = {
  'no-data': {
    illustration: NoDataIllustration,
    defaultTitle: 'No data yet',
    defaultDescription: 'Data will appear here once your systems are connected and generating findings.',
  },
  'no-incidents': {
    illustration: SecureIllustration,
    defaultTitle: 'No open incidents',
    defaultDescription: 'Your environment is clear. We\'ll alert you immediately if an incident is detected.',
  },
  'no-alerts': {
    illustration: SecureIllustration,
    defaultTitle: 'No active alerts',
    defaultDescription: 'All clear. Detection rules are monitoring your environment around the clock.',
  },
  'no-results': {
    illustration: NoResultsIllustration,
    defaultTitle: 'No results found',
    defaultDescription: 'Try adjusting your search terms or filters to find what you\'re looking for.',
  },
  'no-connection': {
    illustration: NoConnectionIllustration,
    defaultTitle: 'No connections configured',
    defaultDescription: 'Connect your cloud, identity, and endpoint systems to start seeing security insights.',
  },
  'secure': {
    illustration: SecureIllustration,
    defaultTitle: 'Looking good',
    defaultDescription: 'No issues detected. Your security posture is healthy.',
  },
  'coming-soon': {
    illustration: ComingSoonIllustration,
    defaultTitle: 'Coming soon',
    defaultDescription: 'This feature is being built. Check back soon for updates.',
  },
  'error': {
    illustration: ErrorIllustration,
    defaultTitle: 'Something went wrong',
    defaultDescription: 'We couldn\'t load this data. Please try refreshing the page.',
  },
};

// ── Component ──────────────────────────────────────────────────────────

export default function EmptyState({
  variant = 'no-data',
  title,
  description,
  action,
  secondaryAction,
  className,
  compact = false,
}: EmptyStateProps) {
  const config = VARIANT_CONFIG[variant];
  const Illustration = config.illustration;

  return (
    <div
      className={clsx(
        'flex flex-col items-center justify-center text-center',
        compact ? 'py-8 px-4' : 'py-16 px-6',
        className
      )}
      role="status"
    >
      <div className={clsx(compact ? 'mb-3' : 'mb-5')}>
        <Illustration />
      </div>
      <h3 className={clsx(
        'font-semibold text-text-main',
        compact ? 'text-sm' : 'text-base'
      )}>
        {title || config.defaultTitle}
      </h3>
      <p className={clsx(
        'text-text-muted mt-1.5 max-w-sm',
        compact ? 'text-xs' : 'text-sm'
      )}>
        {description || config.defaultDescription}
      </p>
      {(action || secondaryAction) && (
        <div className="flex items-center gap-3 mt-5">
          {action && (
            <button
              onClick={action.onClick}
              className="px-4 py-2 text-sm font-medium text-slate-950 bg-primary rounded-lg hover:brightness-110 transition-all min-h-[44px]"
            >
              {action.label}
            </button>
          )}
          {secondaryAction && (
            <button
              onClick={secondaryAction.onClick}
              className="px-4 py-2 text-sm font-medium text-text-main bg-surface-hover border border-border-faint rounded-lg hover:bg-surface-input transition-colors min-h-[44px]"
            >
              {secondaryAction.label}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
