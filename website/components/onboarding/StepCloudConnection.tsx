'use client';

import React, { useState } from 'react';
import { connectCloud, CloudConnectionRequest } from '@/lib/api/onboarding';

interface StepCloudConnectionProps {
  onNext: () => void;
  onBack: () => void;
  onSkip: () => void;
}

export default function StepCloudConnection({
  onNext,
  onBack,
  onSkip,
}: StepCloudConnectionProps) {
  const [cloudProvider, setCloudProvider] = useState<'aws' | 'azure' | 'gcp' | ''>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [connectionData, setConnectionData] = useState<Partial<CloudConnectionRequest>>({});

  const handleProviderSelect = (provider: 'aws' | 'azure' | 'gcp') => {
    setCloudProvider(provider);
    setConnectionData({ cloud_provider: provider });
    setError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!cloudProvider) {
      setError('Please select a cloud provider');
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const request: CloudConnectionRequest = {
        cloud_provider: cloudProvider,
        account_id: connectionData.account_id || '',
        ...connectionData,
      } as CloudConnectionRequest;

      await connectCloud(request);
      onNext();
    } catch (err: any) {
      console.error('Error connecting cloud:', err);
      setError(err.message || 'Failed to connect cloud provider');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold mb-2">Connect Your Cloud</h2>
        <p className="text-slate-300">
          Connect your cloud so we can ingest audit logs and security findings from your cloud accounts.
        </p>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 text-sm text-red-300">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Cloud Provider Selection */}
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">
            Select Cloud Provider
          </label>
          <div className="grid grid-cols-3 gap-4">
            <button
              type="button"
              onClick={() => handleProviderSelect('aws')}
              className={`
                border-2 rounded-lg p-4 text-center transition-all
                ${
                  cloudProvider === 'aws'
                    ? 'border-cyan-400 bg-cyan-400/10'
                    : 'border-slate-700 hover:border-slate-600'
                }
              `}
            >
              <div className="text-2xl mb-2">☁️</div>
              <div className="font-medium">AWS</div>
            </button>
            <button
              type="button"
              onClick={() => handleProviderSelect('azure')}
              className={`
                border-2 rounded-lg p-4 text-center transition-all
                ${
                  cloudProvider === 'azure'
                    ? 'border-cyan-400 bg-cyan-400/10'
                    : 'border-slate-700 hover:border-slate-600'
                }
              `}
            >
              <div className="text-2xl mb-2">☁️</div>
              <div className="font-medium">Azure</div>
            </button>
            <button
              type="button"
              onClick={() => handleProviderSelect('gcp')}
              className={`
                border-2 rounded-lg p-4 text-center transition-all
                ${
                  cloudProvider === 'gcp'
                    ? 'border-cyan-400 bg-cyan-400/10'
                    : 'border-slate-700 hover:border-slate-600'
                }
              `}
            >
              <div className="text-2xl mb-2">☁️</div>
              <div className="font-medium">GCP</div>
            </button>
          </div>
        </div>

        {/* Provider-Specific Fields */}
        {cloudProvider === 'aws' && (
          <div className="space-y-4 bg-slate-800/50 rounded-lg p-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">
                AWS Account ID
              </label>
              <input
                type="text"
                required
                value={connectionData.account_id || ''}
                onChange={(e) => setConnectionData({ ...connectionData, account_id: e.target.value })}
                className="w-full rounded-lg border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-200"
                placeholder="123456789012"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">
                IAM Role ARN
              </label>
              <input
                type="text"
                value={connectionData.role_arn || ''}
                onChange={(e) => setConnectionData({ ...connectionData, role_arn: e.target.value })}
                className="w-full rounded-lg border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-200"
                placeholder="arn:aws:iam::123456789012:role/SentinelGridMonitorRole"
              />
              <p className="text-xs text-slate-400 mt-1">
                Use our Terraform module or CloudFormation template to create this role
              </p>
            </div>
          </div>
        )}

        {cloudProvider === 'azure' && (
          <div className="space-y-4 bg-slate-800/50 rounded-lg p-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">
                Tenant ID
              </label>
              <input
                type="text"
                required
                value={connectionData.tenant_id || ''}
                onChange={(e) => setConnectionData({ ...connectionData, tenant_id: e.target.value })}
                className="w-full rounded-lg border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-200"
                placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">
                Client ID
              </label>
              <input
                type="text"
                required
                value={connectionData.client_id || ''}
                onChange={(e) => setConnectionData({ ...connectionData, client_id: e.target.value })}
                className="w-full rounded-lg border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-200"
                placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">
                Client Secret
              </label>
              <input
                type="password"
                required
                value={connectionData.client_secret || ''}
                onChange={(e) => setConnectionData({ ...connectionData, client_secret: e.target.value })}
                className="w-full rounded-lg border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-200"
                placeholder="••••••••"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">
                Subscription ID
              </label>
              <input
                type="text"
                required
                value={connectionData.account_id || ''}
                onChange={(e) => setConnectionData({ ...connectionData, account_id: e.target.value })}
                className="w-full rounded-lg border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-200"
                placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
              />
            </div>
          </div>
        )}

        {cloudProvider === 'gcp' && (
          <div className="space-y-4 bg-slate-800/50 rounded-lg p-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">
                Project ID
              </label>
              <input
                type="text"
                required
                value={connectionData.project_id || ''}
                onChange={(e) => setConnectionData({ ...connectionData, project_id: e.target.value })}
                className="w-full rounded-lg border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-200"
                placeholder="my-project-12345"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">
                Service Account Email
              </label>
              <input
                type="text"
                required
                value={connectionData.client_id || ''}
                onChange={(e) => setConnectionData({ ...connectionData, client_id: e.target.value })}
                className="w-full rounded-lg border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-200"
                placeholder="sentinelgrid-monitor@my-project.iam.gserviceaccount.com"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">
                Service Account JSON Key
              </label>
              <textarea
                required
                value={connectionData.service_account_key || ''}
                onChange={(e) => setConnectionData({ ...connectionData, service_account_key: e.target.value })}
                className="w-full rounded-lg border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-200 font-mono"
                rows={6}
                placeholder='{"type": "service_account", ...}'
              />
            </div>
          </div>
        )}

        <div className="flex justify-between pt-4">
          <button
            type="button"
            onClick={onBack}
            className="text-sm text-slate-300 hover:text-slate-100"
          >
            ← Back
          </button>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={onSkip}
              className="text-sm text-slate-300 hover:text-slate-100"
            >
              Skip
            </button>
            <button
              type="submit"
              disabled={loading || !cloudProvider}
              className="inline-flex items-center justify-center rounded-full px-5 py-2 text-sm font-medium bg-cyan-400 text-slate-950 hover:bg-cyan-300 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Connecting...' : 'Continue'}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}

