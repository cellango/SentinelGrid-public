/**
 * App Connector Wizard Component
 * Step-by-step wizard for connecting applications
 */

'use client';

import { useEffect, useState } from 'react';
import { XMarkIcon, CheckCircleIcon } from '@heroicons/react/24/outline';
import clsx from 'clsx';

interface AppCatalogItem {
  id: string;
  name: string;
  display_name: string;
  description?: string;
  app_type: string;
  protocol: string;
  required_fields: string[];
  optional_fields: string[];
}

interface AppConnectorWizardProps {
  app: AppCatalogItem;
  onClose: () => void;
  onConnect: (config: Record<string, any>) => void;
  isLoading?: boolean;
}

type WizardStep = 'info' | 'configure' | 'review';
type StepId = 'basics' | 'redirects' | 'claims' | 'security' | 'keys' | 'assignments' | 'review';

export default function AppConnectorWizard({
  app,
  onClose,
  onConnect,
  isLoading = false,
}: AppConnectorWizardProps) {
  const slugify = (val: string) =>
    (val || '')
      .toLowerCase()
      .trim()
      .replace(/[^a-z0-9-_]+/g, '-')
      .replace(/-+/g, '-')
      .replace(/^-+|-+$/g, '')
      .slice(0, 64);

  const [step, setStep] = useState<StepId>('basics');
  const [config, setConfig] = useState<Record<string, any>>({
    app_name: app.display_name,
    app_slug: slugify(app.display_name || app.name || 'app'),
    protocol: app.protocol?.toLowerCase(),
    redirect_uris: '',
    acs_url: '',
    entity_id: '',
    audience: '',
    scopes: 'openid email profile',
    group_claim: 'groups',
    nameid_format: 'email',
    sign_assertions: true,
    pkce_required: true,
    refresh_tokens: false,
    client_secret_action: 'generate',
    entitlements: 'admin, editor, viewer',
    assign_groups: '',
    assign_users: '',
    activation_mode: 'draft',
  });

  const handleFieldChange = (field: string, value: any) => {
    setConfig((prev) => ({ ...prev, [field]: value }));
  };

  const steps: { id: StepId; label: string }[] = [
    { id: 'basics', label: 'Basics' },
    { id: 'redirects', label: 'Redirects / ACS' },
    { id: 'claims', label: 'Claims' },
    { id: 'security', label: 'Security' },
    { id: 'keys', label: 'Keys & Metadata' },
    { id: 'assignments', label: 'Assignments' },
    { id: 'review', label: 'Review' },
  ];

  const stepIndex = steps.findIndex((s) => s.id === step);
  const goNext = () => {
    if (stepIndex < steps.length - 1) {
      setStep(steps[stepIndex + 1].id);
    }
  };
  const goBack = () => {
    if (stepIndex > 0) {
      setStep(steps[stepIndex - 1].id);
    }
  };

  const handleConnect = () => onConnect(config);

  const protocol = app.protocol?.toLowerCase() || 'oidc';
  const requiresRedirects = protocol === 'oidc';
  const requiresACS = protocol === 'saml' || protocol === 'saml2' || config.protocol === 'saml';

  const isStepValid = (id: StepId) => {
    if (id === 'basics') {
      if (!config.app_name || !config.app_slug) return false;
      if (!/^[a-z0-9][a-z0-9-_]{2,63}$/.test(config.app_slug || '')) return false;
      return true;
    }
    if (id === 'redirects') {
      if (requiresRedirects && !(config.redirect_uris || '').trim()) return false;
      if (requiresACS && !(config.acs_url || '').trim()) return false;
      return true;
    }
    if (id === 'assignments') {
      // Allow draft with no assignments; activation requires assignments
      if (config.activation_mode === 'active') {
        const hasAssignments = Boolean((config.assign_groups || config.assign_users || '').trim());
        const hasEntitlements = Boolean((config.entitlements || '').trim());
        return hasAssignments && hasEntitlements;
      }
      return true;
    }
    return true;
  };

  const fieldTitle = (name: string) => name.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase());
  const allStepsValid = steps.every((s) => isStepValid(s.id as StepId));

  useEffect(() => {
    if (!config.app_name) return;
    const auto = slugify(config.app_name);
    // only auto-sync if user hasn't manually deviated (heuristic: original slug or empty)
    if (!config.app_slug || config.app_slug === slugify(app.display_name || app.name || 'app')) {
      setConfig((prev) => ({ ...prev, app_slug: auto }));
    }
  }, [config.app_name]);

  const renderStep = () => {
    if (step === 'basics') {
      return (
        <div className="space-y-4">
          <div>
            <h3 className="font-semibold text-text-main mb-2">About {app.display_name}</h3>
            {app.description && <p className="text-sm text-text-muted mb-4">{app.description}</p>}
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-text-muted">Protocol:</span>
                <span className="text-sm text-text-muted">{app.protocol}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-text-muted">Type:</span>
                <span className="text-sm text-text-muted">{app.app_type}</span>
              </div>
            </div>
          </div>
          <div className="space-y-3">
            <label className="block text-sm font-medium text-text-muted">Application Name</label>
            <input
              value={config.app_name || ''}
              onChange={(e) => handleFieldChange('app_name', e.target.value)}
              className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-slate-900 dark:border-slate-700 dark:text-text-main dark:placeholder:text-text-muted"
            />
            <label className="block text-sm font-medium text-text-muted mt-3">Application Slug (locks after activation)</label>
            <input
              value={config.app_slug || ''}
              onChange={(e) => handleFieldChange('app_slug', slugify(e.target.value))}
              className={clsx(
                "w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-slate-900 dark:border-slate-700 dark:text-text-main dark:placeholder:text-text-muted",
                /^[a-z0-9][a-z0-9-_]{2,63}$/.test(config.app_slug || '')
                  ? "border-border"
                  : "border-red-400"
              )}
              placeholder="app-slug"
            />
            <p className="text-xs text-text-muted">
              Lowercase letters/numbers/hyphen/underscore, 3-64 chars. Used in client_id and role names (e.g., {config.app_slug || 'app'}:admin).
            </p>
          </div>
        </div>
      );
    }
    if (step === 'redirects') {
      return (
        <div className="space-y-4">
          <h3 className="font-semibold text-text-main">Redirects / ACS</h3>
          <p className="text-sm text-text-muted">Provide redirect URIs (OIDC) or ACS URL (SAML).</p>
          {requiresRedirects && (
            <div>
              <label className="block text-sm font-medium text-text-muted mb-1">Redirect URIs (comma-separated)</label>
              <textarea
                value={config.redirect_uris || ''}
                onChange={(e) => handleFieldChange('redirect_uris', e.target.value)}
                className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-slate-900 dark:border-slate-700 dark:text-text-main dark:placeholder:text-text-muted"
                placeholder="https://app.example.com/callback, https://app.example.com/auth"
              />
            </div>
          )}
          {requiresACS && (
            <div>
              <label className="block text-sm font-medium text-text-muted mb-1">ACS URL</label>
              <input
                value={config.acs_url || ''}
                onChange={(e) => handleFieldChange('acs_url', e.target.value)}
                className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-slate-900 dark:border-slate-700 dark:text-text-main dark:placeholder:text-text-muted"
                placeholder="https://app.example.com/sso/acs"
              />
            </div>
          )}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-text-muted mb-1">Entity ID / Issuer</label>
              <input
                value={config.entity_id || ''}
                onChange={(e) => handleFieldChange('entity_id', e.target.value)}
                className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-slate-900 dark:border-slate-700 dark:text-text-main dark:placeholder:text-text-muted"
                placeholder="urn:example:sp"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-text-muted mb-1">Audience</label>
              <input
                value={config.audience || ''}
                onChange={(e) => handleFieldChange('audience', e.target.value)}
                className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-slate-900 dark:border-slate-700 dark:text-text-main dark:placeholder:text-text-muted"
                placeholder="urn:example:audience"
              />
            </div>
          </div>
        </div>
      );
    }
    if (step === 'claims') {
      return (
        <div className="space-y-4">
          <h3 className="font-semibold text-text-main">Claims / Attributes</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-text-muted mb-1">Scopes (OIDC)</label>
              <input
                value={config.scopes || ''}
                onChange={(e) => handleFieldChange('scopes', e.target.value)}
                className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-slate-900 dark:border-slate-700 dark:text-text-main dark:placeholder:text-text-muted"
              />
              <p className="text-xs text-text-muted mt-1">Default: openid email profile</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-text-muted mb-1">Group/Role Claim</label>
              <input
                value={config.group_claim || ''}
                onChange={(e) => handleFieldChange('group_claim', e.target.value)}
                className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-slate-900 dark:border-slate-700 dark:text-text-main dark:placeholder:text-text-muted"
                placeholder="groups"
              />
              <p className="text-xs text-text-muted mt-1">Attribute/claim sent for groups/roles.</p>
            </div>
          </div>
        </div>
      );
    }
    if (step === 'security') {
      const isSAML = protocol.startsWith('saml');
      return (
        <div className="space-y-4">
          <h3 className="font-semibold text-text-main">Security Defaults</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {isSAML ? (
              <>
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={!!config.sign_assertions}
                    onChange={(e) => handleFieldChange('sign_assertions', e.target.checked)}
                  />
                  <label className="text-sm text-text-muted">Sign assertions (SHA-256)</label>
                </div>
                <div>
                  <label className="block text-sm font-medium text-text-muted mb-1">NameID Format</label>
                  <select
                    value={config.nameid_format || 'email'}
                    onChange={(e) => handleFieldChange('nameid_format', e.target.value)}
                    className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-slate-900 dark:border-slate-700 dark:text-text-main dark:placeholder:text-text-muted"
                  >
                    <option value="email">EmailAddress</option>
                    <option value="transient">Transient</option>
                    <option value="persistent">Persistent</option>
                  </select>
                </div>
              </>
            ) : (
              <>
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={!!config.pkce_required}
                    onChange={(e) => handleFieldChange('pkce_required', e.target.checked)}
                  />
                  <label className="text-sm text-text-muted">PKCE required (recommended)</label>
                </div>
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={!!config.refresh_tokens}
                    onChange={(e) => handleFieldChange('refresh_tokens', e.target.checked)}
                  />
                  <label className="text-sm text-text-muted">Allow refresh tokens</label>
                </div>
              </>
            )}
          </div>
        </div>
      );
    }
    if (step === 'keys') {
      return (
        <div className="space-y-4">
          <h3 className="font-semibold text-text-main">Keys & Metadata</h3>
          <p className="text-sm text-text-muted">We will generate IdP metadata and a client secret (OIDC) or signing cert (SAML).</p>
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={(config.client_secret_action || 'generate') === 'generate'}
              onChange={(e) => handleFieldChange('client_secret_action', e.target.checked ? 'generate' : 'none')}
            />
            <label className="text-sm text-text-muted">Generate client secret (OIDC)</label>
          </div>
          <div className="text-xs text-text-muted">
            After connecting, you can export IdP metadata (SAML) or view OIDC discovery/secret in the app detail.
          </div>
        </div>
      );
    }
    if (step === 'assignments') {
      return (
        <div className="space-y-4">
          <h3 className="font-semibold text-text-main">Entitlements & Assignments</h3>
          <div>
            <label className="block text-sm font-medium text-text-muted mb-1">Entitlements / Roles (comma-separated)</label>
            <input
              value={config.entitlements || ''}
              onChange={(e) => handleFieldChange('entitlements', e.target.value)}
              className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-slate-900 dark:border-slate-700 dark:text-text-main dark:placeholder:text-text-muted"
            />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-text-muted mb-1">Assign Groups/Teams (comma-separated)</label>
              <input
                value={config.assign_groups || ''}
                onChange={(e) => handleFieldChange('assign_groups', e.target.value)}
                className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-slate-900 dark:border-slate-700 dark:text-text-main dark:placeholder:text-text-muted"
                placeholder="engineering, it-admins"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-text-muted mb-1">Assign People (emails, comma-separated)</label>
              <input
                value={config.assign_users || ''}
                onChange={(e) => handleFieldChange('assign_users', e.target.value)}
                className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-slate-900 dark:border-slate-700 dark:text-text-main dark:placeholder:text-text-muted"
                placeholder="user1@example.com, user2@example.com"
              />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={config.activation_mode === 'active'}
              onChange={(e) => handleFieldChange('activation_mode', e.target.checked ? 'active' : 'draft')}
            />
            <label className="text-sm text-text-muted">Activate immediately (requires assignments)</label>
          </div>
        </div>
      );
    }
    return (
      <div className="space-y-4">
        <h3 className="font-semibold text-text-main">Review & Connect</h3>
        <div className="bg-surface-hover border border-surface-card-border rounded-lg p-4 space-y-2">
          {Object.entries(config).map(([key, value]) => (
            <div key={key} className="flex justify-between">
              <span className="text-sm font-medium text-text-muted">{fieldTitle(key)}:</span>
              <span className="text-sm text-text-muted font-mono">
                {String(
                  key.includes('secret') || key.includes('password')
                    ? '••••••••'
                    : value === true
                      ? 'true'
                      : value === false
                        ? 'false'
                        : value || ''
                )}
              </span>
            </div>
          ))}
        </div>
      </div>
    );
  };

  const actions = (
    <div className="flex gap-3 pt-4">
      <button
        onClick={step === 'basics' ? onClose : goBack}
        className="flex-1 px-4 py-2 border border-border text-text-muted rounded-lg hover:bg-surface-hover transition-colors"
      >
        {step === 'basics' ? 'Cancel' : 'Back'}
      </button>
      {step !== 'review' ? (
        <button
          onClick={goNext}
          disabled={!isStepValid(step)}
          className={clsx(
            'flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors',
            !isStepValid(step) && 'opacity-50 cursor-not-allowed'
          )}
        >
          Next
        </button>
      ) : (
        <button
          onClick={handleConnect}
          disabled={isLoading || !allStepsValid}
          className={clsx(
            "flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50",
            (!allStepsValid || isLoading) && "opacity-50 cursor-not-allowed"
          )}
        >
          {isLoading ? 'Connecting...' : 'Connect App'}
        </button>
      )}
    </div>
  );

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-surface-card rounded-lg p-6 max-w-3xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold text-text-main">Connect {app.display_name}</h2>
          <button onClick={onClose} className="text-text-muted hover:text-text-muted">
            <XMarkIcon className="w-6 h-6" />
          </button>
        </div>

        <div className="mb-6 flex items-center gap-2">
          {steps.map((s, idx) => (
            <div key={s.id} className="flex items-center gap-2">
              <div
                className={clsx(
                  'w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold',
                  idx <= stepIndex ? 'bg-blue-600 text-white' : 'bg-surface-hover text-text-muted'
                )}
              >
                {idx < stepIndex ? <CheckCircleIcon className="w-5 h-5" /> : idx + 1}
              </div>
              <span className={clsx('text-sm', idx <= stepIndex ? 'text-text-main' : 'text-text-muted')}>
                {s.label}
              </span>
              {idx < steps.length - 1 && <div className="w-10 h-0.5 bg-surface-hover" />}
            </div>
          ))}
        </div>

        {renderStep()}
        {actions}
      </div>
    </div>
  );
}
