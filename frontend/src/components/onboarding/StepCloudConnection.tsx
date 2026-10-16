'use client';

import React, { useEffect, useMemo, useState } from 'react';
import { CheckCircleIcon, CloudIcon } from '@heroicons/react/24/outline';
import {
  connectCloud,
  CloudConnectionRequest,
  CloudProviderDefinition,
  CloudProviderField,
  getCloudProviderRegistry,
  recheckHealth,
} from '@/lib/api/onboarding';
import { useAuth } from '@/lib/providers/AuthProvider';

interface StepCloudConnectionProps {
  onNext: () => void;
  onBack: () => void;
  onSkip: () => void;
}

type FieldValue = string | boolean;
type ConnectionFormData = Record<string, FieldValue>;

function fieldLabel(field: CloudProviderField): string {
  if (field.label) return field.label;
  return field.name
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

function stringifyDefault(value: string | boolean | string[] | undefined): FieldValue {
  if (Array.isArray(value)) return value.join(',');
  if (typeof value === 'boolean') return value;
  return value ?? '';
}

function defaultsFor(provider: CloudProviderDefinition | undefined): ConnectionFormData {
  const data: ConnectionFormData = {};
  provider?.onboarding_fields?.forEach((field) => {
    data[field.name] = stringifyDefault(field.default);
  });
  return data;
}

function isEmptyValue(value: FieldValue | undefined): boolean {
  return value === undefined || value === '';
}

function normalizeFieldValue(field: CloudProviderField, value: FieldValue | undefined): any {
  if (field.type === 'checkbox') return Boolean(value);
  if (field.type === 'csv') {
    if (typeof value !== 'string') return [];
    return value
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean);
  }
  return value;
}

function buildConfig(provider: CloudProviderDefinition, data: ConnectionFormData): Record<string, any> {
  const config: Record<string, any> = {};
  provider.onboarding_fields.forEach((field) => {
    const value = data[field.name];
    if (field.type !== 'checkbox' && isEmptyValue(value)) return;
    config[field.name] = normalizeFieldValue(field, value);
  });

  if (provider.onboarding?.target_mode) {
    config.target_mode = provider.onboarding.target_mode;
  }
  if (provider.onboarding?.integration_method) {
    config.integration_method = provider.onboarding.integration_method;
  }
  const defaultTarget = provider.targets?.[0];
  if (defaultTarget?.id) {
    config.target = defaultTarget.id;
  }
  return config;
}

function selectInitialProvider(providers: CloudProviderDefinition[]): CloudProviderDefinition | undefined {
  return providers.find((provider) => provider.onboarding?.default) || providers[0];
}

export default function StepCloudConnection({
  onNext,
  onBack,
  onSkip,
}: StepCloudConnectionProps) {
  const { tenantId } = useAuth();
  const [providers, setProviders] = useState<CloudProviderDefinition[]>([]);
  const [cloudProvider, setCloudProvider] = useState('');
  const [loading, setLoading] = useState(false);
  const [registryLoading, setRegistryLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [connectionData, setConnectionData] = useState<ConnectionFormData>({});
  const [healthOk, setHealthOk] = useState(false);
  const [lastTest, setLastTest] = useState<string | null>(null);
  const [logHealth, setLogHealth] = useState<any>(null);
  const [healthLoading, setHealthLoading] = useState(false);

  useEffect(() => {
    let mounted = true;
    async function loadProviders() {
      try {
        setRegistryLoading(true);
        const registry = await getCloudProviderRegistry();
        if (!mounted) return;
        const available = (registry.providers || []).filter(
          (provider) => provider.onboarding?.enabled !== false
        );
        setProviders(available);
        const initial = selectInitialProvider(available);
        if (initial) {
          setCloudProvider(initial.id);
          setConnectionData(defaultsFor(initial));
        }
      } catch (err: any) {
        if (mounted) {
          setError(err.message || 'Failed to load cloud provider registry');
        }
      } finally {
        if (mounted) setRegistryLoading(false);
      }
    }

    loadProviders();
    return () => {
      mounted = false;
    };
  }, []);

  const selectedProvider = useMemo(
    () => providers.find((provider) => provider.id === cloudProvider),
    [providers, cloudProvider]
  );

  const handleProviderSelect = (provider: CloudProviderDefinition) => {
    setCloudProvider(provider.id);
    setConnectionData(defaultsFor(provider));
    setError(null);
    setHealthOk(false);
    setLastTest(null);
  };

  const updateField = (field: CloudProviderField, value: FieldValue) => {
    setConnectionData((current) => ({ ...current, [field.name]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!selectedProvider) {
      setError('Please select a cloud provider');
      return;
    }

    if (!tenantId) {
      setError('Tenant ID not found. Please log in again.');
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const request: CloudConnectionRequest = {
        tenant_id: tenantId,
        cloud_provider: selectedProvider.id,
        config: buildConfig(selectedProvider, connectionData),
      };

      const resp = await connectCloud(request);
      setLogHealth(resp?.health || resp?.test_connection_result || null);
      setHealthOk(true);
      setLastTest(new Date().toLocaleString());
      onNext();
    } catch (err: any) {
      console.error('Error connecting cloud:', err);
      setError(err.message || 'Failed to connect cloud provider');
      setHealthOk(false);
      setLastTest(null);
    } finally {
      setLoading(false);
    }
  };

  const recheckCloudHealth = async () => {
    try {
      setHealthLoading(true);
      setError(null);
      const res = await recheckHealth('cloud' as any);
      setLogHealth(res?.health || null);
      setHealthOk(res?.health?.success ?? false);
      setLastTest(new Date().toLocaleString());
    } catch (err: any) {
      setError(err.message || 'Cloud health check failed');
    } finally {
      setHealthLoading(false);
    }
  };

  const renderField = (field: CloudProviderField) => {
    const id = `cloud-${selectedProvider?.id || 'provider'}-${field.name}`;
    const label = fieldLabel(field);
    const value = connectionData[field.name];
    const sharedClass =
      'w-full rounded-lg border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-200 placeholder:text-slate-500';

    if (field.type === 'checkbox') {
      return (
        <label key={field.name} htmlFor={id} className="flex items-start gap-3 rounded-lg border border-slate-800 bg-slate-950/40 p-3 text-sm text-slate-300">
          <input
            id={id}
            type="checkbox"
            checked={Boolean(value)}
            onChange={(event) => updateField(field, event.target.checked)}
            className="mt-0.5 rounded border-slate-700 bg-slate-950/60 text-cyan-400"
          />
          <span>
            <span className="block font-medium text-slate-200">{label}</span>
            {field.help_text && <span className="mt-1 block text-xs text-slate-400">{field.help_text}</span>}
          </span>
        </label>
      );
    }

    return (
      <div key={field.name} className="space-y-1.5">
        <label htmlFor={id} className="block text-sm font-medium text-slate-300">
          {label}
        </label>
        {field.type === 'textarea' ? (
          <textarea
            id={id}
            required={field.required}
            rows={field.format === 'json' ? 6 : 4}
            value={typeof value === 'string' ? value : ''}
            onChange={(event) => updateField(field, event.target.value)}
            className={`${sharedClass} font-mono`}
            placeholder={field.placeholder}
          />
        ) : field.type === 'select' ? (
          <select
            id={id}
            required={field.required}
            value={typeof value === 'string' ? value : ''}
            onChange={(event) => updateField(field, event.target.value)}
            className={sharedClass}
          >
            <option value="">Select {label}</option>
            {(field.options || []).map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        ) : (
          <input
            id={id}
            type={field.type === 'secret' ? 'password' : 'text'}
            required={field.required}
            value={typeof value === 'string' ? value : ''}
            onChange={(event) => updateField(field, event.target.value)}
            className={sharedClass}
            placeholder={field.placeholder}
          />
        )}
        {field.help_text && <p className="text-xs text-slate-400">{field.help_text}</p>}
      </div>
    );
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="mb-2 text-2xl font-bold">Connect Your Cloud</h2>
        <p className="text-slate-300">
          Connect a provider target so SentinelGrid can test access, run a baseline scan, and prepare approval-gated fixes.
        </p>
        <div className="mt-3 rounded-lg border border-cyan-500/20 bg-cyan-500/5 px-4 py-3 text-sm text-slate-300">
          Pilot targets are available for the first end-to-end cloud security run.
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">
          {error}
        </div>
      )}

      {healthOk && (
        <div className="flex items-center justify-between rounded-lg border border-green-500/30 bg-green-500/10 p-3 text-sm text-green-300">
          <span>Connection saved and health check passed {lastTest ? `(${lastTest})` : ''}.</span>
          <span className="inline-flex items-center gap-1 rounded-full border border-green-500/40 bg-green-600/20 px-2 py-1 text-xs">
            <CheckCircleIcon className="h-4 w-4" />
            Healthy
          </span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-5">
        <fieldset>
          <legend className="mb-2 block text-sm font-medium text-slate-300">
            Select Cloud Provider
          </legend>
          {registryLoading ? (
            <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-4 text-sm text-slate-400">
              Loading cloud providers...
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
              {providers.map((provider) => {
                const selected = provider.id === cloudProvider;
                return (
                  <button
                    key={provider.id}
                    type="button"
                    onClick={() => handleProviderSelect(provider)}
                    className={`relative rounded-lg border-2 p-4 text-left transition-all ${
                      selected
                        ? 'border-cyan-400 bg-cyan-400/10'
                        : 'border-slate-700 hover:border-slate-600'
                    }`}
                  >
                    {provider.onboarding?.badge && (
                      <span className="absolute right-2 top-2 rounded-full border border-cyan-500/30 px-2 py-0.5 text-[10px] uppercase tracking-[0.14em] text-cyan-300">
                        {provider.onboarding.badge}
                      </span>
                    )}
                    <CloudIcon className="mb-3 h-7 w-7 text-cyan-300" />
                    <div className="font-medium text-slate-100">{provider.display_name}</div>
                    {provider.onboarding?.target_mode && (
                      <div className="mt-1 text-xs text-slate-400">{provider.onboarding.target_mode.replace(/_/g, ' ')}</div>
                    )}
                  </button>
                );
              })}
            </div>
          )}
        </fieldset>

        {selectedProvider && (
          <div className="space-y-4 rounded-lg border border-slate-800 bg-slate-900/40 p-4">
            <div className="flex flex-col gap-2 border-b border-slate-800 pb-3 md:flex-row md:items-start md:justify-between">
              <div>
                <h3 className="text-sm font-semibold text-slate-100">{selectedProvider.display_name}</h3>
                {selectedProvider.onboarding?.description && (
                  <p className="mt-1 text-xs text-slate-400">{selectedProvider.onboarding.description}</p>
                )}
              </div>
              {selectedProvider.targets?.[0]?.id && (
                <span className="rounded-full border border-slate-700 px-2.5 py-1 text-xs text-slate-300">
                  Target: {selectedProvider.targets[0].id}
                </span>
              )}
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              {selectedProvider.onboarding_fields.map(renderField)}
            </div>

            {logHealth && (
              <div className="rounded-lg border border-slate-800 bg-slate-950/50 p-3 text-xs text-slate-300">
                <pre className="max-h-40 overflow-auto whitespace-pre-wrap">{JSON.stringify(logHealth, null, 2)}</pre>
              </div>
            )}

            <button
              type="button"
              onClick={recheckCloudHealth}
              disabled={healthLoading}
              className="text-xs text-cyan-300 underline disabled:cursor-not-allowed disabled:opacity-50"
            >
              {healthLoading ? 'Checking health...' : 'Recheck cloud health'}
            </button>
          </div>
        )}

        <div className="flex justify-between pt-4">
          <button
            type="button"
            onClick={onBack}
            className="text-sm text-slate-300 hover:text-slate-100"
          >
            Back
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
              disabled={loading || registryLoading || !selectedProvider}
              className="inline-flex items-center justify-center rounded-full bg-cyan-400 px-5 py-2 text-sm font-medium text-slate-950 transition-colors hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading ? 'Connecting...' : 'Continue'}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}
