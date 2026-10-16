/**
 * IAM Policies Page
 * Global policy editor with tabs for different policy types
 */

'use client';

import React, { useState, type ComponentType, type SVGProps } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { PlusIcon, Cog6ToothIcon, ShieldCheckIcon, KeyIcon, ClipboardDocumentCheckIcon, EyeIcon } from '@heroicons/react/24/outline';
import { getPolicies, getPolicyTemplates, createPolicyFromTemplate, deletePolicy, listPolicyBundles, clonePolicyBundle, updatePolicy } from '@/lib/api/iam-portal';
import type { Policy, PolicyTemplate, PolicyBundle, PolicyCreate } from '@/lib/api/iam-portal';
import PolicyEditor from '@/components/iam/PolicyEditor';

type PolicyType = 'signon' | 'access' | 'approval' | 'sod' | 'authorization';

const TAB_CONFIG: { id: PolicyType; label: string; icon: ComponentType<SVGProps<SVGSVGElement>> }[] = [
  { id: 'signon', label: 'Sign-on Policies', icon: KeyIcon },
  { id: 'access', label: 'Access Policies', icon: ShieldCheckIcon },
  { id: 'approval', label: 'Approval & Workflow', icon: ClipboardDocumentCheckIcon },
  { id: 'sod', label: 'SoD & Risk', icon: Cog6ToothIcon },
  { id: 'authorization', label: 'Authorization (Visual)', icon: ShieldCheckIcon },
];

const TAB_IDS: PolicyType[] = TAB_CONFIG.map((t) => t.id);

function getInitialTab(): PolicyType {
  if (typeof window === 'undefined') return 'signon';
  const tabParam = new URLSearchParams(window.location.search).get('tab') as PolicyType | null;
  return tabParam && TAB_IDS.includes(tabParam) ? tabParam : 'signon';
}

export default function PoliciesPage() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<PolicyType>(getInitialTab());
  const [selectedPolicy, setSelectedPolicy] = useState<Policy | null>(null);
  const [showTemplateModal, setShowTemplateModal] = useState(false);
  const [cloningId, setCloningId] = useState<string | null>(null);
  const [cloneModalBundle, setCloneModalBundle] = useState<PolicyBundle | null>(null);
  const [cloneName, setCloneName] = useState('');
  const [cloneError, setCloneError] = useState<string | null>(null);
  const [editorError, setEditorError] = useState<string | null>(null);
  
  const queryClient = useQueryClient();
  const isAuthorizationTab = activeTab === 'authorization';
  // Fetch policies
  const { data: policies = [], isLoading } = useQuery({
    queryKey: ['iam-policies', activeTab],
    queryFn: () => getPolicies(activeTab),
  });

  // Fetch templates
  const { data: templates = [], isFetching: templatesLoading } = useQuery({
    queryKey: ['iam-policy-templates', activeTab],
    queryFn: () => getPolicyTemplates(activeTab),
    enabled: activeTab !== 'authorization',
  });

  const createFromTemplate = useMutation({
    mutationFn: async (tpl: PolicyTemplate) => {
      const base = (tpl.name || tpl.display_name).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
      const name = `${base || 'policy'}-${Date.now()}`;
      const display = `${tpl.display_name} (${new Date().toLocaleDateString()})`;
      return createPolicyFromTemplate(tpl.id, name, display);
    },
    onSuccess: (policy) => {
      setShowTemplateModal(false);
      setActiveTab(policy.policy_type as PolicyType);
      setSelectedPolicy(policy);
      queryClient.invalidateQueries({ queryKey: ['iam-policies'] });
    },
    onError: (err: any) => {
      alert(err?.message || 'Failed to create policy from template');
    },
  });
  
  // Delete policy mutation
  const deletePolicyMutation = useMutation({
    mutationFn: deletePolicy,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['iam-policies'] });
    },
  });

  const savePolicyMutation = useMutation({
    mutationFn: (policy: Policy) => {
      const payload: Partial<PolicyCreate> = {
        display_name: policy.display_name,
        description: policy.description,
        policy_data: policy.policy_data,
        is_active: policy.is_active,
        priority: policy.priority,
      };
      return updatePolicy(policy.id, payload);
    },
    onSuccess: () => {
      setEditorError(null);
      setSelectedPolicy(null);
      queryClient.invalidateQueries({ queryKey: ['iam-policies'] });
      queryClient.invalidateQueries({ queryKey: ['policy-bundles'] });
    },
    onError: (err: any) => {
      console.error('Save failed', err);
      setEditorError(err?.message || 'Failed to save policy');
    },
  });
  
  const { data: bundles = [] } = useQuery<PolicyBundle[]>({
    queryKey: ['policy-bundles'],
    queryFn: () => listPolicyBundles(),
  });
  const seedsForTab = bundles.filter((b) => b.policy_type === activeTab);
  const globalPolicies = isAuthorizationTab ? seedsForTab : [];

  const cloneBundle = useMutation({
    mutationFn: async (payload?: { bundleId: string; name?: string }) => {
      if (!payload) {
        throw new Error('Missing clone payload');
      }
      const { bundleId, name } = payload;
      setCloningId(bundleId);
      setCloneError(null);
      return clonePolicyBundle(bundleId, name ? { name } : undefined);
    },
    onSuccess: () => {
      setCloneModalBundle(null);
      setCloneName('');
      queryClient.invalidateQueries({ queryKey: ['iam-policies'] });
      queryClient.invalidateQueries({ queryKey: ['policy-bundles'] });
    },
    onError: (err: any) => {
      console.error('Clone failed', err);
      setCloneError(err?.message || 'Failed to clone policy bundle');
    },
    onSettled: () => setCloningId(null),
  });

  const openCloneModal = (bundle: PolicyBundle) => {
    setCloneModalBundle(bundle);
    setCloneError(null);
    const today = new Date().toISOString().slice(0, 10);
    const suffix = Math.random().toString(36).slice(2, 6);
    setCloneName(`${bundle.display_name} (${today})-${suffix}`);
  };

  const handleConfirmClone = async () => {
    if (!cloneModalBundle) return;
    if (!cloneName.trim()) {
      setCloneError('Please enter a name.');
      return;
    }
    try {
      await cloneBundle.mutateAsync({
        bundleId: cloneModalBundle.id,
        name: cloneName.trim(),
      });
    } catch (err: any) {
      console.error('Clone failed', err);
      setCloneError(err?.message || 'Failed to clone policy bundle');
    }
  };
  
  return (
    <div className="p-6 max-w-7xl mx-auto">
      {cloneModalBundle && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-md rounded-lg bg-surface-card p-6 shadow-xl">
            <h3 className="mb-1 text-lg font-semibold text-text-main">Clone policy</h3>
            <p className="mb-4 text-sm text-text-muted">
              Source: <span className="font-medium">{cloneModalBundle.display_name}</span>
            </p>
            <label className="mb-1 block text-sm font-medium text-text-muted" htmlFor="clone-name">
              New policy name
            </label>
            <input
              id="clone-name"
              data-testid="clone-policy-name"
              className="w-full rounded border border-border px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              value={cloneName}
              onChange={(e) => setCloneName(e.target.value)}
              placeholder="Enter a unique name"
            />
            <p className="mt-1 text-xs text-text-muted">Names must be unique per tenant to prevent duplicate clones.</p>
            {cloneError && <p className="mt-2 text-sm text-red-600">{cloneError}</p>}
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                className="rounded border border-border px-4 py-2 text-sm text-text-muted hover:bg-bg-alt"
                onClick={() => {
                  setCloneModalBundle(null);
                  setCloneError(null);
                  setCloneName('');
                }}
              >
                Cancel
              </button>
              <button
                type="button"
                data-testid="clone-policy-confirm"
                disabled={!cloneName.trim() || cloningId === cloneModalBundle.id}
                onClick={handleConfirmClone}
                className={`rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors ${
                  !cloneName.trim() || cloningId === cloneModalBundle.id ? 'opacity-60' : 'hover:bg-blue-700'
                }`}
              >
                {cloningId === cloneModalBundle.id ? 'Cloning...' : 'Clone to my tenant'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-main">Policies</h1>
          <p className="text-sm text-text-muted mt-1">Define who can do what, when, and how</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setShowTemplateModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            <PlusIcon className="w-5 h-5" />
            Use Template
          </button>
          <button
            onClick={() => {
              // Take the user to the full drag-and-drop builder
              router.push('/dashboard/policies/builder');
            }}
            className="flex items-center gap-2 px-4 py-2 bg-border text-white rounded-lg hover:bg-surface-hover transition-colors"
          >
            <PlusIcon className="w-5 h-5" />
            New Policy
          </button>
        </div>
      </div>
      
      {/* Tabs */}
      <div className="mb-6 border-b border-surface-card-border">
        <nav className="flex gap-6">
          {TAB_CONFIG.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => {
                  setEditorError(null);
                  setActiveTab(tab.id);
                  setSelectedPolicy(null);
                  router.replace(`/dashboard/iam/policies?tab=${tab.id}`, { scroll: false });
                }}
                className={`flex items-center gap-2 pb-3 px-1 border-b-2 font-medium text-sm transition-colors ${
                  activeTab === tab.id
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-text-muted hover:text-text-muted'
                }`}
              >
                <Icon className="w-5 h-5" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </nav>
      </div>
      
      {/* Content */}
      {activeTab === 'authorization' ? (
        <div className="bg-surface-card border border-surface-card-border rounded-lg p-6">
          <h2 className="text-lg font-semibold text-text-main mb-2">Authorization Policy Builder</h2>
          <p className="text-sm text-text-muted mb-4">
            Use the drag-and-drop canvas to design authorization policies visually. Changes here operate on the same policy objects as the list view.
          </p>
          <div className="mt-2">
            <h3 className="text-md font-semibold text-text-main mb-2">Global policies (sg_admin)</h3>
            {globalPolicies.length === 0 ? (
              <p className="text-sm text-text-muted bg-surface-hover border border-surface-card-border rounded-lg p-4">
                No global authorization policies available.
              </p>
            ) : (
              <div className="grid gap-3">
                {globalPolicies.map((policy) => (
                  <PolicyCard
                    key={policy.id}
                    policy={policy}
                    dataTestId="policy-card-authorization-global"
                    readOnly
                    showMeta={false}
                    extraActions={
                      <div className="flex items-center gap-2">
                        <a
                          href={`/dashboard/policies/builder?seed_id=${policy.id}&read_only=1`}
                          className="px-2 py-1 text-xs rounded border border-border text-text-muted hover:bg-surface-hover"
                          data-testid="policy-seed-preview"
                        >
                          Preview
                        </a>
                        <button
                          onClick={() => openCloneModal(policy)}
                          disabled={cloningId === policy.id}
                          className="px-2 py-1 text-xs rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-60"
                          data-testid="policy-seed-clone"
                        >
                          {cloningId === policy.id ? 'Cloning...' : 'Clone'}
                        </button>
                      </div>
                    }
                  />
                ))}
              </div>
            )}
          </div>

          <div className="mt-6">
            <h3 className="text-md font-semibold text-text-main mb-2">Tenant policies</h3>
            <p className="text-xs text-text-muted mb-3">
              These authorization policies are persisted to your tenant. Use the visual builder for full rule editing and graph design.
            </p>
            {isLoading ? (
              <div className="text-center py-6">
                <div className="inline-block animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
              </div>
            ) : policies.length === 0 ? (
              <p className="text-sm text-text-muted bg-surface-hover border border-surface-card-border rounded-lg p-4">
                No authorization policies found for this tenant.
              </p>
            ) : (
              <div className="grid gap-3">
                {policies.map((policy) => (
                  <PolicyCard
                    key={policy.id}
                    policy={policy}
                    dataTestId="policy-card-authorization"
                    onEdit={() => router.push(`/dashboard/policies/builder?policy_id=${policy.id}`)}
                    onDelete={() => {
                      if (confirm(`Delete policy "${policy.display_name}"?`)) {
                        deletePolicyMutation.mutate(policy.id);
                      }
                    }}
                    extraActions={
                      <a
                        href={`/dashboard/policies/builder?policy_id=${policy.id}`}
                        className="px-3 py-1 text-xs font-medium rounded bg-blue-600 text-white hover:bg-blue-700 transition-colors inline-flex items-center gap-1"
                        data-testid="policy-open-visual"
                      >
                        <EyeIcon className="w-4 h-4" /> Open in Visual Editor
                      </a>
                    }
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      ) : selectedPolicy ? (
        <PolicyEditor
          policy={selectedPolicy}
          policyType={activeTab}
          onClose={() => {
            setEditorError(null);
            setSelectedPolicy(null);
          }}
          onOpenVisualBuilder={(policy) => {
            if (policy?.id) {
              router.push(`/dashboard/policies/builder?policy_id=${policy.id}`);
              return;
            }
            router.push('/dashboard/policies/builder');
          }}
          savePending={savePolicyMutation.isPending}
          saveError={editorError}
          onSave={(updatedPolicy) => {
            setEditorError(null);
            savePolicyMutation.mutate(updatedPolicy);
          }}
        />
      ) : (
        <div>
          <div className="mb-4 rounded-lg border border-surface-card-border bg-surface-hover p-4" data-testid="policy-seed-list">
            <div className="flex items-center justify-between mb-2">
              <div>
                <h3 className="text-md font-semibold text-text-main">Global policies (sg_admin)</h3>
                <p className="text-xs text-text-muted mt-1">Clone a starter policy into your tenant.</p>
              </div>
            </div>
            {seedsForTab.length === 0 ? (
              <p className="text-xs text-text-muted">No seed policies available for this type.</p>
            ) : (
              <div className="grid gap-3">
                {seedsForTab.map((b) => (
                  <div key={b.id} className="flex items-center justify-between gap-2 rounded border border-surface-card-border bg-surface-card px-3 py-2" data-testid="policy-seed-card">
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-text-main truncate">{b.display_name}</p>
                      <p className="text-xs text-text-muted truncate">{b.description || b.policy_type}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <a
                        href={`/dashboard/policies/builder?seed_id=${b.id}&read_only=1`}
                        className="px-3 py-1 text-xs rounded border border-border text-text-muted hover:bg-surface-hover"
                        data-testid="policy-seed-preview"
                      >
                        Preview
                      </a>
                      <button
                        onClick={() => openCloneModal(b)}
                        disabled={cloningId === b.id}
                        className="px-3 py-1 text-xs rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-60"
                        data-testid="policy-seed-clone"
                      >
                        {cloningId === b.id ? 'Cloning...' : 'Clone to my tenant'}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <h3 className="text-md font-semibold text-text-main mb-2">Tenant policies</h3>
          <p className="text-xs text-text-muted mb-3">
            Policies shown here are live tenant records. Inline editing saves metadata and current JSON; advanced rule authoring belongs in the visual builder.
          </p>
          {isLoading ? (
            <div className="text-center py-12">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              <p className="mt-2 text-text-muted">Loading policies...</p>
            </div>
          ) : policies.length === 0 ? (
            <div className="text-center py-12 bg-surface-hover rounded-lg border border-surface-card-border">
              <Cog6ToothIcon className="w-12 h-12 text-text-muted mx-auto mb-4" />
              <p className="text-text-muted mb-4">No {activeTab} policies configured</p>
              <button
                onClick={() => setShowTemplateModal(true)}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                Start with a Template
              </button>
            </div>
          ) : (
            <div className="grid gap-4">
              {policies.map((policy) => (
                <PolicyCard
                  key={policy.id}
                  policy={policy}
                  dataTestId="policy-card"
                  onEdit={() => {
                    setEditorError(null);
                    setSelectedPolicy(policy);
                  }}
                  onDelete={() => {
                    if (confirm(`Delete policy "${policy.display_name}"?`)) {
                      deletePolicyMutation.mutate(policy.id);
                    }
                  }}
                  extraActions={
                    <a
                      href={`/dashboard/policies/builder?policy_id=${policy.id}`}
                      className="px-3 py-1 text-xs font-medium rounded bg-blue-600 text-white hover:bg-blue-700 transition-colors inline-flex items-center gap-1"
                      data-testid="policy-open-visual"
                    >
                      <EyeIcon className="w-4 h-4" /> Open in Visual Editor
                    </a>
                  }
                />
              ))}
            </div>
          )}
        </div>
      )}
      
      {/* Template Modal */}
      {showTemplateModal && (
        <TemplateModal
          templates={templates}
          policyType={activeTab}
          onClose={() => setShowTemplateModal(false)}
          onSelect={(template) => {
            createFromTemplate.mutate(template);
          }}
          loading={templatesLoading || createFromTemplate.status === 'pending'}
        />
      )}
    </div>
  );
}

type PolicyCardProps = {
  policy: Policy;
  onEdit?: () => void;
  onDelete?: () => void;
  dataTestId?: string;
  extraActions?: React.ReactNode;
  readOnly?: boolean;
  showMeta?: boolean;
};

function PolicyCard({ policy, onEdit, onDelete, dataTestId, extraActions, readOnly = false, showMeta = true }: PolicyCardProps) {
  const primaryBtn =
    'px-3 py-1 text-xs font-medium rounded bg-blue-600 text-white hover:bg-blue-700 transition-colors';
  const dangerBtn =
    'px-3 py-1 text-xs font-medium rounded bg-red-600 text-white hover:bg-red-700 transition-colors';

  return (
    <div
      className="bg-surface-card border border-surface-card-border rounded-lg p-6 hover:shadow-md transition-shadow"
      data-testid={dataTestId}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <h3 className="text-lg font-semibold text-text-main">{policy.display_name}</h3>
            {policy.is_active ? (
              <span className="px-2 py-0.5 bg-green-100 text-green-800 text-xs rounded">
                Active
              </span>
            ) : (
              <span className="px-2 py-0.5 bg-bg-alt text-text-main text-xs rounded">
                Inactive
              </span>
            )}
            <span className="px-2 py-0.5 bg-blue-100 text-blue-800 text-xs rounded">
              Priority: {policy.priority}
            </span>
          </div>
          {policy.description && (
            <p className="text-sm text-text-muted mb-3">{policy.description}</p>
          )}
          {showMeta && (
            <div className="flex items-center gap-4 text-xs text-text-muted">
              <span>Scope: {policy.scope}</span>
              <span>Rules: {policy.policy_data?.rules?.length || 0}</span>
            </div>
          )}
        </div>
        <div className="flex gap-2">
          {!readOnly && onEdit && (
            <button
              onClick={onEdit}
              className={primaryBtn}
            >
              Edit
            </button>
          )}
          {!readOnly && onDelete && (
            <button
              onClick={onDelete}
              className={dangerBtn}
            >
              Delete
            </button>
          )}
          {extraActions && <div className="flex items-center">{extraActions}</div>}
        </div>
      </div>
    </div>
  );
}

function TemplateModal({
  templates,
  policyType,
  onClose,
  onSelect,
  loading = false,
}: {
  templates: PolicyTemplate[];
  policyType: PolicyType;
  onClose: () => void;
  onSelect: (template: PolicyTemplate) => void;
  loading?: boolean;
}) {
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-surface-card rounded-lg p-6 max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <h2 className="text-xl font-bold text-text-main mb-4">Choose a Template</h2>
        <div className="grid gap-3">
          {loading ? (
            <p className="text-text-muted text-center py-8">Loading templates...</p>
          ) : templates.length === 0 ? (
            <p className="text-text-muted text-center py-8">No templates available</p>
          ) : (
            templates.map((template) => (
              <button
                key={template.id}
                onClick={() => onSelect(template)}
                className="text-left p-4 border border-surface-card-border rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-colors"
              >
                <h3 className="font-semibold text-text-main">{template.display_name}</h3>
                {template.description && (
                  <p className="text-sm text-text-muted mt-1">{template.description}</p>
                )}
                {template.category && (
                  <span className="inline-block mt-2 px-2 py-0.5 bg-bg-alt text-text-muted text-xs rounded">
                    {template.category}
                  </span>
                )}
              </button>
            ))
          )}
        </div>
        <div className="mt-6 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 border border-border text-text-muted rounded-lg hover:bg-surface-hover transition-colors"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
