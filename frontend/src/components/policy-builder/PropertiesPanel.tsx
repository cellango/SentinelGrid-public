/**
 * Properties Panel Component
 * Shows and allows editing of selected node properties
 */

'use client';

import { useState, useEffect } from 'react';
import { Node } from 'reactflow';
import {
  RolePolicyData,
  TimePolicyData,
  IPPolicyData,
  AggregatePolicyData,
  PolicyLogic,
  DecisionStrategy,
  AggregateGateType,
} from '@/lib/policy/types';

interface PropertiesPanelProps {
  selectedNode: Node | null;
  onUpdateNode: (nodeId: string, data: any) => void;
  roles?: Array<{ id: string; name: string }>; // For role policy
  readonly?: boolean;
}

const DAY_NAMES = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

export function PropertiesPanel({
  selectedNode,
  onUpdateNode,
  roles = [],
  readonly = false,
}: PropertiesPanelProps) {
  const [localData, setLocalData] = useState<any>(null);

  useEffect(() => {
    if (selectedNode) {
      setLocalData(selectedNode.data);
    } else {
      setLocalData(null);
    }
  }, [selectedNode]);

  if (!selectedNode || !localData) {
    return (
      <div className="w-80 bg-surface-card border-l border-surface-card-border h-full flex items-center justify-center">
        <p className="text-sm text-text-muted">
          {readonly ? 'Select a node to inspect properties' : 'Select a node to edit properties'}
        </p>
      </div>
    );
  }

  const editorBodyClassName = readonly ? 'pointer-events-none opacity-60' : '';

  const handleSave = () => {
    if (selectedNode) {
      onUpdateNode(selectedNode.id, localData);
    }
  };

  const handleChange = (field: string, value: any) => {
    setLocalData((prev: any) => ({
      ...prev,
      [field]: value,
    }));
  };

  // Role Policy Panel
  if (localData.type === 'role') {
    const data = localData as RolePolicyData & { label: string };
    const selectedRoles = data.roles || [];

    return (
      <div className="w-80 bg-surface-card border-l border-surface-card-border h-full overflow-y-auto">
        <div className="p-4 border-b border-surface-card-border sticky top-0 bg-surface-card z-10">
          <h3 className="text-sm font-semibold text-text-main">Properties: Role Policy</h3>
        </div>

        <div className={`p-4 space-y-4 ${editorBodyClassName}`}>
          <div>
            <label className="block text-sm font-medium text-text-muted mb-2">
              Policy Name
            </label>
            <input
              type="text"
              value={data.label || ''}
              onChange={(e) => handleChange('label', e.target.value)}
              className="w-full px-3 py-2 border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-text-muted mb-2">
              Roles <span className="text-red-500">*</span>
            </label>
            <div className="space-y-2 max-h-48 overflow-y-auto border border-surface-card-border rounded-md p-2">
              {roles.length === 0 ? (
                <p className="text-xs text-text-muted">Loading roles...</p>
              ) : (
                roles.map((role) => {
                  const isSelected = selectedRoles.some((r) => r.id === role.id);
                  return (
                    <label
                      key={role.id}
                      className="flex items-center gap-2 p-2 hover:bg-surface-hover rounded cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={(e) => {
                          if (e.target.checked) {
                            handleChange('roles', [
                              ...selectedRoles,
                              { id: role.id, name: role.name, required: true },
                            ]);
                          } else {
                            handleChange(
                              'roles',
                              selectedRoles.filter((r) => r.id !== role.id)
                            );
                          }
                        }}
                        className="rounded border-border text-blue-600 focus:ring-blue-500"
                      />
                      <span className="text-sm text-text-muted">{role.name}</span>
                    </label>
                  );
                })
              )}
            </div>
          </div>

          <div>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={selectedRoles.every((r) => r.required) && selectedRoles.length > 0}
                onChange={(e) => {
                  handleChange(
                    'roles',
                    selectedRoles.map((r) => ({ ...r, required: e.target.checked }))
                  );
                }}
                className="rounded border-border text-blue-600 focus:ring-blue-500"
              />
              <span className="text-sm text-text-muted">All roles required (UNANIMOUS)</span>
            </label>
          </div>

          <div>
            <label className="block text-sm font-medium text-text-muted mb-2">Logic</label>
            <div className="space-y-2">
              <label className="flex items-center gap-2">
                <input
                  type="radio"
                  name="logic"
                  value="POSITIVE"
                  checked={data.logic === 'POSITIVE'}
                  onChange={(e) => handleChange('logic', e.target.value as PolicyLogic)}
                  className="border-border text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-text-muted">Positive (Allow)</span>
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="radio"
                  name="logic"
                  value="NEGATIVE"
                  checked={data.logic === 'NEGATIVE'}
                  onChange={(e) => handleChange('logic', e.target.value as PolicyLogic)}
                  className="border-border text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-text-muted">Negative (Deny)</span>
              </label>
            </div>
          </div>

          <div className="pt-4 border-t border-surface-card-border">
            <button
              onClick={handleSave}
              className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm font-medium"
            >
              Save Changes
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Time Policy Panel
  if (localData.type === 'time') {
    const data = localData as TimePolicyData & { label: string };
    const selectedDays = data.daysOfWeek || [];

    return (
      <div className="w-80 bg-surface-card border-l border-surface-card-border h-full overflow-y-auto">
        <div className="p-4 border-b border-surface-card-border sticky top-0 bg-surface-card z-10">
          <h3 className="text-sm font-semibold text-text-main">Properties: Time Policy</h3>
        </div>

        <div className={`p-4 space-y-4 ${editorBodyClassName}`}>
          <div>
            <label className="block text-sm font-medium text-text-muted mb-2">
              Policy Name
            </label>
            <input
              type="text"
              value={data.label || ''}
              onChange={(e) => handleChange('label', e.target.value)}
              className="w-full px-3 py-2 border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-text-muted mb-2">Days of Week</label>
            <div className="grid grid-cols-2 gap-2">
              {DAY_NAMES.map((day, index) => (
                <label
                  key={index}
                  className="flex items-center gap-2 p-2 border border-surface-card-border rounded hover:bg-surface-hover cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={selectedDays.includes(index)}
                    onChange={(e) => {
                      if (e.target.checked) {
                        handleChange('daysOfWeek', [...selectedDays, index].sort());
                      } else {
                        handleChange(
                          'daysOfWeek',
                          selectedDays.filter((d) => d !== index)
                        );
                      }
                    }}
                    className="rounded border-border text-blue-600 focus:ring-blue-500"
                  />
                  <span className="text-sm text-text-muted">{day}</span>
                </label>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-text-muted mb-2">Start Time</label>
              <div className="flex gap-2">
                <input
                  type="number"
                  min="0"
                  max="23"
                  value={data.hour}
                  onChange={(e) => handleChange('hour', parseInt(e.target.value) || 0)}
                  className="w-1/2 px-3 py-2 border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Hour"
                />
                <input
                  type="number"
                  min="0"
                  max="59"
                  value={data.minute}
                  onChange={(e) => handleChange('minute', parseInt(e.target.value) || 0)}
                  className="w-1/2 px-3 py-2 border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Min"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-text-muted mb-2">End Time</label>
              <div className="flex gap-2">
                <input
                  type="number"
                  min="0"
                  max="23"
                  value={data.hourEnd}
                  onChange={(e) => handleChange('hourEnd', parseInt(e.target.value) || 0)}
                  className="w-1/2 px-3 py-2 border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Hour"
                />
                <input
                  type="number"
                  min="0"
                  max="59"
                  value={data.minuteEnd}
                  onChange={(e) => handleChange('minuteEnd', parseInt(e.target.value) || 0)}
                  className="w-1/2 px-3 py-2 border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Min"
                />
              </div>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-text-muted mb-2">Timezone</label>
            <select
              value={data.timezone || 'UTC'}
              onChange={(e) => handleChange('timezone', e.target.value)}
              className="w-full px-3 py-2 border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="UTC">UTC</option>
              <option value="America/New_York">America/New_York (EST/EDT)</option>
              <option value="America/Chicago">America/Chicago (CST/CDT)</option>
              <option value="America/Denver">America/Denver (MST/MDT)</option>
              <option value="America/Los_Angeles">America/Los_Angeles (PST/PDT)</option>
              <option value="Europe/London">Europe/London (GMT/BST)</option>
            </select>
          </div>

          <div className="pt-4 border-t border-surface-card-border">
            <button
              onClick={handleSave}
              className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm font-medium"
            >
              Save Changes
            </button>
          </div>
        </div>
      </div>
    );
  }

  // IP Policy Panel
  if (localData.type === 'ip') {
    const data = localData as IPPolicyData & { label: string };
    const ipAddresses = data.ipAddresses || [];

    return (
      <div className="w-80 bg-surface-card border-l border-surface-card-border h-full overflow-y-auto">
        <div className="p-4 border-b border-surface-card-border sticky top-0 bg-surface-card z-10">
          <h3 className="text-sm font-semibold text-text-main">Properties: IP Policy</h3>
        </div>

        <div className={`p-4 space-y-4 ${editorBodyClassName}`}>
          <div>
            <label className="block text-sm font-medium text-text-muted mb-2">
              Policy Name
            </label>
            <input
              type="text"
              value={data.label || ''}
              onChange={(e) => handleChange('label', e.target.value)}
              className="w-full px-3 py-2 border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-text-muted mb-2">
              IP Addresses (CIDR) <span className="text-red-500">*</span>
            </label>
            <div className="space-y-2">
              {ipAddresses.map((ip, index) => (
                <div key={index} className="flex gap-2">
                  <input
                    type="text"
                    value={ip}
                    onChange={(e) => {
                      const newIPs = [...ipAddresses];
                      newIPs[index] = e.target.value;
                      handleChange('ipAddresses', newIPs);
                    }}
                    placeholder="10.0.0.0/8"
                    className="flex-1 px-3 py-2 border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <button
                    onClick={() => {
                      handleChange(
                        'ipAddresses',
                        ipAddresses.filter((_, i) => i !== index)
                      );
                    }}
                    className="px-3 py-2 text-sm text-red-600 hover:bg-red-50 rounded-md"
                  >
                    ×
                  </button>
                </div>
              ))}
              <button
                onClick={() => {
                  handleChange('ipAddresses', [...ipAddresses, '']);
                }}
                className="w-full px-3 py-2 text-sm border border-border rounded-md text-text-muted hover:bg-surface-hover"
              >
                + Add IP Range
              </button>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-text-muted mb-2">Logic</label>
            <div className="space-y-2">
              <label className="flex items-center gap-2">
                <input
                  type="radio"
                  name="logic"
                  value="POSITIVE"
                  checked={data.logic === 'POSITIVE'}
                  onChange={(e) => handleChange('logic', e.target.value as PolicyLogic)}
                  className="border-border text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-text-muted">Positive (Allow)</span>
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="radio"
                  name="logic"
                  value="NEGATIVE"
                  checked={data.logic === 'NEGATIVE'}
                  onChange={(e) => handleChange('logic', e.target.value as PolicyLogic)}
                  className="border-border text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-text-muted">Negative (Deny)</span>
              </label>
            </div>
          </div>

          <div className="pt-4 border-t border-surface-card-border">
            <button
              onClick={handleSave}
              className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm font-medium"
            >
              Save Changes
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Aggregate Node Panel
  if (localData.type === 'aggregate') {
    const data = localData as AggregatePolicyData & { label: string; gateType: AggregateGateType };

    return (
      <div className="w-80 bg-surface-card border-l border-surface-card-border h-full overflow-y-auto">
        <div className="p-4 border-b border-surface-card-border sticky top-0 bg-surface-card z-10">
          <h3 className="text-sm font-semibold text-text-main">Properties: {data.gateType} Gate</h3>
        </div>

        <div className={`p-4 space-y-4 ${editorBodyClassName}`}>
          <div>
            <label className="block text-sm font-medium text-text-muted mb-2">
              Gate Name
            </label>
            <input
              type="text"
              value={data.label || ''}
              onChange={(e) => handleChange('label', e.target.value)}
              className="w-full px-3 py-2 border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {data.gateType === 'AND' && (
            <div>
              <label className="block text-sm font-medium text-text-muted mb-2">
                Decision Strategy
              </label>
              <select
                value={data.decisionStrategy || 'UNANIMOUS'}
                onChange={(e) =>
                  handleChange('decisionStrategy', e.target.value as DecisionStrategy)
                }
                className="w-full px-3 py-2 border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="UNANIMOUS">UNANIMOUS (All must grant)</option>
                <option value="AFFIRMATIVE">AFFIRMATIVE (At least one grants)</option>
                <option value="CONSENSUS">CONSENSUS (Majority grants)</option>
              </select>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-text-muted mb-2">Logic</label>
            <div className="space-y-2">
              <label className="flex items-center gap-2">
                <input
                  type="radio"
                  name="logic"
                  value="POSITIVE"
                  checked={data.logic === 'POSITIVE'}
                  onChange={(e) => handleChange('logic', e.target.value as PolicyLogic)}
                  className="border-border text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-text-muted">Positive (Allow)</span>
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="radio"
                  name="logic"
                  value="NEGATIVE"
                  checked={data.logic === 'NEGATIVE'}
                  onChange={(e) => handleChange('logic', e.target.value as PolicyLogic)}
                  className="border-border text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-text-muted">Negative (Deny)</span>
              </label>
            </div>
          </div>

          <div className="pt-4 border-t border-surface-card-border">
            <button
              onClick={handleSave}
              className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm font-medium"
            >
              Save Changes
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Group Policy Panel
  if (localData.type === 'group') {
    const data = localData as any & { label: string };
    const selectedGroups = data.groups || [];

    return (
      <div className="w-80 bg-surface-card border-l border-surface-card-border h-full overflow-y-auto">
        <div className="p-4 border-b border-surface-card-border sticky top-0 bg-surface-card z-10">
          <h3 className="text-sm font-semibold text-text-main">Properties: Group Policy</h3>
        </div>

        <div className={`p-4 space-y-4 ${editorBodyClassName}`}>
          <div>
            <label className="block text-sm font-medium text-text-muted mb-2">
              Policy Name
            </label>
            <input
              type="text"
              value={data.label || ''}
              onChange={(e) => handleChange('label', e.target.value)}
              className="w-full px-3 py-2 border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-text-muted mb-2">
              Groups <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              placeholder="Enter group IDs (comma-separated)"
              className="w-full px-3 py-2 border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              onChange={(e) => {
                const groupIds = e.target.value
                  .split(',')
                  .map((id) => id.trim())
                  .filter(Boolean);
                handleChange(
                  'groups',
                  groupIds.map((id) => ({ id, name: id, extendChildren: false }))
                );
              }}
              value={selectedGroups.map((g: any) => g.id || g.name).join(', ')}
            />
            <p className="mt-1 text-xs text-text-muted">
              Enter group IDs separated by commas
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-text-muted mb-2">Logic</label>
            <div className="space-y-2">
              <label className="flex items-center gap-2">
                <input
                  type="radio"
                  name="logic"
                  value="POSITIVE"
                  checked={data.logic === 'POSITIVE'}
                  onChange={(e) => handleChange('logic', e.target.value as PolicyLogic)}
                  className="border-border text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-text-muted">Positive (Allow)</span>
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="radio"
                  name="logic"
                  value="NEGATIVE"
                  checked={data.logic === 'NEGATIVE'}
                  onChange={(e) => handleChange('logic', e.target.value as PolicyLogic)}
                  className="border-border text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-text-muted">Negative (Deny)</span>
              </label>
            </div>
          </div>

          <div className="pt-4 border-t border-surface-card-border">
            <button
              onClick={handleSave}
              className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm font-medium"
            >
              Save Changes
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Client Policy Panel
  if (localData.type === 'client') {
    const data = localData as any & { label: string };
    const clients = data.clients || [];

    return (
      <div className="w-80 bg-surface-card border-l border-surface-card-border h-full overflow-y-auto">
        <div className="p-4 border-b border-surface-card-border sticky top-0 bg-surface-card z-10">
          <h3 className="text-sm font-semibold text-text-main">Properties: Client Policy</h3>
        </div>

        <div className={`p-4 space-y-4 ${editorBodyClassName}`}>
          <div>
            <label className="block text-sm font-medium text-text-muted mb-2">
              Policy Name
            </label>
            <input
              type="text"
              value={data.label || ''}
              onChange={(e) => handleChange('label', e.target.value)}
              className="w-full px-3 py-2 border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-text-muted mb-2">
              Clients <span className="text-red-500">*</span>
            </label>
            <div className="space-y-2">
              {clients.map((client: string, index: number) => (
                <div key={index} className="flex gap-2">
                  <input
                    type="text"
                    value={client}
                    onChange={(e) => {
                      const newClients = [...clients];
                      newClients[index] = e.target.value;
                      handleChange('clients', newClients);
                    }}
                    placeholder="client-id"
                    className="flex-1 px-3 py-2 border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <button
                    onClick={() => {
                      handleChange(
                        'clients',
                        clients.filter((_: any, i: number) => i !== index)
                      );
                    }}
                    className="px-3 py-2 text-sm text-red-600 hover:bg-red-50 rounded-md"
                  >
                    ×
                  </button>
                </div>
              ))}
              <button
                onClick={() => {
                  handleChange('clients', [...clients, '']);
                }}
                className="w-full px-3 py-2 text-sm border border-border rounded-md text-text-muted hover:bg-surface-hover"
              >
                + Add Client
              </button>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-text-muted mb-2">Logic</label>
            <div className="space-y-2">
              <label className="flex items-center gap-2">
                <input
                  type="radio"
                  name="logic"
                  value="POSITIVE"
                  checked={data.logic === 'POSITIVE'}
                  onChange={(e) => handleChange('logic', e.target.value as PolicyLogic)}
                  className="border-border text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-text-muted">Positive (Allow)</span>
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="radio"
                  name="logic"
                  value="NEGATIVE"
                  checked={data.logic === 'NEGATIVE'}
                  onChange={(e) => handleChange('logic', e.target.value as PolicyLogic)}
                  className="border-border text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-text-muted">Negative (Deny)</span>
              </label>
            </div>
          </div>

          <div className="pt-4 border-t border-surface-card-border">
            <button
              onClick={handleSave}
              className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm font-medium"
            >
              Save Changes
            </button>
          </div>
        </div>
      </div>
    );
  }

  // User Policy Panel
  if (localData.type === 'user') {
    const data = localData as any & { label: string };
    const users = data.users || [];

    return (
      <div className="w-80 bg-surface-card border-l border-surface-card-border h-full overflow-y-auto">
        <div className="p-4 border-b border-surface-card-border sticky top-0 bg-surface-card z-10">
          <h3 className="text-sm font-semibold text-text-main">Properties: User Policy</h3>
        </div>

        <div className={`p-4 space-y-4 ${editorBodyClassName}`}>
          <div>
            <label className="block text-sm font-medium text-text-muted mb-2">
              Policy Name
            </label>
            <input
              type="text"
              value={data.label || ''}
              onChange={(e) => handleChange('label', e.target.value)}
              className="w-full px-3 py-2 border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-text-muted mb-2">
              Users <span className="text-red-500">*</span>
            </label>
            <div className="space-y-2">
              {users.map((user: string, index: number) => (
                <div key={index} className="flex gap-2">
                  <input
                    type="text"
                    value={user}
                    onChange={(e) => {
                      const newUsers = [...users];
                      newUsers[index] = e.target.value;
                      handleChange('users', newUsers);
                    }}
                    placeholder="user-id or username"
                    className="flex-1 px-3 py-2 border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <button
                    onClick={() => {
                      handleChange(
                        'users',
                        users.filter((_: any, i: number) => i !== index)
                      );
                    }}
                    className="px-3 py-2 text-sm text-red-600 hover:bg-red-50 rounded-md"
                  >
                    ×
                  </button>
                </div>
              ))}
              <button
                onClick={() => {
                  handleChange('users', [...users, '']);
                }}
                className="w-full px-3 py-2 text-sm border border-border rounded-md text-text-muted hover:bg-surface-hover"
              >
                + Add User
              </button>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-text-muted mb-2">Logic</label>
            <div className="space-y-2">
              <label className="flex items-center gap-2">
                <input
                  type="radio"
                  name="logic"
                  value="POSITIVE"
                  checked={data.logic === 'POSITIVE'}
                  onChange={(e) => handleChange('logic', e.target.value as PolicyLogic)}
                  className="border-border text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-text-muted">Positive (Allow)</span>
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="radio"
                  name="logic"
                  value="NEGATIVE"
                  checked={data.logic === 'NEGATIVE'}
                  onChange={(e) => handleChange('logic', e.target.value as PolicyLogic)}
                  className="border-border text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-text-muted">Negative (Deny)</span>
              </label>
            </div>
          </div>

          <div className="pt-4 border-t border-surface-card-border">
            <button
              onClick={handleSave}
              className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm font-medium"
            >
              Save Changes
            </button>
          </div>
        </div>
      </div>
    );
  }

  // JavaScript Policy Panel
  if (localData.type === 'js') {
    const data = localData as any & { label: string };

    return (
      <div className="w-80 bg-surface-card border-l border-surface-card-border h-full overflow-y-auto">
        <div className="p-4 border-b border-surface-card-border sticky top-0 bg-surface-card z-10">
          <h3 className="text-sm font-semibold text-text-main">Properties: JavaScript Policy</h3>
        </div>

        <div className={`p-4 space-y-4 ${editorBodyClassName}`}>
          <div>
            <label className="block text-sm font-medium text-text-muted mb-2">
              Policy Name
            </label>
            <input
              type="text"
              value={data.label || ''}
              onChange={(e) => handleChange('label', e.target.value)}
              className="w-full px-3 py-2 border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-text-muted mb-2">
              JavaScript Code <span className="text-red-500">*</span>
            </label>
            <textarea
              value={data.code || ''}
              onChange={(e) => handleChange('code', e.target.value)}
              placeholder="// Enter JavaScript code for policy evaluation&#10;var context = $evaluation.getContext();&#10;..."
              className="w-full px-3 py-2 border border-border rounded-md text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500"
              rows={12}
            />
            <p className="mt-1 text-xs text-text-muted">
              Use Keycloak JavaScript policy syntax. Access context via $evaluation.
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-text-muted mb-2">Logic</label>
            <div className="space-y-2">
              <label className="flex items-center gap-2">
                <input
                  type="radio"
                  name="logic"
                  value="POSITIVE"
                  checked={data.logic === 'POSITIVE'}
                  onChange={(e) => handleChange('logic', e.target.value as PolicyLogic)}
                  className="border-border text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-text-muted">Positive (Allow)</span>
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="radio"
                  name="logic"
                  value="NEGATIVE"
                  checked={data.logic === 'NEGATIVE'}
                  onChange={(e) => handleChange('logic', e.target.value as PolicyLogic)}
                  className="border-border text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-text-muted">Negative (Deny)</span>
              </label>
            </div>
          </div>

          <div className="pt-4 border-t border-surface-card-border">
            <button
              onClick={handleSave}
              className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm font-medium"
            >
              Save Changes
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Default panel for other node types
  return (
    <div className="w-80 bg-surface-card border-l border-surface-card-border h-full flex items-center justify-center">
      <p className="text-sm text-text-muted">Properties panel for this node type coming soon</p>
    </div>
  );
}
