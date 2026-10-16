'use client';

import React, { useState } from 'react';
import { connectGitProvider, GitProviderConnectRequest } from '@/lib/api/git-providers';
import { recheckHealth } from '@/lib/api/onboarding';

interface StepGitSecurityProps {
  onNext: () => void;
  onBack: () => void;
  onSkip: () => void;
}

export default function StepGitSecurity({
  onNext,
  onBack,
  onSkip,
}: StepGitSecurityProps) {
  const [provider, setProvider] = useState<GitProviderConnectRequest['provider'] | ''>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [config, setConfig] = useState<Record<string, string>>({});
  const [healthOk, setHealthOk] = useState(false);
  const [lastTest, setLastTest] = useState<string | null>(null);
  const [healthDetails, setHealthDetails] = useState<any>(null);
  const [healthLoading, setHealthLoading] = useState(false);

  const providerOptions: Array<{
    value: GitProviderConnectRequest['provider'];
    label: string;
    icon: string;
  }> = [
    { value: 'github', label: 'GitHub', icon: '🐙' },
    { value: 'gitlab', label: 'GitLab', icon: '🦊' },
    { value: 'bitbucket', label: 'Bitbucket', icon: '🔵' },
    { value: 'azure_devops', label: 'Azure DevOps', icon: '🔷' },
  ];

  const handleProviderSelect = (selectedProvider: GitProviderConnectRequest['provider']) => {
    setProvider(selectedProvider);
    setConfig({});
    setError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!provider) {
      setError('Please select a Git provider');
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const resp = await connectGitProvider({
        provider: provider as GitProviderConnectRequest['provider'],
        config,
        organization: config.organization,
        workspace: config.workspace,
        project: config.project,
      });

      const health = (resp as any)?.test_result || (resp as any)?.health;
      setHealthOk(health?.success ?? true);
      setHealthDetails(health || null);
      setLastTest(new Date().toLocaleString());
      onNext();
    } catch (err: any) {
      console.error('Error connecting Git provider:', err);
      setError(err.message || 'Failed to connect Git provider');
      setHealthOk(false);
      setLastTest(null);
    } finally {
      setLoading(false);
    }
  };

  const handleRecheck = async () => {
    try {
      setHealthLoading(true);
      const res = await recheckHealth('git' as any);
      setHealthDetails(res?.health || null);
      setHealthOk(res?.health?.success ?? false);
      setLastTest(new Date().toLocaleString());
    } catch (err: any) {
      setError(err.message || 'Failed to recheck git health');
    } finally {
      setHealthLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold mb-2">Connect Your Git Repositories</h2>
        <p className="text-slate-300">
          Connect your Git repositories so we can scan them for secrets, vulnerabilities, and code issues.
        </p>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 text-sm text-red-300">
          {error}
        </div>
      )}
      {healthOk && (
        <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-3 text-sm text-green-300 flex items-center justify-between">
          <span>Connection saved and health check passed {lastTest ? `(${lastTest})` : ''}.</span>
          <span className="text-xs bg-green-600/20 px-2 py-1 rounded-full border border-green-500/40">Healthy</span>
        </div>
      )}
      {healthDetails && (
        <div className="bg-slate-800/60 border border-slate-700 rounded-lg p-3 text-xs text-slate-200">
          <div className="flex items-center justify-between">
            <div className="font-semibold text-slate-200">Health details</div>
            <button
              type="button"
              onClick={handleRecheck}
              disabled={healthLoading}
              className="text-cyan-300 hover:text-cyan-200 text-xs"
            >
              {healthLoading ? 'Checking...' : 'Re-run health'}
            </button>
          </div>
          <div className="text-slate-300">{healthDetails.message || 'Validation performed'}</div>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Provider Selection */}
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">
            Select Git Provider
          </label>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {providerOptions.map((option) => (
              <button
                key={option.value}
                type="button"
                onClick={() => handleProviderSelect(option.value)}
                className={`
                  border-2 rounded-lg p-4 text-center transition-all
                  ${
                    provider === option.value
                      ? 'border-cyan-400 bg-cyan-400/10'
                      : 'border-slate-700 hover:border-slate-600'
                  }
                `}
              >
                <div className="text-2xl mb-2">{option.icon}</div>
                <div className="font-medium text-sm">{option.label}</div>
              </button>
            ))}
          </div>
        </div>

        {/* Provider-Specific Configuration */}
        {provider === 'github' && (
          <div className="space-y-4 bg-slate-800/50 rounded-lg p-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">
                GitHub Access Token
              </label>
              <input
                type="password"
                required
                value={config.access_token || ''}
                onChange={(e) => setConfig({ ...config, access_token: e.target.value })}
                className="w-full rounded-lg border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-200"
                placeholder="ghp_xxxxxxxxxxxx"
              />
              <p className="text-xs text-slate-400 mt-1">
                Create a personal access token with <code>repo</code> scope
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">
                Organization (Optional)
              </label>
              <input
                type="text"
                value={config.organization || ''}
                onChange={(e) => setConfig({ ...config, organization: e.target.value })}
                className="w-full rounded-lg border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-200"
                placeholder="my-org"
              />
            </div>
          </div>
        )}

        {provider === 'gitlab' && (
          <div className="space-y-4 bg-slate-800/50 rounded-lg p-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">
                GitLab URL
              </label>
              <input
                type="url"
                value={config.gitlab_url || 'https://gitlab.com'}
                onChange={(e) => setConfig({ ...config, gitlab_url: e.target.value })}
                className="w-full rounded-lg border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-200"
                placeholder="https://gitlab.com"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">
                Personal Access Token
              </label>
              <input
                type="password"
                required
                value={config.access_token || ''}
                onChange={(e) => setConfig({ ...config, access_token: e.target.value })}
                className="w-full rounded-lg border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-200"
                placeholder="glpat-xxxxxxxxxxxx"
              />
            </div>
          </div>
        )}

        {provider === 'bitbucket' && (
          <div className="space-y-4 bg-slate-800/50 rounded-lg p-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">
                Username
              </label>
              <input
                type="text"
                required
                value={config.username || ''}
                onChange={(e) => setConfig({ ...config, username: e.target.value })}
                className="w-full rounded-lg border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-200"
                placeholder="your-username"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">
                App Password
              </label>
              <input
                type="password"
                required
                value={config.app_password || ''}
                onChange={(e) => setConfig({ ...config, app_password: e.target.value })}
                className="w-full rounded-lg border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-200"
                placeholder="••••••••"
              />
              <p className="text-xs text-slate-400 mt-1">
                Create an app password in Bitbucket settings (not your regular password)
              </p>
            </div>
          </div>
        )}

        {provider === 'azure_devops' && (
          <div className="space-y-4 bg-slate-800/50 rounded-lg p-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">
                Organization
              </label>
              <input
                type="text"
                required
                value={config.organization || ''}
                onChange={(e) => setConfig({ ...config, organization: e.target.value })}
                className="w-full rounded-lg border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-200"
                placeholder="my-org"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">
                Personal Access Token
              </label>
              <input
                type="password"
                required
                value={config.personal_access_token || ''}
                onChange={(e) => setConfig({ ...config, personal_access_token: e.target.value })}
                className="w-full rounded-lg border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-200"
                placeholder="••••••••"
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
              disabled={loading || !provider}
              className="inline-flex items-center justify-center rounded-full px-5 py-2 text-sm font-medium bg-cyan-400 text-slate-950 hover:bg-cyan-300 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Connecting...' : 'Complete Setup'}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}
