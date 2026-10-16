'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'react-hot-toast';
import {
  listDetectionRules,
  cloneDetectionRule,
  approveDetectionRule,
  rejectDetectionRule,
  deployDetectionRule,
  disableDetectionRule,
  DetectionRule
} from '@/lib/api/detection-rules';
import { useSearchParams } from 'next/navigation';
import { getSourceHealth, SourceHealth } from '@/lib/api/siem';
import { PlanGate } from '@/components/PlanGate';
import HealthBadge from '@/components/ui/HealthBadge';

export default function DetectionRulesPage() {
  const queryClient = useQueryClient();
  const [deployingId, setDeployingId] = useState<string | null>(null);
  const [cloningId, setCloningId] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [selectedCategories, setSelectedCategories] = useState<string[]>(['all']);
  const [searchTerm, setSearchTerm] = useState('');
  const [needsAuth, setNeedsAuth] = useState(false);
  const searchParams = useSearchParams();
  const { data: sourceHealth, isLoading: loadingHealth, error: healthError } = useQuery<SourceHealth>({
    queryKey: ['source-health'],
    queryFn: getSourceHealth,
    retry: 1,
    staleTime: 30000
  });

  useEffect(() => {
    if (healthError) {
      const err: any = healthError;
      const status = err?.response?.status || err?.status;
      if (status === 401 || status === 403) setNeedsAuth(true);
    }
  }, [healthError]);

  const sourceInfo = (indexPattern?: string) => {
    const pat = (indexPattern || '').toLowerCase();
    if (pat.includes('-ai-')) return { label: 'AI telemetry', color: 'bg-indigo-500/10 border-indigo-500/40 text-indigo-200' };
    if (pat.includes('-auth-')) return { label: 'Identity/Auth', color: 'bg-emerald-500/10 border-emerald-500/40 text-emerald-200' };
    if (pat.includes('-endpoint-')) return { label: 'Endpoint', color: 'bg-orange-500/10 border-orange-500/40 text-orange-200' };
    if (pat.includes('-network-')) return { label: 'Network/Flow', color: 'bg-blue-500/10 border-blue-500/40 text-blue-200' };
    if (pat.includes('-cloud-')) return { label: 'Cloud', color: 'bg-cyan-500/10 border-cyan-500/40 text-cyan-200' };
    return { label: 'Unknown source', color: 'bg-slate-700/60 border-slate-600 text-text-muted' };
  };

  const { data: rules, isLoading } = useQuery<DetectionRule[]>({
    queryKey: ['detection-rules'],
    queryFn: async () => listDetectionRules()
  });

  const cloneMutation = useMutation({
    mutationFn: async ({ id, name, rule_key, description }: { id: string; name: string; rule_key: string; description?: string }) =>
      cloneDetectionRule(id, { name, rule_key, description }),
    onSuccess: () => {
      toast.success('Rule cloned');
      queryClient.invalidateQueries({ queryKey: ['detection-rules'] });
    },
    onError: (err: any) => toast.error(`Clone failed: ${err?.message || 'error'}`)
  });

  const approveMutation = useMutation({
    mutationFn: async (id: string) => approveDetectionRule(id),
    onSuccess: () => {
      toast.success('Rule approved');
      queryClient.invalidateQueries({ queryKey: ['detection-rules'] });
    },
    onError: (err: any) => toast.error(`Approve failed: ${err?.message || 'error'}`)
  });

  const rejectMutation = useMutation({
    mutationFn: async (id: string) => rejectDetectionRule(id),
    onSuccess: () => {
      toast.success('Rule rejected');
      queryClient.invalidateQueries({ queryKey: ['detection-rules'] });
    },
    onError: (err: any) => toast.error(`Reject failed: ${err?.message || 'error'}`)
  });

  const deployMutation = useMutation({
    mutationFn: async ({ id, destination_id }: { id: string; destination_id: string }) =>
      deployDetectionRule(id, { destination_id }),
    onMutate: ({ id }) => setDeployingId(id),
    onSuccess: (resp) => {
      setDeployingId(null);
      if (resp.deployed) {
        toast.success(`Deployed monitor ${resp.monitor_id}`);
      } else {
        toast(`Approval status: ${resp.approval_status || 'pending'}`);
      }
      queryClient.invalidateQueries({ queryKey: ['detection-rules'] });
    },
    onError: (err: any) => {
      setDeployingId(null);
      toast.error(`Deploy failed: ${err?.message || 'error'}`);
    }
  });

  const disableMutation = useMutation({
    mutationFn: async (id: string) => disableDetectionRule(id),
    onSuccess: () => {
      toast.success('Rule disabled');
      queryClient.invalidateQueries({ queryKey: ['detection-rules'] });
    },
    onError: (err: any) => toast.error(`Disable failed: ${err?.message || 'error'}`)
  });

  const handleClone = (rule: DetectionRule) => {
    const name = prompt('New rule name', `${rule.name} Copy`);
    const ruleKey = prompt('New rule key', `${rule.rule_key}-COPY`);
    if (!name || !ruleKey) return;
    setCloningId(rule.id);
    cloneMutation.mutate({ id: rule.id, name, rule_key: ruleKey, description: rule.description });
    setCloningId(null);
  };

  const handleDeploy = (rule: DetectionRule) => {
    const dest = prompt('Enter OpenSearch destination_id (webhook config id):');
    if (!dest || !dest.trim()) {
      toast.error('Destination ID is required');
      return;
    }
    deployMutation.mutate({ id: rule.id, destination_id: dest });
    queryClient.invalidateQueries({ queryKey: ['detection-rules'] });
  };

  const loading = isLoading || !rules;
  const categories = ['all', ...Array.from(new Set((rules || []).map((r) => r.category || 'uncategorized')))];

  // Seed search from query param so deep-links work (e.g., from playbooks)
  useEffect(() => {
    const seed = searchParams.get('search');
    if (seed) {
      setSearchTerm(seed);
    }
  }, [searchParams]);

  const filteredRules =
    rules?.filter((rule) => {
      const matchesSearch =
        rule.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        rule.description?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        rule.rule_key.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesCategory =
        selectedCategories.includes('all') || selectedCategories.includes(rule.category || 'uncategorized');
      return matchesCategory && matchesSearch;
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

  return (
    <PlanGate
      requiredTier="protect_defend"
      title="Unlock detections & response"
      description="The Protect + Defend plan includes detection engineering, rule deployments, and SIEM monitoring."
    >
      <div className="p-6 space-y-4">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div>
            <h1 className="text-3xl font-bold text-text-main">Detection Rules</h1>
            <p className="text-text-muted">Built-in templates and your cloned rules</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setViewMode('grid')}
              className={`px-3 py-1.5 rounded-md text-sm border ${
                viewMode === 'grid'
                  ? 'border-primary text-primary bg-primary/10'
                  : 'border-surface-card text-text-main hover:border-primary/50'
              }`}
            >
              Tiled
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`px-3 py-1.5 rounded-md text-sm border ${
                viewMode === 'list'
                  ? 'border-primary text-primary bg-primary/10'
                  : 'border-surface-card text-text-main hover:border-primary/50'
              }`}
            >
              List
            </button>
            <Link
              href="/dashboard/siem/detection-rules/builder"
              className="px-3 py-2 bg-blue-600 text-white rounded text-sm hover:bg-blue-700"
            >
              New Rule (Builder)
            </Link>
          </div>
        </div>

        <div className="flex flex-wrap gap-2 items-center text-xs text-text-muted">
          <span className="uppercase tracking-wide">Pipeline health</span>
          <HealthBadge label="Ingestion" status={sourceHealth?.ingestion_service} />
          <HealthBadge label="SIEM agent" status={sourceHealth?.siem_agent} />
          <HealthBadge label="OpenSearch" status={sourceHealth?.opensearch} />
          {loadingHealth && <span className="text-[11px]">checking...</span>}
          {healthError && <span className="text-amber-300 text-[11px]">health endpoint unavailable</span>}
          {needsAuth && (
            <Link href="/login" className="text-primary text-[11px] underline">
              Session expired? Sign in again.
            </Link>
          )}
        </div>

        <div className="flex flex-wrap gap-3 items-center">
          <div className="flex-1 min-w-[240px]">
            <input
              type="text"
              placeholder="Search detection rules..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full px-4 py-2 rounded-md border border-slate-700 bg-[rgba(15,23,42,0.6)] text-text-main placeholder:text-text-muted focus:outline-none focus:border-primary"
            />
          </div>
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
                    active ? 'border-primary text-primary bg-primary/10' : 'border-slate-700 text-text-muted'
                  }`}
                >
                  {label}
                </button>
              );
            })}
          </div>
        </div>

        {loading ? (
          <div className="animate-pulse space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-16 rounded-lg bg-surface-card" />
            ))}
          </div>
        ) : (
          <div className={viewMode === 'grid' ? 'grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4' : 'space-y-3'}>
            {filteredRules.map((rule) => {
              const latest = rule.versions?.[0];
              const isDeploying = deployingId === rule.id;
              const isCloning = cloningId === rule.id;
              const mappingKey = rule.mapping?.playbook_key || '';
              const source = sourceInfo(latest?.index_pattern);
              return (
                <div
                  key={rule.id}
                  data-testid="detection-card"
                  className={`flex ${
                    viewMode === 'grid'
                      ? 'flex-col gap-3'
                      : 'flex-col gap-2 md:flex-row md:items-center md:justify-between'
                  } rounded-lg border border-surface-card-border bg-surface-card p-4`}
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-primary font-mono text-xs">{rule.rule_key}</span>
                      <span className="text-text-main font-semibold">{rule.name}</span>
                      <span className={`px-2 py-0.5 text-[11px] rounded-full border ${source.color}`}>
                        {source.label}
                      </span>
                      {rule.approval_required && (
                        <span className="px-2 py-1 text-xs rounded-full bg-yellow-500/10 border border-yellow-500/30 text-yellow-500">
                          Approval required
                        </span>
                      )}
                    </div>
                    <div className="text-text-muted text-sm">{rule.description || 'No description'}</div>
                    <div className="text-xs text-text-muted mt-1">
                      Category: {rule.category} • Version: {rule.current_version} • Severity: {latest?.severity || 'n/a'}
                      {rule.deployment?.approval_status && (
                        <span className="ml-2">• Status: {rule.deployment.approval_status}</span>
                      )}
                      {rule.deployment?.is_enabled === false && <span className="ml-2">• Disabled</span>}
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Link
                      href={`/dashboard/siem/detection-rules/${rule.id}`}
                      className="px-3 py-1.5 text-sm bg-primary text-white rounded-lg hover:bg-primary/90 transition-colors"
                    >
                      View
                    </Link>
                    <span className="px-3 py-1.5 text-xs rounded-lg border border-slate-700 text-text-muted">
                      v{rule.current_version}
                    </span>
                    {mappingKey ? (
                      <Link
                        href={`/dashboard/playbooks?search=${encodeURIComponent(mappingKey)}`}
                        className="px-3 py-1.5 text-sm border border-surface-card-border rounded-lg text-text-main hover:border-primary/50"
                      >
                        Linked playbook
                      </Link>
                    ) : (
                      <span className="px-3 py-1.5 text-sm border border-dashed border-slate-700 rounded-lg text-text-muted cursor-not-allowed">
                        No linked playbook
                      </span>
                    )}
                    <button
                      onClick={() => handleClone(rule)}
                      disabled={isCloning}
                      className="px-3 py-1.5 text-sm border border-surface-card-border rounded-lg text-text-main hover:border-primary/50 disabled:opacity-50"
                    >
                      {isCloning ? 'Cloning...' : 'Clone'}
                    </button>
                    <button
                      onClick={() => handleDeploy(rule)}
                      disabled={isDeploying}
                      className="px-3 py-1.5 text-sm border border-surface-card-border rounded-lg text-text-main hover:border-primary/50 disabled:opacity-50"
                    >
                      {isDeploying ? 'Deploying...' : 'Deploy'}
                    </button>
                    <button
                      onClick={() => approveMutation.mutate(rule.id)}
                      className="px-3 py-1.5 text-sm border border-green-500/40 text-green-400 rounded-lg hover:border-green-500/80"
                    >
                      Approve
                    </button>
                    <button
                      onClick={() => rejectMutation.mutate(rule.id)}
                      className="px-3 py-1.5 text-sm border border-red-500/40 text-red-400 rounded-lg hover:border-red-500/80"
                    >
                      Reject
                    </button>
                    <button
                      onClick={() => disableMutation.mutate(rule.id)}
                      className="px-3 py-1.5 text-sm border border-surface-card-border rounded-lg text-text-main hover:border-primary/50"
                    >
                      Disable
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </PlanGate>
  );
}
