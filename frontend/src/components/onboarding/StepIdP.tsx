'use client';

import React, { useState } from 'react';
import { connectIdP, IdPConnectionRequest, recheckHealth } from '@/lib/api/onboarding';
import { getOnboardingIdpMeta } from '@/lib/onboarding/idp';
import { mergeOnboardingMetricsContext } from '@/lib/onboarding/metrics';
import { useAuth } from '@/lib/providers/AuthProvider';

interface StepIdPProps {
  onNext: () => void;
  onSkip: () => void;
}

export default function StepIdP({ onNext, onSkip }: StepIdPProps) {
  const { tenantId } = useAuth();
  const [idpType, setIdpType] = useState<IdPConnectionRequest['provider'] | 'none' | ''>(
    'microsoft_entra'
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [healthOk, setHealthOk] = useState(false);
  const [lastTest, setLastTest] = useState<string | null>(null);
  const [healthDetails, setHealthDetails] = useState<any>(null);
  const [healthLoading, setHealthLoading] = useState(false);

  const idpOptions: Array<{
    value: IdPConnectionRequest['provider'] | 'none';
    label: string;
    icon: string;
    recommended?: boolean;
  }> = [
    { value: 'microsoft_entra', label: 'Microsoft 365 / Entra ID', icon: '🔷', recommended: true },
    // Keep SG identity available for customers who want SentinelGrid-hosted identity
    { value: 'sentinelgrid', label: 'Use SentinelGrid Identity', icon: '🛡️' },
    { value: 'google_workspace', label: 'Google Workspace', icon: '🔵' },
    { value: 'okta', label: 'Okta', icon: '🟢' },
  ];
  const selectedMeta =
    idpType && idpType !== 'none' ? getOnboardingIdpMeta(idpType as IdPConnectionRequest['provider']) : null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!idpType) {
      setError('Please select an identity provider');
      return;
    }

    if (!tenantId) {
      setError('Tenant ID not found. Please log in again.');
      return;
    }

    try {
      setLoading(true);
      setError(null);

      if (idpType === 'sentinelgrid') {
        // Mark SentinelGrid Identity as the chosen IdP to flip progress to completed
        await connectIdP({
          tenant_id: tenantId,
          provider: 'sentinelgrid',
          config: { mode: 'sentinelgrid_idp' },
        });
      } else {
        // TODO: Implement OAuth flow or configuration form based on idpType
        await connectIdP({
          tenant_id: tenantId,
          provider: idpType as Exclude<IdPConnectionRequest['provider'], 'sentinelgrid'>,
          config: {}, // Would be populated from OAuth or form
        });
      }

      setHealthOk(true);
      setLastTest(new Date().toLocaleString());
      mergeOnboardingMetricsContext({
        servicesSelected: {
          idpProvider: idpType,
        },
      });
      onNext();
    } catch (err: any) {
      console.error('Error connecting IdP:', err);
      setError(err.message || 'Failed to connect identity provider');
      setHealthOk(false);
      setLastTest(null);
    } finally {
      setLoading(false);
    }
  };

  const handleRecheck = async () => {
    try {
      setHealthLoading(true);
      const res = await recheckHealth('idp');
      setHealthDetails(res?.health || null);
      setHealthOk((res?.health?.status || '').toLowerCase() === 'healthy');
      setLastTest(new Date().toLocaleString());
    } catch (err: any) {
      setError(err.message || 'Failed to recheck IdP health');
    } finally {
      setHealthLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold mb-2">Connect Your Identity</h2>
        <p className="text-slate-300">
          Connect your identity/SSO source so we can understand your users, admins, and sign-ins.
          Or use SentinelGrid Identity — we'll act as your SSO with MFA and federated login built-in.
        </p>
        <div className="mt-3 rounded-lg border border-cyan-500/20 bg-cyan-500/5 px-4 py-3 text-sm text-slate-300">
          <span className="font-medium text-cyan-300">Recommended for the fastest SMB rollout:</span>{' '}
          start with your primary directory. Microsoft 365 / Entra is the default path for most SMB deployments,
          but Google Workspace is a first-class option if that is where your users and admins live.
        </div>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 text-sm text-red-300">
          {error}
        </div>
      )}
      {healthOk && (
        <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-3 text-sm text-green-300 flex items-center justify-between">
          <span>Identity connected {lastTest ? `(${lastTest})` : ''}.</span>
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
        <fieldset>
          <legend className="mb-3 text-sm font-medium text-slate-200">Choose an identity provider</legend>
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
                  onChange={(e) => setIdpType(e.target.value as IdPConnectionRequest['provider'] | 'none' | '')}
                  className="sr-only"
                />
                <div className="flex items-center gap-3">
                  <span className="text-2xl">{option.icon}</span>
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{option.label}</span>
                    {option.recommended && (
                      <span className="rounded-full border border-cyan-500/30 px-2 py-0.5 text-[10px] uppercase tracking-[0.14em] text-cyan-300">
                        Recommended
                      </span>
                    )}
                  </div>
                </div>
              </label>
            ))}
          </div>
        </fieldset>

        {idpType && idpType !== 'none' && (
          <div className="rounded-xl border border-blue-500/30 bg-blue-500/10 p-4">
            <p className="text-sm font-medium text-blue-200">{selectedMeta?.authHint}</p>
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              <div>
                <p className="text-[11px] uppercase tracking-[0.14em] text-blue-300">First-week visibility</p>
                <ul className="mt-2 space-y-2 text-sm text-slate-200">
                  {selectedMeta?.valuePoints.map((item) => (
                    <li key={item} className="flex gap-2">
                      <span className="text-blue-300">•</span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <p className="text-[11px] uppercase tracking-[0.14em] text-blue-300">Prepare before continuing</p>
                <ul className="mt-2 space-y-2 text-sm text-slate-200">
                  {selectedMeta?.prepPoints.map((item) => (
                    <li key={item} className="flex gap-2">
                      <span className="text-blue-300">•</span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
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
            {loading ? 'Connecting...' : `Continue with ${selectedMeta?.shortLabel || 'identity'}`}
          </button>
        </div>
      </form>
    </div>
  );
}
