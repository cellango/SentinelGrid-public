/**
 * Playbook Trigger Configuration Page
 * Configure automated trigger conditions for a playbook
 */

'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Breadcrumbs from '@/components/ui/Breadcrumbs';
import { playbooksApi, Playbook } from '@/lib/api/playbooks';
import { TriggerCondition } from '@/lib/api/automated-response';
import TriggerConditionBuilder from '@/components/playbooks/TriggerConditionBuilder';
import TriggerHistory from '@/components/playbooks/TriggerHistory';
import { listAlerts } from '@/lib/api/siem';
import { listDetectionRules, setDetectionRuleMapping } from '@/lib/api/detection-rules';
import { toast } from 'react-hot-toast';

export default function PlaybookTriggersPage() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const playbookId = params.id as string;

  const { data: playbook, isLoading } = useQuery({
    queryKey: ['playbook', playbookId],
    queryFn: () => playbooksApi.get(playbookId),
    enabled: !!playbookId,
  });

  const [triggerConditions, setTriggerConditions] = useState<TriggerCondition>({});
  const [autoTriggerEnabled, setAutoTriggerEnabled] = useState(false);
  const [triggerPriority, setTriggerPriority] = useState(0);
  const [validating, setValidating] = useState(false);
  const [sampleAlertId, setSampleAlertId] = useState<string>('');
  const [sampleAlerts, setSampleAlerts] = useState<Array<{ id: string; alert_type?: string; title?: string }>>([]);
  const [previewResult, setPreviewResult] = useState<{ matches: number; reasons: string[] } | null>(null);
  const [ruleMappings, setRuleMappings] = useState<{ rule_id: string; alert_type: string; auto_execute: boolean; requires_approval: boolean }>({
    rule_id: '',
    alert_type: '',
    auto_execute: true,
    requires_approval: false,
  });

  useEffect(() => {
    if (playbook) {
      // Note: These fields may not exist in the Playbook type yet
      // They will be added when we update the playbook schema
      const conditions = (playbook as any).trigger_conditions || {};
      const autoTrigger = (playbook as any).auto_trigger_enabled || false;
      const priority = (playbook as any).trigger_priority || 0;
      
      setTriggerConditions(conditions);
      setAutoTriggerEnabled(autoTrigger);
      setTriggerPriority(priority);
      setRuleMappings((m) => ({
        ...m,
        alert_type: (playbook as any).alert_type || m.alert_type,
      }));
    }
  }, [playbook]);

  useEffect(() => {
    // Load recent alerts to test against
    listAlerts({ limit: 10 })
      .then((res) => {
        const alerts = res.alerts || [];
        setSampleAlerts(
          alerts.map((a: any) => ({
            id: a.id || a.alert_id || a._id,
            alert_type: a.alert_type,
            title: a.title || a.name || a.rule_name,
          }))
        );
      })
      .catch(() => {
        // ignore
      });
    // Load detection rules for mapping dropdown
    listDetectionRules()
      .then((rules) => {
        if (rules?.length) {
          setRuleMappings((m) => ({
            ...m,
            rule_id: m.rule_id || rules[0].id,
            alert_type: m.alert_type || rules[0].mapping?.alert_type || '',
          }));
        }
      })
      .catch(() => {
        // ignore
      });
  }, []);

  const { data: detectionRules } = useQuery({
    queryKey: ['detection-rules'],
    queryFn: listDetectionRules,
  });

  const updateTriggerConfig = useMutation({
    mutationFn: async (config: {
      trigger_conditions: TriggerCondition;
      auto_trigger_enabled: boolean;
      trigger_priority: number;
    }) => {
      // Update playbook with trigger configuration
      // Note: This will need to be added to the playbook update API
      await playbooksApi.update(playbookId, {
        ...config,
      } as any);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['playbook', playbookId] });
      toast.success('Trigger configuration saved');
    },
    onError: (error: any) => {
      toast.error(`Failed to save trigger configuration: ${error.message}`);
    },
  });

  const previewTrigger = async () => {
    if (!playbook) return;
    if (!sampleAlertId) {
      toast.error('Select a sample alert');
      return;
    }
    try {
      setValidating(true);
      const res = await playbooksApi.preview(playbookId, {
        alert_id: sampleAlertId,
        trigger_conditions: triggerConditions,
        auto_trigger_enabled: autoTriggerEnabled,
        trigger_priority: triggerPriority,
      });
      setPreviewResult({
        matches: (res as any)?.matching_playbooks?.length || 0,
        reasons: (res as any)?.matching_playbooks?.map((m: any) => m.trigger_reason || '') || [],
      });
      toast.success(res.valid ? 'Trigger matches' : 'No match');
    } catch (err: any) {
      toast.error(`Preview failed: ${err?.message || 'error'}`);
    } finally {
      setValidating(false);
    }
  };

  const handleSave = () => {
    updateTriggerConfig.mutate({
      trigger_conditions: triggerConditions,
      auto_trigger_enabled: autoTriggerEnabled,
      trigger_priority: triggerPriority,
    });
  };

  const saveMapping = async () => {
    if (!ruleMappings.rule_id || !ruleMappings.alert_type) {
      toast.error('Rule and alert type required');
      return;
    }
    try {
      await setDetectionRuleMapping(ruleMappings.rule_id, {
        alert_type: ruleMappings.alert_type,
        playbook_key: (playbook as any)?.playbook_key || playbookId,
        auto_execute: ruleMappings.auto_execute,
        requires_approval: ruleMappings.requires_approval,
      });
      toast.success('Mapping saved');
    } catch (err: any) {
      toast.error(err?.message || 'Failed to save mapping');
    }
  };

  if (isLoading) {
    return (
      <div className="h-screen flex items-center justify-center">
        <div className="text-text-muted dark:text-text-muted">Loading playbook...</div>
      </div>
    );
  }

  if (!playbook) {
    return (
      <div className="h-screen flex items-center justify-center">
        <div className="text-red-600">Playbook not found</div>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      <Breadcrumbs />
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-main">
            Trigger Configuration: {playbook.name}
          </h1>
          <p className="mt-1 text-sm text-text-muted dark:text-text-muted">
            Configure automated trigger conditions for this playbook
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={previewTrigger}
            disabled={validating}
            className="px-4 py-2 bg-surface-card text-white rounded-md hover:bg-surface-hover focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
          >
            {validating ? 'Validating...' : 'Preview'}
          </button>
          <button
            onClick={handleSave}
            disabled={updateTriggerConfig.isPending}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
          >
            {updateTriggerConfig.isPending ? 'Saving...' : 'Save Configuration'}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Configuration */}
        <div className="lg:col-span-2 space-y-6">
          {/* Auto-Trigger Toggle */}
          <div className="bg-surface-card rounded-lg shadow-sm border border-surface-card-border dark:border-surface-card-border p-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold text-text-main">
                  Auto-Trigger
                </h2>
                <p className="text-sm text-text-muted dark:text-text-muted mt-1">
                  Automatically trigger this playbook when conditions are met
                </p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={autoTriggerEnabled}
                  onChange={(e) => setAutoTriggerEnabled(e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-surface-hover peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 dark:peer-focus:ring-blue-800 rounded-full peer dark:bg-bg-alt peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-surface-card after:border-border after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-border peer-checked:bg-blue-600"></div>
              </label>
            </div>

            {autoTriggerEnabled && (
              <div className="mt-4">
                <label className="block text-sm font-medium text-text-muted dark:text-text-muted mb-2">
                  Trigger Priority
                </label>
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={triggerPriority}
                  onChange={(e) => setTriggerPriority(parseInt(e.target.value) || 0)}
                  className="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-bg-alt dark:border-border dark:text-white"
                  placeholder="0 (higher = evaluated first)"
                />
                <p className="text-xs text-text-muted dark:text-text-muted mt-1">
                  Higher priority playbooks are evaluated first when multiple triggers match
                </p>
              </div>
            )}
          </div>

          {/* Trigger Condition Builder */}
          {autoTriggerEnabled && (
            <TriggerConditionBuilder
              conditions={triggerConditions}
              onChange={setTriggerConditions}
            />
          )}

          {/* Preview against sample alerts */}
          {autoTriggerEnabled && (
            <div className="bg-surface-card rounded-lg shadow-sm border border-surface-card-border dark:border-surface-card-border p-6 space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-semibold text-text-main">Preview against alerts</h2>
                  <p className="text-sm text-text-muted dark:text-text-muted">Pick a recent alert and evaluate trigger conditions.</p>
                </div>
                <button
                  onClick={previewTrigger}
                  disabled={validating}
                  className="px-4 py-2 bg-surface-card text-white rounded-md hover:bg-surface-hover focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
                >
                  {validating ? 'Validating...' : 'Preview'}
                </button>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-text-muted dark:text-text-muted mb-1">Sample alert</label>
                  <select
                    className="w-full px-3 py-2 border rounded text-sm dark:bg-bg-alt dark:border-border dark:text-white"
                    value={sampleAlertId}
                    onChange={(e) => setSampleAlertId(e.target.value)}
                  >
                    <option value="">Select alert...</option>
                    {sampleAlerts.map((a) => (
                      <option key={a.id} value={a.id}>
                        {a.title || a.id} {a.alert_type ? `(${a.alert_type})` : ''}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-text-muted dark:text-text-muted mb-1">Priority</label>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    value={triggerPriority}
                    onChange={(e) => setTriggerPriority(parseInt(e.target.value) || 0)}
                    className="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-bg-alt dark:border-border dark:text-white"
                    placeholder="0 (higher = evaluated first)"
                  />
                </div>
              </div>
              {previewResult && (
                <div className="text-sm text-text-muted dark:text-text-muted">
                  Matches: {previewResult.matches}
                  {previewResult.reasons?.length ? (
                    <ul className="list-disc list-inside text-xs text-text-muted mt-1">
                      {previewResult.reasons.map((r, i) => (
                        <li key={i}>{r}</li>
                      ))}
                    </ul>
                  ) : null}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Trigger History */}
          <TriggerHistory playbookId={playbookId} />

          {/* Mapping UI */}
          <div className="bg-surface-card rounded-lg shadow-sm border border-surface-card-border dark:border-surface-card-border p-6 space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold text-text-main">Alert → Playbook Mapping</h2>
                <p className="text-sm text-text-muted dark:text-text-muted">Map an alert type to this playbook.</p>
              </div>
            </div>
            <div className="space-y-2">
              <label className="block text-sm font-medium text-text-muted dark:text-text-muted">Detection rule</label>
              <select
                className="w-full px-3 py-2 border rounded text-sm dark:bg-bg-alt dark:border-border dark:text-white"
                value={ruleMappings.rule_id}
                onChange={(e) => setRuleMappings((m) => ({ ...m, rule_id: e.target.value }))}
              >
                <option value="">Select rule...</option>
                {(detectionRules || []).map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.rule_key} — {r.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              <label className="block text-sm font-medium text-text-muted dark:text-text-muted">Alert type</label>
              <input
                className="w-full px-3 py-2 border rounded text-sm dark:bg-bg-alt dark:border-border dark:text-white"
                value={ruleMappings.alert_type}
                onChange={(e) => setRuleMappings((m) => ({ ...m, alert_type: e.target.value }))}
                placeholder="e.g., suspicious_login"
              />
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={ruleMappings.auto_execute}
                onChange={(e) => setRuleMappings((m) => ({ ...m, auto_execute: e.target.checked }))}
              />
              <span className="text-sm text-text-muted dark:text-text-muted">Auto-execute</span>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={ruleMappings.requires_approval}
                onChange={(e) => setRuleMappings((m) => ({ ...m, requires_approval: e.target.checked }))}
              />
              <span className="text-sm text-text-muted dark:text-text-muted">Requires approval</span>
            </div>
            <button
              onClick={saveMapping}
              className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              Save Mapping
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
