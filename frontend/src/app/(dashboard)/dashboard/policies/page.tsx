/**
 * Policies Page
 * List and manage tenant policies
 */

'use client';

import Link from 'next/link';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { policiesApi, Policy, PolicyTemplate } from '@/lib/api/policies';
import { useState } from 'react';
import { toast } from 'react-hot-toast';

export default function PoliciesPage() {
  const queryClient = useQueryClient();
  const [policyType, setPolicyType] = useState<string>('all');
  const { data: policies, isLoading } = useQuery<Policy[]>({
    queryKey: ['policies', policyType],
    queryFn: async () => policiesApi.list(policyType === 'all' ? undefined : policyType),
  });
  const { data: templates } = useQuery<PolicyTemplate[]>({
    queryKey: ['policy-templates'],
    queryFn: () => policiesApi.listTemplates(),
  });

  const cloneFromTemplate = useMutation({
    mutationFn: async ({ template_id, name, display_name }: { template_id: string; name: string; display_name: string }) =>
      policiesApi.createFromTemplate(template_id, name, display_name),
    onSuccess: () => {
      toast.success('Policy created from template');
      queryClient.invalidateQueries({ queryKey: ['policies'] });
    },
    onError: (err: any) => toast.error(err?.message || 'Create failed'),
  });

  const approveMutation = useMutation({
    mutationFn: async (id: string) => policiesApi.approve(id),
    onSuccess: () => {
      toast.success('Policy approved');
      queryClient.invalidateQueries({ queryKey: ['policies'] });
    },
    onError: (err: any) => toast.error(err?.message || 'Approve failed'),
  });

  const rejectMutation = useMutation({
    mutationFn: async (id: string) => policiesApi.reject(id),
    onSuccess: () => {
      toast.success('Policy rejected');
      queryClient.invalidateQueries({ queryKey: ['policies'] });
    },
    onError: (err: any) => toast.error(err?.message || 'Reject failed'),
  });

  const handleClone = (template: PolicyTemplate) => {
    const name = prompt('New policy name?', `${template.name}-copy`);
    const display = prompt('Display name?', template.display_name);
    if (!name || !display) return;
    cloneFromTemplate.mutate({ template_id: template.id, name, display_name: display });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-main">Authorization Policies</h1>
          <p className="mt-1 text-sm text-text-muted">
            Create and manage tenant policy records and open them in the visual builder
          </p>
        </div>
        <Link
          href="/dashboard/policies/builder"
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          Create Policy
        </Link>
      </div>

      {/* Templates */}
      <div className="bg-surface-card rounded-lg shadow-sm border border-surface-card-border p-4">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-lg font-semibold text-text-main">Templates</h2>
          <span className="text-sm text-text-muted">Clone to start quickly</span>
        </div>
        {templates && templates.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {templates.map((tpl) => (
              <div key={tpl.id} className="border rounded-lg p-3">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-sm font-semibold">{tpl.display_name}</div>
                    <div className="text-xs text-text-muted">{tpl.policy_type}</div>
                  </div>
                  <button
                    onClick={() => handleClone(tpl)}
                    className="px-3 py-1 text-xs bg-bg-alt rounded border hover:bg-surface-hover"
                  >
                    Clone
                  </button>
                </div>
                {tpl.description && (
                  <div className="text-xs text-text-muted mt-1">{tpl.description}</div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="text-sm text-text-muted">No templates available.</div>
        )}
      </div>

      {/* Policies List */}
      <div className="bg-surface-card rounded-lg shadow-sm border border-surface-card-border p-6 space-y-3">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <span className="text-sm text-text-muted">Filter:</span>
            <select
              value={policyType}
              onChange={(e) => setPolicyType(e.target.value)}
              className="px-3 py-1 border rounded text-sm"
            >
              <option value="all">All</option>
              <option value="access">Access</option>
              <option value="signon">Sign-on</option>
              <option value="approval">Approval</option>
              <option value="authorization">Authorization</option>
            </select>
          </div>
          <Link href="/dashboard/policies/builder" className="text-sm text-blue-600 hover:underline">
            Open Builder
          </Link>
        </div>
        {isLoading && <div className="text-sm text-text-muted">Loading...</div>}
        {!isLoading && policies && policies.length === 0 && (
          <div className="text-sm text-text-muted">No policies yet. Use a template above to start.</div>
        )}
        <div className="space-y-2">
          {policies?.map((p) => (
            <div key={p.id} className="flex flex-col md:flex-row md:items-center md:justify-between border rounded-lg p-3">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold">{p.display_name}</span>
                  {p.is_active ? (
                    <span className="px-2 py-0.5 text-xs rounded-full bg-green-100 text-green-700">Active</span>
                  ) : (
                    <span className="px-2 py-0.5 text-xs rounded-full bg-red-100 text-red-700">Inactive</span>
                  )}
                </div>
                <div className="text-xs text-text-muted">
                  {p.policy_type} • priority {p.priority ?? 100}
                </div>
                {p.description && (
                  <div className="text-xs text-text-muted mt-1">{p.description}</div>
                )}
              </div>
              <div className="flex gap-2 mt-2 md:mt-0">
                <Link
                  href={`/dashboard/policies/builder?policy_id=${p.id}`}
                  className="px-3 py-1 text-xs border border-border rounded hover:bg-surface-hover"
                >
                  Open in Builder
                </Link>
                <button
                  onClick={() => approveMutation.mutate(p.id)}
                  className="px-3 py-1 text-xs border border-green-500 text-green-600 rounded hover:bg-green-50"
                >
                  Approve
                </button>
                <button
                  onClick={() => rejectMutation.mutate(p.id)}
                  className="px-3 py-1 text-xs border border-red-500 text-red-600 rounded hover:bg-red-50"
                >
                  Reject
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
