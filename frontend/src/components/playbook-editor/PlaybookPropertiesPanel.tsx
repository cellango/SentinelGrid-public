/**
 * Playbook Properties Panel Component
 * Configure selected node properties
 */

'use client';

import { useState, useEffect } from 'react';
import { Node } from 'reactflow';
import { AnalyzerSelector } from './AnalyzerSelector';

interface PlaybookPropertiesPanelProps {
  node: Node;
  onUpdate: (node: Node) => void;
}

export function PlaybookPropertiesPanel({ node, onUpdate }: PlaybookPropertiesPanelProps) {
  const [localNode, setLocalNode] = useState<Node>(node);
  const fieldId = (name: string) => `playbook-node-${node.id}-${name}`;

  useEffect(() => {
    setLocalNode(node);
  }, [node]);

  const handleUpdate = (updates: Partial<Node['data']>) => {
    const updated = {
      ...localNode,
      data: {
        ...localNode.data,
        ...updates,
      },
    };
    setLocalNode(updated);
    onUpdate(updated);
  };

  const renderNodeConfig = () => {
    switch (node.type) {
      case 'trigger':
        return (
          <div className="space-y-4">
            <div>
              <label htmlFor={fieldId('trigger-type')} className="block text-sm font-medium text-text-muted dark:text-text-muted mb-1">
                Trigger Type
              </label>
              <select
                id={fieldId('trigger-type')}
                value={localNode.data.trigger_type || 'manual'}
                onChange={(e) => handleUpdate({ trigger_type: e.target.value })}
                className="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-bg-alt dark:border-border dark:text-white"
              >
                <option value="manual">Manual</option>
                <option value="alert">Alert</option>
                <option value="incident">Incident</option>
                <option value="scheduled">Scheduled</option>
              </select>
            </div>
            {localNode.data.trigger_type === 'scheduled' && (
              <div>
                <label htmlFor={fieldId('cron-expression')} className="block text-sm font-medium text-text-muted dark:text-text-muted mb-1">
                  Cron Expression
                </label>
                <input
                  id={fieldId('cron-expression')}
                  type="text"
                  value={localNode.data.cron || ''}
                  onChange={(e) => handleUpdate({ cron: e.target.value })}
                  placeholder="0 0 * * *"
                  className="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-bg-alt dark:border-border dark:text-white"
                />
              </div>
            )}
          </div>
        );

      case 'action':
        return (
          <div className="space-y-4">
            <div>
              <label htmlFor={fieldId('action-type')} className="block text-sm font-medium text-text-muted dark:text-text-muted mb-1">
                Action Type
              </label>
              <select
                id={fieldId('action-type')}
                value={localNode.data.action_type || 'iam_action'}
                onChange={(e) => handleUpdate({ action_type: e.target.value })}
                className="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-bg-alt dark:border-border dark:text-white"
              >
                <option value="iam_action">IAM Action</option>
                <option value="email_action">Email Action</option>
                <option value="ticket_action">Ticket Action</option>
                <option value="notification">Notification</option>
              </select>
            </div>
            {localNode.data.action_type === 'iam_action' && (
              <div>
                <label htmlFor={fieldId('iam-operation')} className="block text-sm font-medium text-text-muted dark:text-text-muted mb-1">
                  IAM Operation
                </label>
                <select
                  id={fieldId('iam-operation')}
                  value={localNode.data.iam_operation || 'disable_sessions'}
                  onChange={(e) => handleUpdate({ iam_operation: e.target.value })}
                  className="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-bg-alt dark:border-border dark:text-white"
                >
                  <option value="disable_sessions">Disable Sessions</option>
                  <option value="force_password_reset">Force Password Reset</option>
                  <option value="enforce_mfa">Enforce MFA</option>
                  <option value="lock_account">Lock Account</option>
                </select>
              </div>
            )}
          </div>
        );

      case 'observable':
        return (
          <div className="space-y-4">
            <div>
              <label htmlFor={fieldId('data-type')} className="block text-sm font-medium text-text-muted dark:text-text-muted mb-1">
                Data Type
              </label>
              <select
                id={fieldId('data-type')}
                value={localNode.data.data_type || 'ip'}
                onChange={(e) => handleUpdate({ data_type: e.target.value })}
                className="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-bg-alt dark:border-border dark:text-white"
              >
                <option value="ip">IP Address</option>
                <option value="domain">Domain</option>
                <option value="url">URL</option>
                <option value="hash_md5">Hash (MD5)</option>
                <option value="hash_sha1">Hash (SHA1)</option>
                <option value="hash_sha256">Hash (SHA256)</option>
                <option value="email">Email Address</option>
                <option value="filename">Filename</option>
                <option value="filepath">File Path</option>
              </select>
            </div>
            <div>
              <label htmlFor={fieldId('extraction-path')} className="block text-sm font-medium text-text-muted dark:text-text-muted mb-1">
                Extraction Path (JSONPath)
              </label>
              <input
                id={fieldId('extraction-path')}
                type="text"
                value={localNode.data.extraction_path || ''}
                onChange={(e) => handleUpdate({ extraction_path: e.target.value })}
                placeholder="$.source.ip"
                className="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-bg-alt dark:border-border dark:text-white"
              />
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id={fieldId('mark-as-ioc')}
                checked={localNode.data.mark_as_ioc || false}
                onChange={(e) => handleUpdate({ mark_as_ioc: e.target.checked })}
                className="w-4 h-4 text-blue-600 border-border rounded focus:ring-blue-500"
              />
              <label htmlFor={fieldId('mark-as-ioc')} className="text-sm text-text-muted dark:text-text-muted">
                Mark as IOC
              </label>
            </div>
          </div>
        );

      case 'analyzer':
        return (
          <div className="space-y-4">
            <div>
              <label htmlFor={fieldId('analyzer-id')} className="block text-sm font-medium text-text-muted dark:text-text-muted mb-1">
                Analyzer ID
              </label>
              <AnalyzerSelector
                id={fieldId('analyzer-id')}
                value={localNode.data.analyzer_id || ''}
                onChange={(analyzerId) => handleUpdate({ analyzer_id: analyzerId })}
                observableDataType={localNode.data.observable_data_type}
              />
            </div>
            <div>
              <label htmlFor={fieldId('observable-node-id')} className="block text-sm font-medium text-text-muted dark:text-text-muted mb-1">
                Observable Source Node ID
              </label>
              <input
                id={fieldId('observable-node-id')}
                type="text"
                value={localNode.data.observable_node_id || ''}
                onChange={(e) => handleUpdate({ observable_node_id: e.target.value })}
                placeholder="node-id"
                className="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-bg-alt dark:border-border dark:text-white"
              />
            </div>
          </div>
        );

      case 'decision':
        return (
          <div className="space-y-4">
            <div>
              <label htmlFor={fieldId('decision-condition')} className="block text-sm font-medium text-text-muted dark:text-text-muted mb-1">
                Condition
              </label>
              <textarea
                id={fieldId('decision-condition')}
                value={localNode.data.condition || ''}
                onChange={(e) => handleUpdate({ condition: e.target.value })}
                placeholder="e.g., analyzer.verdict === 'malicious'"
                rows={4}
                className="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-bg-alt dark:border-border dark:text-white font-mono text-sm"
              />
            </div>
          </div>
        );

      case 'terminal':
        return (
          <div className="space-y-4">
            <div>
              <label htmlFor={fieldId('terminal-result')} className="block text-sm font-medium text-text-muted dark:text-text-muted mb-1">
                Result Type
              </label>
              <select
                id={fieldId('terminal-result')}
                value={localNode.data.result || 'success'}
                onChange={(e) => handleUpdate({ result: e.target.value })}
                className="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-bg-alt dark:border-border dark:text-white"
              >
                <option value="success">Success</option>
                <option value="failure">Failure</option>
                <option value="escalation">Escalation</option>
              </select>
            </div>
          </div>
        );

      default:
        return (
          <div className="text-sm text-text-muted dark:text-text-muted">
            No configuration available for this node type.
          </div>
        );
    }
  };

  return (
    <div className="p-4 space-y-4">
      <div className="border-b border-surface-card-border dark:border-surface-card-border pb-4">
        <h3 className="text-lg font-semibold text-text-main">Node Properties</h3>
        <p className="text-sm text-text-muted dark:text-text-muted mt-1">{node.type}</p>
      </div>

      <div>
        <label htmlFor={fieldId('node-label')} className="block text-sm font-medium text-text-muted dark:text-text-muted mb-1">
          Label
        </label>
        <input
          id={fieldId('node-label')}
          type="text"
          value={localNode.data.label || ''}
          onChange={(e) => handleUpdate({ label: e.target.value })}
          className="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-bg-alt dark:border-border dark:text-white"
        />
      </div>

      {renderNodeConfig()}
    </div>
  );
}
