'use client';

import { useMemo, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import {
  ClipboardDocumentListIcon,
  ClipboardIcon,
  DocumentTextIcon,
  SparklesIcon,
} from '@heroicons/react/24/outline';
import { questionnaireAssist, type QuestionnaireAssistResponse } from '@/lib/api/reports';
import { TRUST_ARTIFACTS } from '@/lib/trustArtifacts';
import { toast } from 'react-hot-toast';

const FALLBACK_STARTER_QUESTIONS = [
  'How do we answer customer security questionnaires quickly?',
  'What can we share for a customer security review?',
  'How do we evidence MFA and access control coverage?',
  'How do we show detection and response coverage?',
];

const ARTIFACT_LABELS = TRUST_ARTIFACTS.reduce<Record<string, string>>((accumulator, artifact) => {
  accumulator[artifact.templateKey] = artifact.title;
  return accumulator;
}, {});

function confidenceClasses(confidence: string) {
  switch (confidence) {
    case 'high':
      return 'bg-emerald-50 text-emerald-700 border-emerald-200';
    case 'medium':
      return 'bg-amber-50 text-amber-700 border-amber-200';
    default:
      return 'border-border-faint bg-surface-hover text-text-muted';
  }
}

export function QuestionnaireAssistPanel() {
  const [questionsText, setQuestionsText] = useState('');
  const [result, setResult] = useState<QuestionnaireAssistResponse | null>(null);

  const mutation = useMutation({
    mutationFn: (questions: string[]) => questionnaireAssist({ questions }),
    onSuccess: (data) => {
      setResult(data);
      toast.success('Drafted questionnaire answers are ready.');
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || 'Failed to draft questionnaire answers');
    },
  });

  const starterQuestions = result?.suggested_questions?.length
    ? result.suggested_questions
    : FALLBACK_STARTER_QUESTIONS;

  const parsedQuestions = useMemo(
    () =>
      questionsText
        .split('\n')
        .map((item) => item.trim())
        .filter(Boolean),
    [questionsText]
  );

  const handleRunAssist = () => {
    if (parsedQuestions.length === 0) {
      toast.error('Enter at least one questionnaire item.');
      return;
    }
    mutation.mutate(parsedQuestions);
  };

  const handleAddStarter = (question: string) => {
    setQuestionsText((current) => {
      const lines = current
        .split('\n')
        .map((item) => item.trim())
        .filter(Boolean);

      if (lines.includes(question)) {
        return current;
      }

      return [...lines, question].join('\n');
    });
  };

  const handleCopyAll = async () => {
    if (!result?.answers?.length) {
      toast.error('Run questionnaire assist first.');
      return;
    }

    const content = result.answers
      .map(
        (answer) =>
          `Question: ${answer.question}\nAnswer: ${answer.answer}\nRecommended artifacts: ${answer.recommended_artifacts
            .map((artifact) => ARTIFACT_LABELS[artifact.template_key] || artifact.template_key)
            .join(', ')}\nFollow-up: ${answer.follow_up.join(' ')}`
      )
      .join('\n\n');

    try {
      await navigator.clipboard.writeText(content);
      toast.success('Drafted answers copied.');
    } catch {
      toast.error('Failed to copy drafted answers');
    }
  };

  return (
    <div id="questionnaire-assist" className="mb-6 rounded-lg border border-surface-card-border bg-surface-card p-6 shadow">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h2 className="text-xl font-semibold text-text-main">Questionnaire Assist</h2>
          <p className="mt-1 text-sm text-text-muted">
            Paste customer security-review questions and SentinelGrid will draft answers from live compliance data and recommend the right trust artifact.
          </p>
        </div>
        <button
          onClick={handleCopyAll}
          className="inline-flex items-center rounded-lg border border-border-faint px-4 py-2 text-sm font-medium text-text-main hover:bg-surface-hover"
        >
          <ClipboardIcon className="mr-2 h-4 w-4" />
          Copy drafted answers
        </button>
      </div>

      <div className="mt-5 rounded-xl border border-primary/20 bg-primary/10 p-4">
        <p className="text-xs uppercase tracking-wide text-primary">Starter questions</p>
        <div className="mt-3 flex flex-wrap gap-2">
          {starterQuestions.map((question) => (
            <button
              key={question}
              onClick={() => handleAddStarter(question)}
              className="rounded-full border border-primary/30 bg-surface-card px-3 py-1.5 text-sm text-primary hover:border-primary/50"
            >
              {question}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-5">
        <label htmlFor="questionnaire-assist-input" className="mb-2 block text-sm font-medium text-text-main">
          Questionnaire items
        </label>
        <textarea
          id="questionnaire-assist-input"
          value={questionsText}
          onChange={(event) => setQuestionsText(event.target.value)}
          placeholder="Paste one customer security-review or audit question per line."
          rows={6}
          className="w-full rounded-lg border border-border-faint bg-surface-input px-3 py-3 text-sm text-text-main focus:outline-none focus:ring-2 focus:ring-primary"
        />
        <div className="mt-3 flex items-center justify-between gap-3 flex-wrap">
          <p className="text-xs text-text-muted">
            {parsedQuestions.length} question{parsedQuestions.length === 1 ? '' : 's'} ready
          </p>
          <button
            onClick={handleRunAssist}
            disabled={mutation.isPending}
            className="inline-flex items-center rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary/90 disabled:opacity-50"
          >
            <SparklesIcon className="mr-2 h-4 w-4" />
            {mutation.isPending ? 'Drafting answers…' : 'Draft answers'}
          </button>
        </div>
      </div>

      {result ? (
        <div className="mt-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="rounded-xl border border-border-faint bg-surface-hover p-4">
              <p className="text-xs uppercase tracking-wide text-text-muted">Overall score</p>
              <p className="mt-2 text-3xl font-bold text-text-main">{result.summary.overall_score}/100</p>
            </div>
            <div className="rounded-xl border border-border-faint bg-surface-hover p-4">
              <p className="text-xs uppercase tracking-wide text-text-muted">Criteria ready</p>
              <p className="mt-2 text-3xl font-bold text-text-main">{result.summary.criteria_ready}</p>
            </div>
            <div className="rounded-xl border border-border-faint bg-surface-hover p-4">
              <p className="text-xs uppercase tracking-wide text-text-muted">Mapped detections</p>
              <p className="mt-2 text-3xl font-bold text-text-main">{result.summary.mapped_detections}</p>
            </div>
            <div className="rounded-xl border border-border-faint bg-surface-hover p-4">
              <p className="text-xs uppercase tracking-wide text-text-muted">Evidence items</p>
              <p className="mt-2 text-3xl font-bold text-text-main">{result.summary.evidence_items}</p>
            </div>
          </div>

          <div className="mt-5 rounded-xl border border-border-faint bg-surface-hover p-4">
            <p className="text-xs uppercase tracking-wide text-text-muted">Recommended trust artifacts</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {result.summary.recommended_artifacts.map((artifact) => (
                <span
                  key={artifact.template_key}
                  className="rounded-full border border-primary/30 bg-surface-card px-3 py-1.5 text-sm text-primary"
                >
                  {ARTIFACT_LABELS[artifact.template_key] || artifact.template_key}
                </span>
              ))}
            </div>
          </div>

          <div className="mt-6 space-y-4">
            {result.answers.map((answer) => (
              <div key={answer.question} className="rounded-2xl border border-border-faint p-5">
                <div className="flex items-start justify-between gap-3 flex-wrap">
                  <div>
                    <p className="text-xs uppercase tracking-wide text-text-muted">Question</p>
                    <h3 className="mt-2 text-lg font-semibold text-text-main">{answer.question}</h3>
                  </div>
                  <span className={`rounded-full border px-3 py-1 text-xs font-medium ${confidenceClasses(answer.confidence)}`}>
                    {answer.confidence} confidence
                  </span>
                </div>

                <div className="mt-4 rounded-xl bg-surface-hover p-4 text-sm leading-6 text-text-main">
                  {answer.answer}
                </div>

                <div className="mt-4 grid grid-cols-1 xl:grid-cols-3 gap-4">
                  <div className="rounded-xl border border-border-faint p-4">
                    <div className="flex items-center gap-2">
                      <DocumentTextIcon className="h-4 w-4 text-primary" />
                      <p className="text-sm font-semibold text-text-main">Recommended artifacts</p>
                    </div>
                    <div className="mt-3 space-y-2">
                      {answer.recommended_artifacts.map((artifact) => (
                        <div key={artifact.template_key} className="rounded-lg bg-surface-hover px-3 py-2">
                          <p className="text-sm font-medium text-text-main">
                            {ARTIFACT_LABELS[artifact.template_key] || artifact.template_key}
                          </p>
                          <p className="mt-1 text-xs text-text-muted">{artifact.reason}</p>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="rounded-xl border border-border-faint p-4">
                    <div className="flex items-center gap-2">
                      <ClipboardDocumentListIcon className="h-4 w-4 text-primary" />
                      <p className="text-sm font-semibold text-text-main">Supporting criteria</p>
                    </div>
                    <div className="mt-3 space-y-2">
                      {answer.supporting_controls.length > 0 ? (
                        answer.supporting_controls.map((control) => (
                          <div key={control.id} className="rounded-lg bg-surface-hover px-3 py-2">
                            <p className="text-sm font-medium text-text-main">
                              {control.id} · {control.title}
                            </p>
                            <p className="mt-1 text-xs text-text-muted">
                              {control.status.replace(/_/g, ' ')} · {control.open_findings} open findings · {control.evidence_items} evidence items
                            </p>
                          </div>
                        ))
                      ) : (
                        <p className="text-sm text-text-muted">No supporting criteria were identified for this question.</p>
                      )}
                    </div>
                  </div>

                  <div className="rounded-xl border border-border-faint p-4">
                    <div className="flex items-center gap-2">
                      <SparklesIcon className="h-4 w-4 text-primary" />
                      <p className="text-sm font-semibold text-text-main">Follow-up</p>
                    </div>
                    <div className="mt-3 space-y-2">
                      {answer.follow_up.map((item) => (
                        <div key={item} className="rounded-lg bg-surface-hover px-3 py-2 text-sm text-text-main">
                          {item}
                        </div>
                      ))}
                    </div>
                    {answer.supporting_signals.length > 0 ? (
                      <div className="mt-4 border-t border-border-faint pt-4">
                        <p className="text-xs uppercase tracking-wide text-text-muted">Supporting signals</p>
                        <div className="mt-2 space-y-2">
                          {answer.supporting_signals.map((signal) => (
                            <div key={signal.id} className="rounded-lg bg-surface-hover px-3 py-2">
                              <p className="text-sm font-medium text-text-main">{signal.title}</p>
                              <p className="mt-1 text-xs text-text-muted">
                                {signal.source_label || 'Signal'}
                                {signal.status ? ` · ${signal.status.replace(/_/g, ' ')}` : ''}
                              </p>
                            </div>
                          ))}
                        </div>
                      </div>
                    ) : null}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}
