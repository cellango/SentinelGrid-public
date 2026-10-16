/**
 * Playbook Editor Page
 * Edit an existing playbook
 */

'use client';

import { useState, useEffect } from 'react';
import dynamic from 'next/dynamic';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import Breadcrumbs from '@/components/ui/Breadcrumbs';
import { playbooksApi, Playbook } from '@/lib/api/playbooks';
import { toast } from 'react-hot-toast';
import { Node, Edge } from 'reactflow';
import { getNistControlInfo } from '@/lib/framework/nist';

const PlaybookEditorCanvasWrapper = dynamic(
  () =>
    import('@/components/playbook-editor/PlaybookEditorCanvas').then(
      (mod) => mod.PlaybookEditorCanvasWrapper
    ),
  {
    ssr: false,
    loading: () => (
      <div className="flex min-h-[32rem] items-center justify-center rounded-xl border border-border-faint bg-surface-card">
        <p className="text-sm text-text-muted">Loading playbook editor…</p>
      </div>
    ),
  }
);

const STARTER_WORKFLOW = {
  nodes: [
    { id: 't1', type: 'trigger', position: { x: 0, y: 0 }, data: { label: 'Alert Trigger' } },
    { id: 'a1', type: 'action', position: { x: 220, y: 0 }, data: { label: 'Initial Response' } },
  ] as Node[],
  edges: [
    { id: 'e1', source: 't1', target: 'a1', type: 'smoothstep' },
  ] as Edge[],
};

export default function PlaybookEditPage() {
  const params = useParams();
  const playbookId = params.id as string;
  const mitreLink = (val?: string) => {
    if (!val) return undefined;
    const tech = val.match(/T\d{4}/i)?.[0];
    if (tech) return `https://attack.mitre.org/techniques/${tech.toUpperCase()}`;
    const tactic = val.match(/TA\d{4}/i)?.[0];
    if (tactic) return `https://attack.mitre.org/tactics/${tactic.toUpperCase()}`;
    return undefined;
  };
  const controlLink = (control?: string) =>
    control ? `/dashboard/compliance?control=${encodeURIComponent(control)}` : undefined;

  const { data: playbook, isLoading } = useQuery({
    queryKey: ['playbook', playbookId],
    queryFn: () => playbooksApi.get(playbookId),
    enabled: !!playbookId,
  });

  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [selectedNistControl, setSelectedNistControl] = useState<string | null>(null);

  useEffect(() => {
    if (playbook) {
      if (playbook.workflow?.nodes) {
        setNodes(playbook.workflow.nodes || []);
        setEdges(playbook.workflow.edges || []);
        return;
      }
      setNodes(STARTER_WORKFLOW.nodes);
      setEdges(STARTER_WORKFLOW.edges);
    }
  }, [playbook]);

  useEffect(() => {
    if (!selectedNistControl) return;
    const onKeyDown = (evt: KeyboardEvent) => {
      if (evt.key === 'Escape') setSelectedNistControl(null);
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [selectedNistControl]);

  const handleSave = async (nodes: Node[], edges: Edge[]) => {
    try {
      await playbooksApi.update(playbookId, {
        workflow: { nodes, edges },
      });
      toast.success('Playbook saved successfully');
    } catch (error: any) {
      toast.error(`Failed to save playbook: ${error.message}`);
    }
  };

  if (isLoading) {
    return (
      <div className="h-screen flex items-center justify-center">
        <div className="text-text-muted dark:text-text-muted">Loading playbook...</div>
      </div>
    );
  }

  if (!playbook) {
    return (
      <div className="h-screen flex items-center justify-center">
        <div className="text-red-600">Playbook not found</div>
      </div>
    );
  }

  const nistInfo = selectedNistControl ? getNistControlInfo(selectedNistControl) : null;

  return (
    <div className="space-y-4 p-4">
      <Breadcrumbs />
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="min-w-[260px]">
          <Link href="/dashboard/playbooks" className="text-sm text-primary hover:underline mb-2 inline-block">
            ← Back to Playbooks
          </Link>
          <h1 className="text-2xl font-semibold text-text-main">{playbook.name}</h1>
          {playbook.description ? (
            <p className="text-sm text-text-muted mt-1">{playbook.description}</p>
          ) : null}
        </div>
        <div className="flex items-center gap-2 text-xs text-text-muted">
          <span className="px-2 py-1 rounded border border-[rgba(15,23,42,0.95)] bg-slate-900/60">
            v{playbook.version || '1.0'}
          </span>
          {playbook.playbook_key ? (
            <span className="px-2 py-1 rounded border border-[rgba(15,23,42,0.95)] bg-slate-900/60 font-mono">
              {playbook.playbook_key}
            </span>
          ) : null}
        </div>
      </div>
      <div className="bg-[rgba(15,23,42,0.9)] border border-[rgba(15,23,42,0.95)] rounded-xl p-4">
        <div className="flex flex-wrap gap-3">
          <div>
            <div className="text-sm text-text-muted">MITRE Tactics/Techniques</div>
            <div className="flex flex-wrap gap-2 mt-1">
              {(playbook.mitre_tactics || []).map((t) => (
                <a
                  key={t}
                  href={mitreLink(t) || '#'}
                  target={mitreLink(t) ? '_blank' : undefined}
                  rel="noreferrer"
                  className="px-2 py-1 rounded bg-primary/10 border border-primary/30 text-primary text-xs hover:bg-primary/20"
                  title="View MITRE tactic"
                >
                  {t}
                </a>
              ))}
              {(playbook.mitre_techniques || []).map((tech) => (
                <a
                  key={tech}
                  href={mitreLink(tech) || '#'}
                  target={mitreLink(tech) ? '_blank' : undefined}
                  rel="noreferrer"
                  className="px-2 py-1 rounded bg-primary/10 border border-primary/30 text-primary text-xs hover:bg-primary/20"
                  title="View MITRE technique"
                >
                  {tech}
                </a>
              ))}
              {(!playbook.mitre_tactics?.length && !playbook.mitre_techniques?.length) && (
                <span className="text-text-muted text-xs">None mapped</span>
              )}
            </div>
          </div>
          <div>
            <div className="text-sm text-text-muted">NIST Controls</div>
            <div className="flex flex-wrap gap-2 mt-1">
              {(playbook.nist_controls || []).map((c) => (
                <button
                  key={c}
                  type="button"
                  className="px-2 py-1 rounded bg-green-500/10 border border-green-500/30 text-green-400 text-xs hover:bg-green-500/20"
                  title={`Explain NIST control ${c}`}
                  onClick={() => setSelectedNistControl(c)}
                >
                  {c}
                </button>
              ))}
              {(!playbook.nist_controls || playbook.nist_controls.length === 0) && (
                <span className="text-text-muted text-xs">None mapped</span>
              )}
            </div>
          </div>
          <div>
            <div className="text-sm text-text-muted">Tags</div>
            <div className="flex flex-wrap gap-2 mt-1">
              {(playbook.tags || []).map((tag) => (
                <span
                  key={tag}
                  className="px-2 py-1 rounded bg-slate-700 text-text-main text-xs"
                >
                  {tag}
                </span>
              ))}
              {(!playbook.tags || playbook.tags.length === 0) && (
                <span className="text-text-muted text-xs">None</span>
              )}
            </div>
          </div>
        </div>
      </div>

      {playbook.workflow_status && playbook.workflow_status !== 'stored' ? (
        <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4">
          <h2 className="text-sm font-semibold text-amber-100">Workflow visibility notice</h2>
          <p className="mt-2 text-sm text-amber-50/90">
            {playbook.workflow_message ||
              'This playbook is not exposing a stored workflow graph in the launch editor.'}
          </p>
          <p className="mt-2 text-xs text-amber-100/80">
            The canvas below is a local starter graph until you save a real workflow.
          </p>
        </div>
      ) : null}

      <PlaybookEditorCanvasWrapper
        playbookId={playbookId}
        initialNodes={nodes}
        initialEdges={edges}
        onSave={handleSave}
      />

      {nistInfo && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm px-4"
          onClick={() => setSelectedNistControl(null)}
          role="dialog"
          aria-modal="true"
        >
          <div
            className="w-full max-w-xl rounded-2xl border border-slate-800 bg-slate-900/95 shadow-2xl p-6"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-xl font-semibold text-text-main">
                  {nistInfo.id} — {nistInfo.title}
                </h2>
                <div className="mt-1 text-sm text-text-muted">
                  {nistInfo.framework}
                  {nistInfo.family ? ` • ${nistInfo.family}` : ''}
                </div>
              </div>
              <button
                type="button"
                onClick={() => setSelectedNistControl(null)}
                className="px-3 py-2 rounded-lg border border-slate-700 bg-slate-800/70 text-text-main hover:border-primary/60"
                aria-label="Close"
              >
                ✕
              </button>
            </div>

            <div className="mt-4 text-sm text-text-main leading-relaxed">
              {nistInfo.summary}
            </div>

            <div className="mt-6 flex items-center justify-end gap-2">
              <Link
                href={controlLink(nistInfo.id) || '#'}
                className="px-4 py-2 rounded-lg bg-primary text-bg text-sm font-medium hover:brightness-105"
              >
                View in Compliance
              </Link>
              <button
                type="button"
                onClick={() => setSelectedNistControl(null)}
                className="px-4 py-2 rounded-lg border border-slate-700 bg-slate-800/70 text-text-main text-sm hover:border-primary/60"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
