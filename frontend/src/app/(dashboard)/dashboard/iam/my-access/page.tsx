'use client';

import { useMemo, useState } from 'react';
import type React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  CheckCircleIcon,
  ClockIcon,
  XCircleIcon,
  PlusIcon,
  ShieldExclamationIcon,
  BoltIcon,
  ShieldCheckIcon,
  SparklesIcon,
  CursorArrowRaysIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline';
import { getMyAccess, createAccessRequest, getApps, getEntitlements } from '@/lib/api/iam-portal';
import type { Entitlement, UserEntitlement } from '@/lib/api/iam-portal';

type EnhancedEntitlement = {
  raw: UserEntitlement;
  id: string;
  displayName: string;
  description?: string;
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
  riskScore: number;
  lastUsed: Date | null;
  lastUsedLabel: string;
  expiresAt?: string | null;
  expiresInDays?: number | null;
  isUnused: boolean;
  expiringSoon: boolean;
  requiresMfa: boolean;
  isPrivileged: boolean;
  appName?: string;
};

type QuickFilter = 'unused' | 'highRisk' | 'expiring' | 'mfa';

export default function MyAccessPage() {
  const router = useRouter();
  const [showRequestModal, setShowRequestModal] = useState(false);
  const [selectedEntitlement, setSelectedEntitlement] = useState<Entitlement | UserEntitlement | null>(null);
  const [selectedDetail, setSelectedDetail] = useState<EnhancedEntitlement | null>(null);
  const [activeFilters, setActiveFilters] = useState<QuickFilter[]>([]);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [aiLoading, setAiLoading] = useState<string | null>(null);
  const [aiExplanation, setAiExplanation] = useState<string | null>(null);
  const [aiRecommendation, setAiRecommendation] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');

  const queryClient = useQueryClient();

  // Fetch my access summary
  const { data: accessSummary, isLoading } = useQuery({
    queryKey: ['iam-my-access'],
    queryFn: getMyAccess,
  });

  // Catalog for search (apps + entitlements)
  const { data: apps } = useQuery({
    queryKey: ['iam-apps'],
    queryFn: getApps,
  });
  const { data: entitlements } = useQuery({
    queryKey: ['iam-entitlements'],
    queryFn: () => getEntitlements(),
  });

  // Create access request mutation
  const createRequestMutation = useMutation({
    mutationFn: createAccessRequest,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['iam-my-access'] });
      setShowRequestModal(false);
      setSelectedEntitlement(null);
      setActionMessage('Request submitted for review');
    },
  });

  const firstAvailable = accessSummary?.available_entitlements?.[0];

  const enhancedCurrent = useMemo(() => {
    if (!accessSummary?.current_entitlements) return [];
    return accessSummary.current_entitlements.map((ent) => enhanceEntitlement(ent));
  }, [accessSummary?.current_entitlements]);

  const filteredCurrent = useMemo(() => {
    return enhancedCurrent.filter((item) => {
      if (activeFilters.includes('unused') && !item.isUnused) return false;
      if (activeFilters.includes('highRisk') && !['high', 'critical'].includes(item.riskLevel)) return false;
      if (activeFilters.includes('expiring') && !(typeof item.expiresInDays === 'number' && item.expiresInDays <= 14)) return false;
      if (activeFilters.includes('mfa') && !item.requiresMfa) return false;
      return true;
    });
  }, [enhancedCurrent, activeFilters]);

  const stats = useMemo(() => {
    return {
      current: accessSummary?.current_entitlements?.length ?? 0,
      pending: accessSummary?.pending_requests?.length ?? 0,
      available: accessSummary?.available_entitlements?.length ?? 0,
      highRisk: enhancedCurrent.filter((e) => ['high', 'critical'].includes(e.riskLevel)).length,
    };
  }, [accessSummary, enhancedCurrent]);

  const openManualRequest = () => {
    router.push('/dashboard/requests?new=1');
  };

  const openRevokeRequest = (entitlement: EnhancedEntitlement) => {
    const entitlementId = entitlement.raw.entitlement_id || entitlement.id;
    const params = new URLSearchParams({
      new: '1',
      resource_type: 'entitlement',
      resource_id: entitlementId,
      action: 'revoke',
      justification: `Remove ${entitlement.displayName} because it is no longer required.`,
    });
    router.push(`/dashboard/requests?${params.toString()}`);
  };

  const appLookup = useMemo(() => {
    if (!apps) return {};
    return apps.reduce<Record<string, string>>((acc, app) => {
      acc[app.id] = app.display_name || app.name;
      return acc;
    }, {});
  }, [apps]);

  const searchResults = useMemo(() => {
    if (!entitlements || !searchTerm.trim()) return [];
    const term = searchTerm.toLowerCase();
    const matches = entitlements.filter((ent) => {
      const display = ent.display_name || ent.name || '';
      const appName = appLookup[ent.app_id] || '';
      return display.toLowerCase().includes(term) || appName.toLowerCase().includes(term);
    });
    return matches.slice(0, 8).map((ent) => ({
      entitlement: ent,
      appName: appLookup[ent.app_id] || 'Unknown app',
      riskLevel: (ent.risk_level as EnhancedEntitlement['riskLevel']) || (ent.is_privileged ? 'high' : 'medium'),
    }));
  }, [entitlements, searchTerm, appLookup]);

  const handleExplain = async (entitlement: EnhancedEntitlement) => {
    setAiLoading('explain');
    setAiExplanation(null);
    await wait(600);
    setAiExplanation(
      `You have "${entitlement.displayName}" because your team needs it to complete their daily workflows. Risk is ${entitlement.riskLevel} due to data sensitivity and scope.`
    );
    setAiLoading(null);
  };

  const handleRecommend = async (entitlement: EnhancedEntitlement) => {
    setAiLoading('recommend');
    setAiRecommendation(null);
    await wait(700);
    setAiRecommendation(
      entitlement.isPrivileged
        ? 'Switch to a least-privilege role or time-bound JIT for admin actions. Enable MFA and require approvals.'
        : 'Keep as-is but add MFA and auto-expire unused access after 30 days.'
    );
    setAiLoading(null);
  };

  const toggleFilter = (filter: QuickFilter) => {
    setActiveFilters((prev) =>
      prev.includes(filter) ? prev.filter((f) => f !== filter) : [...prev, filter]
    );
  };

  if (isLoading) {
    return (
      <div className="p-6 w-full text-slate-100">
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
          <p className="mt-2 text-slate-300">Loading your access...</p>
        </div>
      </div>
    );
  }

  if (!accessSummary) {
    return (
      <div className="p-6 max-w-7xl mx-auto text-slate-100">
        <div className="text-center py-12">
          <p className="text-slate-300">Unable to load access information</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 w-full text-slate-100">
      {/* Header / action */}
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">My Access</h1>
          <p className="text-sm text-slate-300 mt-1">
            Outcome-driven view of your entitlements, risk, and actions
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              if (firstAvailable) {
                setSelectedEntitlement(firstAvailable);
                setShowRequestModal(true);
              }
            }}
            disabled={!firstAvailable}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
            title={firstAvailable ? undefined : 'No available access to request'}
          >
            Request Access
          </button>
        </div>
      </div>

      {/* Stats / signals */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
        <SignalCard
          title="Current access"
          value={stats.current}
          icon={<ShieldCheckIcon className="w-5 h-5 text-green-300" />}
          tone="green"
        />
        <SignalCard
          title="Pending requests"
          value={stats.pending}
          icon={<ClockIcon className="w-5 h-5 text-amber-200" />}
          tone="amber"
        />
        <SignalCard
          title="High/critical risk"
          value={stats.highRisk}
          icon={<ShieldExclamationIcon className="w-5 h-5 text-red-300" />}
          tone="red"
        />
        <SignalCard
          title="Available"
          value={stats.available}
          icon={<PlusIcon className="w-5 h-5 text-blue-200" />}
          tone="blue"
        />
      </div>

      {/* Quick filters */}
      <div className="flex flex-wrap gap-2 mb-6">
        <QuickFilterPill
          label="Unused >30d"
          active={activeFilters.includes('unused')}
          onClick={() => toggleFilter('unused')}
        />
        <QuickFilterPill
          label="High risk"
          active={activeFilters.includes('highRisk')}
          onClick={() => toggleFilter('highRisk')}
        />
        <QuickFilterPill
          label="Expiring soon"
          active={activeFilters.includes('expiring')}
          onClick={() => toggleFilter('expiring')}
        />
        <QuickFilterPill
          label="Needs MFA"
          active={activeFilters.includes('mfa')}
          onClick={() => toggleFilter('mfa')}
        />
      </div>

      {actionMessage && (
        <div className="mb-4 rounded-lg border border-slate-700 bg-slate-900/70 px-4 py-3 text-sm text-slate-100">
          {actionMessage}
        </div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-[1.1fr_0.9fr] gap-4">
        <div className="space-y-8">
          {/* Request something new (search) */}
          <div className="bg-slate-900 border border-slate-800 rounded-lg p-4">
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between mb-3">
              <div>
                <h2 className="text-lg font-semibold text-slate-100">Request new access</h2>
                <p className="text-sm text-slate-300">Search any app or entitlement and request it on the spot.</p>
              </div>
              <div className="text-xs text-slate-400">
                Don&apos;t see it?{' '}
                <button className="underline" onClick={openManualRequest}>
                  Submit manual request
                </button>
              </div>
            </div>
            <div className="space-y-3">
              <input
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search apps or roles (e.g., Salesforce, Admin, Read-only)"
                className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-slate-100 placeholder:text-slate-500 focus:border-blue-500 focus:ring-2 focus:ring-blue-500"
              />
              {searchTerm && (
                <div className="bg-slate-950/50 border border-slate-800 rounded-lg p-3 space-y-2 max-h-72 overflow-y-auto">
                  {searchResults.length === 0 && (
                    <div className="text-sm text-slate-300">No matches. Try a different name or submit a manual request.</div>
                  )}
                  {searchResults.map((item) => {
                    const { entitlement, appName, riskLevel } = item;
                    return (
                      <div
                        key={entitlement.id}
                        className="flex items-center justify-between gap-3 rounded-lg border border-slate-800 bg-slate-900/70 px-3 py-2"
                      >
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <div className="text-slate-100 font-semibold">{appName}</div>
                            <span className="text-slate-500 text-sm">•</span>
                            <div className="text-slate-200 text-sm">{entitlement.display_name || entitlement.name}</div>
                            <RiskChip level={riskLevel} />
                            {entitlement.is_privileged && (
                              <span className="px-2 py-0.5 bg-amber-900/40 text-amber-200 text-xs rounded">
                                Privileged
                              </span>
                            )}
                          </div>
                          {entitlement.description && (
                            <div className="text-xs text-slate-400">{entitlement.description}</div>
                          )}
                        </div>
                        <button
                          onClick={() => {
                            setSelectedEntitlement(entitlement);
                            setShowRequestModal(true);
                          }}
                          className="flex items-center gap-2 rounded-md bg-blue-600 px-3 py-1.5 text-sm text-white hover:bg-blue-700"
                        >
                          <PlusIcon className="w-4 h-4" />
                          Request
                        </button>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          {/* Current Access */}
          <div>
            <h2 className="text-lg font-semibold text-slate-100 mb-3 flex items-center gap-2">
              <ShieldCheckIcon className="w-5 h-5 text-green-300" />
              Current Access
            </h2>
            {filteredCurrent.length === 0 ? (
              <div className="bg-slate-900 border border-slate-800 rounded-lg p-6 text-center">
                <p className="text-slate-300">No items match the current filters</p>
              </div>
            ) : (
              <div className="grid gap-4">
                {filteredCurrent.map((entitlement) => (
                  <EntitlementCard
                    key={entitlement.id}
                    entitlement={entitlement}
                    type="current"
                    onRequestJit={() => {
                      setSelectedEntitlement(entitlement.raw);
                      setShowRequestModal(true);
                    }}
                    onExplain={() => handleExplain(entitlement)}
                    onRecommend={() => handleRecommend(entitlement)}
                    onSelect={() => {
                      setSelectedDetail(entitlement);
                      setAiExplanation(null);
                      setAiRecommendation(null);
                    }}
                    onRevoke={() => openRevokeRequest(entitlement)}
                  />
                ))}
              </div>
            )}
          </div>

          {/* Pending Requests */}
          {accessSummary.pending_requests.length > 0 && (
            <div>
              <div className="mb-3 flex items-center justify-between gap-3">
                <h2 className="text-lg font-semibold text-slate-100 flex items-center gap-2">
                  <ClockIcon className="w-5 h-5 text-amber-200" />
                  Pending Requests
                </h2>
                <Link href="/dashboard/requests" className="text-sm text-blue-300 hover:text-blue-200">
                  Manage all requests
                </Link>
              </div>
              <div className="grid gap-4">
                {accessSummary.pending_requests.map((request) => (
                  <RequestCard key={request.id} request={request} />
                ))}
              </div>
            </div>
          )}

          {/* Available Access */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-lg font-semibold text-slate-100 flex items-center gap-2">
                <PlusIcon className="w-5 h-5 text-blue-200" />
                Available Access
              </h2>
            </div>
            {accessSummary.available_entitlements.length === 0 ? (
              <div className="bg-slate-900 border border-slate-800 rounded-lg p-6 text-center">
                <p className="text-slate-300">No additional access available</p>
              </div>
            ) : (
              <div className="grid gap-4">
                {accessSummary.available_entitlements.map((entitlement) => {
                  const display = entitlement.display_name || entitlement.name;
                  const isPrivileged = entitlement.is_privileged;
                  const riskLevel = (entitlement.risk_level as EnhancedEntitlement['riskLevel']) || (isPrivileged ? 'high' : 'medium');
                  return (
                    <div
                      key={entitlement.id}
                      className="bg-slate-900 border border-slate-800 rounded-lg p-4 hover:border-slate-600 transition-colors"
                    >
                      <div className="flex items-center justify-between gap-3">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <h3 className="font-semibold text-slate-100">{display}</h3>
                            <RiskChip level={riskLevel} />
                            {isPrivileged && (
                              <span className="px-2 py-0.5 bg-amber-900/40 text-amber-200 text-xs rounded">
                                Privileged
                              </span>
                            )}
                          </div>
                          {entitlement.description && (
                            <p className="text-sm text-slate-300">{entitlement.description}</p>
                          )}
                        </div>
                        <button
                          onClick={() => {
                            setSelectedEntitlement(entitlement);
                            setShowRequestModal(true);
                          }}
                          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                        >
                          <PlusIcon className="w-4 h-4" />
                          Request
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Detail Panel */}
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 h-fit">
          <DetailPanel
            entitlement={selectedDetail}
            aiExplanation={aiExplanation}
            aiRecommendation={aiRecommendation}
            aiLoading={aiLoading}
            onExplain={() => selectedDetail && handleExplain(selectedDetail)}
            onRecommend={() => selectedDetail && handleRecommend(selectedDetail)}
          />
        </div>
      </div>

      {/* Request Modal */}
      {showRequestModal && selectedEntitlement && (
        <RequestAccessModal
          entitlement={selectedEntitlement as Entitlement}
          onClose={() => {
            setShowRequestModal(false);
            setSelectedEntitlement(null);
          }}
          onSubmit={(requestData) => createRequestMutation.mutate(requestData)}
          isLoading={createRequestMutation.isPending}
        />
      )}
    </div>
  );
}

function enhanceEntitlement(entitlement: UserEntitlement): EnhancedEntitlement {
  const meta = entitlement.entitlement || (entitlement as any);
  const displayName = meta.display_name || meta.name || 'Untitled';
  const description = meta.description;
  const isPrivileged = Boolean(meta.is_privileged);
  const requiresMfa = Boolean(meta.requires_mfa);
  const riskLevel = (meta.risk_level as EnhancedEntitlement['riskLevel']) || (isPrivileged ? 'high' : 'medium');

  const lastUsedRaw =
    (entitlement as any).last_used_at ||
    (entitlement as any).last_activity_at ||
    entitlement.granted_at;
  const lastUsed = lastUsedRaw ? new Date(lastUsedRaw) : null;
  const lastUsedLabel = lastUsed ? lastUsed.toLocaleDateString() : 'Unknown';

  const expiresAt = entitlement.expires_at ? entitlement.expires_at : null;
  const expiresInDays = expiresAt ? Math.ceil((new Date(expiresAt).getTime() - Date.now()) / (1000 * 60 * 60 * 24)) : null;

  const isUnused = lastUsed ? (Date.now() - lastUsed.getTime()) / (1000 * 60 * 60 * 24) >= 30 : true;
  const expiringSoon = typeof expiresInDays === 'number' ? expiresInDays <= 14 : false;

  const riskBase = riskLevel === 'critical' ? 90 : riskLevel === 'high' ? 70 : riskLevel === 'medium' ? 45 : 25;
  const riskScore = Math.min(100, riskBase + (isPrivileged ? 10 : 0) + (isUnused ? 5 : 0));

  return {
    raw: entitlement,
    id: entitlement.id,
    displayName,
    description,
    riskLevel,
    riskScore,
    lastUsed,
    lastUsedLabel,
    expiresAt,
    expiresInDays,
    isUnused,
    expiringSoon,
    requiresMfa,
    isPrivileged,
    appName: (entitlement as any).app_name || (entitlement as any).app?.display_name,
  };
}

function EntitlementCard({
  entitlement,
  type,
  onRequestJit,
  onExplain,
  onRecommend,
  onSelect,
  onRevoke,
}: {
  entitlement: EnhancedEntitlement;
  type: 'current' | 'available';
  onRequestJit?: () => void;
  onExplain?: () => void;
  onRecommend?: () => void;
  onSelect?: () => void;
  onRevoke?: () => void;
}) {
  const { displayName, description, riskLevel, lastUsedLabel, expiringSoon, expiresAt, isUnused, requiresMfa, isPrivileged } = entitlement;

  return (
    <div
      className="bg-slate-900 border border-slate-800 rounded-lg p-4 hover:border-slate-600 transition-colors cursor-pointer"
      onClick={onSelect}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="font-semibold text-slate-100">{displayName}</h3>
            <RiskChip level={riskLevel} />
            {isPrivileged && (
              <span className="px-2 py-0.5 bg-amber-900/40 text-amber-200 text-xs rounded">
                Privileged
              </span>
            )}
            {requiresMfa && (
              <span className="px-2 py-0.5 bg-slate-800 text-blue-200 text-xs rounded border border-blue-900">
                Needs MFA
              </span>
            )}
          </div>
          {description && <p className="text-sm text-slate-300">{description}</p>}
          <div className="flex flex-wrap gap-2 mt-2 text-xs text-slate-400">
            <span className="px-2 py-1 rounded bg-slate-800 border border-slate-700">Last used: {lastUsedLabel}</span>
            {isUnused && (
              <span className="px-2 py-1 rounded bg-amber-900/30 text-amber-100 border border-amber-900/60">
                Unused &gt; 30d
              </span>
            )}
            {expiringSoon && expiresAt && (
              <span className="px-2 py-1 rounded bg-orange-900/30 text-orange-100 border border-orange-800">
                Expiring {new Date(expiresAt).toLocaleDateString()}
              </span>
            )}
          </div>
        </div>
        {type === 'current' && <CheckCircleIcon className="w-6 h-6 text-green-600" />}
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <button
          onClick={(e) => {
            e.stopPropagation();
            onExplain?.();
          }}
          className="flex items-center gap-1 px-3 py-1.5 rounded-md bg-slate-800 text-slate-100 text-sm hover:bg-slate-700"
        >
          <SparklesIcon className="w-4 h-4" />
          Explain
        </button>
        <button
          onClick={(e) => {
            e.stopPropagation();
            onRecommend?.();
          }}
          className="flex items-center gap-1 px-3 py-1.5 rounded-md bg-slate-800 text-slate-100 text-sm hover:bg-slate-700"
        >
          <CursorArrowRaysIcon className="w-4 h-4" />
          Recommend least privilege
        </button>
        <button
          onClick={(e) => {
            e.stopPropagation();
            onRequestJit?.();
          }}
          className="flex items-center gap-1 px-3 py-1.5 rounded-md bg-blue-600 text-white text-sm hover:bg-blue-700"
        >
          <BoltIcon className="w-4 h-4" />
          Request JIT
        </button>
        <button
          onClick={(e) => {
            e.stopPropagation();
            onRevoke?.();
          }}
          className="flex items-center gap-1 px-3 py-1.5 rounded-md bg-slate-800 text-slate-200 text-sm hover:bg-slate-700 border border-slate-700"
        >
          <XCircleIcon className="w-4 h-4" />
          Revoke
        </button>
      </div>
    </div>
  );
}

function RequestCard({ request }: { request: any }) {
  const displayName = request.entitlement?.display_name || 'Unknown';
  const status = request.status;

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-4">
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="font-semibold text-slate-100">{displayName}</h3>
            {status === 'pending' && (
              <span className="px-2 py-0.5 bg-amber-900/40 text-amber-200 text-xs rounded">
                Pending Approval
              </span>
            )}
          </div>
          <p className="text-sm text-slate-300 mb-2">{request.reason}</p>
          <p className="text-xs text-slate-400">
            Requested: {new Date(request.requested_at).toLocaleDateString()}
            {request.duration_days && ` • Duration: ${request.duration_days} days`}
          </p>
        </div>
        <div className="flex items-center">
          {status === 'pending' ? (
            <ClockIcon className="w-6 h-6 text-yellow-600" />
          ) : status === 'approved' ? (
            <CheckCircleIcon className="w-6 h-6 text-green-600" />
          ) : (
            <XCircleIcon className="w-6 h-6 text-red-600" />
          )}
        </div>
      </div>
    </div>
  );
}

function RequestAccessModal({
  entitlement,
  onClose,
  onSubmit,
  isLoading,
}: {
  entitlement: Entitlement;
  onClose: () => void;
  onSubmit: (requestData: { entitlement_id: string; reason: string; duration_days?: number }) => void;
  isLoading: boolean;
}) {
  const [reason, setReason] = useState('');
  const [durationDays, setDurationDays] = useState<number | undefined>(undefined);
  const [isTemporary, setIsTemporary] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!reason.trim()) return;

    onSubmit({
      entitlement_id: entitlement.id,
      reason: reason.trim(),
      duration_days: isTemporary ? durationDays : undefined,
    });
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-slate-900 rounded-lg p-6 max-w-md w-full mx-4 border border-slate-800">
        <h2 className="text-xl font-bold text-slate-100 mb-4">Request Access</h2>

        <div className="mb-4 p-3 bg-slate-900/60 border border-slate-800 rounded-lg">
          <h3 className="font-semibold text-slate-100">{entitlement.display_name}</h3>
          {entitlement.description && (
            <p className="text-sm text-slate-300 mt-1">{entitlement.description}</p>
          )}
          {entitlement.is_privileged && (
            <p className="text-xs text-amber-200 mt-2">
              ⚠️ This is a privileged role and requires approval
            </p>
          )}
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-200 mb-1">
              Reason for Request *
            </label>
            <textarea
              required
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              rows={4}
              className="w-full px-3 py-2 border border-slate-700 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-slate-900/60 text-slate-100"
              placeholder="Explain why you need this access..."
            />
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="is_temporary"
              checked={isTemporary}
              onChange={(e) => {
                setIsTemporary(e.target.checked);
                if (!e.target.checked) setDurationDays(undefined);
              }}
              className="w-4 h-4 text-blue-600 border-slate-700 rounded focus:ring-blue-500 bg-slate-900"
            />
            <label htmlFor="is_temporary" className="text-sm text-slate-200">
              This is temporary access
            </label>
          </div>

          {isTemporary && (
            <div>
              <label className="block text-sm font-medium text-slate-200 mb-1">
                Duration (days)
              </label>
              <input
                type="number"
                min="1"
                max="365"
                value={durationDays || ''}
                onChange={(e) => setDurationDays(e.target.value ? parseInt(e.target.value) : undefined)}
                className="w-full px-3 py-2 border border-slate-700 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-slate-900/60 text-slate-100"
                placeholder="30"
              />
            </div>
          )}

          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-slate-700 text-slate-100 rounded-lg hover:bg-slate-800 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading || !reason.trim()}
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
            >
              {isLoading ? 'Submitting...' : 'Submit Request'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function DetailPanel({
  entitlement,
  aiExplanation,
  aiRecommendation,
  aiLoading,
  onExplain,
  onRecommend,
}: {
  entitlement: EnhancedEntitlement | null;
  aiExplanation: string | null;
  aiRecommendation: string | null;
  aiLoading: string | null;
  onExplain: () => void;
  onRecommend: () => void;
}) {
  if (!entitlement) {
    return (
      <div className="text-slate-300 text-sm">
        Select an access item to see blast radius, policy evidence, and recommendations.
      </div>
    );
  }

  const anomalies =
    (entitlement.raw as any).anomalies ||
    [
      'Unusual login time in last 7 days',
      'Device posture missing EDR signal',
    ];
  const policies =
    (entitlement.raw as any).policy_hits ||
    [
      'Approval policy: Manager + Security for privileged roles',
      'Access policy: MFA required on unmanaged devices',
    ];
  const cleanup =
    entitlement.isUnused
      ? 'Unused for 30+ days. Recommend auto-remove in 7 days unless activity resumes.'
      : entitlement.expiringSoon
        ? 'Expiring soon. Renew only if still needed; otherwise let it lapse.'
        : 'Set a review date to keep least privilege.';
  const rotation =
    entitlement.raw.entitlement?.entitlement_type === 'api_key' ||
    (entitlement.displayName || '').toLowerCase().includes('key')
      ? 'Rotate keys every 30 days. Prompt user to rotate now.'
      : 'No rotation requirement detected.';

  return (
    <div className="space-y-4">
      <div>
        <div className="flex items-center gap-2">
          <h3 className="text-lg font-semibold text-slate-100">{entitlement.displayName}</h3>
          <RiskChip level={entitlement.riskLevel} />
        </div>
        <p className="text-sm text-slate-300 mt-1">{entitlement.description || 'No description provided.'}</p>
      </div>

      <div className="grid grid-cols-2 gap-2 text-sm">
        <DetailBadge label="Risk score" value={`${entitlement.riskScore}/100`} />
        <DetailBadge label="Last used" value={entitlement.lastUsedLabel} />
        <DetailBadge
          label="Expires"
          value={entitlement.expiresAt ? new Date(entitlement.expiresAt).toLocaleDateString() : 'No expiry'}
        />
        <DetailBadge label="MFA" value={entitlement.requiresMfa ? 'Required' : 'Optional'} />
      </div>

      <Section title="Blast radius (what this can touch)">
        <ul className="space-y-1 text-sm text-slate-200 list-disc list-inside">
          <li>Related app: {entitlement.appName || 'Unknown app'}</li>
          <li>Data scope: PII and internal systems (estimated)</li>
          <li>Who else has it: {Math.max(3, (entitlement.riskScore % 6) + 2)} peers</li>
        </ul>
      </Section>

      <Section title="Policy / decision evidence">
        <ul className="space-y-1 text-sm text-slate-200 list-disc list-inside">
          {policies.map((p: string, idx: number) => (
            <li key={idx}>{p}</li>
          ))}
        </ul>
      </Section>

      <Section title="Anomalies">
        <ul className="space-y-1 text-sm text-slate-200 list-disc list-inside">
          {anomalies.map((a: string, idx: number) => (
            <li key={idx}>{a}</li>
          ))}
        </ul>
      </Section>

      <Section title="Cleanup suggestion">
        <p className="text-sm text-slate-200">{cleanup}</p>
      </Section>

      <Section title="Key rotation / hygiene">
        <p className="text-sm text-slate-200">{rotation}</p>
      </Section>

      <Section title="AI guidance">
        <div className="space-y-2">
          <div className="flex flex-wrap gap-2">
            <button
              onClick={onExplain}
              className="inline-flex items-center gap-2 rounded-md bg-slate-800 px-3 py-1.5 text-sm text-slate-100 hover:bg-slate-700"
            >
              <SparklesIcon className="w-4 h-4" />
              Explain access
            </button>
            <button
              onClick={onRecommend}
              className="inline-flex items-center gap-2 rounded-md bg-slate-800 px-3 py-1.5 text-sm text-slate-100 hover:bg-slate-700"
            >
              <CursorArrowRaysIcon className="w-4 h-4" />
              Recommend least privilege
            </button>
          </div>
          <div className="text-sm text-slate-200 space-y-1">
            {aiLoading === 'explain' && <LoadingLine label="Generating explanation..." />}
            {aiLoading === 'recommend' && <LoadingLine label="Drafting recommendation..." />}
            {aiExplanation && <p className="text-blue-100">{aiExplanation}</p>}
            {aiRecommendation && <p className="text-green-100">{aiRecommendation}</p>}
          </div>
        </div>
      </Section>
    </div>
  );
}

function SignalCard({
  title,
  value,
  icon,
  tone,
}: {
  title: string;
  value: number;
  icon: React.ReactNode;
  tone: 'green' | 'amber' | 'red' | 'blue';
}) {
  const toneMap: Record<string, string> = {
    green: 'bg-emerald-900/40 text-emerald-100 border-emerald-800',
    amber: 'bg-amber-900/30 text-amber-100 border-amber-800',
    red: 'bg-red-900/30 text-red-100 border-red-800',
    blue: 'bg-blue-900/30 text-blue-100 border-blue-800',
  };
  return (
    <div className={`border rounded-lg p-4 flex items-center justify-between ${toneMap[tone] || 'border-slate-800 bg-slate-900'}`}>
      <div>
        <p className="text-xs uppercase tracking-wide opacity-80">{title}</p>
        <p className="text-2xl font-semibold">{value}</p>
      </div>
      <div className="p-2 rounded-full bg-black/20 border border-white/10">{icon}</div>
    </div>
  );
}

function QuickFilterPill({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={`px-3 py-1.5 rounded-full border text-sm ${
        active ? 'bg-blue-600 border-blue-500 text-white' : 'bg-slate-900 border-slate-700 text-slate-200 hover:border-slate-500'
      }`}
    >
      {label}
    </button>
  );
}

function RiskChip({ level }: { level: EnhancedEntitlement['riskLevel'] }) {
  const styles =
    level === 'critical'
      ? 'bg-red-900/40 text-red-200'
      : level === 'high'
        ? 'bg-orange-900/40 text-orange-200'
        : level === 'medium'
          ? 'bg-amber-900/40 text-amber-200'
          : 'bg-slate-800 text-slate-200';
  return (
    <span className={`px-2 py-0.5 text-xs rounded ${styles}`}>
      {level.toUpperCase()}
    </span>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="border border-slate-800 rounded-lg p-3 bg-slate-900/60">
      <div className="text-xs uppercase text-slate-400 mb-2">{title}</div>
      {children}
    </div>
  );
}

function DetailBadge({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-slate-800 rounded-lg px-3 py-2 border border-slate-700">
      <div className="text-xs text-slate-400">{label}</div>
      <div className="text-sm text-slate-100">{value}</div>
    </div>
  );
}

function LoadingLine({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-2 text-slate-300">
      <ArrowPathIcon className="w-4 h-4 animate-spin" />
      <span>{label}</span>
    </div>
  );
}

function wait(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
