'use client';

import React, { useState, useEffect } from 'react';
import { connectAIShield, recheckHealth } from '@/lib/api/onboarding';

interface StepAIShieldProps {
  onNext: () => void;
  onBack: () => void;
  onSkip: () => void;
  mode: 'hosted' | 'self';
  initialHealth?: any;
}

export default function StepAIShield({
  onNext,
  onBack,
  onSkip,
  mode,
  initialHealth,
}: StepAIShieldProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [healthOk, setHealthOk] = useState(false);
  const [lastTest, setLastTest] = useState<string | null>(null);
  const [healthStatus, setHealthStatus] = useState<string>('unknown');

  const [form, setForm] = useState<Record<string, string>>({
    endpoint_url: '',
    api_key: '',
    gateway_url: '',
    client_id: '',
    client_secret: '',
  });

  useEffect(() => {
    if (initialHealth) {
      setHealthOk(initialHealth.status === 'healthy');
      setHealthStatus(initialHealth.status || 'unknown');
      setLastTest(initialHealth.checked_at || null);
    }
  }, [initialHealth]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const result = await connectAIShield({
        mode,
        endpoint_url: form.endpoint_url,
        api_key: form.api_key,
        gateway_url: form.gateway_url,
        client_id: form.client_id,
        client_secret: form.client_secret,
      });
      const health = result?.health;
      const status = health?.status || result?.status || 'unknown';
      const checkedAt = health?.checked_at || new Date().toLocaleString();
      const success = result?.success === true || status === 'healthy';

      setHealthOk(success);
      setHealthStatus(status);
      setLastTest(checkedAt);

      if (success) {
        onNext();
      } else {
        setError(result?.message || `AI Shield health is ${status}`);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to save AI Shield settings');
      setHealthOk(false);
      setHealthStatus('unreachable');
      setLastTest(new Date().toLocaleString());
    } finally {
      setLoading(false);
    }
  };

  const hosted = mode === 'hosted';

  const handleRecheck = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await recheckHealth('ai');
      const h = res?.health;
      if (h) {
        setHealthStatus(h.status || 'unknown');
        setHealthOk(h.status === 'healthy');
        setLastTest(h.checked_at || new Date().toLocaleString());
      }
    } catch (err: any) {
      setError(err.message || 'Health check failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold mb-2">AI Shield</h2>
        <p className="text-slate-300">
          {hosted
            ? 'Use SentinelGrid-hosted AI Shield gateway.'
            : 'Point to your self-hosted AI Shield gateway.'}
        </p>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 text-sm text-red-300">
          {error}
        </div>
      )}
      {healthOk && (
        <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-3 text-sm text-green-300 flex items-center justify-between">
          <span>Health: {healthStatus} {lastTest ? `(${lastTest})` : ''}.</span>
          <span className="text-xs bg-green-600/20 px-2 py-1 rounded-full border border-green-500/40">Healthy</span>
        </div>
      )}
      {!healthOk && lastTest && (
        <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-3 text-sm text-yellow-300 flex items-center justify-between">
          <span>Last health: {healthStatus} {lastTest ? `(${lastTest})` : ''}.</span>
          <span className="text-xs bg-yellow-600/20 px-2 py-1 rounded-full border border-yellow-500/40">Needs attention</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        {hosted ? (
          <>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">
                AI Shield Endpoint URL
              </label>
              <input
                type="url"
                required
                value={form.endpoint_url}
                onChange={(e) => setForm({ ...form, endpoint_url: e.target.value })}
                className="w-full rounded-lg border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-200"
                placeholder="https://ai-shield.sentinelgrid.ai/gateway"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">
                API Key / Client Secret
              </label>
              <input
                type="password"
                required
                value={form.api_key}
                onChange={(e) => setForm({ ...form, api_key: e.target.value })}
                className="w-full rounded-lg border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-200"
                placeholder="••••••••"
              />
            </div>
          </>
        ) : (
          <>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">
                Gateway URL
              </label>
              <input
                type="url"
                required
                value={form.gateway_url}
                onChange={(e) => setForm({ ...form, gateway_url: e.target.value })}
                className="w-full rounded-lg border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-200"
                placeholder="https://ai-gateway.yourdomain.com"
              />
            </div>
            <div className="grid md:grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">
                  Client ID
                </label>
                <input
                  type="text"
                  required
                  value={form.client_id}
                  onChange={(e) => setForm({ ...form, client_id: e.target.value })}
                  className="w-full rounded-lg border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-200"
                  placeholder="client-id"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">
                  Client Secret
                </label>
                <input
                  type="password"
                  required
                  value={form.client_secret}
                  onChange={(e) => setForm({ ...form, client_secret: e.target.value })}
                  className="w-full rounded-lg border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-200"
                  placeholder="••••••••"
                />
              </div>
            </div>
          </>
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
              type="button"
              onClick={handleRecheck}
              disabled={loading}
              className="inline-flex items-center justify-center rounded-full px-5 py-2 text-sm font-medium border border-cyan-400 text-cyan-300 hover:bg-cyan-400/10 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Checking...' : 'Re-run Health'}
            </button>
            <button
              type="submit"
              disabled={loading}
              className="inline-flex items-center justify-center rounded-full px-5 py-2 text-sm font-medium bg-cyan-400 text-slate-950 hover:bg-cyan-300 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Checking...' : 'Save & Check Health'}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}
