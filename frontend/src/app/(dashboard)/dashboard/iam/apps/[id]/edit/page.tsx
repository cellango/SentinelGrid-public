'use client';

import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import Breadcrumbs from '@/components/ui/Breadcrumbs';
import { getApp, getEntitlements, listAppAssignments, addAppAssignment, removeAppAssignment, setAppStatus } from '@/lib/api/iam-portal';
import { useState } from 'react';
import { Cog6ToothIcon } from '@heroicons/react/24/outline';
import AppAssignments from '@/components/iam/AppAssignments';
import { buildEntityGraphHref } from '@/lib/security/graph-context';

export default function AppEditPage() {
  const params = useParams();
  const router = useRouter();
  const appId = params.id as string;
  const { data: app, isLoading } = useQuery({
    queryKey: ['iam-app', appId],
    queryFn: () => getApp(appId),
    enabled: !!appId,
  });
  const { data: entitlements = [] } = useQuery({
    queryKey: ['iam-app-entitlements', appId],
    queryFn: () => getEntitlements(appId),
    enabled: !!appId,
  });
  const [activeTab, setActiveTab] = useState<'overview' | 'entitlements' | 'assignments'>('overview');
  const hasRedirect = Array.isArray((app as any)?.config?.redirect_uris)
    ? ((app as any)?.config?.redirect_uris || []).length > 0
    : Boolean((app as any)?.config?.redirect_uris || (app as any)?.config?.redirect_uri);
  const hasACS = Boolean((app as any)?.config?.acs_url);
  const needsAttention = (!app?.is_active && (!hasRedirect && !hasACS)) || (entitlements.length === 0);
  const graphHref = app
    ? buildEntityGraphHref({
        entityType: 'resource',
        entityId: app.id,
        entityLabel: app.display_name,
        entityDomain: 'application',
        title: `${app.display_name} access graph`,
        severity: app.is_active ? 'medium' : 'low',
        summary: app.description || `${app.protocol || 'Application'} access and entitlement relationships.`,
        entitlementsCount: entitlements.length,
        sourceLabel: 'Application details',
        sourceHref: `/dashboard/iam/apps/${app.id}/edit`,
      })
    : '/dashboard/security-graph';

  if (isLoading) {
    return (
      <div className="p-6">
        <div className="text-text-muted">Loading application...</div>
      </div>
    );
  }

  if (!app) {
    return (
      <div className="p-6">
        <div className="text-red-600">Application not found</div>
        <button onClick={() => router.back()} className="text-blue-600 hover:text-blue-700 mt-2 text-sm">
          Go back
        </button>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <Breadcrumbs />
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-text-main">{app.display_name}</h1>
          <p className="text-sm text-text-muted dark:text-text-muted">{app.description || app.app_type}</p>
          <div className="flex items-center gap-2 mt-2 text-xs text-text-muted">
            <span className="px-2 py-1 rounded border border-surface-card-border">{app.protocol || 'unknown'}</span>
            <span className="px-2 py-1 rounded border border-surface-card-border">
              {app.is_active ? 'Active' : 'Draft'}
            </span>
            {needsAttention && (
              <span className="px-2 py-1 rounded bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200">
                Needs Attention: add redirect/ACS and entitlements
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Link
            href={graphHref}
            className="px-3 py-1 text-sm border border-border rounded hover:bg-surface-hover"
          >
            View Graph
          </Link>
          <button
            onClick={async () => {
              if (!app.is_active) return;
              await setAppStatus(appId, false);
              window.location.reload();
            }}
            className="px-3 py-1 text-sm border border-border rounded hover:bg-surface-hover"
          >
            Deactivate
          </button>
          <button
            onClick={async () => {
              if (needsAttention) {
                alert('Add at least one entitlement and a redirect/ACS URL before activating.');
                return;
              }
              await setAppStatus(appId, true);
              window.location.reload();
            }}
            className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Activate
          </button>
        </div>
        <Link href="/dashboard/iam/apps" className="text-sm text-blue-600 hover:text-blue-700">
          ← Back to Applications
        </Link>
      </div>

      <div className="border-b border-surface-card-border">
        <nav className="flex gap-6">
          {[
            { id: 'overview', label: 'Overview' },
            { id: 'entitlements', label: 'Entitlements' },
            { id: 'assignments', label: 'Assignments' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as typeof activeTab)}
              className={`pb-3 px-1 border-b-2 font-medium text-sm transition-colors ${
                activeTab === tab.id ? 'border-blue-600 text-blue-600' : 'border-transparent text-text-muted hover:text-text-muted'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {activeTab === 'overview' && (
        <div className="bg-surface-card border border-surface-card-border rounded-lg p-6 space-y-4">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-blue-100 rounded flex items-center justify-center">
              <Cog6ToothIcon className="w-6 h-6 text-blue-600" />
            </div>
            <div className="text-sm text-text-muted dark:text-text-muted">
              <div>App ID: <span className="font-mono">{app.id}</span></div>
              {app.client_id && (
                <div className="mt-1">Client ID: <span className="font-mono">{app.client_id}</span></div>
              )}
              {app.issuer && (
                <div className="mt-1">Issuer: <span className="font-mono">{app.issuer}</span></div>
              )}
              {app.config && (
                <div className="mt-2 text-xs text-text-muted dark:text-text-muted">
                  Config saved. Edit assignments and entitlements below.
                </div>
              )}
            </div>
          </div>
          <div className="flex flex-wrap gap-3 text-sm">
            <div className="flex items-center gap-2">
              <span className="text-text-muted">Download:</span>
              <button
                onClick={() => {
                  const blob = new Blob(
                    [JSON.stringify({ client_id: app.client_id, issuer: app.issuer, protocol: app.protocol, config: app.config }, null, 2)],
                    { type: 'application/json' }
                  );
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = url;
                  a.download = `${app.display_name || 'app'}-proxy-config.json`;
                  a.click();
                  URL.revokeObjectURL(url);
                }}
                className="px-3 py-1.5 border border-border rounded-lg hover:bg-surface-hover"
              >
                Auth Proxy Config (JSON)
              </button>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'entitlements' && (
        <div className="bg-surface-card border border-surface-card-border rounded-lg p-6 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-text-main">Entitlements</h3>
            <span className="text-xs text-text-muted dark:text-text-muted">{entitlements.length} roles</span>
          </div>
          {entitlements.length === 0 ? (
            <p className="text-sm text-text-muted dark:text-text-muted">No entitlements defined yet.</p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {entitlements.map((ent) => (
                <div key={ent.id} className="p-3 border border-surface-card-border rounded">
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-medium text-sm text-text-main">{ent.display_name}</span>
                    {ent.is_privileged && (
                      <span className="text-[11px] px-2 py-0.5 rounded bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200">
                        Privileged
                      </span>
                    )}
                  </div>
                  {ent.description && <p className="text-xs text-text-muted dark:text-text-muted">{ent.description}</p>}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === 'assignments' && (
        <div className="bg-surface-card border border-surface-card-border rounded-lg p-6">
          <h3 className="text-lg font-semibold text-text-main mb-2">Assignments</h3>
          <AppAssignments
            appId={appId}
            entitlements={entitlements.map((e) => ({ id: e.id, display_name: e.display_name }))}
            listAssignments={listAppAssignments}
            addAssignment={addAppAssignment}
            removeAssignment={removeAppAssignment}
          />
        </div>
      )}
    </div>
  );
}
