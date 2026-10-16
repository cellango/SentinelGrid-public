'use client';

import React, { useState, useEffect } from 'react';
import { connectAppSec, recheckHealth } from '@/lib/api/onboarding';

interface StepAppSecProps {
  onNext: () => void;
  onBack: () => void;
  onSkip: () => void;
  initialHealth?: any;
}

export default function StepAppSec({ onNext, onBack, onSkip, initialHealth }: StepAppSecProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [healthOk, setHealthOk] = useState(false);
  const [lastTest, setLastTest] = useState<string | null>(null);
  const [healthStatus, setHealthStatus] = useState<string>('unknown');

  const [form, setForm] = useState({
    gateway_url: '',
    api_key: '',
    app_id: '',
    openapi_url: '',
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const response = await connectAppSec({
        gateway_url: form.gateway_url,
        api_key: form.api_key,
        app_id: form.app_id,
        openapi_url: form.openapi_url,
      });
      const nextHealth = response?.health || { status: response?.status || 'unknown' };
      const nextStatus = nextHealth.status || response?.status || 'unknown';
      const isHealthy = nextStatus === 'healthy';

      setHealthOk(isHealthy);
      setHealthStatus(nextStatus);
      setLastTest(nextHealth.checked_at || new Date().toLocaleString());

      if (isHealthy) {
        onNext();
        return;
      }

      setError(
        response?.message ||
          nextHealth.message ||
          'AppSec settings were saved, but health still needs attention.'
      );
    } catch (err: any) {
      setError(err.message || 'Failed to save AppSec settings');
      setHealthOk(false);
      setHealthStatus('unreachable');
      setLastTest(new Date().toLocaleString());
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (initialHealth) {
      setHealthOk(initialHealth.status === 'healthy');
      setHealthStatus(initialHealth.status || 'unknown');
      setLastTest(initialHealth.checked_at || null);
    }
  }, [initialHealth]);

  const handleRecheck = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await recheckHealth('appsec');
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
        <h2 className="text-2xl font-bold mb-2">Application Security</h2>
        <p className="text-slate-300">
          Provide an app gateway endpoint or OpenAPI spec so we can observe and protect your apps/APIs.
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
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-1">
            App Gateway URL (or Ingress)
          </label>
          <input
            type="url"
            required
            value={form.gateway_url}
            onChange={(e) => setForm({ ...form, gateway_url: e.target.value })}
            className="w-full rounded-lg border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-200"
            placeholder="https://apps.yourdomain.com"
          />
        </div>
        <div className="grid md:grid-cols-2 gap-3">
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">
              API Key / Token
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
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">
              App / Service ID (optional)
            </label>
            <input
              type="text"
              value={form.app_id}
              onChange={(e) => setForm({ ...form, app_id: e.target.value })}
              className="w-full rounded-lg border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-200"
              placeholder="customer-portal"
            />
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-1">
            OpenAPI URL (optional)
          </label>
          <input
            type="url"
            value={form.openapi_url}
            onChange={(e) => setForm({ ...form, openapi_url: e.target.value })}
            className="w-full rounded-lg border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-200"
            placeholder="https://apps.yourdomain.com/openapi.json"
          />
          <p className="text-xs text-slate-400 mt-1">
            If provided, we can pre-seed API posture checks and detections.
          </p>
        </div>

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
