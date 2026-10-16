'use client';

import React, { useMemo, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import { withSessionAuthorization } from '@/lib/auth/session';
import {
  CalendarIcon,
  ArrowPathIcon,
  PlusCircleIcon,
  TrashIcon,
} from '@heroicons/react/24/outline';

type ScheduleRequest = {
  template_id: string;
  schedule: {
    frequency: 'daily' | 'weekly' | 'monthly' | 'quarterly';
    day?: string;
    time: string;
    recipients: string[];
    enabled: boolean;
  };
};

type TemplateSummary = {
  id: string;
  name: string;
  type: string;
  schedule?: {
    frequency: string;
    day?: string;
    time?: string;
    enabled?: boolean;
  };
};

type ScheduledJob = {
  job_id: string;
  next_run_time: string | null;
  trigger: string;
  template_name?: string;
  template_id?: string;
};

const frequencyOptions = [
  { value: 'daily', label: 'Daily' },
  { value: 'weekly', label: 'Weekly' },
  { value: 'monthly', label: 'Monthly' },
  { value: 'quarterly', label: 'Quarterly' },
];

const weekDays = [
  'monday',
  'tuesday',
  'wednesday',
  'thursday',
  'friday',
  'saturday',
  'sunday',
];

export default function ComplianceReportSchedules() {
  const queryClient = useQueryClient();
  const [typeFilter, setTypeFilter] = useState<string>('soc2');
  const [templateId, setTemplateId] = useState<string>('');
  const [frequency, setFrequency] = useState<'daily' | 'weekly' | 'monthly' | 'quarterly'>('monthly');
  const [day, setDay] = useState<string>('1'); // day of month for monthly/quarterly
  const [dayOfWeek, setDayOfWeek] = useState<string>('monday'); // for weekly
  const [time, setTime] = useState<string>('09:00');
  const [recipientsText, setRecipientsText] = useState<string>('');
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const authHeaders = (): HeadersInit => {
    return withSessionAuthorization();
  };

  const { data: templates, isLoading: loadingTemplates } = useQuery<TemplateSummary[]>({
    queryKey: ['scheduled-report-templates', typeFilter],
    queryFn: async () => {
      const url = typeFilter
        ? `/api/v1/reports/scheduled/templates?type_filter=${typeFilter}`
        : '/api/v1/reports/scheduled/templates';
      const res = await fetch(url, { headers: { ...authHeaders() }, credentials: 'include' });
      if (!res.ok) throw new Error('Failed to load templates');
      return res.json();
    },
  });

  const { data: scheduledJobs, isLoading: loadingJobs } = useQuery<{ items: ScheduledJob[] }>({
    queryKey: ['scheduled-reports'],
    queryFn: async () => {
      const res = await fetch('/api/v1/reports/scheduled/', {
        headers: { ...authHeaders() },
        credentials: 'include',
      });
      if (!res.ok) throw new Error('Failed to load schedules');
      return res.json();
    },
  });

  const createSchedule = useMutation({
    mutationFn: async (payload: ScheduleRequest) => {
      const res = await fetch('/api/v1/reports/scheduled/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        credentials: 'include',
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const msg = await res.text();
        throw new Error(msg || 'Failed to create schedule');
      }
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scheduled-reports'] });
      setErrorMessage(null);
    },
    onError: (err: any) => {
      setErrorMessage(err?.message || 'Failed to create schedule');
    },
  });

  const deleteSchedule = useMutation({
    mutationFn: async (jobId: string) => {
      const res = await fetch(`/api/v1/reports/scheduled/${jobId}`, {
        method: 'DELETE',
        headers: { ...authHeaders() },
        credentials: 'include',
      });
      if (!res.ok) {
        const msg = await res.text();
        throw new Error(msg || 'Failed to delete schedule');
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scheduled-reports'] });
    },
  });

  const selectedTemplate = useMemo(
    () => templates?.find((t) => t.id === templateId),
    [templates, templateId]
  );

  const handleSubmit = async () => {
    if (!templateId) {
      setErrorMessage('Please choose a template to schedule.');
      return;
    }
    setSubmitting(true);
    try {
      const recipients = recipientsText
        .split(',')
        .map((r) => r.trim())
        .filter(Boolean);

      const payload: ScheduleRequest = {
        template_id: templateId,
        schedule: {
          frequency,
          day: frequency === 'weekly' ? dayOfWeek : day,
          time,
          recipients,
          enabled: true,
        },
      };

      await createSchedule.mutateAsync(payload);
      setErrorMessage(null);
    } catch (err) {
      // error handled in mutation onError
    } finally {
      setSubmitting(false);
    }
  };

  const renderDaySelector = () => {
    if (frequency === 'weekly') {
      return (
        <select
          value={dayOfWeek}
          onChange={(e) => setDayOfWeek(e.target.value)}
          className="w-full rounded-lg border border-border-faint bg-surface-input px-3 py-2 text-text-main focus:outline-none focus:ring-2 focus:ring-primary"
        >
          {weekDays.map((d) => (
            <option key={d} value={d}>
              {d.charAt(0).toUpperCase() + d.slice(1)}
            </option>
          ))}
        </select>
      );
    }
    return (
      <input
        type="number"
        min={1}
        max={31}
        value={day}
        onChange={(e) => setDay(e.target.value)}
        className="w-full rounded-lg border border-border-faint bg-surface-input px-3 py-2 text-text-main focus:outline-none focus:ring-2 focus:ring-primary"
      />
    );
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-text-main">Report Scheduling</h1>
          <p className="mt-2 text-text-muted">
            Automate SOC 2 and other compliance reports with weekly, monthly, or quarterly schedules.
          </p>
        </div>
        <Link
          href="/dashboard/compliance/reports"
          className="inline-flex items-center rounded-lg border border-border-faint bg-surface-hover px-4 py-2 text-text-main hover:bg-surface-input"
        >
          <CalendarIcon className="h-5 w-5 mr-2" />
          Back to Reports
        </Link>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="space-y-4 rounded-xl border border-surface-card-border bg-surface-card p-5 shadow">
          <div className="flex items-center gap-2">
            <PlusCircleIcon className="h-6 w-6 text-primary" />
            <div>
              <h2 className="text-xl font-semibold text-text-main">New Schedule</h2>
              <p className="text-sm text-text-muted">Choose a template and cadence.</p>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4">
            <div>
              <label className="text-sm font-medium text-text-main">Template Type</label>
              <select
                value={typeFilter}
                onChange={(e) => {
                  setTypeFilter(e.target.value);
                  setTemplateId('');
                }}
                className="mt-1 w-full rounded-lg border border-border-faint bg-surface-input px-3 py-2 text-text-main focus:outline-none focus:ring-2 focus:ring-primary"
                data-testid="schedule-template-type-select"
              >
                <option value="">All</option>
                <option value="soc2">SOC 2</option>
                <option value="compliance">Compliance</option>
                <option value="security_posture">Security Posture</option>
              </select>
            </div>

            <div>
              <label className="text-sm font-medium text-text-main">Template</label>
              <select
                value={templateId}
                onChange={(e) => setTemplateId(e.target.value)}
                className="mt-1 w-full rounded-lg border border-border-faint bg-surface-input px-3 py-2 text-text-main focus:outline-none focus:ring-2 focus:ring-primary"
                disabled={loadingTemplates}
                data-testid="schedule-template-select"
              >
                <option value="">Select a template</option>
                {templates?.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </select>
              {selectedTemplate?.schedule && (
                <p className="mt-1 text-xs text-text-muted">
                  Existing schedule: {selectedTemplate.schedule.frequency} at {selectedTemplate.schedule.time}{' '}
                  {selectedTemplate.schedule.day ? `on ${selectedTemplate.schedule.day}` : ''}
                </p>
              )}
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-text-main">Frequency</label>
                <select
                  value={frequency}
                  onChange={(e) => setFrequency(e.target.value as any)}
                  className="mt-1 w-full rounded-lg border border-border-faint bg-surface-input px-3 py-2 text-text-main focus:outline-none focus:ring-2 focus:ring-primary"
                  data-testid="schedule-frequency-select"
                >
                  {frequencyOptions.map((f) => (
                    <option key={f.value} value={f.value}>
                      {f.label}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-sm font-medium text-text-main">
                  {frequency === 'weekly' ? 'Day of Week' : 'Day of Month'}
                </label>
                <div className="mt-1">{renderDaySelector()}</div>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-text-main">Time (UTC)</label>
                <input
                  type="time"
                  value={time}
                  onChange={(e) => setTime(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-border-faint bg-surface-input px-3 py-2 text-text-main focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
              <div>
                <label className="text-sm font-medium text-text-main">Recipients (comma-separated)</label>
                <input
                  type="text"
                  placeholder="security@example.com, compliance@example.com"
                  value={recipientsText}
                  onChange={(e) => setRecipientsText(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-border-faint bg-surface-input px-3 py-2 text-text-main focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
            </div>

            {errorMessage && (
              <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-600" role="alert">
                {errorMessage}
              </div>
            )}

            <button
              onClick={handleSubmit}
              disabled={submitting}
              className="inline-flex items-center justify-center rounded-lg bg-primary px-4 py-2 text-white hover:bg-primary/90 disabled:opacity-70"
            >
              {submitting ? (
                <>
                  <ArrowPathIcon className="h-5 w-5 mr-2 animate-spin" />
                  Creating schedule...
                </>
              ) : (
                <>
                  <PlusCircleIcon className="h-5 w-5 mr-2" />
                  Create schedule
                </>
              )}
            </button>
          </div>
        </div>

        <div className="space-y-4 rounded-xl border border-surface-card-border bg-surface-card p-5 shadow">
          <div className="flex items-center gap-2">
            <CalendarIcon className="h-6 w-6 text-emerald-600" />
            <div>
              <h2 className="text-xl font-semibold text-text-main">Scheduled Jobs</h2>
              <p className="text-sm text-text-muted">View or remove active schedules.</p>
            </div>
          </div>

          {loadingJobs ? (
            <div className="text-sm text-text-muted">Loading schedules...</div>
          ) : scheduledJobs?.items?.length ? (
            <div className="space-y-3">
              {scheduledJobs.items.map((job) => (
                <div
                  key={job.job_id}
                  className="flex items-start justify-between rounded-lg border border-border-faint p-3"
                >
                  <div>
                    <p className="text-sm font-semibold text-text-main">
                      {job.template_name || 'Report Template'}
                    </p>
                    <p className="text-xs text-text-muted">Job ID: {job.job_id}</p>
                    <p className="text-xs text-text-muted">
                      Next run: {job.next_run_time ? new Date(job.next_run_time).toUTCString() : 'Not scheduled'}
                    </p>
                    <p className="text-xs text-text-muted">Trigger: {job.trigger}</p>
                  </div>
                  <button
                    onClick={() => deleteSchedule.mutate(job.job_id)}
                    className="text-red-600 hover:text-red-700"
                    title="Remove scheduled report"
                    aria-label={`Remove scheduled report ${job.template_name || job.job_id}`}
                  >
                    <TrashIcon className="h-5 w-5" />
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-sm text-text-muted">No scheduled reports yet.</div>
          )}
        </div>
      </div>
    </div>
  );
}
