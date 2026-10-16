/**
 * Detection Rule Builder (no-code)
 * Simple form-based builder that assembles OpenSearch DSL + trigger script, supports templates, preview, deploy.
 */

'use client';

import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import {
  DetectionRule,
  DetectionRuleVersion,
  createDetectionRule,
  deployDetectionRule,
  getDetectionRule,
  listDetectionRules,
  previewDetectionRule,
  DetectionRuleCreate,
  DeployRequest,
  PreviewResponse,
} from '@/lib/api/detection-rules';
import { toast } from 'react-hot-toast';
import { catalogApi, CatalogDetection } from '@/lib/api/catalogs';
import { getSourceHealth, type SourceHealth } from '@/lib/api/siem';
import { apiClient } from '@/lib/api/client';
import HealthBadge from '@/components/ui/HealthBadge';

type FilterRow = {
  field: string;
  operator: 'term' | 'match_phrase';
  value: string;
};

const SYSTEM_TENANT_ID = '9c7df7a9-5a0b-4412-a41c-0c0ea777b2f0';

export default function DetectionRuleBuilderPage() {
  const searchParams = useSearchParams();
  const { data: rules } = useQuery<DetectionRule[]>({
    queryKey: ['detection-rules'],
    queryFn: listDetectionRules,
  });
  const { data: catalogDetections } = useQuery<CatalogDetection[]>({
    queryKey: ['catalog-detections'],
    queryFn: catalogApi.listDetections,
  });
  const { data: sourceHealth } = useQuery<SourceHealth>({
    queryKey: ['source-health'],
    queryFn: getSourceHealth,
    retry: 1,
    staleTime: 30000,
  });

  const templates = useMemo(() => {
    return (rules || []).filter((r) => r.versions?.[0]?.is_template || (r.rule_key || '').startsWith('SG-DET'));
  }, [rules]);

  const [selectedTemplateId, setSelectedTemplateId] = useState<string>('');
  const [selectedCatalogId, setSelectedCatalogId] = useState<string>('');
  const [ruleId, setRuleId] = useState<string | null>(null);
  const [version, setVersion] = useState<DetectionRuleVersion | null>(null);
  const [name, setName] = useState('');
  const [ruleKey, setRuleKey] = useState('');
  const [category, setCategory] = useState('identity');
  const [description, setDescription] = useState('');
  const [severity, setSeverity] = useState('medium');
  const [indexPattern, setIndexPattern] = useState('sg-{tenant_id}-*');
  const [filters, setFilters] = useState<FilterRow[]>([{ field: 'event.action', operator: 'term', value: '' }]);
  const [timeRange, setTimeRange] = useState(60);
  const [threshold, setThreshold] = useState(1);
  const [destinationId, setDestinationId] = useState('');
  const [scheduleMinutes, setScheduleMinutes] = useState(5);
  const [previewData, setPreviewData] = useState<PreviewResponse | null>(null);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [loadingSave, setLoadingSave] = useState(false);
  const [loadingDeploy, setLoadingDeploy] = useState(false);
  const [preloadedRuleId, setPreloadedRuleId] = useState<string | null>(null);
  const [loadingSample, setLoadingSample] = useState(false);
  const fieldClass =
    "w-full border rounded px-3 py-2 text-sm bg-slate-900/80 text-text-main placeholder:text-slate-400 border-slate-700 focus:outline-none focus:ring-1 focus:ring-primary/70 focus:border-primary/50";
  const fieldClassSmall =
    "border rounded px-2 py-1 text-sm bg-slate-900/80 text-text-main placeholder:text-slate-400 border-slate-700 focus:outline-none focus:ring-1 focus:ring-primary/70 focus:border-primary/50";

  const loadTemplate = (tpl: DetectionRule) => {
    const v = tpl.versions?.[0];
    if (!v) return;
    setVersion(v);
    setRuleId(null);
    setName(tpl.name);
    setRuleKey(`${tpl.rule_key}-CLONE`);
    setCategory(tpl.category);
    setDescription(tpl.description || '');
    setSeverity(v.severity);
    setIndexPattern(v.index_pattern);
    setFilters([
      {
        field: v.query?.query?.bool?.filter?.[0]?.term ? Object.keys(v.query.query.bool.filter[0].term)[0] : 'event.action',
        operator: 'term',
        value: v.query?.query?.bool?.filter?.[0]?.term
          ? (Object.values(v.query.query.bool.filter[0].term)[0] as string)
          : '',
      },
    ]);
    setThreshold(1);
    setTimeRange(60);
    setPreviewData(null);
  };

  useEffect(() => {
    if (!selectedTemplateId) return;
    const tpl = templates.find((t) => t.id === selectedTemplateId);
    if (tpl) {
      loadTemplate(tpl);
    }
  }, [selectedTemplateId, templates]);

  const isUuid = (val: string) => /^[0-9a-fA-F-]{36}$/.test(val);

  const findRuleIdByKey = async (key: string): Promise<string | null> => {
    // First check cached rules
    const cached = (rules || []).find((r) => r.rule_key === key);
    if (cached?.id) return cached.id;
    try {
      const latest = await listDetectionRules();
      const found = latest.find((r) => r.rule_key === key);
      return found?.id || null;
    } catch {
      return null;
    }
  };

  const fetchRuleWithFallback = async (id: string): Promise<{ rule: DetectionRule; fallbackUsed: boolean }> => {
    try {
      const rule = await getDetectionRule(id);
      return { rule, fallbackUsed: false };
    } catch (err: any) {
      const status = err?.response?.status;
      if (status === 404 || status === 403) {
        const res = await apiClient.get<DetectionRule>(`/siem/detection-rules/${id}`, {
          headers: { 'X-Tenant-ID': SYSTEM_TENANT_ID },
        });
        return { rule: res.data, fallbackUsed: true };
      }
      throw err;
    }
  };

  const loadRuleForClone = async (id: string) => {
    try {
      const { rule, fallbackUsed } = await fetchRuleWithFallback(id);
      const v = rule.versions?.[0];
      if (!v) throw new Error('No version found on rule');
      setVersion(v);
      setRuleId(null); // clone into a new draft
      setName(`${rule.name} (Clone)`);
      setRuleKey(`${rule.rule_key}-CLONE`);
      setCategory(rule.category);
      setDescription(rule.description || '');
      setSeverity(v.severity);
      setIndexPattern(v.index_pattern);
      const graph = (v.graph_json as any) || {};
      setFilters(
        graph.filters || [
          { field: 'event.action', operator: 'term', value: '' },
        ]
      );
      setTimeRange(graph.time_range || 60);
      setThreshold(graph.threshold || 1);
      toast.success(fallbackUsed ? 'Loaded system detection (cloned into builder)' : 'Loaded detection into builder');
    } catch (err: any) {
      toast.error(err?.message || 'Failed to load rule into builder');
    }
  };

  // Auto-load when arriving with ?ruleId=... (from detail page deep-link)
  useEffect(() => {
    const rid = searchParams.get('ruleId');
    if (rid && rid !== preloadedRuleId) {
      setPreloadedRuleId(rid);
      loadRuleForClone(rid);
    }
  }, [searchParams, preloadedRuleId]);

  const loadCatalogTemplate = (tpl: CatalogDetection) => {
    setVersion(null);
    setRuleId(null);
    setName(tpl.name);
    setRuleKey(`${tpl.id}-CLONE`);
    setCategory(tpl.category);
    setDescription(tpl.incident_type || tpl.default_playbook_key || '');
    setSeverity(tpl.severity || 'medium');
    setIndexPattern('sg-{tenant_id}-*');
    setFilters([{ field: 'event.action', operator: 'term', value: '' }]);
    setThreshold(1);
    setTimeRange(60);
    setPreviewData(null);
  };

  useEffect(() => {
    if (!selectedCatalogId || !catalogDetections) return;
    const tpl = catalogDetections.find((t) => t.id === selectedCatalogId);
    if (tpl) {
      loadCatalogTemplate(tpl);
    }
  }, [selectedCatalogId, catalogDetections]);

  const buildQuery = () => {
    const filterClauses = filters
      .filter((f) => f.field && f.value)
      .map((f) => ({
        [f.operator]: { [f.field]: f.value },
      }));
    return {
      size: 0,
      query: {
        bool: {
          filter: filterClauses,
        },
      },
    };
  };

  const buildTrigger = () => ({
    script: {
      source: `return ctx.results[0].hits.total.value >= ${threshold};`,
    },
  });

  const graphJson = () => ({
    index_pattern: indexPattern,
    filters,
    time_range: timeRange,
    threshold,
    severity,
  });

  const handleSaveDraft = async () => {
    if (!name || !ruleKey) {
      toast.error('Name and rule key are required');
      return;
    }
    setLoadingSave(true);
    try {
      const payload: DetectionRuleCreate = {
        rule_key: ruleKey,
        name,
        description,
        category,
        approval_required: false,
        version: {
          version: version?.version || '1.0.0',
          index_pattern: indexPattern,
          query: buildQuery(),
          trigger_condition: buildTrigger(),
          severity,
          action_config: {},
          metadata: {
            alert_type: category,
            template_source: selectedTemplateId || null,
          },
          is_active: true,
          is_template: false,
          graph_json: graphJson(),
        },
      };
      const res = await createDetectionRule(payload);
      setRuleId(res.id);
      toast.success('Saved draft');
    } catch (err: any) {
      toast.error(err?.message || 'Save failed');
    } finally {
      setLoadingSave(false);
    }
  };

  const handleLoadExisting = async () => {
    const input = prompt('Enter rule ID or rule key to load');
    const trimmed = (input || '').trim();
    if (!trimmed) return;
    try {
      let targetId = trimmed;
      if (!isUuid(trimmed)) {
        const byKey = await findRuleIdByKey(trimmed);
        if (!byKey) {
          toast.error('Rule key not found');
          return;
        }
        targetId = byKey;
      }
      const { rule, fallbackUsed } = await fetchRuleWithFallback(targetId);
      const v = rule.versions?.[0];
      if (!v) throw new Error('No version found on rule');
      if (fallbackUsed) {
        setRuleId(null);
        setName(`${rule.name} (Clone)`);
        setRuleKey(`${rule.rule_key}-CLONE`);
      } else {
        setRuleId(rule.id);
        setName(rule.name);
        setRuleKey(rule.rule_key);
      }
      setCategory(rule.category);
      setDescription(rule.description || '');
      setSeverity(v.severity);
      setIndexPattern(v.index_pattern);
      setFilters(
        (v.graph_json as any)?.filters || [
          { field: 'event.action', operator: 'term', value: '' },
        ]
      );
      setTimeRange((v.graph_json as any)?.time_range || 60);
      setThreshold((v.graph_json as any)?.threshold || 1);
      toast.success(fallbackUsed ? 'Loaded system detection (cloned)' : 'Loaded rule');
    } catch (err: any) {
      toast.error(err?.message || 'Failed to load rule');
    }
  };

  const handlePreview = async () => {
    if (!ruleId) {
      toast.error('Save the rule first, then preview');
      return;
    }
    setLoadingPreview(true);
    try {
      const res = await previewDetectionRule(ruleId, {
        index_pattern: indexPattern,
        query: buildQuery(),
        trigger_condition: buildTrigger(),
        time_range_minutes: timeRange,
      });
      setPreviewData(res);
      toast.success('Preview complete');
    } catch (err: any) {
      toast.error(err?.message || 'Preview failed');
    } finally {
      setLoadingPreview(false);
    }
  };

  const handleDeploy = async () => {
    if (!ruleId) {
      toast.error('Save the rule first');
      return;
    }
    if (!destinationId.trim()) {
      toast.error('Destination ID is required to deploy');
      return;
    }
    setLoadingDeploy(true);
    try {
      const payload: DeployRequest = {
        destination_id: destinationId,
        auto_execute: true,
        schedule_minutes: scheduleMinutes,
        severity,
      };
      const res = await deployDetectionRule(ruleId, payload);
      toast.success(res.deployed ? 'Deployed monitor' : `Status: ${res.approval_status || 'pending'}`);
    } catch (err: any) {
      toast.error(err?.message || 'Deploy failed');
    } finally {
      setLoadingDeploy(false);
    }
  };

  return (
    <div className="p-6 space-y-4 min-h-screen bg-slate-950 text-text-main">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-text-main">Detection Rule Builder</h1>
          <p className="text-sm text-text-muted">Create or clone an alarm without writing DSL.</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleLoadExisting}
            className="px-3 py-2 border border-slate-700 bg-slate-800/70 text-text-main rounded text-sm hover:border-primary/60"
          >
            Load Existing Rule
          </button>
          <button
            onClick={handleSaveDraft}
            disabled={loadingSave}
            className="px-4 py-2 bg-blue-600 text-white rounded text-sm disabled:opacity-50 hover:bg-blue-500"
          >
            {loadingSave ? 'Creating Draft Rule...' : 'Create Draft Rule'}
          </button>
          <button
            onClick={handleDeploy}
            disabled={loadingDeploy}
            className="px-4 py-2 bg-green-600 text-white rounded text-sm disabled:opacity-50 hover:bg-green-500"
          >
            {loadingDeploy ? 'Deploying Rule...' : 'Create and Deploy Rule'}
          </button>
        </div>
      </div>
      <div className="flex flex-wrap gap-2 text-xs text-text-muted">
        <span className="uppercase tracking-wide">Pipeline health</span>
        <HealthBadge label="Ingestion" status={sourceHealth?.ingestion_service} />
        <HealthBadge label="SIEM agent" status={sourceHealth?.siem_agent} />
        <HealthBadge label="OpenSearch" status={sourceHealth?.opensearch} />
      </div>
      <div className="flex flex-wrap gap-2 text-xs text-text-muted">
        <span className="uppercase tracking-wide">Sample data</span>
        {[
          { label: 'AI sample', source: 'ai' },
          { label: 'Auth sample', source: 'auth' },
          { label: 'Endpoint sample', source: 'endpoint' },
          { label: 'Network sample', source: 'network' },
          { label: 'Cloud sample', source: 'cloud' },
          { label: 'Git sample', source: 'git' },
        ].map((item) => (
          <button
            key={item.source}
            onClick={async () => {
              setLoadingSample(true);
              try {
                await apiClient.post('/ingestion/load-sample', { source: item.source });
                toast.success(`Loaded ${item.label.toLowerCase()}`);
              } catch (err: any) {
                toast.error(err?.message || `Failed to load ${item.label.toLowerCase()}`);
              } finally {
                setLoadingSample(false);
              }
            }}
            className="px-2 py-1 rounded border border-surface-card-border bg-slate-900/70 text-text-main hover:border-primary/60 disabled:opacity-50"
            disabled={loadingSample}
          >
            {loadingSample ? 'Loading…' : item.label}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Builder form */}
        <div className="lg:col-span-2 space-y-4">
          <div className="bg-surface-card rounded border border-surface-card-border p-4 space-y-3">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-text-muted">Template</label>
                <select
                  value={selectedTemplateId}
                  onChange={(e) => setSelectedTemplateId(e.target.value)}
                  className={fieldClass}
                >
                  <option value="">None</option>
                  {templates.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.rule_key} — {t.name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs text-text-muted">Catalog (100 OOTB)</label>
                <select
                  value={selectedCatalogId}
                  onChange={(e) => setSelectedCatalogId(e.target.value)}
                  className={fieldClass}
                >
                  <option value="">None</option>
                  {(catalogDetections || []).map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.id} — {t.name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs text-text-muted">Rule Key</label>
                <input
                  className={fieldClass}
                  value={ruleKey}
                  onChange={(e) => setRuleKey(e.target.value)}
                  placeholder="SG-DET-XXX"
                />
              </div>
              <div>
                <label className="block text-xs text-text-muted">Name</label>
                <input
                  className={fieldClass}
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </div>
              <div>
                <label className="block text-xs text-text-muted">Category</label>
                <input
                  className={fieldClass}
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                />
              </div>
            </div>
            <div>
              <label className="block text-xs text-text-muted">Description</label>
              <textarea
                className={fieldClass}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </div>
          </div>

          <div className="bg-surface-card rounded border border-surface-card-border p-4 space-y-3">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-text-muted">Index pattern</label>
                <input
                  className={fieldClass}
                  value={indexPattern}
                  onChange={(e) => setIndexPattern(e.target.value)}
                />
              </div>
              <div>
                <label className="block text-xs text-text-muted">Severity</label>
                <select
                  className={fieldClass}
                  value={severity}
                  onChange={(e) => setSeverity(e.target.value)}
                >
                  {['critical', 'high', 'medium', 'low', 'informational'].map((s) => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs text-text-muted">Time range (minutes)</label>
                <input
                  type="number"
                  className={fieldClass}
                  value={timeRange}
                  onChange={(e) => setTimeRange(parseInt(e.target.value) || 60)}
                  min={1}
                />
              </div>
              <div>
                <label className="block text-xs text-text-muted">Threshold (count ≥)</label>
                <input
                  type="number"
                  className={fieldClass}
                  value={threshold}
                  onChange={(e) => setThreshold(parseInt(e.target.value) || 1)}
                  min={1}
                />
              </div>
            </div>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-xs text-text-muted">Filters</label>
                <button
                  className="text-sm text-primary hover:text-primary/80"
                  onClick={() => setFilters((f) => [...f, { field: '', operator: 'term', value: '' }])}
                >
                  + Add filter
                </button>
              </div>
              {filters.map((f, idx) => (
                <div key={idx} className="grid grid-cols-12 gap-2">
                  <input
                    className={`col-span-5 ${fieldClassSmall}`}
                    placeholder="field"
                    value={f.field}
                    onChange={(e) => {
                      const copy = [...filters];
                      copy[idx].field = e.target.value;
                      setFilters(copy);
                    }}
                  />
                  <select
                    className={`col-span-2 ${fieldClassSmall}`}
                    value={f.operator}
                    onChange={(e) => {
                      const copy = [...filters];
                      copy[idx].operator = e.target.value as FilterRow['operator'];
                      setFilters(copy);
                    }}
                  >
                    <option value="term">term</option>
                    <option value="match_phrase">match_phrase</option>
                  </select>
                  <input
                    className={`col-span-4 ${fieldClassSmall}`}
                    placeholder="value"
                    value={f.value}
                    onChange={(e) => {
                      const copy = [...filters];
                      copy[idx].value = e.target.value;
                      setFilters(copy);
                    }}
                  />
                  <button
                    className="col-span-1 text-xs text-red-500"
                    onClick={() => setFilters((cur) => cur.filter((_, i) => i !== idx))}
                    disabled={filters.length === 1}
                  >
                    ✕
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-4">
          <div className="bg-surface-card rounded border border-surface-card-border p-4 space-y-3">
            <div>
              <label className="block text-xs text-text-muted">Destination ID (webhook)</label>
              <input
                className={fieldClass}
                value={destinationId}
                onChange={(e) => setDestinationId(e.target.value)}
                placeholder="opensearch destination id"
              />
            </div>
            <div>
              <label className="block text-xs text-text-muted">Schedule (minutes)</label>
              <input
                type="number"
                className={fieldClass}
                value={scheduleMinutes}
                onChange={(e) => setScheduleMinutes(parseInt(e.target.value) || 5)}
                min={1}
              />
            </div>
            <div className="flex gap-2">
              <button
                onClick={handlePreview}
                disabled={loadingPreview}
                className="px-3 py-2 border border-slate-700 bg-slate-800/70 text-text-main rounded text-sm w-full hover:border-primary/60"
              >
                {loadingPreview ? 'Previewing Detection Hits...' : 'Preview Detection Hits'}
              </button>
              <button
                onClick={handleDeploy}
                disabled={loadingDeploy}
                className="px-3 py-2 bg-green-600 text-white rounded text-sm w-full disabled:opacity-50 hover:bg-green-500"
              >
                {loadingDeploy ? 'Deploying Rule...' : 'Deploy Detection Rule'}
              </button>
            </div>
            {ruleId && (
              <div className="text-xs text-text-muted">
                Saved as rule ID: <span className="font-mono">{ruleId}</span>
              </div>
            )}
          </div>

          <div className="bg-surface-card rounded border border-surface-card-border p-4 space-y-2">
            <div className="text-sm font-semibold text-text-main">OpenSearch Query (preview)</div>
            <pre className="text-xs bg-slate-900 p-2 rounded border border-slate-800 overflow-x-auto text-text-main">
{JSON.stringify(buildQuery(), null, 2)}
            </pre>
            <div className="text-sm font-semibold text-text-main">Trigger</div>
            <pre className="text-xs bg-slate-900 p-2 rounded border border-slate-800 overflow-x-auto text-text-main">
{JSON.stringify(buildTrigger(), null, 2)}
            </pre>
          </div>

          {previewData && (
            <div className="bg-surface-card rounded border border-surface-card-border p-4 space-y-2">
              <div className="text-sm font-semibold text-text-main">Preview Results</div>
              <div className="text-xs text-text-muted">Hits: {previewData.hits}</div>
              {previewData.aggregations && (
                <pre className="text-xs bg-slate-900 p-2 rounded border border-slate-800 overflow-x-auto text-text-main">
{JSON.stringify(previewData.aggregations, null, 2)}
                </pre>
              )}
              {previewData.sample?.length ? (
                <pre className="text-xs bg-slate-900 p-2 rounded border border-slate-800 overflow-x-auto text-text-main">
{JSON.stringify(previewData.sample.slice(0, 3), null, 2)}
                </pre>
              ) : (
                <div className="text-xs text-text-muted">No samples returned</div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
