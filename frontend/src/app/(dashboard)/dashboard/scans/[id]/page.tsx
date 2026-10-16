'use client';

import useSWR from 'swr';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { apiClient } from '@/lib/api/client';
import Breadcrumbs from '@/components/ui/Breadcrumbs';
import { getScan, type ScanDetail } from '@/lib/api/scans';
import { useState } from 'react';
import { toast } from 'react-hot-toast';

export default function ScanDetailPage() {
  const params = useParams();
  const scanId = params?.id as string;
  const { data, error, mutate } = useSWR<ScanDetail>(scanId || null, getScan, {
    refreshInterval: 10000,
  });
  const [ticketState, setTicketState] = useState<Record<string, 'idle' | 'saving' | 'done' | 'error'>>({});
  const [scanTicketState, setScanTicketState] = useState<'idle' | 'saving' | 'done'>('idle');

  if (error) {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-bold text-text-main mb-2">Scan Details</h1>
        <div className="rounded border border-amber-500/50 bg-amber-500/10 text-amber-100 text-sm px-3 py-2">
          {error.status === 429 ? 'Rate limit or concurrency limit hit. Please retry shortly.' : 'Failed to load scan details'}
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-bold text-text-main mb-2">Scan Details</h1>
        <p className="text-sm text-text-muted">Loading...</p>
      </div>
    );
  }

  const statusBadge =
    data.status === 'completed'
      ? 'bg-emerald-500/20 text-emerald-300'
      : data.status === 'running'
      ? 'bg-amber-500/20 text-amber-200'
      : data.status === 'failed'
      ? 'bg-rose-500/20 text-rose-200'
      : 'bg-slate-700 text-slate-200';
  const typeLabel = data.scan_type || data.summary?.type || 'scan';
  const cves = Array.isArray(data.summary?.cves) ? data.summary?.cves : [];
  const remediation = data.summary?.remediation || {};
  const externallyExposed = Boolean(data.summary?.externally_exposed);
  const defaultFrameworks: Record<
    string,
    { nist?: string[]; mitre?: string[] }
  > = {
    cloud: { nist: ['RA-5', 'CM-6'], mitre: ['T1580'] },
    vuln: { nist: ['RA-5', 'SI-2'], mitre: ['T1190'] },
    dast: { nist: ['RA-5', 'SI-10'], mitre: ['T1190'] },
    sast: { nist: ['RA-5', 'CM-7'], mitre: ['T1036'] },
    secrets: { nist: ['CM-8'], mitre: ['T1552'] },
    iac: { nist: ['CM-6'], mitre: ['T1552'] },
    git: { nist: ['RA-5'], mitre: ['T1552'] },
    endpoint: { nist: ['RA-5'], mitre: ['T1059.003'] },
    host: { nist: ['RA-5', 'SI-2'], mitre: ['T1068'] },
  };
  const nistControls = (
    Array.isArray(data.summary?.nist_controls) ? data.summary?.nist_controls : defaultFrameworks[typeLabel]?.nist
  ) || [];
  const mitreTechniques = (
    Array.isArray(data.summary?.mitre_techniques) ? data.summary?.mitre_techniques : defaultFrameworks[typeLabel]?.mitre
  ) || [];

  const detailSections: { title: string; rows: { label: string; value?: string | number | boolean | null }[] }[] = [];

  if (typeLabel === 'cloud') {
    detailSections.push({
      title: 'Cloud posture',
      rows: [
        { label: 'Target', value: data.target_ref || data.summary?.account || '—' },
        {
          label: 'Controls failing',
          value: Array.isArray(data.summary?.failing_controls) ? `${data.summary.failing_controls.length}` : undefined,
        },
      ],
    });
  }

  if (typeLabel === 'dast') {
    detailSections.push({
      title: 'Web target',
      rows: [
        { label: 'Target URL', value: data.summary?.target_url || data.target_ref || '—' },
        { label: 'Evidence', value: data.summary?.evidence },
        { label: 'Target kind', value: data.summary?.target_kind },
      ],
    });
  }

  if (typeLabel === 'sast') {
    detailSections.push({
      title: 'Code location',
      rows: [
        { label: 'File', value: data.summary?.file_path },
        { label: 'Line', value: data.summary?.line },
        { label: 'Rule', value: data.summary?.rule_id },
        { label: 'CWE', value: data.summary?.cwe },
      ],
    });
  }

  if (typeLabel === 'secrets') {
    detailSections.push({
      title: 'Secret finding',
      rows: [
        { label: 'File', value: data.summary?.file_path },
        { label: 'Line', value: data.summary?.line },
        { label: 'Secret type', value: data.summary?.secret_type },
        { label: 'Sample', value: data.summary?.secret_sample },
      ],
    });
  }

  if (typeLabel === 'iac') {
    detailSections.push({
      title: 'IaC resource',
      rows: [
        { label: 'Resource', value: data.summary?.resource },
        { label: 'Control', value: data.summary?.control_id },
        { label: 'Desired state', value: data.summary?.desired_state },
      ],
    });
  }

  if (typeLabel === 'git') {
    detailSections.push({
      title: 'Repository',
      rows: [
        { label: 'Repo', value: data.summary?.repo || data.target_ref },
        { label: 'Branch', value: data.summary?.branch },
        { label: 'Last commit', value: data.summary?.last_commit },
      ],
    });
  }

  if (typeLabel === 'host' || typeLabel === 'endpoint') {
    detailSections.push({
      title: 'Host info',
      rows: [
        { label: 'Asset', value: data.target_ref },
        { label: 'Kind', value: data.summary?.target_kind },
      ],
    });
  }

  const handleCreateScanTicket = async () => {
    if (!data?.fix_groups || data.fix_groups.length === 0) {
      toast.error('No fix groups available for ticketing.');
      return;
    }
    const targetFg = data.fix_groups.find((fg) => !fg.ticket_id) || data.fix_groups[0];
    setScanTicketState('saving');
    try {
      const resp = await apiClient.post(`/orchestrator/scans/${data.id}/tickets`, {
        fix_group_id: targetFg.id,
        title: targetFg.description || `Remediate ${typeLabel} scan`,
        description: targetFg.description,
        priority: targetFg.priority,
      });
      const ticketId = resp.data?.id || resp.data?.external_id || targetFg.ticket_id;
      const ticketStatus = resp.data?.status || targetFg.ticket_status || 'open';
      targetFg.ticket_id = ticketId;
      targetFg.ticket_status = ticketStatus;
      setScanTicketState('done');
      toast.success('Ticket created');
      mutate?.();
    } catch (err: any) {
      console.error('Ticket creation failed', err);
      const msg = err?.response?.data?.detail || err?.message || 'Ticket creation failed. Please retry.';
      toast.error(msg);
      setScanTicketState('idle');
    }
  };

  return (
    <div className="p-6 space-y-4">
      <Breadcrumbs />
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-main mb-1">Scan {data.id.slice(0, 8)}...</h1>
          <div className="flex items-center gap-2">
            <span className="text-xs px-2 py-1 rounded-full bg-cyan-500/20 text-cyan-100 border border-cyan-400/40 capitalize">
              {typeLabel}
            </span>
            {externallyExposed && (
              <span className="text-xs px-2 py-1 rounded-full bg-rose-500/20 text-rose-200 border border-rose-400/40">
                Externally facing
              </span>
            )}
          </div>
        </div>
        <Link href="/dashboard/scans" className="text-primary hover:underline text-sm">
          Back to scans
        </Link>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4 space-y-2">
          <div className="flex items-center gap-2">
            <span className={`px-2 py-1 rounded-full text-xs ${statusBadge}`}>{data.status}</span>
            <span className="text-sm text-text-muted">Status</span>
          </div>
          <div className="text-sm text-text-main">Target: {data.target_ref || '—'}</div>
          <div className="text-sm text-text-main capitalize">Type: {typeLabel}</div>
          <div className="text-sm text-text-muted">Created: {data.created_at ? new Date(data.created_at).toLocaleString() : '—'}</div>
          <div className="text-sm text-text-muted">Started: {data.started_at ? new Date(data.started_at).toLocaleString() : '—'}</div>
          <div className="text-sm text-text-muted">Finished: {data.finished_at ? new Date(data.finished_at).toLocaleString() : '—'}</div>
          <div className="text-sm text-text-main">
            Findings: {typeof data.summary?.findings === 'number' ? data.summary.findings : '—'}
          </div>
          <div className="text-sm">
            Artifact:{' '}
            {data.artifact_url || data.raw_artifact_url ? (
              <a
                href={data.artifact_url || data.raw_artifact_url}
                className="text-primary hover:underline"
                target="_blank"
                rel="noreferrer"
              >
                View
              </a>
            ) : (
              '—'
            )}
          </div>
        </div>

        <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4">
          <h2 className="text-lg font-semibold text-text-main mb-2">Summary</h2>
          {data.summary && Object.keys(data.summary).length > 0 ? (
            <div className="space-y-3 text-sm text-text-main">
              {data.summary?.severity && <div>Severity: {String(data.summary.severity).toUpperCase()}</div>}
              {data.summary?.description && <div className="text-text-muted">{data.summary.description}</div>}
              {externallyExposed && <div className="text-rose-200">Risk: Externally facing asset</div>}
              <div className="flex flex-wrap gap-2 text-xs text-text-main">
                {nistControls.map((c) => (
                  <a
                    key={c}
                    href={`https://csrc.nist.gov/search?query=${encodeURIComponent(c)}`}
                    target="_blank"
                    rel="noreferrer"
                    className="px-2 py-1 rounded-full border border-slate-700 bg-slate-800/70 hover:border-cyan-400 text-slate-200"
                  >
                    NIST {c}
                  </a>
                ))}
                {mitreTechniques.map((t) => (
                  <a
                    key={t}
                    href={`https://attack.mitre.org/techniques/${t}/`}
                    target="_blank"
                    rel="noreferrer"
                    className="px-2 py-1 rounded-full border border-slate-700 bg-slate-800/70 hover:border-cyan-400 text-slate-200"
                  >
                    MITRE {t}
                  </a>
                ))}
              </div>
            </div>
          ) : (
            <p className="text-sm text-text-muted">No summary available.</p>
          )}
        </div>
      </div>

      {detailSections.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {detailSections.map((section) => (
            <div key={section.title} className="rounded-lg border border-slate-800 bg-slate-900/60 p-4 space-y-2">
              <h3 className="text-base font-semibold text-text-main">{section.title}</h3>
              <div className="space-y-1 text-sm text-text-main">
                {section.rows
                  .filter((r) => r.value !== undefined && r.value !== null && r.value !== '')
                  .map((row) => (
                    <div key={`${section.title}-${row.label}`} className="flex justify-between gap-3">
                      <span className="text-text-muted">{row.label}</span>
                      <span className="font-medium break-all text-right">{String(row.value)}</span>
                    </div>
                  ))}
                {section.rows.filter((r) => r.value !== undefined && r.value !== null && r.value !== '').length === 0 && (
                  <div className="text-text-muted text-sm">No details available.</div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {cves.length > 0 && (
        <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4 space-y-2">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-text-main">CVEs</h2>
            <span className="text-xs text-slate-400">{cves.length} item(s)</span>
          </div>
          <div className="divide-y divide-slate-800">
            {cves.map((cve, idx) => (
              <div key={cve.id || idx} className="py-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-semibold text-primary">{cve.id}</span>
                  {typeof cve.cvss === 'number' && (
                    <span className="text-xs px-2 py-1 rounded-full bg-amber-500/20 text-amber-100 border border-amber-500/40">
                      CVSS {cve.cvss}
                    </span>
                  )}
                </div>
                {cve.description && <div className="text-xs text-text-muted mt-1">{cve.description}</div>}
                {cve.fix && <div className="text-xs text-emerald-200 mt-1">Fix: {cve.fix}</div>}
              </div>
            ))}
          </div>
        </div>
      )}

      {(remediation.summary || remediation.steps || remediation.validation) && (
        <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-text-main">Remediation</h2>
            <button
              className="text-primary text-sm hover:underline disabled:opacity-50"
              onClick={handleCreateScanTicket}
              disabled={scanTicketState !== 'idle'}
            >
              {scanTicketState === 'saving'
                ? 'Creating...'
                : scanTicketState === 'done'
                ? 'Ticket created'
                : 'Create ticket'}
            </button>
          </div>
          {remediation.summary && <div className="text-sm text-text-main">{remediation.summary}</div>}
          {Array.isArray(remediation.steps) && remediation.steps.length > 0 && (
            <div>
              <div className="text-xs font-semibold text-slate-200 mb-1">Steps</div>
              <ul className="list-disc list-inside text-xs text-text-muted space-y-0.5">
                {remediation.steps.map((s: string, idx: number) => (
                  <li key={idx}>{s}</li>
                ))}
              </ul>
            </div>
          )}
          {Array.isArray(remediation.validation) && remediation.validation.length > 0 && (
            <div>
              <div className="text-xs font-semibold text-slate-200 mb-1">Validation</div>
              <ul className="list-disc list-inside text-xs text-text-muted space-y-0.5">
                {remediation.validation.map((s: string, idx: number) => (
                  <li key={idx}>{s}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {data.fix_groups && data.fix_groups.length > 0 && (
        <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-text-main">Fix groups</h2>
            <span className="text-xs text-slate-400">{data.fix_groups.length} items</span>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            {data.fix_groups.map((fg) => (
              <div key={fg.id} className="border border-slate-800 rounded-lg p-3 bg-slate-950/40 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-semibold text-slate-100 capitalize">{fg.type}</span>
                  <span
                    className={`text-xs px-2 py-1 rounded-full ${
                      fg.status === 'closed'
                        ? 'bg-emerald-500/20 text-emerald-300'
                        : fg.status === 'pending_verify'
                        ? 'bg-amber-500/20 text-amber-200'
                        : 'bg-slate-700 text-slate-200'
                    }`}
                  >
                    {fg.status || 'open'}
                  </span>
                </div>
                <div className="text-sm text-slate-200">{fg.description || 'No description'}</div>
              <div className="text-xs text-slate-400 space-y-1">
                {fg.priority && <div>Priority: {fg.priority}</div>}
                {fg.sla_due && <div>SLA due: {new Date(fg.sla_due).toLocaleString()}</div>}
                {fg.fixed_in_target && <div>Fixed in: {fg.fixed_in_target}</div>}
                {fg.ticket_id && (
                    <div>
                      Ticket:{' '}
                      <Link href={`/dashboard/tickets/${fg.ticket_id}`} className="text-primary hover:underline">
                        {fg.ticket_id}
                      </Link>{' '}
                      ({fg.ticket_status || 'open'})
                    </div>
                  )}
                </div>
                {fg.ai_guidance && Object.keys(fg.ai_guidance).length > 0 && (
                  <div className="text-xs text-slate-200 bg-slate-900/80 border border-slate-800 rounded p-3 space-y-2">
                    <div className="font-semibold text-slate-100">AI guidance</div>
                    {fg.ai_guidance.summary && <div className="text-slate-200">{fg.ai_guidance.summary}</div>}
                    {Array.isArray(fg.ai_guidance.steps) && fg.ai_guidance.steps.length > 0 && (
                      <div>
                        <div className="text-slate-300 font-semibold mb-1">Steps</div>
                        <ul className="list-disc list-inside space-y-0.5 text-[11px] text-slate-300">
                          {fg.ai_guidance.steps.map((s, idx) => (
                            <li key={idx}>{s}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {Array.isArray(fg.ai_guidance.validation) && fg.ai_guidance.validation.length > 0 && (
                      <div>
                        <div className="text-slate-300 font-semibold mb-1">Validation</div>
                        <ul className="list-disc list-inside space-y-0.5 text-[11px] text-slate-300">
                          {fg.ai_guidance.validation.map((s, idx) => (
                            <li key={idx}>{s}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
                <button
                  className="text-xs text-primary hover:underline disabled:opacity-50"
                  disabled={!!fg.ticket_id || ticketState[fg.id] === 'saving' || ticketState[fg.id] === 'done'}
                  onClick={async () => {
                    setTicketState((prev) => ({ ...prev, [fg.id]: 'saving' }));
                    try {
                      const resp = await apiClient.post(`/orchestrator/scans/${data.id}/tickets`, {
                        fix_group_id: fg.id,
                        title: fg.description || `Remediate ${fg.type}`,
                        description: fg.description,
                        priority: fg.priority,
                      });
                      const ticketId = resp.data?.id || resp.data?.external_id || fg.ticket_id;
                      const ticketStatus = resp.data?.status || 'open';
                      fg.ticket_id = ticketId;
                      fg.ticket_status = ticketStatus;
                      setTicketState((prev) => ({ ...prev, [fg.id]: 'done' }));
                      toast.success('Ticket created');
                    } catch (err: any) {
                      console.error('Ticket creation failed', err);
                      const msg = err?.response?.data?.detail || err?.message || 'Ticket creation failed. Please retry.';
                      toast.error(msg);
                      setTicketState((prev) => ({ ...prev, [fg.id]: 'error' }));
                    }
                  }}
                >
                  {fg.ticket_id ? 'Ticket linked' : ticketState[fg.id] === 'done' ? 'Ticket created' : 'Create ticket'}
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
