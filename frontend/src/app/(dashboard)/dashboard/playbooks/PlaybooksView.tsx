/**
 * Shared Playbooks view component for SOAR playbooks list
 */

'use client';

import { useState, useEffect, useRef, useMemo } from 'react';
import Link from 'next/link';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { playbooksApi, type PlaybookExecutionRecord } from '@/lib/api/playbooks';
import { toast } from 'react-hot-toast';
import { useSearchParams, useRouter } from 'next/navigation';
import { useTenant } from '@/lib/hooks/useTenant';
import { useAuth } from '@/lib/providers/AuthProvider';
import { getSourceHealth, type SourceHealth } from '@/lib/api/siem';
import HealthBadge from '@/components/ui/HealthBadge';
import ResponsePackLibrarySection from '@/components/playbooks/ResponsePackLibrarySection';
import { getResponsePackById, getResponsePackPlaybooks } from '@/lib/playbooks/responsePacks';

export interface Playbook {
  id: string;
  name: string;
  description?: string;
  category?: string;
  category_filter?: any;
  version: string;
  is_template: boolean;
  requires_approval: boolean;
  is_enabled?: boolean;
  tags?: string[];
  updated_at: string;
  incident_type?: string;
  owner?: string;
  triggers?: string[];
  phases?: any;
  playbook_key?: string;
}

export function PlaybooksView() {
  const { data: playbooks, isLoading, error } = useQuery({
    queryKey: ['playbooks'],
    queryFn: () => playbooksApi.list(),
  });
  const { tenant } = useTenant();
  const { user } = useAuth();
  const queryClient = useQueryClient();

  const searchParams = useSearchParams();
  const router = useRouter();
  const navigatedByParam = useRef(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategories, setSelectedCategories] = useState<string[]>(['all']);
  const [selectedPackId, setSelectedPackId] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [approvalsMode, setApprovalsMode] = useState(false);
  const [actionBusyId, setActionBusyId] = useState<string | null>(null);
  const categories = useMemo(() => {
    const deriveCategory = (pb: Playbook) => {
      const raw =
        (pb.category ||
          (Array.isArray(pb.category_filter) ? pb.category_filter[0] : null) ||
          (pb.category_filter && pb.category_filter.categories ? pb.category_filter.categories[0] : null) ||
          pb.owner ||
          pb.incident_type ||
          '').trim().toLowerCase();
      if (!raw || raw === 'custom') return null;
      if (raw.includes('identity')) return 'identity';
      if (raw.includes('endpoint') || raw.includes('edr')) return 'endpoint';
      if (raw.includes('email')) return 'email';
      if (raw.includes('cloud')) return 'cloud';
      if (raw.includes('network')) return 'network';
      if (raw.includes('ai')) return 'ai';
      return raw.replace(/[^a-z0-9_-]+/g, '_');
    };
    const derived = (playbooks || [])
      .map((pb) => deriveCategory(pb))
      .filter((c): c is string => !!c);
    return ['all', ...Array.from(new Set(derived))];
  }, [playbooks]);

  const makeKey = (name: string) =>
    `${name}`.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '') + `-${Date.now().toString(36)}`;

  const cloneMutation = useMutation({
    mutationFn: async (id: string) => {
      const name = prompt('New playbook name?');
      if (!name) throw new Error('Name required');
      return playbooksApi.copy(id, { new_name: name, new_key: makeKey(name) });
    },
    onMutate: (id) => setActionBusyId(id),
    onSuccess: () => {
      toast.success('Playbook cloned to tenant');
      queryClient.invalidateQueries({ queryKey: ['playbooks'] });
      setActionBusyId(null);
    },
    onError: (err: any) => {
      toast.error(err?.message || 'Clone failed');
      setActionBusyId(null);
    }
  });

  const approveMutation = useMutation({
    mutationFn: async (id: string) => playbooksApi.approve(id),
    onMutate: (id) => setActionBusyId(id),
    onSuccess: () => {
      toast.success('Playbook approved');
      queryClient.invalidateQueries({ queryKey: ['playbooks'] });
      setActionBusyId(null);
    },
    onError: (err: any) => {
      toast.error(err?.message || 'Approve failed');
      setActionBusyId(null);
    }
  });

  const rejectMutation = useMutation({
    mutationFn: async (id: string) => playbooksApi.reject(id),
    onMutate: (id) => setActionBusyId(id),
    onSuccess: () => {
      toast.success('Playbook rejected');
      queryClient.invalidateQueries({ queryKey: ['playbooks'] });
      setActionBusyId(null);
    },
    onError: (err: any) => {
      toast.error(err?.message || 'Reject failed');
      setActionBusyId(null);
    }
  });

  const previewMutation = useMutation({
    mutationFn: async (id: string) => playbooksApi.preview(id),
    onMutate: (id) => setActionBusyId(id),
    onSuccess: (res) => {
      setActionBusyId(null);
      if (res.valid) {
        toast.success('Playbook valid');
      } else {
        toast.error(`Validation failed: ${res.errors.join(', ')}`);
      }
    },
    onError: (err: any) => {
      const detail =
        err?.response?.data?.detail ||
        err?.response?.data?.message ||
        err?.message ||
        '';
      const lower = typeof detail === 'string' ? detail.toLowerCase() : '';
      if (lower.includes('trigger')) {
        toast.error('Add at least one trigger node before validating this playbook.');
      } else {
        toast.error(detail || 'Preview failed');
      }
      setActionBusyId(null);
    }
  });

  // Handle deep-link into a specific playbook
  const isCustomerManaged = tenant?.incident_management_mode === 'customer_managed';
  const isAdmin = (user?.roles || []).some((r) => r.toLowerCase().includes('admin'));
  const { data: pendingApprovals, isLoading: approvalsLoading } = useQuery<PlaybookExecutionRecord[]>({
    queryKey: ['playbook-executions', 'pending-approvals'],
    queryFn: () =>
      playbooksApi.listExecutions({
        status: 'pending',
        approval_status: 'pending',
        limit: 5,
      }),
    enabled: approvalsMode && isCustomerManaged,
  });

  useEffect(() => {
    const targetId = searchParams.get('playbook_id');
    if (targetId && !navigatedByParam.current) {
      navigatedByParam.current = true;
      router.push(`/dashboard/playbooks/${targetId}/edit`);
    }
    const approvals = searchParams.get('approvals');
    if (approvals && approvals !== 'false' && isCustomerManaged) {
      setApprovalsMode(true);
    }
    const seedSearch = searchParams.get('search');
    if (seedSearch) {
      setSearchTerm(seedSearch);
    }
    const seedPack = searchParams.get('pack');
    if (seedPack) {
      setSelectedPackId(seedPack);
    }
  }, [router, searchParams, isCustomerManaged]);

  const selectedPack = useMemo(() => getResponsePackById(selectedPackId), [selectedPackId]);
  const selectedPackPlaybookIds = useMemo(
    () => new Set((selectedPackId ? getResponsePackPlaybooks(selectedPackId, playbooks || []) : []).map((playbook) => playbook.id)),
    [selectedPackId, playbooks]
  );

  const filteredPlaybooks =
    playbooks
      ?.map((playbook: Playbook) => {
        const rawCategory =
          (playbook.category ||
            (Array.isArray(playbook.category_filter) ? playbook.category_filter[0] : null) ||
            (playbook.category_filter && playbook.category_filter.categories ? playbook.category_filter.categories[0] : null) ||
            playbook.owner ||
            playbook.incident_type ||
            '').trim().toLowerCase();
        let category: string | null = null;
        if (rawCategory && rawCategory !== 'custom') {
          if (rawCategory.includes('identity')) category = 'identity';
          else if (rawCategory.includes('endpoint') || rawCategory.includes('edr')) category = 'endpoint';
          else if (rawCategory.includes('email')) category = 'email';
          else if (rawCategory.includes('cloud')) category = 'cloud';
          else if (rawCategory.includes('network')) category = 'network';
          else if (rawCategory.includes('ai')) category = 'ai';
          else category = rawCategory.replace(/[^a-z0-9_-]+/g, '_');
        }
        return { playbook, category };
      })
      .filter(({ playbook, category }) => {
        const matchesSearch =
          playbook.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
          (playbook.playbook_key || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
          playbook.description?.toLowerCase().includes(searchTerm.toLowerCase());
        const matchesCategory =
          selectedCategories.includes('all') || (category ? selectedCategories.includes(category) : false);
        const matchesPack = !selectedPack || selectedPackPlaybookIds.has(playbook.id);
        return matchesSearch && matchesCategory && matchesPack;
      }) || [];

  const toggleCategory = (cat: string) => {
    if (cat === 'all') {
      setSelectedCategories(['all']);
      return;
    }
    setSelectedCategories((prev) => {
      const next = prev.includes(cat) ? prev.filter((c) => c !== cat) : [...prev.filter((c) => c !== 'all'), cat];
      return next.length === 0 ? ['all'] : next;
    });
  };

  const { data: sourceHealth } = useQuery<SourceHealth>({
    queryKey: ['source-health'],
    queryFn: getSourceHealth,
    retry: 1,
    staleTime: 30000,
  });

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-text-main">SOAR Playbooks</h1>
          <p className="mt-1 text-sm text-text-muted dark:text-text-muted">
            Create and manage automated incident response playbooks
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setViewMode('grid')}
            className={`px-3 py-1.5 rounded-md text-sm border ${
              viewMode === 'grid'
                ? 'border-primary text-primary bg-primary/10'
                : 'border-slate-700 text-text-main hover:border-primary/50'
            }`}
          >
            Tiled
          </button>
          <button
            onClick={() => setViewMode('list')}
            className={`px-3 py-1.5 rounded-md text-sm border ${
              viewMode === 'list'
                ? 'border-primary text-primary bg-primary/10'
                : 'border-slate-700 text-text-main hover:border-primary/50'
            }`}
          >
            List
          </button>
          <Link
            href="/dashboard/playbooks/new"
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            Create Playbook
          </Link>
        </div>
      </div>
      <div className="flex flex-wrap gap-2 text-xs text-text-muted dark:text-text-muted">
        <span className="uppercase tracking-wide">Pipeline health</span>
        <HealthBadge label="Ingestion" status={sourceHealth?.ingestion_service} />
        <HealthBadge label="SIEM agent" status={sourceHealth?.siem_agent} />
        <HealthBadge label="OpenSearch" status={sourceHealth?.opensearch} />
      </div>

      {approvalsMode && isCustomerManaged && (
        <div className="rounded-lg border border-yellow-300 bg-yellow-50 px-4 py-3 text-sm text-yellow-900 dark:bg-yellow-900/30 dark:border-yellow-800 dark:text-yellow-200">
          <div className="flex items-center justify-between gap-3">
            <div>
              <div className="font-semibold">
                Pending execution approvals
                {pendingApprovals && pendingApprovals.length > 0 ? ` (${pendingApprovals.length})` : ''}
              </div>
              <div className="mt-1 text-xs">
                Approval-required playbook runs stay pending here until the execution-level approval workflow is connected.
              </div>
            </div>
            <Link
              href="/dashboard/playbooks/executions?status=pending&approval_status=pending"
              className="rounded-md border border-yellow-400/60 px-3 py-2 text-xs font-medium hover:bg-yellow-100/70 dark:hover:bg-yellow-900/40"
            >
              Open execution queue
            </Link>
          </div>
          <div className="mt-3 space-y-2">
            {approvalsLoading ? (
              <div className="text-xs opacity-80">Loading pending approvals...</div>
            ) : pendingApprovals && pendingApprovals.length > 0 ? (
              pendingApprovals.map((execution) => (
                <div
                  key={execution.id}
                  className="rounded-md border border-yellow-200/80 bg-white/70 px-3 py-2 text-xs dark:border-yellow-800/70 dark:bg-yellow-950/20"
                >
                  <div className="font-medium text-yellow-950 dark:text-yellow-100">
                    {execution.playbook_name || `Playbook ${execution.playbook_id?.slice(0, 8) || execution.id.slice(0, 8)}`}
                  </div>
                  <div className="mt-1">
                    Trigger: {execution.trigger_type || 'manual'}
                    {execution.alert_id ? ` • Alert ${execution.alert_id.slice(0, 8)}...` : ''}
                    {execution.started_at ? ` • Requested ${new Date(execution.started_at).toLocaleString()}` : ''}
                  </div>
                </div>
              ))
            ) : (
              <div className="text-xs opacity-80">No approval-blocked executions are queued right now.</div>
            )}
          </div>
        </div>
      )}

      <ResponsePackLibrarySection
        playbooks={playbooks || []}
        selectedPackId={selectedPackId}
        onSelectPack={setSelectedPackId}
      />

      {/* Filters */}
      <div className="space-y-3">
        <div className="flex gap-4 items-center flex-wrap">
          <div className="flex-1 min-w-[260px]">
            <input
              type="text"
              placeholder="Search playbooks..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full px-4 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-surface-card dark:border-border dark:text-white"
            />
          </div>
          {selectedPack && (
            <button
              type="button"
              onClick={() => setSelectedPackId(null)}
              className="rounded-full border border-primary/30 bg-primary/10 px-3 py-2 text-sm text-primary"
            >
              Response pack: {selectedPack.label}
            </button>
          )}
        </div>
        <div className="flex flex-col gap-1">
          <div className="text-xs uppercase tracking-wide text-text-muted dark:text-text-muted">Categories</div>
          <div className="flex gap-2 flex-wrap">
            {categories.map((cat) => {
              const active = selectedCategories.includes(cat);
              const label =
                cat === 'all' ? 'All categories' : cat.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
              return (
                <button
                  key={cat}
                  onClick={() => toggleCategory(cat)}
                  className={`px-3 py-1.5 rounded-full text-sm border ${
                    active
                      ? 'border-primary text-primary bg-primary/10'
                      : 'border-slate-700 text-text-muted'
                  }`}
                >
                  {label}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Playbooks Grid */}
      {isLoading ? (
        <div className="text-center py-12 text-text-muted dark:text-text-muted">Loading playbooks...</div>
      ) : error ? (
        <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-6 text-center">
          <p className="text-yellow-800 dark:text-yellow-200">Unable to load playbooks from the server.</p>
          <p className="text-sm text-yellow-600 dark:text-yellow-400 mt-2">The SOAR service may not be configured yet. You can still create playbooks.</p>
        </div>
      ) : filteredPlaybooks.length === 0 ? (
        <div className="bg-surface-card rounded-lg shadow-sm border border-surface-card-border dark:border-surface-card-border p-12 text-center">
          <p className="text-text-muted dark:text-text-muted">No playbooks found</p>
          <p className="text-sm text-text-muted dark:text-text-muted mt-2">
            {searchTerm || !selectedCategories.includes('all')
              ? 'Try adjusting your filters'
              : 'Create your first playbook to get started'}
          </p>
        </div>
      ) : (
        <div className={viewMode === 'grid' ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6' : 'space-y-3'}>
          {filteredPlaybooks.map(({ playbook, category }) => {
            const hasTriggers =
              Array.isArray(playbook.triggers) && playbook.triggers.length > 0;
            const searchKey = playbook.playbook_key || playbook.name;
            const body = (
              <>
                <div className="flex items-start justify-between">
                  <div>
                    <Link
                      href={`/dashboard/playbooks/${playbook.id}/edit`}
                      className="text-lg font-semibold text-text-main hover:underline"
                      data-testid="playbook-card"
                    >
                      {playbook.name}
                    </Link>
                    {playbook.description && (
                      <p className="text-sm text-text-muted dark:text-text-muted mt-1 line-clamp-2">
                        {playbook.description}
                      </p>
                    )}
                    <div className="text-xs text-text-muted dark:text-text-muted mt-1">
                      {(category || 'uncategorized')} • v{playbook.version} • {playbook.is_template ? 'Template' : 'Playbook'}
                      {playbook.requires_approval && (
                        <span className="ml-2 px-2 py-0.5 text-xs rounded-full bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200">
                          Requires approval
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="text-xs text-text-muted dark:text-text-muted">{new Date(playbook.updated_at).toLocaleDateString()}</div>
                </div>

                {playbook.tags && playbook.tags.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {playbook.tags.map((tag) => (
                      <span
                        key={tag}
                        className="inline-flex px-2 py-0.5 text-xs rounded-full bg-bg-alt text-text-muted dark:bg-bg-alt dark:text-text-main"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                )}

                <div className="flex items-center gap-2">
                  <Link
                    href={`/dashboard/playbooks/${playbook.id}/edit`}
                    className="px-3 py-1 text-sm border border-border rounded-md hover:bg-surface-hover dark:border-border dark:hover:bg-surface-hover"
                  >
                    View
                  </Link>
                  <button
                    onClick={() => hasTriggers && previewMutation.mutate(playbook.id)}
                    disabled={actionBusyId === playbook.id || !hasTriggers}
                    className={`px-3 py-1 text-sm border rounded-md ${
                      hasTriggers
                        ? 'border-border hover:bg-surface-hover dark:border-border dark:hover:bg-surface-hover'
                        : 'border-border dark:border-surface-card-border text-text-muted cursor-not-allowed'
                    }`}
                    title={hasTriggers ? 'Validate playbook' : 'Validate disabled: add at least one trigger'}
                  >
                    Validate
                  </button>
                  {searchKey && (
                    <Link
                      href={`/dashboard/siem/detection-rules?search=${encodeURIComponent(searchKey)}`}
                      className="px-3 py-1 text-sm border border-border rounded-md hover:bg-surface-hover dark:border-border dark:hover:bg-surface-hover"
                    >
                      Linked detections
                    </Link>
                  )}
                  {isCustomerManaged && (
                    <button
                      onClick={() => cloneMutation.mutate(playbook.id)}
                      disabled={actionBusyId === playbook.id}
                      className="px-3 py-1 text-sm border border-border rounded-md hover:bg-surface-hover dark:border-border dark:hover:bg-surface-hover"
                    >
                      Clone to my tenant
                    </button>
                  )}
                  {playbook.requires_approval && isCustomerManaged && isAdmin && (
                    <>
                      <button
                        onClick={() => approveMutation.mutate(playbook.id)}
                        disabled={actionBusyId === playbook.id}
                        className="px-3 py-1 text-sm border border-green-300 text-green-700 rounded-md hover:bg-green-50 dark:border-green-800 dark:text-green-300 dark:hover:bg-green-900/40"
                      >
                        Approve
                      </button>
                      <button
                        onClick={() => rejectMutation.mutate(playbook.id)}
                        disabled={actionBusyId === playbook.id}
                        className="px-3 py-1 text-sm border border-red-300 text-red-700 rounded-md hover:bg-red-50 dark:border-red-800 dark:text-red-300 dark:hover:bg-red-900/40"
                      >
                        Reject
                      </button>
                    </>
                  )}
                  {playbook.is_template && (
                    <span className="ml-auto text-xs px-2 py-0.5 rounded-full bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                      Template
                    </span>
                  )}
                </div>
              </>
            );

            return (
              <div
                key={playbook.id}
                data-testid="playbook-card"
                className={`bg-surface-card rounded-lg shadow-sm border border-surface-card-border dark:border-surface-card-border p-6 hover:shadow-md transition-shadow space-y-3 ${
                  viewMode === 'list' ? 'flex flex-col' : ''
                }`}
              >
                {body}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
