'use client';

import { useEffect, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { toast } from 'react-hot-toast';
import Breadcrumbs from '@/components/ui/Breadcrumbs';
import {
  getDetectionRule,
  previewDetectionRule,
  deployDetectionRule,
  disableDetectionRule,
  setDetectionRuleMapping
} from '@/lib/api/detection-rules';
import { apiClient } from '@/lib/api/client';

interface DetectionRule {
  id: string;
  rule_key: string;
  name: string;
  description?: string;
  category: string;
  current_version: string;
  approval_required: boolean;
  mapping?: {
    alert_type?: string;
    playbook_key?: string;
    auto_execute?: boolean;
    requires_approval?: boolean;
  };
  deployment?: {
    monitor_id?: string;
    destination_id?: string;
    is_enabled?: boolean;
    approval_status?: string;
    rule_version?: string;
  };
  versions: Array<{
    id?: string;
    version: string;
    index_pattern: string;
    query: any;
    trigger_condition: any;
    severity: string;
    metadata?: {
      mitre_techniques?: string[];
      mitre_tactics?: string[];
      nist_controls?: string[];
      cis_controls?: string[];
      alert_type?: string;
    };
  }>;
}

export default function DetectionRuleDetailPage() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState('overview');
  const [fallbackUsed, setFallbackUsed] = useState(false);
  const [mappingAlertType, setMappingAlertType] = useState('');
  const [mappingPlaybook, setMappingPlaybook] = useState('');
  const [mappingAuto, setMappingAuto] = useState(false);
  const [mappingApproval, setMappingApproval] = useState(false);
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

  const { data: rule, isLoading, error } = useQuery<DetectionRule>({
    queryKey: ['detection-rule', params.id],
    queryFn: async () => {
      try {
        return await getDetectionRule(params.id as string);
      } catch (err: any) {
        const status = err?.response?.status;
        if (status === 404 || status === 403) {
          // Retry against system tenant
          const res = await apiClient.get<DetectionRule>(`/siem/detection-rules/${params.id}`, {
            headers: { 'X-Tenant-ID': '9c7df7a9-5a0b-4412-a41c-0c0ea777b2f0' }
          });
          setFallbackUsed(true);
          return res.data;
        }
        throw err;
      }
    }
  });

  useEffect(() => {
    if (rule) {
      const latest = rule.versions?.[0];
      setMappingAlertType(rule.mapping?.alert_type || latest?.metadata?.alert_type || '');
      setMappingPlaybook(rule.mapping?.playbook_key || '');
      setMappingAuto(rule.mapping?.auto_execute || false);
      setMappingApproval(rule.mapping?.requires_approval || false);
    }
  }, [rule]);

  const previewMutation = useMutation({
    mutationFn: async () => {
      if (!rule || !rule.versions?.length) throw new Error('No version available');
      const v = rule.versions[0];
      return previewDetectionRule(rule.id, {
        index_pattern: v.index_pattern,
        query: v.query,
        trigger_condition: v.trigger_condition,
        time_range_minutes: 60
      });
    },
    onSuccess: (data) => {
      toast.success(`Preview hits: ${data.hits}`);
    },
    onError: (err: any) => {
      toast.error(`Preview failed: ${err?.message || 'error'}`);
    }
  });

  const deployMutation = useMutation({
    mutationFn: async (destId: string) => {
      if (!rule) throw new Error('Rule not loaded');
      return deployDetectionRule(rule.id, {
        destination_id: destId,
        schedule_minutes: 5,
        auto_execute: false
      });
    },
    onSuccess: (resp) => {
      if (resp.deployed) {
        toast.success(`Deployed monitor ${resp.monitor_id}`);
      } else {
        toast(`Approval status: ${resp.approval_status || 'pending'}`);
      }
      queryClient.invalidateQueries({ queryKey: ['detection-rule', params.id] });
    },
    onError: (err: any) => {
      toast.error(`Deploy failed: ${err?.message || 'error'}`);
    }
  });

  const disableMutation = useMutation({
    mutationFn: async () => {
      if (!rule) throw new Error('Rule not loaded');
      return disableDetectionRule(rule.id);
    },
    onSuccess: () => {
      toast.success('Rule disabled');
      queryClient.invalidateQueries({ queryKey: ['detection-rule', params.id] });
    },
    onError: (err: any) => {
      toast.error(`Disable failed: ${err?.message || 'error'}`);
    }
  });

  const mappingMutation = useMutation({
    mutationFn: async (payload: { alert_type: string; playbook_key: string; auto_execute: boolean; requires_approval: boolean }) => {
      if (!rule) throw new Error('Rule not loaded');
      return setDetectionRuleMapping(rule.id, payload);
    },
    onSuccess: () => {
      toast.success('Mapping saved');
      queryClient.invalidateQueries({ queryKey: ['detection-rule', params.id] });
    },
    onError: (err: any) => {
      toast.error(`Mapping failed: ${err?.message || 'error'}`);
    }
  });

  const handleDeploy = () => {
    const dest = prompt('Enter OpenSearch destination_id (webhook config id):');
    if (!dest) return;
    deployMutation.mutate(dest);
    queryClient.invalidateQueries({ queryKey: ['detection-rule', params.id] });
  };

  if (isLoading) {
    return (
      <div className="p-6">
        <div className="animate-pulse">
          <div className="h-8 bg-bg-alt rounded w-1/2 mb-6"></div>
          <div className="h-64 bg-bg-alt rounded"></div>
        </div>
      </div>
    );
  }

  if (!rule || error) {
    return (
      <div className="p-6">
        <Link href="/dashboard/siem/detection-rules" className="text-sm text-primary hover:underline mb-2 inline-block">
          ← Back to Detection Rules
        </Link>
        <div className="rounded-lg border border-red-500/40 bg-red-500/10 p-4 text-red-200">
          <p className="font-semibold">Detection not available in this tenant.</p>
          <p className="text-sm">
            {fallbackUsed
              ? 'Attempted to load from system tenant but failed.'
              : 'Switch to the system tenant or contact an admin to access this detection.'}
          </p>
        </div>
      </div>
    );
  }

  const latestVersion = rule.versions?.[0];
  const stats = (rule as any).statistics || {
    total_fires: 0,
    fires_24h: 0,
    fires_7d: 0,
    incidents_created: 0,
    last_fired: 'N/A'
  };

  return (
    <div className="p-6">
      <Breadcrumbs />
      {/* Header */}
      <div className="mb-6">
        <Link
          href="/dashboard/siem/detection-rules"
          className="text-sm text-primary hover:underline mb-2 inline-block"
        >
          ← Back to Detection Rules
        </Link>
        
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-bold text-text-main mb-2">
              {rule.rule_key}: {rule.name}
            </h1>
            <p className="text-text-muted">{rule.description}</p>
            {rule.deployment?.monitor_id && (
              <p className="text-xs text-text-muted mt-1">
                Monitor: {rule.deployment.monitor_id} • Status: {rule.deployment.approval_status || 'n/a'} {rule.deployment.is_enabled === false ? '(disabled)' : ''}
              </p>
            )}
          </div>
          
          <div className="px-3 py-2 rounded-lg border border-[rgba(15,23,42,0.95)] text-sm text-text-muted">
            {rule.approval_required ? 'Approval required' : 'Auto deploy allowed'}
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-6 border-b border-[rgba(15,23,42,0.9)] overflow-x-auto">
        {[
          { id: 'overview', label: 'Overview', icon: '📊' },
          { id: 'configuration', label: 'Configuration', icon: '⚙️' },
          { id: 'performance', label: 'Performance', icon: '📈' },
          { id: 'compliance', label: 'Compliance', icon: '✓' },
          { id: 'history', label: 'History', icon: '📜' }
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`
              px-4 py-2 text-sm font-medium transition-colors whitespace-nowrap flex items-center gap-2
              ${activeTab === tab.id
                ? 'text-primary border-b-2 border-primary'
                : 'text-text-muted hover:text-text-main'
              }
            `}
          >
            <span>{tab.icon}</span>
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && (
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Configuration */}
          <div className="bg-[rgba(15,23,42,0.9)] rounded-xl border border-[rgba(15,23,42,0.95)] p-6">
            <h2 className="text-xl font-semibold text-text-main mb-4">Configuration</h2>
            <div className="space-y-3">
              <div>
                <span className="text-sm text-text-muted">Rule Key:</span>
                <p className="text-text-main font-mono">{rule.rule_key}</p>
              </div>
              <div>
                <span className="text-sm text-text-muted">Version:</span>
                <p className="text-text-main">{rule.current_version}</p>
              </div>
              <div>
                <span className="text-sm text-text-muted">Category:</span>
                <p className="text-text-main capitalize">{rule.category}</p>
              </div>
              <div>
                <span className="text-sm text-text-muted">Severity:</span>
                <p className="text-text-main capitalize">{latestVersion?.severity || 'n/a'}</p>
              </div>
              {latestVersion && (
                <div>
                  <span className="text-sm text-text-muted">Index Pattern:</span>
                  <p className="text-text-main font-mono text-sm">{latestVersion.index_pattern}</p>
                </div>
              )}
            </div>
          </div>

          {/* Statistics */}
          <div className="bg-[rgba(15,23,42,0.9)] rounded-xl border border-[rgba(15,23,42,0.95)] p-6">
            <h2 className="text-xl font-semibold text-text-main mb-4">Statistics</h2>
            <div className="grid grid-cols-2 gap-4">
              <div className="text-center p-4 rounded-lg bg-primary/10 border border-primary/30">
                <div className="text-3xl font-bold text-primary">
                  {stats.fires_24h}
                </div>
                <div className="text-sm text-text-muted mt-1">Fires (24h)</div>
              </div>
              <div className="text-center p-4 rounded-lg bg-primary/10 border border-primary/30">
                <div className="text-3xl font-bold text-primary">
                  {stats.fires_7d}
                </div>
                <div className="text-sm text-text-muted mt-1">Fires (7d)</div>
              </div>
              <div className="text-center p-4 rounded-lg bg-primary/10 border border-primary/30">
                <div className="text-3xl font-bold text-primary">
                  {stats.incidents_created}
                </div>
                <div className="text-sm text-text-muted mt-1">Incidents Created</div>
              </div>
              <div className="text-center p-4 rounded-lg bg-primary/10 border border-primary/30">
                <div className="text-sm text-text-muted">Last Fired</div>
                <div className="text-base font-medium text-text-main mt-1">
                  {stats.last_fired}
                </div>
              </div>
            </div>
          </div>

          {/* Linked Playbook */}
          <div className="bg-[rgba(15,23,42,0.9)] rounded-xl border border-[rgba(15,23,42,0.95)] p-6">
            <h2 className="text-xl font-semibold text-text-main mb-4">Linked Playbook</h2>
            {mappingPlaybook ? (
              <div className="space-y-2">
                <div className="text-sm text-text-muted">Playbook Key</div>
                <div className="text-text-main font-mono">{mappingPlaybook}</div>
                <div className="text-sm text-text-muted">Alert Type</div>
                <div className="text-text-main">{mappingAlertType || '—'}</div>
                <Link
                  href={`/dashboard/playbooks?search=${encodeURIComponent(mappingPlaybook)}`}
                  className="inline-flex mt-3 px-3 py-2 rounded-md bg-primary text-white text-sm hover:bg-primary/90"
                >
                  View playbook
                </Link>
              </div>
            ) : (
              <div className="text-sm text-text-muted">
                No playbook mapping found.{' '}
                {fallbackUsed
                  ? 'This is a system rule; update mapping in the system tenant.'
                  : 'Add a mapping to trigger a response playbook.'}
              </div>
            )}
          </div>
        </div>
      )}

      {activeTab === 'configuration' && latestVersion && (
        <div className="space-y-4">
          <div className="bg-[rgba(15,23,42,0.9)] rounded-xl border border-[rgba(15,23,42,0.95)] p-6">
            <h2 className="text-xl font-semibold text-text-main mb-4">Detection Query</h2>
            <div className="space-y-4">
              <div>
                <h3 className="text-sm font-medium text-text-muted mb-2">OpenSearch Query DSL</h3>
                <pre className="bg-black/50 p-4 rounded-lg overflow-x-auto text-sm">
                  <code className="text-green-400">
                    {JSON.stringify(latestVersion.query, null, 2)}
                  </code>
                </pre>
              </div>
              <div>
                <h3 className="text-sm font-medium text-text-muted mb-2">Trigger Condition</h3>
                <pre className="bg-black/50 p-4 rounded-lg overflow-x-auto text-sm">
                  <code className="text-green-400">
                    {JSON.stringify(latestVersion.trigger_condition, null, 2)}
                  </code>
                </pre>
              </div>
            </div>
          </div>

          <div className="bg-[rgba(15,23,42,0.9)] rounded-xl border border-[rgba(15,23,42,0.95)] p-6">
            <h2 className="text-xl font-semibold text-text-main mb-4">Playbook Mapping</h2>
            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-text-muted mb-1">Alert Type</label>
                <input
                  value={mappingAlertType}
                  onChange={(e) => setMappingAlertType(e.target.value)}
                  className="w-full px-3 py-2 rounded border border-[rgba(15,23,42,0.95)] bg-transparent text-text-main"
                  placeholder="e.g., suspicious_login"
                />
              </div>
              <div>
                <label className="block text-sm text-text-muted mb-1">Playbook Key</label>
                <input
                  value={mappingPlaybook}
                  onChange={(e) => setMappingPlaybook(e.target.value)}
                  className="w-full px-3 py-2 rounded border border-[rgba(15,23,42,0.95)] bg-transparent text-text-main"
                  placeholder="e.g., PLAYBOOK_ACCOUNT_TAKEOVER"
                />
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={mappingAuto}
                  onChange={(e) => setMappingAuto(e.target.checked)}
                />
                <span className="text-sm text-text-main">Auto-execute</span>
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={mappingApproval}
                  onChange={(e) => setMappingApproval(e.target.checked)}
                />
                <span className="text-sm text-text-main">Requires approval</span>
              </div>
            </div>
            <button
              onClick={() =>
                mappingMutation.mutate({
                  alert_type: mappingAlertType,
                  playbook_key: mappingPlaybook,
                  auto_execute: mappingAuto,
                  requires_approval: mappingApproval
                })
              }
              className="mt-4 px-4 py-2 bg-primary text-white rounded hover:bg-primary/90"
            >
              Save Mapping
            </button>
          </div>
        </div>
      )}

      {activeTab === 'performance' && (
        <div className="bg-[rgba(15,23,42,0.9)] rounded-xl border border-[rgba(15,23,42,0.95)] p-6">
          <h2 className="text-xl font-semibold text-text-main mb-4">Detailed Statistics</h2>
          <div className="space-y-4">
            <div className="p-4 rounded-lg border border-[rgba(15,23,42,0.9)]">
              <h3 className="font-medium text-text-main mb-2">Fire History</h3>
              <div className="text-sm text-text-muted">
                Timeline visualization coming soon...
              </div>
            </div>
            <div className="p-4 rounded-lg border border-[rgba(15,23,42,0.9)]">
              <h3 className="font-medium text-text-main mb-2">Incident Creation Rate</h3>
              <div className="text-sm text-text-muted">
                Incident creation metrics coming soon...
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'compliance' && (
        <div className="grid gap-6 lg:grid-cols-2">
          {/* MITRE ATT&CK */}
          <div className="bg-[rgba(15,23,42,0.9)] rounded-xl border border-[rgba(15,23,42,0.95)] p-6">
            <h2 className="text-xl font-semibold text-text-main mb-4">MITRE ATT&CK</h2>
            <div className="space-y-3">
              <div>
                <h3 className="text-sm font-medium text-text-muted mb-2">Tactics</h3>
                <div className="flex flex-wrap gap-2">
                  {latestVersion?.metadata?.mitre_tactics?.map(tactic => (
                    <a
                      key={tactic}
                      href={mitreLink(tactic) || '#'}
                      target={mitreLink(tactic) ? '_blank' : undefined}
                      rel="noreferrer"
                      title={`MITRE tactic ${tactic}`}
                      className="px-3 py-1 text-sm rounded-full bg-primary/10 border border-primary/30 text-primary hover:bg-primary/20"
                    >
                      {tactic}
                    </a>
                  ))}
                </div>
              </div>
              <div>
                <h3 className="text-sm font-medium text-text-muted mb-2">Techniques</h3>
                <div className="flex flex-wrap gap-2">
                  {latestVersion?.metadata?.mitre_techniques?.map(technique => (
                    <a
                      key={technique}
                      href={mitreLink(technique) || '#'}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="px-3 py-1 text-sm rounded-full bg-primary/10 border border-primary/30 text-primary hover:bg-primary/20"
                      title={`MITRE technique ${technique}`}
                    >
                      {technique}
                    </a>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* NIST Controls */}
          <div className="bg-[rgba(15,23,42,0.9)] rounded-xl border border-[rgba(15,23,42,0.95)] p-6">
            <h2 className="text-xl font-semibold text-text-main mb-4">NIST SP 800-53</h2>
            <div className="space-y-3">
              <div>
                <h3 className="text-sm font-medium text-text-muted mb-2">Controls</h3>
                <div className="flex flex-wrap gap-2">
                  {latestVersion?.metadata?.nist_controls?.map(control => (
                    <Link
                      key={control}
                      href={controlLink(control) || '#'}
                      className="px-3 py-1 text-sm rounded-full bg-green-500/10 border border-green-500/30 text-green-500 hover:bg-green-500/20"
                      title={`NIST control ${control}`}
                    >
                      {control}
                    </Link>
                  ))}
                </div>
              </div>
              <div>
                <h3 className="text-sm font-medium text-text-muted mb-2">CIS Controls</h3>
                <div className="flex flex-wrap gap-2">
                  {latestVersion?.metadata?.cis_controls?.map(control => (
                    <Link
                      key={control}
                      href={controlLink(`CIS-${control}`) || '#'}
                      className="px-3 py-1 text-sm rounded-full bg-blue-500/10 border border-blue-500/30 text-blue-500 hover:bg-blue-500/20"
                      title={`CIS control ${control}`}
                    >
                      CIS {control}
                    </Link>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'history' && (
        <div className="space-y-4">
          {/* Version History */}
          <div className="bg-[rgba(15,23,42,0.9)] rounded-xl border border-[rgba(15,23,42,0.95)] p-6">
            <h2 className="text-xl font-semibold text-text-main mb-4">Version History</h2>
            <div className="space-y-3">
              {[
                { version: '1.0.0', date: '2025-12-01', author: 'admin@example.com', changes: 'Initial rule deployment' },
                { version: '0.9.0', date: '2025-11-28', author: 'security@example.com', changes: 'Beta testing version' }
              ].map((entry, idx) => (
                <div key={idx} className="flex items-start gap-4 p-4 rounded-lg border border-[rgba(15,23,42,0.9)]">
                  <div className="flex-shrink-0">
                    <span className="px-3 py-1 text-sm rounded-full bg-primary/10 border border-primary/30 text-primary font-mono">
                      v{entry.version}
                    </span>
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-text-main font-medium">{entry.changes}</span>
                    </div>
                    <div className="text-sm text-text-muted">
                      <span>{entry.date}</span> • <span>{entry.author}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Audit Log */}
          <div className="bg-[rgba(15,23,42,0.9)] rounded-xl border border-[rgba(15,23,42,0.95)] p-6">
            <h2 className="text-xl font-semibold text-text-main mb-4">Recent Activity</h2>
            <div className="space-y-2">
              {[
                { timestamp: '2025-12-04 10:30:00', action: 'Rule Enabled', user: 'admin@example.com' },
                { timestamp: '2025-12-03 15:45:00', action: 'Configuration Updated', user: 'security@example.com' },
                { timestamp: '2025-12-01 09:00:00', action: 'Rule Created', user: 'admin@example.com' }
              ].map((entry, idx) => (
                <div key={idx} className="flex items-center gap-4 p-3 rounded-lg border border-[rgba(15,23,42,0.9)] hover:border-primary/30 transition-colors">
                  <div className="flex-shrink-0 text-2xl">
                    {entry.action.includes('Enabled') ? '✓' : entry.action.includes('Created') ? '🎉' : '⚙️'}
                  </div>
                  <div className="flex-1">
                    <div className="text-text-main font-medium">{entry.action}</div>
                    <div className="text-sm text-text-muted">{entry.timestamp}</div>
                  </div>
                  <div className="text-sm text-text-muted">{entry.user}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="mt-8 flex gap-3">
        <button
          onClick={() => previewMutation.mutate()}
          disabled={previewMutation.isPending}
          className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50"
        >
          {previewMutation.isPending ? 'Testing...' : 'Test Rule'}
        </button>
        <Link
          href={`/dashboard/siem/detection-rules/builder?ruleId=${encodeURIComponent(rule.id)}`}
          className="px-4 py-2 bg-[rgba(15,23,42,0.9)] border border-[rgba(15,23,42,0.95)] text-text-main rounded-lg hover:border-primary/50 transition-colors"
          title="Opens a cloned copy in the no-code builder (does not modify the original rule)."
        >
          Open in Builder
        </Link>
        <button
          onClick={handleDeploy}
          disabled={deployMutation.isPending}
          className="px-4 py-2 bg-[rgba(15,23,42,0.9)] border border-[rgba(15,23,42,0.95)] text-text-main rounded-lg hover:border-primary/50 transition-colors disabled:opacity-50"
        >
          {deployMutation.isPending ? 'Deploying...' : 'Deploy'}
        </button>
        <button
          onClick={() => disableMutation.mutate()}
          disabled={disableMutation.isPending}
          className="px-4 py-2 bg-[rgba(15,23,42,0.9)] border border-[rgba(15,23,42,0.95)] text-text-main rounded-lg hover:border-primary/50 transition-colors disabled:opacity-50"
        >
          {disableMutation.isPending ? 'Disabling...' : 'Disable'}
        </button>
      </div>
    </div>
  );
}
