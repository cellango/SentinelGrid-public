'use client';

import React, { useState } from 'react';
import { connectIdP } from '@/lib/api/onboarding';

type IdpType = 'google' | 'microsoft' | 'okta' | 'keycloak' | 'none';

interface StepIdPProps {
  onNext: () => void;
  onSkip: () => void;
}

export default function StepIdP({ onNext, onSkip }: StepIdPProps) {
  const [idpType, setIdpType] = useState<IdpType | ''>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const idpOptions: Array<{ value: IdpType; label: string; icon: string }> = [
    { value: 'google', label: 'Google Workspace', icon: '🔵' },
    { value: 'microsoft', label: 'Microsoft 365 / Entra ID', icon: '🔷' },
    { value: 'okta', label: 'Okta', icon: '🟢' },
    { value: 'keycloak', label: 'Keycloak / Self-hosted', icon: '🔐' },
    { value: 'none', label: 'Use SentinelGrid Identity', icon: '🛡️' },
  ];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!idpType) {
      setError('Please select an identity provider');
      return;
    }

    if (idpType === 'none') {
      // Use SentinelGrid Identity - no connection needed
      onNext();
      return;
    }

    try {
      setLoading(true);
      setError(null);

      // TODO: Implement OAuth flow or configuration form based on idpType
      // For now, just proceed
      await connectIdP({
        idp_type: idpType as IdpType,
        config: {}, // Would be populated from OAuth or form
      });

      onNext();
    } catch (err: any) {
      console.error('Error connecting IdP:', err);
      setError(err.message || 'Failed to connect identity provider');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold mb-2">Connect Your Identity Provider</h2>
        <p className="text-slate-300">
          Connect your identity provider so we can understand your users, admins, and sign-ins.
          Or use SentinelGrid Identity — we&apos;ll act as your IdP with MFA and SSO built-in.
        </p>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 text-sm text-red-300">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {idpOptions.map((option) => (
            <label
              key={option.value}
              className={`
                border-2 rounded-lg p-4 cursor-pointer transition-all
                ${
                  idpType === option.value
                    ? 'border-cyan-400 bg-cyan-400/10'
                    : 'border-slate-700 hover:border-slate-600'
                }
              `}
            >
              <input
                type="radio"
                name="idp"
                value={option.value}
                checked={idpType === option.value}
                onChange={(e) => setIdpType(e.target.value as IdpType)}
                className="sr-only"
              />
              <div className="flex items-center gap-3">
                <span className="text-2xl">{option.icon}</span>
                <span className="font-medium">{option.label}</span>
              </div>
            </label>
          ))}
        </div>

        {idpType && idpType !== 'none' && (
          <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4">
            <p className="text-sm text-blue-300">
              {idpType === 'google' && 'You will be redirected to Google to authorize access.'}
              {idpType === 'microsoft' && 'You will be redirected to Microsoft to authorize access.'}
              {idpType === 'okta' && 'Please provide your Okta domain and API token.'}
              {idpType === 'keycloak' && 'Please provide your Keycloak server URL and credentials.'}
            </p>
          </div>
        )}

        <div className="flex justify-between pt-4">
          <button
            type="button"
            onClick={onSkip}
            className="text-sm text-slate-300 hover:text-slate-100"
          >
            Skip for now
          </button>
          <button
            type="submit"
            disabled={loading || !idpType}
            className="inline-flex items-center justify-center rounded-full px-5 py-2 text-sm font-medium bg-cyan-400 text-slate-950 hover:bg-cyan-300 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Connecting...' : 'Continue'}
          </button>
        </div>
      </form>
    </div>
  );
}
