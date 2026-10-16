'use client';

import { useEffect, useMemo, useState } from 'react';
import dynamic from 'next/dynamic';
import { useQuery } from '@tanstack/react-query';
import { toast } from 'react-hot-toast';

import Breadcrumbs from '@/components/ui/Breadcrumbs';
import { listPentestPlaybookTemplates } from '@/lib/api/pentestPlaybooks';
import {
  graphToRuntimePlaybook,
  validatePentestPlaybookGraph,
  type PentestEditorEdge,
  type PentestEditorNode,
  type PentestTemplateRecord,
} from '@/lib/pentest/playbookEditorSchema';

const PentestPlaybookEditorCanvasWrapper = dynamic(
  () =>
    import('@/components/pentest-editor/PentestPlaybookEditorCanvas').then(
      (mod) => mod.PentestPlaybookEditorCanvasWrapper
    ),
  {
    ssr: false,
    loading: () => (
      <div className="flex min-h-[32rem] items-center justify-center rounded-2xl border border-surface-card-border bg-surface-card">
        <p className="text-sm text-text-muted">Loading pentest playbook builder…</p>
      </div>
    ),
  }
);

function cloneTemplateGraph(template: PentestTemplateRecord) {
  return {
    nodes: template.graph.nodes.map((node) => ({
      ...node,
      position: { ...node.position },
      data: {
        ...node.data,
        checklist: [...(node.data.checklist || [])],
        tools: (node.data.tools || []).map((tool) => ({
          ...tool,
          params: tool.params ? { ...tool.params } : undefined,
        })),
        assetTypes: [...(node.data.assetTypes || [])],
      },
    })),
    edges: template.graph.edges.map((edge) => ({ ...edge })),
  };
}

export default function PentestPlaybookBuilderPage() {
  const { data: templates = [], isLoading } = useQuery({
    queryKey: ['pentest-playbook-templates'],
    queryFn: listPentestPlaybookTemplates,
  });
  const [selectedTemplateSlug, setSelectedTemplateSlug] = useState<string>('');
  const [nodes, setNodes] = useState<PentestEditorNode[]>([]);
  const [edges, setEdges] = useState<PentestEditorEdge[]>([]);

  useEffect(() => {
    if (!templates.length) {
      return;
    }
    setSelectedTemplateSlug((current) => current || templates[0].slug);
  }, [templates]);

  const selectedTemplate = useMemo(
    () => templates.find((template) => template.slug === selectedTemplateSlug) || null,
    [selectedTemplateSlug, templates]
  );

  useEffect(() => {
    if (!selectedTemplate) {
      return;
    }
    const cloned = cloneTemplateGraph(selectedTemplate);
    setNodes(cloned.nodes);
    setEdges(cloned.edges);
  }, [selectedTemplate]);

  const validation = useMemo(() => validatePentestPlaybookGraph(nodes, edges), [edges, nodes]);

  const runtimePreview = useMemo(() => {
    if (!selectedTemplate) {
      return null;
    }
    try {
      return graphToRuntimePlaybook(nodes, edges, {
        name: selectedTemplate.name,
        engagementType: selectedTemplate.engagementType,
        description: selectedTemplate.description,
      });
    } catch {
      return null;
    }
  }, [edges, nodes, selectedTemplate]);

  const copyPreview = async () => {
    if (!runtimePreview) {
      toast.error('Fix validation errors before exporting the runtime playbook.');
      return;
    }
    await navigator.clipboard.writeText(JSON.stringify(runtimePreview, null, 2));
    toast.success('Runtime playbook JSON copied');
  };

  const resetTemplate = () => {
    if (!selectedTemplate) {
      return;
    }
    const cloned = cloneTemplateGraph(selectedTemplate);
    setNodes(cloned.nodes);
    setEdges(cloned.edges);
    toast.success(`Reset to ${selectedTemplate.name}`);
  };

  return (
    <div className="space-y-6 p-6">
      <div className="mx-auto max-w-7xl space-y-6">
        <Breadcrumbs />

        <section className="rounded-2xl border border-surface-card-border bg-surface-card p-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="max-w-3xl">
              <div className="inline-flex rounded-full border border-amber-500/30 bg-amber-500/10 px-3 py-1 text-xs font-medium text-amber-200">
                Internal builder, not a launch-facing self-serve surface
              </div>
              <h1 className="mt-4 text-3xl font-semibold text-text-main">
                Pentest Playbook Builder
              </h1>
              <p className="mt-3 text-sm leading-6 text-text-muted">
                This workbench reuses the drag-and-drop canvas pattern but keeps pentest playbooks
                on a separate schema and UX layer. Approval, credential, escalation, and report-QA
                controls are first-class nodes, and the validator blocks unsafe graphs before a
                runtime playbook can be exported.
              </p>
            </div>
            <div className="grid min-w-[240px] gap-2 rounded-xl border border-surface-card-border bg-bg-alt p-4 text-sm">
              <div className="flex items-center justify-between">
                <span className="text-text-muted">Templates loaded</span>
                <span className="font-medium text-text-main">{templates.length}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-text-muted">Validation status</span>
                <span className={validation.valid ? 'text-green-400' : 'text-red-400'}>
                  {validation.valid ? 'Valid' : 'Blocked'}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-text-muted">Runtime export</span>
                <span className={runtimePreview ? 'text-green-400' : 'text-amber-300'}>
                  {runtimePreview ? 'Ready' : 'Fix graph'}
                </span>
              </div>
            </div>
          </div>
        </section>

        <section className="rounded-2xl border border-surface-card-border bg-surface-card p-6">
          <div className="mb-4">
            <h2 className="text-lg font-semibold text-text-main">Starter Templates</h2>
            <p className="mt-1 text-sm text-text-muted">
              Templates are derived from the shipped typed pentest YAML playbooks and wrapped with
              scope verification, approval, credential, QA, and report-release controls.
            </p>
          </div>

          {isLoading ? (
            <div className="text-sm text-text-muted">Loading pentest templates…</div>
          ) : (
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {templates.map((template: PentestTemplateRecord) => (
                <button
                  key={template.slug}
                  type="button"
                  onClick={() => setSelectedTemplateSlug(template.slug)}
                  className={`rounded-xl border p-4 text-left transition ${
                    selectedTemplateSlug === template.slug
                      ? 'border-blue-500 bg-blue-500/10'
                      : 'border-surface-card-border bg-bg-alt hover:border-blue-500/40'
                  }`}
                >
                  <div className="text-sm font-semibold text-text-main">{template.name}</div>
                  <div className="mt-2 text-xs uppercase tracking-[0.18em] text-text-muted">
                    {template.engagementType.replace(/_/g, ' ')}
                  </div>
                  <p className="mt-3 text-sm text-text-muted line-clamp-4">{template.description}</p>
                </button>
              ))}
            </div>
          )}
        </section>

        {selectedTemplate ? (
          <>
            <PentestPlaybookEditorCanvasWrapper
              initialNodes={nodes}
              initialEdges={edges}
              onGraphChange={(nextNodes, nextEdges) => {
                setNodes(nextNodes);
                setEdges(nextEdges);
              }}
              onReset={resetTemplate}
            />

            <div className="grid gap-6 lg:grid-cols-[1.1fr_1fr]">
              <section className="rounded-2xl border border-surface-card-border bg-surface-card p-5">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <h2 className="text-lg font-semibold text-text-main">Validation</h2>
                    <p className="mt-1 text-sm text-text-muted">
                      The editor blocks unsafe control flow before export.
                    </p>
                  </div>
                  <div
                    className={`rounded-full px-3 py-1 text-xs font-medium ${
                      validation.valid
                        ? 'bg-green-500/15 text-green-300'
                        : 'bg-red-500/15 text-red-300'
                    }`}
                  >
                    {validation.valid ? 'Ready to export' : 'Graph blocked'}
                  </div>
                </div>

                <div className="mt-5 grid gap-4 md:grid-cols-2">
                  <div className="rounded-xl border border-surface-card-border bg-bg-alt p-4">
                    <div className="text-sm font-medium text-text-main">Errors</div>
                    <ul className="mt-3 space-y-2 text-sm text-red-300">
                      {validation.errors.length ? (
                        validation.errors.map((error) => <li key={error}>{error}</li>)
                      ) : (
                        <li className="text-green-300">No blocking errors.</li>
                      )}
                    </ul>
                  </div>
                  <div className="rounded-xl border border-surface-card-border bg-bg-alt p-4">
                    <div className="text-sm font-medium text-text-main">Warnings</div>
                    <ul className="mt-3 space-y-2 text-sm text-amber-200">
                      {validation.warnings.length ? (
                        validation.warnings.map((warning) => <li key={warning}>{warning}</li>)
                      ) : (
                        <li className="text-text-muted">No warnings.</li>
                      )}
                    </ul>
                  </div>
                </div>
              </section>

              <section className="rounded-2xl border border-surface-card-border bg-surface-card p-5">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <h2 className="text-lg font-semibold text-text-main">Runtime Export Preview</h2>
                    <p className="mt-1 text-sm text-text-muted">
                      Exported phases remain pentest-specific and separate from SOC workflow JSON.
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={copyPreview}
                    className="rounded-md border border-border px-3 py-2 text-sm text-text-muted hover:bg-surface-hover"
                  >
                    Copy JSON
                  </button>
                </div>

                <pre className="mt-4 max-h-[420px] overflow-auto rounded-xl border border-surface-card-border bg-bg-alt p-4 text-xs text-text-main">
                  {runtimePreview
                    ? JSON.stringify(runtimePreview, null, 2)
                    : 'Runtime export unavailable until validation errors are resolved.'}
                </pre>
              </section>
            </div>
          </>
        ) : null}
      </div>
    </div>
  );
}
