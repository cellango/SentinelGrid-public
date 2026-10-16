/**
 * Identity Providers (Tenant) - federated auth via external IdPs.
 * Supports Microsoft/Google quick connects plus generic OIDC/SAML via gateway.
 */

'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '@/lib/providers/AuthProvider';
import {
  BuildingOfficeIcon,
  GlobeAltIcon,
  PlusIcon,
  TrashIcon,
  CheckCircleIcon,
  ShieldCheckIcon,
  LinkIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline';
import { buildEntityGraphHref } from '@/lib/security/graph-context';

type IdPProvider = {
  alias: string;
  provider_id: string;
  display_name: string;
  provider_type: string;
  enabled: boolean;
};

type GatewayEndpoints = {
  acs_url: string;
  saml_metadata_url: string;
  oidc_authorize_url: string;
  oidc_callback_url: string;
  oidc_logout_url: string;
  tenant_param: string;
};

type OIDCRequest = {
  display_name: string;
  discovery_url: string;
  client_id: string;
  client_secret: string;
  scopes: string[];
  allowed_domains: string[];
  default_role?: string;
  claim_mappings: { claim: string; to: string }[];
  group_role_mappings: { group: string; role: string }[];
};

type SAMLRequest = {
  display_name: string;
  metadata_url: string;
  authn_contexts: string[];
  allowed_domains: string[];
  default_role?: string;
  claim_mappings: { claim: string; to: string }[];
  group_role_mappings: { group: string; role: string }[];
};

async function getIdPProviders(): Promise<IdPProvider[]> {
  const response = await fetch(`/api/v1/idp/providers`, {
    credentials: 'include',
  });
  return response.json();
}

async function getGatewayEndpoints(): Promise<GatewayEndpoints> {
  const response = await fetch(`/api/v1/idp/gateway/endpoints`, {
    credentials: 'include',
  });
  return response.json();
}

async function connectMicrosoft(
  data: {
    tenant_id: string;
    client_id: string;
    client_secret: string;
    sync_users: boolean;
    sync_groups: boolean;
  }
) {
  const response = await fetch(`/api/v1/idp/microsoft/connect`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include',
    body: JSON.stringify(data),
  });
  return response.json();
}

async function connectGoogle(
  data: {
    domain: string;
    client_id: string;
    client_secret: string;
    sync_users: boolean;
    sync_groups: boolean;
  }
) {
  const response = await fetch(`/api/v1/idp/google/connect`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include',
    body: JSON.stringify(data),
  });
  return response.json();
}

async function createOidc(data: OIDCRequest) {
  const response = await fetch(`/api/v1/idp/oidc`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include',
    body: JSON.stringify(data),
  });
  return response.json();
}

async function createSaml(data: SAMLRequest) {
  const response = await fetch(`/api/v1/idp/saml`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include',
    body: JSON.stringify(data),
  });
  return response.json();
}

async function testOidc(discovery_url: string, client_id?: string, client_secret?: string) {
  const response = await fetch(`/api/v1/idp/test/oidc`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ discovery_url, client_id, client_secret }),
  });
  return response.json();
}

async function testSaml(metadata_url: string) {
  const response = await fetch(`/api/v1/idp/test/saml`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ metadata_url }),
  });
  return response.json();
}

async function disconnectIdP(alias: string): Promise<void> {
  await fetch(`/api/v1/idp/providers/${alias}`, {
    method: 'DELETE',
    credentials: 'include',
  });
}

export default function IdentityProvidersPage() {
  const { isAuthenticated } = useAuth();
  const queryClient = useQueryClient();
  const [showMicrosoftModal, setShowMicrosoftModal] = useState(false);
  const [showGoogleModal, setShowGoogleModal] = useState(false);
  const [showOidcModal, setShowOidcModal] = useState(false);
  const [showSamlModal, setShowSamlModal] = useState(false);

  const { data: providers = [], isLoading } = useQuery({
    queryKey: ['idp-providers'],
    queryFn: () => getIdPProviders(),
    enabled: isAuthenticated,
  });

  const { data: gateway } = useQuery({
    queryKey: ['idp-gateway-endpoints'],
    queryFn: () => getGatewayEndpoints(),
    enabled: isAuthenticated,
  });

  const connectMicrosoftMutation = useMutation({
    mutationFn: (data: Parameters<typeof connectMicrosoft>[0]) =>
      connectMicrosoft(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['idp-providers'] });
      setShowMicrosoftModal(false);
    },
  });

  const connectGoogleMutation = useMutation({
    mutationFn: (data: Parameters<typeof connectGoogle>[0]) =>
      connectGoogle(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['idp-providers'] });
      setShowGoogleModal(false);
    },
  });

  const createOidcMutation = useMutation({
    mutationFn: (data: OIDCRequest) => createOidc(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['idp-providers'] });
      setShowOidcModal(false);
    },
  });

  const createSamlMutation = useMutation({
    mutationFn: (data: SAMLRequest) => createSaml(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['idp-providers'] });
      setShowSamlModal(false);
    },
  });

  const disconnectMutation = useMutation({
    mutationFn: (alias: string) => disconnectIdP(alias),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['idp-providers'] });
    },
  });

  if (isLoading) {
    return (
      <div className="p-6 max-w-7xl mx-auto">
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <p className="mt-2 text-text-muted">Loading identity providers...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-main">Identity Providers</h1>
          <p className="text-sm text-text-muted mt-1">
            Connect external identity providers for federated authentication
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setShowOidcModal(true)}
            className="inline-flex items-center gap-2 px-3 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
          >
            <LinkIcon className="w-4 h-4" />
            Add OIDC
          </button>
          <button
            onClick={() => setShowSamlModal(true)}
            className="inline-flex items-center gap-2 px-3 py-2 text-sm bg-cyan-600 text-white rounded-lg hover:bg-cyan-700"
          >
            <ShieldCheckIcon className="w-4 h-4" />
            Add SAML
          </button>
        </div>
      </div>

      {/* Gateway endpoints */}
      {gateway && (
        <div className="mb-6 bg-surface-card border border-surface-card-border rounded-lg p-4">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h2 className="text-lg font-semibold text-text-main">Gateway endpoints</h2>
              <p className="text-sm text-text-muted">Share these with customer IdPs.</p>
            </div>
          </div>
          <div className="grid md:grid-cols-2 gap-3 text-sm">
            <CopyRow label="SAML Metadata" value={gateway.saml_metadata_url} />
            <CopyRow label="SAML ACS" value={gateway.acs_url} />
            <CopyRow label="OIDC Authorize" value={gateway.oidc_authorize_url} />
            <CopyRow label="OIDC Callback" value={gateway.oidc_callback_url} />
          </div>
        </div>
      )}

      {/* Connected Providers */}
      {providers.length > 0 && (
        <div className="mb-6">
          <h2 className="text-lg font-semibold text-text-main mb-4">Connected Providers</h2>
          <div className="space-y-4">
            {providers.map((provider) => (
              (() => {
                const graphHref = buildEntityGraphHref({
                  entityType: 'resource',
                  entityId: provider.alias,
                  entityLabel: provider.display_name,
                  entityDomain: 'identity',
                  title: `${provider.display_name} federation graph`,
                  severity: provider.enabled ? 'medium' : 'low',
                  summary: `${provider.provider_type.toUpperCase()} federation relationships and blast radius.`,
                  sourceLabel: 'Identity Providers',
                  sourceHref: '/dashboard/iam/identity-providers',
                });

                return (
              <div
                key={provider.alias}
                className="bg-surface-card border border-surface-card-border rounded-lg p-4 flex items-center justify-between"
              >
                <div className="flex items-center gap-4">
                  {provider.provider_type === 'microsoft' ? (
                    <BuildingOfficeIcon className="w-8 h-8 text-blue-600" />
                  ) : provider.provider_type === 'google' ? (
                    <GlobeAltIcon className="w-8 h-8 text-green-600" />
                  ) : provider.provider_type === 'saml' ? (
                    <ShieldCheckIcon className="w-8 h-8 text-cyan-600" />
                  ) : (
                    <LinkIcon className="w-8 h-8 text-indigo-600" />
                  )}
                  <div>
                    <h3 className="font-semibold text-text-main">{provider.display_name}</h3>
                    <p className="text-sm text-text-muted">
                      {provider.provider_type === 'microsoft'
                        ? 'Microsoft 365'
                        : provider.provider_type === 'google'
                          ? 'Google Workspace'
                          : provider.provider_type === 'saml'
                            ? 'SAML'
                            : 'OIDC'}
                    </p>
                  </div>
                  {provider.enabled && (
                    <span className="px-2 py-1 bg-green-100 text-green-700 text-xs rounded">
                      Active
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <Link
                    href={graphHref}
                    className="px-3 py-2 text-sm text-text-main border border-surface-card-border rounded-lg hover:bg-surface-hover transition-colors"
                  >
                    View Graph
                  </Link>
                  <button
                    onClick={() => {
                      if (confirm(`Disconnect ${provider.display_name}?`)) {
                        disconnectMutation.mutate(provider.alias);
                      }
                    }}
                    className="px-4 py-2 text-sm text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                  >
                    <TrashIcon className="w-5 h-5" />
                  </button>
                </div>
              </div>
                );
              })()
            ))}
          </div>
        </div>
      )}

      {/* Available Providers */}
      <div>
        <h2 className="text-lg font-semibold text-text-main mb-4">Available Providers</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Microsoft 365 */}
          <div className="bg-surface-card border border-surface-card-border rounded-lg p-6">
            <div className="flex items-center gap-4 mb-4">
              <BuildingOfficeIcon className="w-12 h-12 text-blue-600" />
              <div>
                <h3 className="font-semibold text-text-main">Microsoft 365</h3>
                <p className="text-sm text-text-muted">Azure AD integration</p>
              </div>
            </div>
            <p className="text-sm text-text-muted mb-4">
              Connect Microsoft 365 to allow users to sign in with their Azure AD credentials.
            </p>
            <button
              onClick={() => setShowMicrosoftModal(true)}
              className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              Connect Microsoft 365
            </button>
          </div>

          {/* Google Workspace */}
          <div className="bg-surface-card border border-surface-card-border rounded-lg p-6">
            <div className="flex items-center gap-4 mb-4">
              <GlobeAltIcon className="w-12 h-12 text-green-600" />
              <div>
                <h3 className="font-semibold text-text-main">Google Workspace</h3>
                <p className="text-sm text-text-muted">Google OAuth integration</p>
              </div>
            </div>
            <p className="text-sm text-text-muted mb-4">
              Connect Google Workspace to allow users to sign in with their Google accounts.
            </p>
            <button
              onClick={() => setShowGoogleModal(true)}
              className="w-full px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
            >
              Connect Google Workspace
            </button>
          </div>
        </div>
      </div>

      {/* Microsoft Connection Modal */}
      {showMicrosoftModal && (
        <MicrosoftConnectModal
          onClose={() => setShowMicrosoftModal(false)}
          onConnect={(data) => connectMicrosoftMutation.mutate(data)}
          isLoading={connectMicrosoftMutation.isPending}
        />
      )}

      {/* Google Connection Modal */}
      {showGoogleModal && (
        <GoogleConnectModal
          onClose={() => setShowGoogleModal(false)}
          onConnect={(data) => connectGoogleMutation.mutate(data)}
          isLoading={connectGoogleMutation.isPending}
        />
      )}

      {/* OIDC Modal */}
      {showOidcModal && (
        <OIDCModal
          onClose={() => setShowOidcModal(false)}
          onCreate={(data) => createOidcMutation.mutate(data)}
          isLoading={createOidcMutation.isPending}
        />
      )}

      {/* SAML Modal */}
      {showSamlModal && (
        <SAMLModal
          onClose={() => setShowSamlModal(false)}
          onCreate={(data) => createSamlMutation.mutate(data)}
          isLoading={createSamlMutation.isPending}
        />
      )}
    </div>
  );
}

function CopyRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3 bg-surface-hover border border-surface-card-border rounded-md px-3 py-2">
      <div>
        <p className="text-xs text-text-muted">{label}</p>
        <p className="text-text-main break-all text-sm">{value}</p>
      </div>
      <button
        onClick={() => navigator.clipboard.writeText(value)}
        className="px-2 py-1 text-xs bg-surface-card border border-border rounded hover:bg-bg-alt"
      >
        Copy
      </button>
    </div>
  );
}

// Microsoft Connect Modal Component
function MicrosoftConnectModal({
  onClose,
  onConnect,
  isLoading,
}: {
  onClose: () => void;
  onConnect: (data: Parameters<typeof connectMicrosoft>[0]) => void;
  isLoading: boolean;
}) {
  const [formData, setFormData] = useState({
    tenant_id: '',
    client_id: '',
    client_secret: '',
    sync_users: true,
    sync_groups: false,
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onConnect(formData);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-surface-card rounded-lg p-6 max-w-md w-full mx-4">
        <h2 className="text-xl font-bold text-text-main mb-4">Connect Microsoft 365</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-text-muted mb-1">
              Azure AD Tenant ID *
            </label>
            <input
              type="text"
              required
              value={formData.tenant_id}
              onChange={(e) => setFormData({ ...formData, tenant_id: e.target.value })}
              className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-text-muted mb-1">
              Client ID *
            </label>
            <input
              type="text"
              required
              value={formData.client_id}
              onChange={(e) => setFormData({ ...formData, client_id: e.target.value })}
              className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-text-muted mb-1">
              Client Secret *
            </label>
            <input
              type="password"
              required
              value={formData.client_secret}
              onChange={(e) => setFormData({ ...formData, client_secret: e.target.value })}
              className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          <div className="space-y-2">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={formData.sync_users}
                onChange={(e) => setFormData({ ...formData, sync_users: e.target.checked })}
                className="w-4 h-4 text-blue-600 border-border rounded focus:ring-blue-500"
              />
              <span className="text-sm text-text-muted">Sync users from Azure AD</span>
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={formData.sync_groups}
                onChange={(e) => setFormData({ ...formData, sync_groups: e.target.checked })}
                className="w-4 h-4 text-blue-600 border-border rounded focus:ring-blue-500"
              />
              <span className="text-sm text-text-muted">Sync groups from Azure AD</span>
            </label>
          </div>
          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-border text-text-muted rounded-lg hover:bg-surface-hover transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
            >
              {isLoading ? 'Connecting...' : 'Connect'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// Google Connect Modal Component
function GoogleConnectModal({
  onClose,
  onConnect,
  isLoading,
}: {
  onClose: () => void;
  onConnect: (data: Parameters<typeof connectGoogle>[0]) => void;
  isLoading: boolean;
}) {
  const [formData, setFormData] = useState({
    domain: '',
    client_id: '',
    client_secret: '',
    sync_users: true,
    sync_groups: false,
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onConnect(formData);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-surface-card rounded-lg p-6 max-w-md w-full mx-4">
        <h2 className="text-xl font-bold text-text-main mb-4">Connect Google Workspace</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-text-muted mb-1">
              Google Workspace Domain *
            </label>
            <input
              type="text"
              required
              value={formData.domain}
              onChange={(e) => setFormData({ ...formData, domain: e.target.value })}
              className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
              placeholder="example.com"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-text-muted mb-1">
              OAuth Client ID *
            </label>
            <input
              type="text"
              required
              value={formData.client_id}
              onChange={(e) => setFormData({ ...formData, client_id: e.target.value })}
              className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-text-muted mb-1">
              OAuth Client Secret *
            </label>
            <input
              type="password"
              required
              value={formData.client_secret}
              onChange={(e) => setFormData({ ...formData, client_secret: e.target.value })}
              className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
            />
          </div>
          <div className="space-y-2">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={formData.sync_users}
                onChange={(e) => setFormData({ ...formData, sync_users: e.target.checked })}
                className="w-4 h-4 text-green-600 border-border rounded focus:ring-green-500"
              />
              <span className="text-sm text-text-muted">Sync users from Google Workspace</span>
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={formData.sync_groups}
                onChange={(e) => setFormData({ ...formData, sync_groups: e.target.checked })}
                className="w-4 h-4 text-green-600 border-border rounded focus:ring-green-500"
              />
              <span className="text-sm text-text-muted">Sync groups from Google Workspace</span>
            </label>
          </div>
          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-border text-text-muted rounded-lg hover:bg-surface-hover transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="flex-1 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50"
            >
              {isLoading ? 'Connecting...' : 'Connect'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function OIDCModal({
  onClose,
  onCreate,
  isLoading,
}: {
  onClose: () => void;
  onCreate: (data: OIDCRequest) => void;
  isLoading: boolean;
}) {
  const [formData, setFormData] = useState<OIDCRequest>({
    display_name: '',
    discovery_url: '',
    client_id: '',
    client_secret: '',
    scopes: ['openid', 'email', 'profile'],
    allowed_domains: [],
    default_role: '',
    claim_mappings: [],
    group_role_mappings: [],
  });
  const [testResult, setTestResult] = useState<string | null>(null);
  const [testing, setTesting] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onCreate(formData);
  };

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const result = await testOidc(formData.discovery_url, formData.client_id, formData.client_secret);
      if (result.discovery_ok) {
        setTestResult(`Discovery OK; token_ok=${result.token_ok}`);
      } else {
        setTestResult(`Failed: ${result.error || 'unknown error'}`);
      }
    } catch (err: any) {
      setTestResult(`Error: ${String(err)}`);
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-surface-card rounded-lg p-6 max-w-lg w-full mx-4">
        <h2 className="text-xl font-bold text-text-main mb-4">Add OIDC Provider</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <Input label="Display name *" value={formData.display_name} onChange={(v) => setFormData({ ...formData, display_name: v })} />
          <Input label="Discovery URL *" value={formData.discovery_url} onChange={(v) => setFormData({ ...formData, discovery_url: v })} />
          <Input label="Client ID *" value={formData.client_id} onChange={(v) => setFormData({ ...formData, client_id: v })} />
          <Input label="Client secret *" type="password" value={formData.client_secret} onChange={(v) => setFormData({ ...formData, client_secret: v })} />
          <Input
            label="Scopes (space or comma separated)"
            value={formData.scopes.join(' ')}
            onChange={(v) => setFormData({ ...formData, scopes: v.split(/[,\\s]+/).filter(Boolean) })}
          />
          <Input
            label="Allowed domains (comma separated)"
            value={formData.allowed_domains.join(',')}
            onChange={(v) => setFormData({ ...formData, allowed_domains: v.split(',').map((s) => s.trim()).filter(Boolean) })}
          />
          <Input
            label="Default role (optional)"
            value={formData.default_role || ''}
            onChange={(v) => setFormData({ ...formData, default_role: v })}
          />
          <ClaimMappingEditor
            label="Claim → Attribute mappings (optional)"
            mappings={formData.claim_mappings}
            onChange={(mappings) => setFormData({ ...formData, claim_mappings: mappings })}
          />
          <GroupRoleEditor
            label="Group → Role mappings (optional)"
            mappings={formData.group_role_mappings}
            onChange={(mappings) => setFormData({ ...formData, group_role_mappings: mappings })}
          />
          <div className="flex items-center gap-2 text-sm">
            <button
              type="button"
              onClick={handleTest}
              className="inline-flex items-center gap-2 px-3 py-2 bg-bg-alt border border-border rounded hover:bg-surface-hover"
              disabled={testing}
            >
              <ArrowPathIcon className="w-4 h-4" />
              {testing ? 'Testing...' : 'Test discovery'}
            </button>
            {testResult && <span className="text-text-muted">{testResult}</span>}
          </div>
          <div className="flex gap-3 pt-4">
            <button type="button" onClick={onClose} className="flex-1 px-4 py-2 border border-border text-text-muted rounded-lg hover:bg-surface-hover">
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="flex-1 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50"
            >
              {isLoading ? 'Saving...' : 'Create'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function SAMLModal({
  onClose,
  onCreate,
  isLoading,
}: {
  onClose: () => void;
  onCreate: (data: SAMLRequest) => void;
  isLoading: boolean;
}) {
  const [formData, setFormData] = useState<SAMLRequest>({
    display_name: '',
    metadata_url: '',
    authn_contexts: [],
    allowed_domains: [],
    default_role: '',
    claim_mappings: [],
    group_role_mappings: [],
  });
  const [testResult, setTestResult] = useState<string | null>(null);
  const [testing, setTesting] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onCreate(formData);
  };

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const result = await testSaml(formData.metadata_url);
      if (result.metadata_ok) {
        setTestResult(`Metadata OK; entityID=${result.entity_id || 'n/a'}`);
      } else {
        setTestResult(`Failed: ${result.error || 'unknown error'}`);
      }
    } catch (err: any) {
      setTestResult(`Error: ${String(err)}`);
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-surface-card rounded-lg p-6 max-w-lg w-full mx-4">
        <h2 className="text-xl font-bold text-text-main mb-4">Add SAML Provider</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <Input label="Display name *" value={formData.display_name} onChange={(v) => setFormData({ ...formData, display_name: v })} />
          <Input label="Metadata URL *" value={formData.metadata_url} onChange={(v) => setFormData({ ...formData, metadata_url: v })} />
          <Input
            label="Authn Contexts (space or comma separated)"
            value={formData.authn_contexts.join(' ')}
            onChange={(v) => setFormData({ ...formData, authn_contexts: v.split(/[,\\s]+/).filter(Boolean) })}
          />
          <Input
            label="Allowed domains (comma separated)"
            value={formData.allowed_domains.join(',')}
            onChange={(v) => setFormData({ ...formData, allowed_domains: v.split(',').map((s) => s.trim()).filter(Boolean) })}
          />
          <Input
            label="Default role (optional)"
            value={formData.default_role || ''}
            onChange={(v) => setFormData({ ...formData, default_role: v })}
          />
          <ClaimMappingEditor
            label="Claim → Attribute mappings (optional)"
            mappings={formData.claim_mappings}
            onChange={(mappings) => setFormData({ ...formData, claim_mappings: mappings })}
          />
          <GroupRoleEditor
            label="Group → Role mappings (optional)"
            mappings={formData.group_role_mappings}
            onChange={(mappings) => setFormData({ ...formData, group_role_mappings: mappings })}
          />
          <div className="flex items-center gap-2 text-sm">
            <button
              type="button"
              onClick={handleTest}
              className="inline-flex items-center gap-2 px-3 py-2 bg-bg-alt border border-border rounded hover:bg-surface-hover"
              disabled={testing}
            >
              <ArrowPathIcon className="w-4 h-4" />
              {testing ? 'Testing...' : 'Test metadata'}
            </button>
            {testResult && <span className="text-text-muted">{testResult}</span>}
          </div>
          <div className="flex gap-3 pt-4">
            <button type="button" onClick={onClose} className="flex-1 px-4 py-2 border border-border text-text-muted rounded-lg hover:bg-surface-hover">
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="flex-1 px-4 py-2 bg-cyan-600 text-white rounded-lg hover:bg-cyan-700 disabled:opacity-50"
            >
              {isLoading ? 'Saving...' : 'Create'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function Input({
  label,
  value,
  onChange,
  type = 'text',
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-text-muted mb-1">{label}</label>
      <input
        type={type}
        required
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
      />
    </div>
  );
}

function GroupRoleEditor({
  label,
  mappings,
  onChange,
}: {
  label: string;
  mappings: { group: string; role: string }[];
  onChange: (m: { group: string; role: string }[]) => void;
}) {
  const update = (idx: number, field: 'group' | 'role', value: string) => {
    const next = mappings.map((m, i) => (i === idx ? { ...m, [field]: value } : m));
    onChange(next);
  };
  const add = () => onChange([...mappings, { group: '', role: '' }]);
  const remove = (idx: number) => onChange(mappings.filter((_, i) => i !== idx));

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <label className="block text-sm font-medium text-text-muted">{label}</label>
        <button
          type="button"
          onClick={add}
          className="inline-flex items-center gap-1 text-xs px-2 py-1 bg-bg-alt border border-border rounded hover:bg-surface-hover"
        >
          <PlusIcon className="w-4 h-4" /> Add
        </button>
      </div>
      {mappings.length === 0 && <p className="text-xs text-text-muted">No mappings added.</p>}
      <div className="space-y-2">
        {mappings.map((m, idx) => (
          <div key={idx} className="grid grid-cols-2 gap-2 items-center">
            <input
              type="text"
              placeholder="Group value (e.g., Engineering)"
              value={m.group}
              onChange={(e) => update(idx, 'group', e.target.value)}
              className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            />
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="Role (e.g., tenant_admin)"
                value={m.role}
                onChange={(e) => update(idx, 'role', e.target.value)}
                className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              />
              <button
                type="button"
                onClick={() => remove(idx)}
                className="px-2 py-2 text-red-600 border border-red-200 rounded hover:bg-red-50"
              >
                <TrashIcon className="w-4 h-4" />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ClaimMappingEditor({
  label,
  mappings,
  onChange,
}: {
  label: string;
  mappings: { claim: string; to: string }[];
  onChange: (m: { claim: string; to: string }[]) => void;
}) {
  const update = (idx: number, field: 'claim' | 'to', value: string) => {
    const next = mappings.map((m, i) => (i === idx ? { ...m, [field]: value } : m));
    onChange(next);
  };
  const add = () => onChange([...mappings, { claim: '', to: '' }]);
  const remove = (idx: number) => onChange(mappings.filter((_, i) => i !== idx));

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <label className="block text-sm font-medium text-text-muted">{label}</label>
        <button
          type="button"
          onClick={add}
          className="inline-flex items-center gap-1 text-xs px-2 py-1 bg-bg-alt border border-border rounded hover:bg-surface-hover"
        >
          <PlusIcon className="w-4 h-4" /> Add
        </button>
      </div>
      {mappings.length === 0 && <p className="text-xs text-text-muted">No mappings added.</p>}
      <div className="space-y-2">
        {mappings.map((m, idx) => (
          <div key={idx} className="grid grid-cols-2 gap-2 items-center">
            <input
              type="text"
              placeholder="Claim (e.g., email)"
              value={m.claim}
              onChange={(e) => update(idx, 'claim', e.target.value)}
              className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            />
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="User attribute (e.g., email)"
                value={m.to}
                onChange={(e) => update(idx, 'to', e.target.value)}
                className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              />
              <button
                type="button"
                onClick={() => remove(idx)}
                className="px-2 py-2 text-red-600 border border-red-200 rounded hover:bg-red-50"
              >
                <TrashIcon className="w-4 h-4" />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
