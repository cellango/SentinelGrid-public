'use client';

import { type ReactNode, useMemo, useState } from 'react';
import clsx from 'clsx';
import {
  ChevronDownIcon,
  ChevronUpIcon,
  CpuChipIcon,
  HandThumbDownIcon,
  SparklesIcon,
} from '@heroicons/react/24/outline';
import { toast } from 'react-hot-toast';
import {
  describeAIConfidence,
  inferAIProcessingLabel,
} from '@/lib/ai/transparency';

interface AITransparencyPanelProps {
  eyebrow?: string;
  title: string;
  summary?: string;
  why?: string | string[];
  whyLabel?: string;
  confidence?: number | string | null;
  modelName?: string | null;
  modelVersion?: string | null;
  provider?: string | null;
  sourceLabel?: string | null;
  localProcessing?: boolean;
  processingHint?: string | null;
  disagreeLabel?: string;
  onDisagree?: () => void | Promise<void>;
  defaultExpanded?: boolean;
  embedded?: boolean;
  compact?: boolean;
  className?: string;
  children?: ReactNode;
}

const confidenceToneClasses = {
  high: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-200',
  medium: 'border-cyan-500/30 bg-cyan-500/10 text-cyan-200',
  low: 'border-amber-500/30 bg-amber-500/10 text-amber-200',
  review: 'border-rose-500/30 bg-rose-500/10 text-rose-200',
} as const;

export default function AITransparencyPanel({
  eyebrow = 'AI transparency',
  title,
  summary,
  why,
  whyLabel = 'Why this was suggested',
  confidence,
  modelName,
  modelVersion,
  provider,
  sourceLabel,
  localProcessing,
  processingHint,
  disagreeLabel = 'Disagree',
  onDisagree,
  defaultExpanded = false,
  embedded = false,
  compact = false,
  className,
  children,
}: AITransparencyPanelProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);
  const [feedbackSubmitting, setFeedbackSubmitting] = useState(false);

  const whyItems = useMemo(() => {
    if (!why) {
      return [];
    }
    return (Array.isArray(why) ? why : [why]).map((item) => item.trim()).filter(Boolean);
  }, [why]);

  const confidenceDescriptor = useMemo(
    () => describeAIConfidence(confidence),
    [confidence]
  );
  const processingLabel = useMemo(
    () =>
      inferAIProcessingLabel({
        localProcessing,
        processingHint,
        provider,
        modelName,
        sourceLabel,
      }),
    [localProcessing, processingHint, provider, modelName, sourceLabel]
  );

  const hasWhyContent = whyItems.length > 0 || Boolean(children);

  const handleDisagree = async () => {
    if (feedbackSubmitted || feedbackSubmitting) {
      return;
    }

    try {
      setFeedbackSubmitting(true);
      await onDisagree?.();
      setFeedbackSubmitted(true);
      toast.success('Feedback noted for analyst review.');
    } catch (error: any) {
      toast.error(error?.message || 'Failed to save AI feedback.');
    } finally {
      setFeedbackSubmitting(false);
    }
  };

  return (
    <section
      className={clsx(
        embedded
          ? 'rounded-lg border border-border-faint bg-[rgba(15,23,42,0.35)]'
          : 'rounded-xl border border-border-faint bg-surface-hover',
        compact ? 'p-3' : 'p-4',
        className
      )}
    >
      <div className="flex flex-col gap-3">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <SparklesIcon className="h-4 w-4 text-primary" aria-hidden="true" />
              <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-primary">
                {eyebrow}
              </p>
            </div>
            <h3 className={clsx('mt-2 font-semibold text-text-main', compact ? 'text-sm' : 'text-base')}>
              {title}
            </h3>
            {summary && (
              <p className={clsx('mt-2 text-text-main', compact ? 'text-xs' : 'text-sm')}>
                {summary}
              </p>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {confidenceDescriptor && (
              <span
                className={clsx(
                  'rounded-full border px-2.5 py-1 text-[11px] font-medium',
                  confidenceToneClasses[confidenceDescriptor.tone]
                )}
              >
                {confidenceDescriptor.label}
              </span>
            )}
            {(modelName || modelVersion) && (
              <span className="rounded-full border border-border-faint px-2.5 py-1 text-[11px] text-text-muted">
                Model {modelName || 'AI'}{modelVersion ? ` v${modelVersion}` : ''}
              </span>
            )}
            {processingLabel && (
              <span className="inline-flex items-center gap-1 rounded-full border border-primary/25 bg-primary/10 px-2.5 py-1 text-[11px] text-primary">
                <CpuChipIcon className="h-3.5 w-3.5" aria-hidden="true" />
                {processingLabel}
              </span>
            )}
          </div>
        </div>

        {(hasWhyContent || onDisagree || disagreeLabel) && (
          <div className="flex flex-wrap items-center gap-2">
            {hasWhyContent && (
              <button
                type="button"
                onClick={() => setExpanded((current) => !current)}
                className="inline-flex min-h-[38px] items-center gap-2 rounded-lg border border-border-faint px-3 py-2 text-sm text-text-main transition-colors hover:border-primary"
                aria-expanded={expanded}
              >
                {expanded ? (
                  <ChevronUpIcon className="h-4 w-4" aria-hidden="true" />
                ) : (
                  <ChevronDownIcon className="h-4 w-4" aria-hidden="true" />
                )}
                {expanded ? 'Hide why' : whyLabel}
              </button>
            )}
            <button
              type="button"
              onClick={() => void handleDisagree()}
              disabled={feedbackSubmitted || feedbackSubmitting}
              className="inline-flex min-h-[38px] items-center gap-2 rounded-lg border border-border-faint px-3 py-2 text-sm text-text-main transition-colors hover:border-primary disabled:opacity-60"
            >
              <HandThumbDownIcon className="h-4 w-4" aria-hidden="true" />
              {feedbackSubmitted
                ? 'Feedback captured'
                : feedbackSubmitting
                  ? 'Submitting feedback...'
                  : disagreeLabel}
            </button>
          </div>
        )}

        {expanded && hasWhyContent && (
          <div className="space-y-3 border-t border-border-faint pt-3">
            {whyItems.length > 0 && (
              <div className="space-y-2">
                {whyItems.map((item) => (
                  <p
                    key={item}
                    className={clsx('text-text-muted', compact ? 'text-xs' : 'text-sm')}
                  >
                    {item}
                  </p>
                ))}
              </div>
            )}
            {children}
          </div>
        )}
      </div>
    </section>
  );
}
