/**
 * Policy Builder Page
 * Main page for creating and editing tenant policy graphs
 */

'use client';

import { useState, useEffect } from 'react';
import dynamic from 'next/dynamic';
import { policiesApi, PolicyTemplate } from '@/lib/api/policies';
import { rolesApi, TenantRole } from '@/lib/api/roles';
import { toast } from 'react-hot-toast';
import { graphToKeycloakJSON } from '@/lib/policy/graph-to-json';
import { parseKeycloakPolicyJSON, keycloakJSONToGraph } from '@/lib/policy/json-to-graph';
import { useSearchParams } from 'next/navigation';
import { PolicyEvaluationResult } from '@/lib/api/policies';
import { listPolicyBundles } from '@/lib/api/iam-portal';

const PolicyBuilderCanvasWrapper = dynamic(
  () =>
    import('@/components/policy-builder/PolicyBuilderCanvas').then(
      (mod) => mod.PolicyBuilderCanvasWrapper
    ),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-full min-h-[32rem] items-center justify-center rounded-xl border border-border-faint bg-surface-card">
        <p className="text-sm text-text-muted">Loading policy builder…</p>
      </div>
    ),
  }
);

interface Role {
  id: string;
  name: string;
}

export default function PolicyBuilderPage() {
  const evalUserIdFieldId = 'policy-builder-eval-user-id';
  const evalResourceFieldId = 'policy-builder-eval-resource';
  const evalActionFieldId = 'policy-builder-eval-action';
  const evalJsonFieldId = 'policy-builder-eval-json';
  const [roles, setRoles] = useState<Role[]>([]);
  const [rolesError, setRolesError] = useState<string | null>(null);
  const [templates, setTemplates] = useState<PolicyTemplate[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<PolicyTemplate | null>(null);
  const [policyName, setPolicyName] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [policyType, setPolicyType] = useState('access');
  const [importGraph, setImportGraph] = useState<{ nodes: any[]; edges: any[] } | null>(null);
  const [graphKey, setGraphKey] = useState<string>('initial');
  const [graphStats, setGraphStats] = useState<{ nodes: number; edges: number }>({ nodes: 0, edges: 0 });
  const [evalContext, setEvalContext] = useState({
    user_id: '',
    resource: '',
    action: '',
  });
  const [evalContextJson, setEvalContextJson] = useState<string>('');
  const [evaluationResult, setEvaluationResult] = useState<PolicyEvaluationResult | null>(null);
  const searchParams = useSearchParams();
  const policyId = searchParams.get('policy_id');
  const seedId = searchParams.get('seed_id');
  const readOnly = searchParams.get('read_only') === '1' || searchParams.get('readonly') === '1';

  const buildGraphFromRules = (policy: any) => {
    const rules = policy?.policy_data?.rules || [];
    if (!Array.isArray(rules) || rules.length === 0) {
      throw new Error('No rules to visualize');
    }
    const aggId = 'agg-root';
    const nodes: any[] = [
      {
        id: aggId,
        type: 'aggregateNode',
        position: { x: 250, y: 100 },
        data: {
          label: policy.display_name || policy.name || 'Authorization Policy',
          type: 'aggregate',
          gateType: 'AND',
          decisionStrategy: 'UNANIMOUS',
          logic: 'POSITIVE',
        },
      },
    ];
    const edges: any[] = [];
    rules.forEach((rule: any, idx: number) => {
      const nodeId = `rule-${idx}`;
      nodes.push({
        id: nodeId,
        type: 'jsPolicy',
        position: { x: 200, y: 200 + idx * 120 },
        data: {
          label: rule.id || `Rule ${idx + 1}`,
          type: 'js',
          logic: 'POSITIVE',
          code: JSON.stringify(rule, null, 2),
          description: 'Rule preview (read-only)',
        },
      });
      edges.push({
        id: `edge-${aggId}-${nodeId}`,
        source: aggId,
        target: nodeId,
        type: 'smoothstep',
      });
    });
    return { nodes, edges };
  };

  // Normalize policy_data in case API returns it as a JSON string
  const ensurePolicyDataObject = (policy: any) => {
    if (!policy) return policy;
    if (policy.policy_data && typeof policy.policy_data === 'string') {
      try {
        return { ...policy, policy_data: JSON.parse(policy.policy_data) };
      } catch (err) {
        // Leave as-is; downstream handling will show an error toast
        return policy;
      }
    }
    return policy;
  };

  useEffect(() => {
    rolesApi
      .list()
      .then((roleList: TenantRole[]) => {
        setRoles(roleList.map((role) => ({ id: role.id, name: role.name })));
        setRolesError(null);
      })
      .catch((err: any) => {
        const message = err?.message || 'Failed to load tenant roles';
        setRoles([]);
        setRolesError(message);
        toast.error(message);
      });

    policiesApi.listTemplates()
      .then(setTemplates)
      .catch(() => toast.error('Failed to load policy templates'));
  }, []);

  useEffect(() => {
    // Prefer tenant policy load; fallback to seed preview if seed_id provided
    if (policyId) {
      policiesApi.get(policyId)
        .then((policy) => {
          const normalized = ensurePolicyDataObject(policy);
          setPolicyName(policy.name);
          setDisplayName(policy.display_name);
          setPolicyType(policy.policy_type || 'access');
          try {
            const parsed = parseKeycloakPolicyJSON(JSON.stringify(normalized.policy_data));
            const graph = keycloakJSONToGraph(parsed);
            setImportGraph(graph);
            setGraphKey(`policy-${policyId}-${graph.nodes?.length || 0}-${graph.edges?.length || 0}`);
            setGraphStats({ nodes: graph.nodes?.length || 0, edges: graph.edges?.length || 0 });
            toast.success('Loaded policy into canvas');
          } catch (err: any) {
            try {
              const graph = buildGraphFromRules(normalized);
              setImportGraph(graph);
              setGraphKey(`policy-rules-${policyId}-${graph.nodes?.length || 0}-${graph.edges?.length || 0}`);
              setGraphStats({ nodes: graph.nodes?.length || 0, edges: graph.edges?.length || 0 });
              toast.success('Loaded policy into canvas');
            } catch (fallbackErr: any) {
              toast.error(fallbackErr?.message || err?.message || 'Failed to import policy graph');
            }
          }
        })
        .catch(() => toast.error('Failed to load policy'));
    } else if (seedId) {
      listPolicyBundles()
        .then((bundles) => {
          const seed = bundles.find((b) => b.id === seedId);
          if (!seed) {
            toast.error('Seed policy not found');
            return;
          }
          const normalized = ensurePolicyDataObject(seed);
          setPolicyName(seed.name);
          setDisplayName(seed.display_name);
          setPolicyType(seed.policy_type || 'authorization');
          try {
            // Seed policies can contain simplified DSL; render via fallback graph to avoid parse errors.
            const graph = buildGraphFromRules(normalized);
            setImportGraph(graph);
            setGraphKey(`seed-rules-${seed.id}-${graph.nodes?.length || 0}-${graph.edges?.length || 0}`);
            setGraphStats({ nodes: graph.nodes?.length || 0, edges: graph.edges?.length || 0 });
            toast.success(`Previewing seed policy (${graph.nodes?.length || 0} nodes)`);
          } catch (err: any) {
            console.error('[PolicyBuilder] Failed to load seed policy', err);
            toast.error(err?.message || 'Failed to import policy graph');
          }
        })
        .catch(() => toast.error('Failed to load seed policy'));
    }
  }, [policyId, seedId]);

  // Debug reporting when a graph is received
  useEffect(() => {
    if (importGraph) {
      const n = importGraph.nodes?.length || 0;
      if (n === 0) {
        toast.error('Policy graph is empty; check seed/policy data');
      }
    }
  }, [importGraph]);

  const handleSave = async (nodes: any[], edges: any[]) => {
    if (readOnly) {
      throw new Error('Read-only preview: clone the policy first to edit or save it.');
    }
    if (!policyName || !displayName) {
      throw new Error('Name and display name are required');
    }
    const policyJson = graphToKeycloakJSON(nodes, edges, displayName || policyName);
    if (policyId) {
      await policiesApi.update(policyId, {
        name: policyName,
        display_name: displayName,
        policy_type: policyType,
        policy_data: policyJson,
      });
      return;
    }
    await policiesApi.create({
      name: policyName,
      display_name: displayName,
      description: '',
      policy_type: policyType,
      scope: 'tenant',
      policy_data: policyJson,
      is_active: true,
      priority: 100,
    });
  };

  const handleTest = async (nodes: any[], edges: any[]) => {
    try {
      let parsedContext: Record<string, any> = {};
      if (evalContextJson.trim()) {
        try {
          parsedContext = JSON.parse(evalContextJson);
        } catch (parseErr) {
          toast.error('Context JSON is invalid');
          return;
        }
      }
      const mergedContext = {
        ...parsedContext,
        ...(evalContext.user_id ? { user_id: evalContext.user_id } : {}),
        ...(evalContext.resource ? { resource: evalContext.resource } : {}),
        ...(evalContext.action ? { action: evalContext.action } : {}),
      };

      const result = await policiesApi.evaluate(policyType, {
        context: mergedContext,
        policy_data: graphToKeycloakJSON(nodes, edges, displayName || policyName || 'policy'),
      });
      setEvaluationResult(result);
    } catch (err: any) {
      throw new Error(err?.message || 'Policy evaluation failed');
    }
  };

  return (
    <div className="h-screen flex flex-col">
      <div className="p-4 border-b border-surface-card-border flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-text-main" data-testid="policy-builder-title">Policy Builder</h1>
          <p className="text-sm text-text-muted">
            Compose tenant policy graphs for authorization, access, sign-on, and approval workflows
            {readOnly ? ' (preview only)' : ''}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {readOnly && (
            <span
              className="px-2 py-1 text-xs rounded bg-amber-100 text-amber-800 border border-amber-200"
              data-testid="policy-builder-readonly"
            >
              Read-only preview
            </span>
          )}
          <input
            type="text"
            value={policyName}
            onChange={(e) => setPolicyName(e.target.value)}
            placeholder="Policy name"
            disabled={readOnly}
            className="px-3 py-2 border rounded text-sm"
          />
          <input
            type="text"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder="Display name"
            disabled={readOnly}
            className="px-3 py-2 border rounded text-sm"
          />
          <select
            value={policyType}
            onChange={(e) => setPolicyType(e.target.value)}
            disabled={readOnly}
            className="px-3 py-2 border rounded text-sm"
          >
            <option value="authorization">Authorization</option>
            <option value="access">Access</option>
            <option value="signon">Sign-on</option>
            <option value="approval">Approval</option>
          </select>
          <select
            value={selectedTemplate?.id || ''}
            onChange={(e) => {
              if (readOnly) return;
              const tpl = templates.find(t => t.id === e.target.value) || null;
              setSelectedTemplate(tpl);
              if (tpl) {
                try {
                  const policyJson = parseKeycloakPolicyJSON(JSON.stringify(tpl.template_data));
                  const graph = keycloakJSONToGraph(policyJson);
                  setImportGraph(graph);
                  setGraphKey(`template-${tpl.id}-${graph.nodes?.length || 0}-${graph.edges?.length || 0}`);
                  setGraphStats({ nodes: graph.nodes?.length || 0, edges: graph.edges?.length || 0 });
                  setPolicyType(tpl.policy_type || 'access');
                  setPolicyName(tpl.name);
                  setDisplayName(tpl.display_name);
                  toast.success(`Loaded template ${tpl.display_name}`);
                } catch (err: any) {
                  toast.error(err?.message || 'Failed to load template');
                }
              }
            }}
            disabled={readOnly}
            className="px-3 py-2 border rounded text-sm"
          >
            <option value="">Templates...</option>
            {templates.map((tpl) => (
              <option key={tpl.id} value={tpl.id}>
                {tpl.display_name}
              </option>
            ))}
          </select>
          <button
            onClick={() => {
              if (readOnly) {
                toast.error('Read-only preview: template cloning is disabled.');
                return;
              }
              if (!selectedTemplate) return toast.error('Select a template first');
              const name = prompt('New policy name?', `${selectedTemplate.name}-copy`);
              const display = prompt('Display name?', selectedTemplate.display_name);
              if (!name || !display) return;
              policiesApi.createFromTemplate(selectedTemplate.id, name, display)
                .then(() => toast.success('Policy created from template'))
                .catch((err: any) => toast.error(err?.message || 'Clone failed'));
            }}
            disabled={readOnly}
            className="px-3 py-2 bg-bg-alt border rounded text-sm disabled:opacity-60 disabled:cursor-not-allowed"
          >
            Clone Template
          </button>
        </div>
      </div>

      <div className="flex-1 flex">
        {/* Sidebar for evaluation context */}
        <div className="w-64 border-r border-surface-card-border p-4 space-y-3">
          <h3 className="text-sm font-semibold text-text-main">Test Context</h3>
          {rolesError && (
            <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
              Role-backed nodes are available, but live tenant roles could not be loaded for this session.
            </div>
          )}
          <div className="space-y-2">
            <div>
              <label htmlFor={evalUserIdFieldId} className="block text-xs text-text-muted">
                User ID
              </label>
              <input
                id={evalUserIdFieldId}
                className="w-full px-2 py-1 border rounded text-sm"
                value={evalContext.user_id}
                onChange={(e) => setEvalContext((ctx) => ({ ...ctx, user_id: e.target.value }))}
              />
            </div>
            <div>
              <label htmlFor={evalResourceFieldId} className="block text-xs text-text-muted">
                Resource
              </label>
              <input
                id={evalResourceFieldId}
                className="w-full px-2 py-1 border rounded text-sm"
                value={evalContext.resource}
                onChange={(e) => setEvalContext((ctx) => ({ ...ctx, resource: e.target.value }))}
              />
            </div>
            <div>
              <label htmlFor={evalActionFieldId} className="block text-xs text-text-muted">
                Action
              </label>
              <input
                id={evalActionFieldId}
                className="w-full px-2 py-1 border rounded text-sm"
                value={evalContext.action}
                onChange={(e) => setEvalContext((ctx) => ({ ...ctx, action: e.target.value }))}
              />
            </div>
            <div>
              <label htmlFor={evalJsonFieldId} className="block text-xs text-text-muted">
                Context JSON (advanced)
              </label>
              <textarea
                id={evalJsonFieldId}
                className="w-full px-2 py-1 border rounded text-sm h-24"
                placeholder='{"user_id":"123","resource":"file-1","action":"read","groups":["analyst"]}'
                value={evalContextJson}
                onChange={(e) => setEvalContextJson(e.target.value)}
              />
              <p className="text-[11px] text-text-muted mt-1">
                Merged with the fields above for evaluate requests.
              </p>
            </div>
          </div>
          {evaluationResult && (
            <div className="mt-4 border-t border-surface-card-border pt-3 space-y-1">
              <div className="text-xs uppercase text-text-muted">Last evaluation</div>
              <div className="text-sm font-semibold text-text-main">
                Result: {evaluationResult.result}
              </div>
              {evaluationResult.explanation && (
                <div className="text-xs text-text-muted">{evaluationResult.explanation}</div>
              )}
              {evaluationResult.matched_rules?.length ? (
                <div className="text-xs text-text-muted">
                  Matched rules: {evaluationResult.matched_rules.join(', ')}
                </div>
              ) : (
                <div className="text-xs text-text-muted">No rules matched</div>
              )}
            </div>
          )}
        </div>

        <PolicyBuilderCanvasWrapper
          key={graphKey}
          onSave={handleSave}
          onTest={handleTest}
          roles={roles}
          initialNodes={importGraph?.nodes}
          initialEdges={importGraph?.edges}
          readonly={readOnly}
        />
      </div>
      <div className="fixed bottom-4 right-6 rounded-full bg-slate-900/90 text-slate-100 px-4 py-2 shadow-lg text-xs">
        Canvas: {graphStats.nodes} nodes · {graphStats.edges} edges
      </div>
    </div>
  );
}
