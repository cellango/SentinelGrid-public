'use client';

import { useQuery } from '@tanstack/react-query';
import { ClipboardIcon, EnvelopeIcon, SparklesIcon } from '@heroicons/react/24/outline';
import { listSecurityReviewTemplates } from '@/lib/api/reports';
import { TRUST_ARTIFACTS } from '@/lib/trustArtifacts';
import { toast } from 'react-hot-toast';

const ARTIFACT_LABELS = TRUST_ARTIFACTS.reduce<Record<string, string>>((accumulator, artifact) => {
  accumulator[artifact.templateKey] = artifact.title;
  return accumulator;
}, {});

function copyText(value: string, successMessage: string) {
  return navigator.clipboard
    .writeText(value)
    .then(() => {
      toast.success(successMessage);
    })
    .catch(() => {
      toast.error('Failed to copy template');
    });
}

export function SecurityReviewResponseTemplatesPanel() {
  const { data, isLoading } = useQuery({
    queryKey: ['security-review-templates'],
    queryFn: listSecurityReviewTemplates,
  });

  const templates = data?.templates || [];

  return (
    <div id="security-review-templates" className="mb-6 rounded-lg border border-surface-card-border bg-surface-card p-6 shadow">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h2 className="text-xl font-semibold text-text-main">Sales Response Templates</h2>
          <p className="mt-1 text-sm text-text-muted">
            Copy-ready security review replies for sales, solutions engineering, and trust-response workflows.
          </p>
        </div>
        {data ? (
          <div className="flex flex-wrap gap-2 text-xs text-text-muted">
            <span className="rounded-full border border-border-faint bg-surface-hover px-3 py-1">
              Score {data.summary.overall_score}/100
            </span>
            <span className="rounded-full border border-border-faint bg-surface-hover px-3 py-1">
              {data.summary.criteria_ready} criteria ready
            </span>
            <span className="rounded-full border border-border-faint bg-surface-hover px-3 py-1">
              {data.summary.evidence_items} evidence items
            </span>
          </div>
        ) : null}
      </div>

      {isLoading ? (
        <div className="mt-5 rounded-xl border border-dashed border-border-faint p-6 text-sm text-text-muted">
          Loading sales response templates...
        </div>
      ) : templates.length === 0 ? (
        <div className="mt-5 rounded-xl border border-dashed border-border-faint p-6 text-sm text-text-muted">
          No sales response templates are available yet.
        </div>
      ) : (
        <div className="mt-6 space-y-4">
          {templates.map((template) => (
            <div key={template.key} className="rounded-2xl border border-border-faint p-5">
              <div className="flex items-start justify-between gap-4 flex-wrap">
                <div>
                  <p className="text-xs uppercase tracking-wide text-text-muted">Response template</p>
                  <h3 className="mt-2 text-lg font-semibold text-text-main">{template.title}</h3>
                  <p className="mt-1 text-sm text-text-muted">{template.use_when}</p>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => copyText(template.subject, 'Subject copied.')}
                    className="inline-flex items-center rounded-lg border border-border-faint px-3 py-2 text-sm font-medium text-text-main hover:bg-surface-hover"
                  >
                    <EnvelopeIcon className="mr-2 h-4 w-4" />
                    Copy subject
                  </button>
                  <button
                    onClick={() => copyText(`Subject: ${template.subject}\n\n${template.body}`, 'Reply copied.')}
                    className="inline-flex items-center rounded-lg bg-primary px-3 py-2 text-sm font-semibold text-white hover:bg-primary/90"
                  >
                    <ClipboardIcon className="mr-2 h-4 w-4" />
                    Copy reply
                  </button>
                </div>
              </div>

              <div className="mt-4 rounded-xl border border-border-faint bg-surface-hover p-4">
                <p className="text-xs uppercase tracking-wide text-text-muted">Subject line</p>
                <p className="mt-2 text-sm font-medium text-text-main">{template.subject}</p>
              </div>

              <div className="mt-4 rounded-xl bg-surface-hover p-4 text-sm leading-6 text-text-main">
                {template.body}
              </div>

              <div className="mt-4 grid grid-cols-1 xl:grid-cols-3 gap-4">
                <div className="rounded-xl border border-border-faint p-4">
                  <div className="flex items-center gap-2">
                    <SparklesIcon className="h-4 w-4 text-primary" />
                    <p className="text-sm font-semibold text-text-main">Recommended artifacts</p>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {template.recommended_artifacts.map((artifact) => (
                      <span
                        key={artifact.template_key}
                        className="rounded-full border border-primary/30 bg-primary/10 px-3 py-1.5 text-sm text-primary"
                      >
                        {ARTIFACT_LABELS[artifact.template_key] || artifact.template_key}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="rounded-xl border border-border-faint p-4">
                  <p className="text-sm font-semibold text-text-main">Talking points</p>
                  <div className="mt-3 space-y-2">
                    {template.talking_points.map((item) => (
                      <div key={item} className="rounded-lg bg-surface-hover px-3 py-2 text-sm text-text-main">
                        {item}
                      </div>
                    ))}
                  </div>
                </div>

                <div className="rounded-xl border border-border-faint p-4">
                  <p className="text-sm font-semibold text-text-main">Next step</p>
                  <div className="mt-3 space-y-2">
                    {template.follow_up.map((item) => (
                      <div key={item} className="rounded-lg bg-surface-hover px-3 py-2 text-sm text-text-main">
                        {item}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
