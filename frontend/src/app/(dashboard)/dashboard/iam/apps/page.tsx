/**
 * Apps & Access Profiles Page
 * Manage apps, entitlements, and access profiles
 */

'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import { PlusIcon, Cog6ToothIcon } from '@heroicons/react/24/outline';
import { getApps, getEntitlements, getAccessProfiles, setAppStatus, getPolicies } from '@/lib/api/iam-portal';
import type { App, Entitlement, AccessProfile } from '@/lib/api/iam-portal';
import { buildEntityGraphHref } from '@/lib/security/graph-context';

export default function AppsPage() {
  const [activeTab, setActiveTab] = useState<'apps' | 'profiles'>('apps');
  
  // Fetch data
  const { data: apps = [], isLoading: appsLoading } = useQuery({
    queryKey: ['iam-apps'],
    queryFn: getApps,
  });
  
  const { data: entitlements = [], isLoading: entitlementsLoading } = useQuery({
    queryKey: ['iam-entitlements'],
    queryFn: () => getEntitlements(),
  });
  
  const { data: profiles = [], isLoading: profilesLoading } = useQuery({
    queryKey: ['iam-access-profiles'],
    queryFn: getAccessProfiles,
  });
  
  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-text-main">People & Access — Applications</h1>
          <p className="text-sm text-text-muted dark:text-text-muted mt-1">Manage applications, roles, and access profiles</p>
        </div>
        <div className="flex items-center gap-3">
          <Link
            href="/dashboard/iam/apps/catalog"
            className="inline-flex items-center px-3 py-2 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700"
          >
            <PlusIcon className="w-4 h-4 mr-1" />
            New Application
          </Link>
          <Link
            href="/dashboard/iam/apps/catalog"
            className="text-sm text-blue-600 hover:text-blue-700"
          >
            Browse Catalog
          </Link>
        </div>
      </div>
      
      {/* Tabs */}
      <div className="mb-6 border-b border-surface-card-border">
        <nav className="flex gap-6">
          <button
            onClick={() => setActiveTab('apps')}
            className={`pb-3 px-1 border-b-2 font-medium text-sm transition-colors ${
              activeTab === 'apps'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-text-muted hover:text-text-muted'
            }`}
          >
            Apps
          </button>
          <button
            onClick={() => setActiveTab('profiles')}
            className={`pb-3 px-1 border-b-2 font-medium text-sm transition-colors ${
              activeTab === 'profiles'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-text-muted hover:text-text-muted'
            }`}
          >
            Access Profiles
          </button>
        </nav>
      </div>
      
      {/* Content */}
      {activeTab === 'apps' ? (
        <AppsTab apps={apps} entitlements={entitlements} isLoading={appsLoading || entitlementsLoading} />
      ) : (
        <AccessProfilesTab profiles={profiles} isLoading={profilesLoading} />
      )}
    </div>
  );
}

function AppsTab({ apps, entitlements, isLoading }: { apps: App[]; entitlements: Entitlement[]; isLoading: boolean }) {
  if (isLoading) {
    return (
      <div className="text-center py-12">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <p className="mt-2 text-text-muted">Loading apps...</p>
      </div>
    );
  }
  
  return (
    <div className="space-y-6">
      {apps.length === 0 ? (
        <div className="text-center py-12 bg-surface-hover rounded-lg">
          <p className="text-text-muted">No apps configured yet</p>
        </div>
      ) : (
        apps.map((app) => (
          <AppCard key={app.id} app={app} entitlements={entitlements.filter(e => e.app_id === app.id)} />
        ))
      )}
    </div>
  );
}

function AppCard({ app, entitlements }: { app: App; entitlements: Entitlement[] }) {
  const [activeTab, setActiveTab] = useState<'roles' | 'policies'>('roles');
  const hasRedirect = Array.isArray((app as any).config?.redirect_uris)
    ? ((app as any).config?.redirect_uris || []).length > 0
    : Boolean((app as any).config?.redirect_uris || (app as any).config?.redirect_uri);
  const hasACS = Boolean((app as any).config?.acs_url);
  const needsAttention =
    (!app.is_active && (!hasRedirect && !hasACS)) ||
    entitlements.length === 0;
  const queryClient = useQueryClient();
  const statusMutation = useMutation({
    mutationFn: (next: boolean) => setAppStatus(app.id, next),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['iam-apps'] }),
  });
  const graphHref = buildEntityGraphHref({
    entityType: 'resource',
    entityId: app.id,
    entityLabel: app.display_name,
    entityDomain: 'application',
    title: `${app.display_name} access graph`,
    severity: app.is_active ? 'medium' : 'low',
    summary: app.description || `${app.protocol || 'Application'} access and entitlement relationships.`,
    entitlementsCount: entitlements.length,
    sourceLabel: 'Applications',
    sourceHref: `/dashboard/iam/apps/${app.id}/edit`,
  });
  
  return (
    <div className="bg-surface-card border border-surface-card-border rounded-lg p-6">
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-4">
          {app.icon_url ? (
            <img src={app.icon_url} alt={app.display_name} className="w-12 h-12 rounded" />
          ) : (
            <div className="w-12 h-12 bg-blue-100 rounded flex items-center justify-center">
              <Cog6ToothIcon className="w-6 h-6 text-blue-600" />
            </div>
          )}
          <div>
            <h3 className="text-lg font-semibold text-text-main">{app.display_name}</h3>
            <p className="text-sm text-text-muted">{app.description || app.app_type}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Link
            href={graphHref}
            className="text-[11px] px-2 py-1 rounded border border-surface-card-border hover:bg-surface-hover"
          >
            View Graph
          </Link>
          <span className={`px-3 py-1 rounded-full text-xs font-medium ${
            app.is_active ? 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-200' : 'bg-bg-alt text-text-main dark:bg-slate-800 dark:text-slate-200'
          }`}>
            {app.is_active ? 'Active' : 'Draft'}
          </span>
          <span className="text-[11px] text-text-muted px-2 py-1 rounded border border-surface-card-border">
            {app.protocol || 'unknown'}
          </span>
          {needsAttention && (
            <span className="text-[11px] px-2 py-1 rounded bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200">
              Needs Attention
            </span>
          )}
          <button
            onClick={() => {
              if (!app.is_active && needsAttention) {
                alert('Add at least one entitlement and a redirect/ACS URL before activating.');
                return;
              }
              statusMutation.mutate(!app.is_active);
            }}
            className="text-[11px] px-2 py-1 rounded border border-surface-card-border hover:bg-surface-hover"
            disabled={statusMutation.isPending || (!app.is_active && needsAttention)}
          >
            {statusMutation.isPending ? 'Working...' : app.is_active ? 'Deactivate' : 'Activate'}
          </button>
        </div>
      </div>
      
      {/* Tabs */}
      <div className="mb-4 border-b border-surface-card-border">
        <nav className="flex gap-6">
          <button
            onClick={() => setActiveTab('roles')}
            className={`pb-2 px-1 border-b-2 font-medium text-sm transition-colors ${
              activeTab === 'roles'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-text-muted hover:text-text-muted'
            }`}
          >
            Roles
          </button>
          <button
            onClick={() => setActiveTab('policies')}
            className={`pb-2 px-1 border-b-2 font-medium text-sm transition-colors ${
              activeTab === 'policies'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-text-muted hover:text-text-muted'
            }`}
          >
            Access Rules
          </button>
          <Link
            href={`/dashboard/iam/apps/${app.id}/edit`}
            className="ml-auto text-sm text-blue-600 hover:text-blue-700"
          >
            Manage
          </Link>
        </nav>
      </div>
      
      {/* Tab Content */}
      {activeTab === 'roles' ? (
        <AppRolesTab entitlements={entitlements} />
      ) : (
        <AppPoliciesTab appId={app.id} appName={app.display_name} />
      )}
    </div>
  );
}

function AppRolesTab({ entitlements }: { entitlements: Entitlement[] }) {
  return (
    <div>
      <h4 className="text-sm font-medium text-text-muted mb-3">Available Roles</h4>
      {entitlements.length === 0 ? (
        <p className="text-sm text-text-muted">No roles configured for this app</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {entitlements.map((entitlement) => (
            <div
              key={entitlement.id}
              className="p-3 bg-surface-hover rounded-lg border border-surface-card-border"
            >
              <div className="flex items-center justify-between mb-1">
                <span className="font-medium text-text-main text-sm">{entitlement.display_name}</span>
                {entitlement.is_privileged && (
                  <span className="px-2 py-0.5 bg-yellow-100 text-yellow-800 text-xs rounded">
                    Privileged
                  </span>
                )}
              </div>
              {entitlement.description && (
                <p className="text-xs text-text-muted mt-1">{entitlement.description}</p>
              )}
              <div className="flex items-center gap-2 mt-2">
                <span className={`text-xs px-2 py-0.5 rounded ${
                  entitlement.risk_level === 'critical' ? 'bg-red-100 text-red-800' :
                  entitlement.risk_level === 'high' ? 'bg-orange-100 text-orange-800' :
                  entitlement.risk_level === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                  'bg-bg-alt text-text-main'
                }`}>
                  {entitlement.risk_level.toUpperCase()}
                </span>
                {entitlement.requires_mfa && (
                  <span className="text-xs text-blue-600">MFA Required</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function AppPoliciesTab({ appId, appName }: { appId: string; appName: string }) {
  const { data: policies = [], isLoading } = useQuery({
    queryKey: ['iam-policies', 'app', appId],
    queryFn: () => getPolicies('access', 'app', appId),
  });
  
  if (isLoading) {
    return (
      <div className="text-center py-8">
        <div className="inline-block animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
        <p className="mt-2 text-sm text-text-muted">Loading policies...</p>
      </div>
    );
  }
  
  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h4 className="text-sm font-medium text-text-muted">Access Rules for {appName}</h4>
          <p className="text-xs text-text-muted mt-1">
            Define who can access this app and under what conditions
          </p>
        </div>
        <button
          onClick={() => {
            // TODO: Open policy editor for this app
            window.location.href = `/dashboard/iam/policies?app=${appId}&type=access`;
          }}
          className="flex items-center gap-2 px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          <PlusIcon className="w-4 h-4" />
          Add Rule
        </button>
      </div>
      
      {policies.length === 0 ? (
        <div className="text-center py-8 bg-surface-hover rounded-lg border border-surface-card-border">
          <p className="text-sm text-text-muted mb-2">No access rules configured for this app</p>
          <p className="text-xs text-text-muted">
            Click "Add Rule" to define who can access {appName}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {policies.map((policy) => (
            <div
              key={policy.id}
              className="p-4 bg-surface-hover rounded-lg border border-surface-card-border hover:border-blue-300 transition-colors"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <h5 className="font-medium text-text-main text-sm">{policy.display_name}</h5>
                    {policy.is_active ? (
                      <span className="px-2 py-0.5 bg-green-100 text-green-800 text-xs rounded">
                        Active
                      </span>
                    ) : (
                      <span className="px-2 py-0.5 bg-bg-alt text-text-main text-xs rounded">
                        Inactive
                      </span>
                    )}
                  </div>
                  {policy.description && (
                    <p className="text-xs text-text-muted mt-1">{policy.description}</p>
                  )}
                </div>
                <button
                  onClick={() => {
                    window.location.href = `/dashboard/iam/policies?policy=${policy.id}`;
                  }}
                  className="text-xs text-blue-600 hover:text-blue-800"
                >
                  Edit
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function AccessProfilesTab({ profiles, isLoading }: { profiles: AccessProfile[]; isLoading: boolean }) {
  if (isLoading) {
    return (
      <div className="text-center py-12">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <p className="mt-2 text-text-muted">Loading access profiles...</p>
      </div>
    );
  }
  
  return (
    <div className="space-y-4">
      {profiles.length === 0 ? (
        <div className="text-center py-12 bg-surface-hover rounded-lg">
          <p className="text-text-muted">No access profiles configured yet</p>
        </div>
      ) : (
        profiles.map((profile) => (
          <AccessProfileCard key={profile.id} profile={profile} />
        ))
      )}
    </div>
  );
}

function AccessProfileCard({ profile }: { profile: AccessProfile }) {
  return (
    <div className="bg-surface-card border border-surface-card-border rounded-lg p-6">
      <div className="flex items-start justify-between mb-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h3 className="text-lg font-semibold text-text-main">{profile.display_name}</h3>
            {profile.is_default && (
              <span className="px-2 py-0.5 bg-blue-100 text-blue-800 text-xs rounded">
                Default
              </span>
            )}
            {profile.is_system && (
              <span className="px-2 py-0.5 bg-bg-alt text-text-main text-xs rounded">
                System
              </span>
            )}
          </div>
          {profile.description && (
            <p className="text-sm text-text-muted">{profile.description}</p>
          )}
        </div>
      </div>
      
      {/* Entitlements */}
      <div className="mt-4">
        <h4 className="text-sm font-medium text-text-muted mb-3">
          Entitlements ({profile.entitlements.length})
        </h4>
        {profile.entitlements.length === 0 ? (
          <p className="text-sm text-text-muted">No entitlements assigned</p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {profile.entitlements.map((entitlement) => (
              <span
                key={entitlement.id}
                className="px-3 py-1 bg-bg-alt text-text-muted text-sm rounded"
              >
                {entitlement.display_name}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
