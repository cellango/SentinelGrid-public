/**
 * New Playbook Page
 * Create a new playbook
 */

'use client';

import { useMemo, useState } from 'react';
import dynamic from 'next/dynamic';
import { useRouter } from 'next/navigation';
import { playbooksApi } from '@/lib/api/playbooks';
import { toast } from 'react-hot-toast';
import { Node, Edge } from 'reactflow';
import { useQuery } from '@tanstack/react-query';
import { catalogApi, CatalogPlaybook } from '@/lib/api/catalogs';

const PlaybookEditorCanvasWrapper = dynamic(
  () =>
    import('@/components/playbook-editor/PlaybookEditorCanvas').then(
      (mod) => mod.PlaybookEditorCanvasWrapper
    ),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-full min-h-[24rem] items-center justify-center rounded-xl border border-border-faint bg-surface-card">
        <p className="text-sm text-text-muted">Loading playbook editor…</p>
      </div>
    ),
  }
);

export default function NewPlaybookPage() {
  const router = useRouter();
  const [playbookName, setPlaybookName] = useState('');
  const [selectedCatalogId, setSelectedCatalogId] = useState('');
  const playbookNameFieldId = 'new-playbook-name';
  const catalogTemplateFieldId = 'new-playbook-template';
  const { data: catalogPlaybooks } = useQuery<CatalogPlaybook[]>({
    queryKey: ['catalog-playbooks'],
    queryFn: catalogApi.listPlaybooks,
  });

  const catalogOptions = useMemo(() => catalogPlaybooks || [], [catalogPlaybooks]);

  const handleSave = async (nodes: Node[], edges: Edge[]) => {
    if (!playbookName.trim()) {
      toast.error('Please enter a playbook name');
      return;
    }

    try {
      const playbook = await playbooksApi.create({
        name: playbookName,
        description: 'A new playbook',
        category: 'custom',
        version: '1.0.0',
        workflow: { nodes, edges },
        is_template: false,
        requires_approval: false,
        tags: [],
      });

      toast.success('Playbook created successfully');
      router.push(`/dashboard/playbooks/${playbook.id}/edit`);
    } catch (error: any) {
      toast.error(`Failed to create playbook: ${error.message}`);
    }
  };

  const handleCatalogSelect = (id: string) => {
    setSelectedCatalogId(id);
    const tpl = catalogOptions.find((p) => p.id === id);
    if (tpl) {
      setPlaybookName(tpl.name);
    }
  };

  return (
    <div className="h-screen flex flex-col">
      {/* Header with name input */}
      <div className="p-4 border-b border-surface-card-border dark:border-surface-card-border bg-surface-card">
        <div className="flex items-center gap-4">
          <label
            htmlFor={playbookNameFieldId}
            className="text-sm font-medium text-text-muted dark:text-text-muted"
          >
            Playbook Name:
          </label>
          <input
            id={playbookNameFieldId}
            type="text"
            value={playbookName}
            onChange={(e) => setPlaybookName(e.target.value)}
            placeholder="Enter playbook name..."
            className="flex-1 max-w-md px-4 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-bg-alt dark:border-border dark:text-white"
          />
          <select
            id={catalogTemplateFieldId}
            value={selectedCatalogId}
            onChange={(e) => handleCatalogSelect(e.target.value)}
            className="px-3 py-2 border border-border rounded-md bg-surface-card dark:bg-bg-alt dark:border-border dark:text-white"
          >
            <option value="">Catalog (select template)</option>
            {catalogOptions.map((p) => (
              <option key={p.id} value={p.id}>
                {p.id} — {p.name}
              </option>
            ))}
          </select>
          <label htmlFor={catalogTemplateFieldId} className="sr-only">
            Catalog playbook template
          </label>
        </div>
      </div>

      {/* Canvas */}
      <div className="flex-1">
        <PlaybookEditorCanvasWrapper onSave={handleSave} />
      </div>
    </div>
  );
}
