/**
 * Policy Editor Component
 * Graphical editor for creating/editing policies
 */

'use client';

import { useState, useEffect, useRef } from 'react';
import { XMarkIcon, PlayIcon, QuestionMarkCircleIcon } from '@heroicons/react/24/outline';
import type { Policy } from '@/lib/api/iam-portal';

interface PolicyEditorProps {
  policy: Policy | null;
  policyType: 'signon' | 'access' | 'approval' | 'sod';
  onClose: () => void;
  onSave: (policy: Policy) => void | Promise<void>;
  onOpenVisualBuilder?: (policy: Policy | null) => void;
  savePending?: boolean;
  saveError?: string | null;
}

export default function PolicyEditor({
  policy,
  policyType,
  onClose,
  onSave,
  onOpenVisualBuilder,
  savePending = false,
  saveError = null,
}: PolicyEditorProps) {
  const [policyData, setPolicyData] = useState(policy?.policy_data || getDefaultPolicyData(policyType));
  const [displayName, setDisplayName] = useState(policy?.display_name || '');
  const [description, setDescription] = useState(policy?.description || '');
  const didHydrateInitialState = useRef(false);
  const policyNameFieldId = 'iam-policy-editor-name';
  const policyDescriptionFieldId = 'iam-policy-editor-description';
  
  useEffect(() => {
    if (!didHydrateInitialState.current) {
      didHydrateInitialState.current = true;
      return;
    }
    if (policy) {
      setPolicyData(policy.policy_data);
      setDisplayName(policy.display_name);
      setDescription(policy.description || '');
    } else {
      setPolicyData(getDefaultPolicyData(policyType));
      setDisplayName('');
      setDescription('');
    }
  }, [policy, policyType]);
  
  const handleSave = () => {
    if (!displayName.trim()) {
      alert('Please enter a policy name');
      return;
    }
    
    const updatedPolicy: Policy = {
      ...(policy || {} as Policy),
      id: policy?.id || '',
      tenant_id: policy?.tenant_id || '',
      name: displayName.toLowerCase().replace(/\s+/g, '-'),
      display_name: displayName,
      description: description,
      policy_type: policyType,
      policy_data: policyData,
      is_active: policy?.is_active ?? true,
      priority: policy?.priority ?? 100,
      created_at: policy?.created_at || new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    
    onSave(updatedPolicy);
  };
  
  return (
    <div className="bg-surface-card rounded-lg border border-surface-card-border">
      {/* Header */}
      <div className="p-4 border-b border-surface-card-border flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-text-main">
            {policy ? 'Edit Policy' : 'New Policy'}
          </h2>
          <p className="text-sm text-text-muted mt-1">
            {getPolicyTypeDescription(policyType)}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              // TODO: Show AI explanation
            }}
            className="p-2 text-text-muted hover:bg-bg-alt rounded transition-colors"
            title="Explain this policy"
          >
            <QuestionMarkCircleIcon className="w-5 h-5" />
          </button>
          <button
            onClick={onClose}
            className="p-2 text-text-muted hover:bg-bg-alt rounded transition-colors"
          >
            <XMarkIcon className="w-5 h-5" />
          </button>
        </div>
      </div>
      
      {/* Policy Info */}
      <div className="p-4 border-b border-surface-card-border space-y-4">
        <div className="rounded-lg border border-slate-700 bg-slate-900/60 px-4 py-3 text-sm text-text-muted">
          This inline editor saves policy metadata and the current rule JSON. For full condition, action, and graph editing,
          use the visual builder.
        </div>
        {saveError && (
          <div className="rounded-lg border border-red-700 bg-red-900/30 px-4 py-3 text-sm text-red-100">
            {saveError}
          </div>
        )}
        <div>
          <label htmlFor={policyNameFieldId} className="block text-sm font-medium text-text-muted mb-1">
            Policy Name *
          </label>
          <input
            id={policyNameFieldId}
            type="text"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="e.g., Admin Sign-on Policy"
          />
        </div>
        <div>
          <label htmlFor={policyDescriptionFieldId} className="block text-sm font-medium text-text-muted mb-1">
            Description
          </label>
          <textarea
            id={policyDescriptionFieldId}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={2}
            className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="Describe what this policy does..."
            data-testid="policy-editor-textarea"
          />
        </div>
      </div>
      
      {/* Policy Editor */}
      <div className="p-4">
        <div className="mb-4">
          <h3 className="text-sm font-medium text-text-muted mb-2">Policy Rules</h3>
          <p className="text-xs text-text-muted mb-4">
            Define conditions and actions for this policy. Rules are evaluated in priority order.
          </p>
        </div>
        
        {/* Simplified Rule Editor */}
        <div className="space-y-4">
          {policyData.rules?.map((rule: any, index: number) => (
            <RuleEditor
              key={rule.id || index}
              rule={rule}
              index={index}
              onOpenVisualBuilder={() => onOpenVisualBuilder?.(policy)}
              onChange={(updatedRule) => {
                const newRules = [...policyData.rules];
                newRules[index] = updatedRule;
                setPolicyData({ ...policyData, rules: newRules });
              }}
              onDelete={() => {
                const newRules = policyData.rules.filter((_: any, i: number) => i !== index);
                setPolicyData({ ...policyData, rules: newRules });
              }}
            />
          ))}
          
          <button
            onClick={() => {
              const newRule = {
                id: `rule-${Date.now()}`,
                name: `Rule ${(policyData.rules?.length || 0) + 1}`,
                conditions: [],
                actions: [],
                priority: 100,
              };
              setPolicyData({
                ...policyData,
                rules: [...(policyData.rules || []), newRule],
              });
            }}
            className="w-full py-3 border-2 border-dashed border-border rounded-lg text-text-muted hover:border-blue-500 hover:text-blue-600 transition-colors"
          >
            + Add Rule
          </button>
        </div>
      </div>
      
      {/* Footer */}
      <div className="p-4 border-t border-surface-card-border flex items-center justify-between">
        <button
          onClick={onClose}
          className="px-4 py-2 border border-border text-text-muted rounded-lg hover:bg-surface-hover transition-colors"
        >
          Discard Policy Edits
        </button>
        <div className="flex gap-2">
          <button
            onClick={() => onOpenVisualBuilder?.(policy)}
            className="flex items-center gap-2 px-4 py-2 border border-border text-text-muted rounded-lg hover:bg-surface-hover transition-colors"
            data-testid="policy-editor-test"
          >
            <PlayIcon className="w-4 h-4" />
            Open Visual Builder
          </button>
          <button
            onClick={handleSave}
            disabled={savePending}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-60"
            data-testid="policy-editor-save"
          >
            {savePending ? 'Saving...' : 'Save Policy'}
          </button>
        </div>
      </div>
    </div>
  );
}

function RuleEditor({
  rule,
  index,
  onChange,
  onDelete,
  onOpenVisualBuilder,
}: {
  rule: any;
  index: number;
  onChange: (rule: any) => void;
  onDelete: () => void;
  onOpenVisualBuilder: () => void;
}) {
  const [name, setName] = useState(rule.name || `Rule ${index + 1}`);

  return (
    <div className="border border-surface-card-border rounded-lg p-4">
      <div className="flex items-center justify-between mb-4">
        <input
          type="text"
          value={name}
          onChange={(e) => {
            const nextName = e.target.value;
            setName(nextName);
            onChange({ ...rule, name: nextName });
          }}
          className="flex-1 font-medium text-text-main border-none focus:outline-none focus:ring-0"
          placeholder="Rule name"
        />
        <button
          onClick={onDelete}
          className="text-red-600 hover:text-red-700 text-sm"
        >
          Remove Rule
        </button>
      </div>
      
      <div className="space-y-3">
        <div>
          <label className="block text-xs font-medium text-text-muted mb-1">Conditions</label>
          <div className="text-sm text-text-muted bg-surface-hover p-2 rounded">
            {rule.conditions?.length > 0 ? (
              <ul className="list-disc list-inside space-y-1">
                {rule.conditions.map((c: any, i: number) => (
                  <li key={i}>
                    {c.type} {c.op} {JSON.stringify(c.value)}
                  </li>
                ))}
              </ul>
            ) : (
              <span className="text-text-muted">No conditions (always matches)</span>
            )}
          </div>
          <button
            type="button"
            onClick={onOpenVisualBuilder}
            className="mt-2 text-xs text-blue-600 hover:text-blue-700"
          >
            Edit Conditions in Visual Builder
          </button>
        </div>
        
        <div>
          <label className="block text-xs font-medium text-text-muted mb-1">Actions</label>
          <div className="text-sm text-text-muted bg-surface-hover p-2 rounded">
            {rule.actions?.length > 0 ? (
              <ul className="list-disc list-inside space-y-1">
                {rule.actions.map((a: any, i: number) => (
                  <li key={i}>
                    {a.type} {a.value ? `: ${a.value}` : ''}
                  </li>
                ))}
              </ul>
            ) : (
              <span className="text-text-muted">No actions</span>
            )}
          </div>
          <button
            type="button"
            onClick={onOpenVisualBuilder}
            className="mt-2 text-xs text-blue-600 hover:text-blue-700"
          >
            Edit Actions in Visual Builder
          </button>
        </div>
      </div>
    </div>
  );
}

function getDefaultPolicyData(policyType: string) {
  return {
    id: `policy-${Date.now()}`,
    type: policyType,
    scope: 'tenant',
    rules: [],
  };
}

function getPolicyTypeDescription(policyType: string): string {
  const descriptions = {
    signon: 'Control when and how users can sign in',
    access: 'Define who can access which resources',
    approval: 'Configure approval workflows for access requests',
    sod: 'Enforce separation of duties and risk policies',
  };
  return descriptions[policyType as keyof typeof descriptions] || '';
}
