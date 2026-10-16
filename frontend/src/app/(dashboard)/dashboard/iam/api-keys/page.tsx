/**
 * API Keys Page
 * Manage API keys for programmatic access
 */

'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '@/lib/providers/AuthProvider';
import {
  KeyIcon,
  PlusIcon,
  ArrowPathIcon,
  TrashIcon,
  CheckCircleIcon,
} from '@heroicons/react/24/outline';

// Use relative URLs to leverage Next.js rewrites

interface APIKey {
  id: string;
  tenant_id: string;
  user_id?: string;
  name: string;
  key_prefix: string;
  scopes: string[];
  rate_limit_per_minute: number;
  rate_limit_per_hour: number;
  expires_at?: string;
  last_used_at?: string;
  is_active: boolean;
  created_at: string;
}

async function getAPIKeys(): Promise<APIKey[]> {
  const response = await fetch(`/api/v1/api-keys`, {
    credentials: 'include',
  });
  if (!response.ok) {
    throw new Error(`Failed to fetch API keys: ${response.statusText}`);
  }
  return response.json();
}

async function createAPIKey(
  data: {
    name: string;
    scopes: string[];
    rate_limit_per_minute: number;
    rate_limit_per_hour: number;
    expires_in_days?: number;
  }
): Promise<APIKey & { key: string }> {
  const response = await fetch(`/api/v1/api-keys`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include',
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    throw new Error(`Failed to create API key: ${response.statusText}`);
  }
  return response.json();
}

async function revokeAPIKey(keyId: string): Promise<void> {
  const response = await fetch(`/api/v1/api-keys/${keyId}`, {
    method: 'DELETE',
    credentials: 'include',
  });
  if (!response.ok) {
    throw new Error(`Failed to revoke API key: ${response.statusText}`);
  }
}

async function rotateAPIKey(keyId: string): Promise<{ new_key: string }> {
  const response = await fetch(`/api/v1/api-keys/${keyId}/rotate`, {
    method: 'POST',
    credentials: 'include',
  });
  if (!response.ok) {
    throw new Error(`Failed to rotate API key: ${response.statusText}`);
  }
  return response.json();
}

export default function APIKeysPage() {
  const { isAuthenticated } = useAuth();
  const queryClient = useQueryClient();
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newKey, setNewKey] = useState<string | null>(null);

  const { data: apiKeys = [], isLoading } = useQuery({
    queryKey: ['api-keys'],
    queryFn: () => getAPIKeys(),
    enabled: isAuthenticated,
  });

  const createMutation = useMutation({
    mutationFn: (data: Parameters<typeof createAPIKey>[0]) => createAPIKey(data),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['api-keys'] });
      setNewKey(data.key);
      setShowCreateModal(false);
    },
  });

  const revokeMutation = useMutation({
    mutationFn: (keyId: string) => revokeAPIKey(keyId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['api-keys'] });
    },
  });

  const rotateMutation = useMutation({
    mutationFn: (keyId: string) => rotateAPIKey(keyId),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['api-keys'] });
      setNewKey(data.new_key);
    },
  });

  if (isLoading) {
    return (
      <div className="p-6 max-w-7xl mx-auto text-slate-900 dark:text-slate-100">
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <p className="mt-2 text-slate-600 dark:text-slate-300">Loading API keys...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto text-slate-900 dark:text-slate-100">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">API Keys</h1>
          <p className="text-sm text-slate-600 dark:text-slate-300 mt-1">
            Manage API keys for programmatic access
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          <PlusIcon className="w-5 h-5" />
          Create API Key
        </button>
      </div>

      {/* New Key Display */}
      {newKey && (
        <div className="mb-6 bg-green-50 dark:bg-emerald-900/30 border-2 border-green-200 dark:border-emerald-700 rounded-lg p-4">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <h3 className="font-semibold text-green-900 dark:text-emerald-200 mb-2 flex items-center gap-2">
                <CheckCircleIcon className="w-5 h-5" />
                API Key Created
              </h3>
              <p className="text-sm text-green-800 dark:text-emerald-100 mb-3">
                Copy this key now. You won't be able to see it again!
              </p>
              <div className="bg-surface-card border border-green-200 dark:border-emerald-700 rounded p-3 font-mono text-sm break-all">
                {newKey}
              </div>
            </div>
            <button
              onClick={() => {
                navigator.clipboard.writeText(newKey);
                alert('API key copied to clipboard!');
              }}
              className="ml-4 px-3 py-2 bg-green-600 text-white rounded hover:bg-green-700 transition-colors text-sm"
            >
              Copy
            </button>
            <button
              onClick={() => setNewKey(null)}
              className="ml-2 text-green-600 hover:text-green-800"
            >
              ×
            </button>
          </div>
        </div>
      )}

      {/* API Keys List */}
      {apiKeys.length > 0 ? (
        <div className="bg-surface-card border border-surface-card-border rounded-lg overflow-hidden shadow-sm dark:shadow-none">
          <table className="min-w-full divide-y divide-border dark:divide-slate-800">
            <thead className="bg-surface-hover/60">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">
                  Name
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">
                  Key Prefix
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">
                  Scopes
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">
                  Rate Limits
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">
                  Last Used
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-text-muted uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-surface-card divide-y divide-border dark:divide-slate-800">
              {apiKeys.map((key) => (
                <tr key={key.id} className="hover:bg-surface-hover/70">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center gap-2">
                      <KeyIcon className="w-5 h-5 text-text-muted dark:text-slate-400" />
                      <span className="text-sm font-medium">{key.name}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="text-sm text-text-muted font-mono">{key.key_prefix}</span>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex flex-wrap gap-1">
                      {key.scopes.length > 0 ? (
                        key.scopes.map((scope, idx) => (
                          <span
                            key={idx}
                            className="px-2 py-1 text-xs bg-bg-alt text-text-muted dark:bg-slate-800 dark:text-slate-200 rounded"
                          >
                            {scope}
                          </span>
                        ))
                      ) : (
                        <span className="text-xs text-text-muted">No scopes</span>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-text-muted">
                    {key.rate_limit_per_minute}/min, {key.rate_limit_per_hour}/hour
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-text-muted">
                    {key.last_used_at
                      ? new Date(key.last_used_at).toLocaleString()
                      : 'Never'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span
                      className={`px-2 py-1 text-xs font-medium rounded ${
                        key.is_active
                          ? 'bg-green-100 text-green-700'
                          : 'bg-bg-alt text-text-muted'
                      }`}
                    >
                      {key.is_active ? 'Active' : 'Revoked'}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => {
                          if (confirm(`Rotate API key "${key.name}"? The old key will be invalidated.`)) {
                            rotateMutation.mutate(key.id);
                          }
                        }}
                        disabled={rotateMutation.isPending}
                        className="text-blue-600 hover:text-blue-900 disabled:opacity-50"
                        title="Rotate"
                      >
                        <ArrowPathIcon className="w-5 h-5" />
                      </button>
                      {key.is_active && (
                        <button
                          onClick={() => {
                            if (confirm(`Revoke API key "${key.name}"?`)) {
                              revokeMutation.mutate(key.id);
                            }
                          }}
                          disabled={revokeMutation.isPending}
                          className="text-red-600 hover:text-red-900 disabled:opacity-50"
                          title="Revoke"
                        >
                          <TrashIcon className="w-5 h-5" />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="text-center py-12 bg-surface-card border border-surface-card-border rounded-lg">
          <KeyIcon className="w-12 h-12 text-text-muted mx-auto mb-4" />
          <p className="text-text-muted">No API keys created</p>
        </div>
      )}

      {/* Create API Key Modal */}
      {showCreateModal && (
        <CreateAPIKeyModal
          onClose={() => setShowCreateModal(false)}
          onSubmit={(data) => createMutation.mutate(data)}
          isLoading={createMutation.isPending}
        />
      )}
    </div>
  );
}

// Create API Key Modal
function CreateAPIKeyModal({
  onClose,
  onSubmit,
  isLoading,
}: {
  onClose: () => void;
  onSubmit: (data: Parameters<typeof createAPIKey>[0]) => void;
  isLoading: boolean;
}) {
  const [formData, setFormData] = useState({
    name: '',
    scopes: [] as string[],
    rate_limit_per_minute: 60,
    rate_limit_per_hour: 1000,
    expires_in_days: '',
  });
  const [newScope, setNewScope] = useState('');

  const handleAddScope = () => {
    if (newScope && !formData.scopes.includes(newScope)) {
      setFormData({ ...formData, scopes: [...formData.scopes, newScope] });
      setNewScope('');
    }
  };

  const handleRemoveScope = (scope: string) => {
    setFormData({
      ...formData,
      scopes: formData.scopes.filter((s) => s !== scope),
    });
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      name: formData.name,
      scopes: formData.scopes,
      rate_limit_per_minute: formData.rate_limit_per_minute,
      rate_limit_per_hour: formData.rate_limit_per_hour,
      expires_in_days: formData.expires_in_days ? parseInt(formData.expires_in_days) : undefined,
    });
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-surface-card rounded-lg p-6 max-w-md w-full mx-4 max-h-[90vh] overflow-y-auto text-slate-900 dark:text-slate-100">
        <h2 className="text-xl font-bold mb-4">Create API Key</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-text-muted mb-1">
              Name *
            </label>
            <input
              type="text"
              required
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-surface-card text-slate-900 dark:text-slate-100"
              placeholder="e.g., Production API Key"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-text-muted mb-1">
              Scopes
            </label>
            <div className="flex gap-2 mb-2">
              <input
                type="text"
                value={newScope}
                onChange={(e) => setNewScope(e.target.value)}
                onKeyPress={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    handleAddScope();
                  }
                }}
                className="flex-1 px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-surface-card text-slate-900 dark:text-slate-100"
                placeholder="Add scope..."
              />
              <button
                type="button"
                onClick={handleAddScope}
                className="px-4 py-2 bg-bg-alt text-text-main dark:bg-slate-800 dark:text-slate-100 rounded-lg hover:bg-surface-hover dark:hover:bg-slate-700 transition-colors border border-surface-card-border"
              >
                Add
              </button>
            </div>
            {formData.scopes.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {formData.scopes.map((scope) => (
                  <span
                    key={scope}
                    className="px-2 py-1 text-xs bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-200 rounded flex items-center gap-1"
                  >
                    {scope}
                    <button
                      type="button"
                      onClick={() => handleRemoveScope(scope)}
                      className="hover:text-blue-900"
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>
            )}
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-text-muted mb-1">
                Rate Limit (per minute)
              </label>
              <input
                type="number"
                min={1}
                max={10000}
                value={formData.rate_limit_per_minute}
                onChange={(e) =>
                  setFormData({ ...formData, rate_limit_per_minute: parseInt(e.target.value) })
                }
                className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-surface-card text-slate-900 dark:text-slate-100"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-text-muted mb-1">
                Rate Limit (per hour)
              </label>
              <input
                type="number"
                min={1}
                max={100000}
                value={formData.rate_limit_per_hour}
                onChange={(e) =>
                  setFormData({ ...formData, rate_limit_per_hour: parseInt(e.target.value) })
                }
                className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-surface-card text-slate-900 dark:text-slate-100"
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-text-muted mb-1">
              Expires In (days, optional)
            </label>
            <input
              type="number"
              min={1}
              max={365}
              value={formData.expires_in_days}
              onChange={(e) => setFormData({ ...formData, expires_in_days: e.target.value })}
              className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-surface-card text-slate-900 dark:text-slate-100"
              placeholder="Never expires"
            />
          </div>
          <div className="bg-yellow-50 dark:bg-amber-900/30 border border-yellow-200 dark:border-amber-700 rounded-lg p-3">
            <p className="text-sm text-yellow-800 dark:text-amber-100">
              <strong>Important:</strong> Copy the API key immediately after creation. You won't be
              able to see it again!
            </p>
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
              {isLoading ? 'Creating...' : 'Create API Key'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
