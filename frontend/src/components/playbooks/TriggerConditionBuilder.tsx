/**
 * Trigger Condition Builder Component
 * Visual builder for playbook trigger conditions
 */

'use client';

import { useState } from 'react';
import { TriggerCondition } from '@/lib/api/automated-response';

interface TriggerConditionBuilderProps {
  conditions: TriggerCondition;
  onChange: (conditions: TriggerCondition) => void;
}

export default function TriggerConditionBuilder({
  conditions,
  onChange,
}: TriggerConditionBuilderProps) {
  const [severityOptions, setSeverityOptions] = useState<string[]>(
    conditions.severity || []
  );
  const [categoryOptions, setCategoryOptions] = useState<string[]>(
    conditions.category || []
  );
  const [sourceOptions, setSourceOptions] = useState<string[]>(
    conditions.source || []
  );
  const [timeWindow, setTimeWindow] = useState<string>(
    conditions.time_window || ''
  );

  const severityChoices = ['critical', 'high', 'medium', 'low', 'informational'];
  const categoryChoices = ['phishing', 'malware', 'suspicious_login', 'brute_force', 'data_exfiltration', 'privilege_escalation'];
  const sourceChoices = ['siem_agent', 'detection_service', 'email_ingestion', 'iam_agent'];

  const updateConditions = () => {
    const newConditions: TriggerCondition = {};
    
    if (severityOptions.length > 0) {
      newConditions.severity = severityOptions;
    }
    if (categoryOptions.length > 0) {
      newConditions.category = categoryOptions;
    }
    if (sourceOptions.length > 0) {
      newConditions.source = sourceOptions;
    }
    if (timeWindow) {
      newConditions.time_window = timeWindow;
    }
    
    onChange(newConditions);
  };

  const toggleSeverity = (severity: string) => {
    const newOptions = severityOptions.includes(severity)
      ? severityOptions.filter(s => s !== severity)
      : [...severityOptions, severity];
    setSeverityOptions(newOptions);
    onChange({ ...conditions, severity: newOptions });
  };

  const toggleCategory = (category: string) => {
    const newOptions = categoryOptions.includes(category)
      ? categoryOptions.filter(c => c !== category)
      : [...categoryOptions, category];
    setCategoryOptions(newOptions);
    onChange({ ...conditions, category: newOptions });
  };

  const toggleSource = (source: string) => {
    const newOptions = sourceOptions.includes(source)
      ? sourceOptions.filter(s => s !== source)
      : [...sourceOptions, source];
    setSourceOptions(newOptions);
    onChange({ ...conditions, source: newOptions });
  };

  const handleTimeWindowChange = (value: string) => {
    setTimeWindow(value);
    onChange({ ...conditions, time_window: value });
  };

  return (
    <div className="bg-surface-card rounded-lg shadow-sm border border-surface-card-border dark:border-surface-card-border p-6">
      <h2 className="text-lg font-semibold text-text-main mb-4">
        Trigger Conditions
      </h2>
      <p className="text-sm text-text-muted dark:text-text-muted mb-6">
        Configure when this playbook should be automatically triggered. All selected conditions must match.
      </p>

      {/* Severity */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-text-muted dark:text-text-muted mb-2">
          Alert Severity
        </label>
        <div className="flex flex-wrap gap-2">
          {severityChoices.map((severity) => (
            <button
              key={severity}
              type="button"
              onClick={() => toggleSeverity(severity)}
              className={`px-3 py-1 rounded-md text-sm font-medium transition-colors ${
                severityOptions.includes(severity)
                  ? 'bg-blue-600 text-white'
                  : 'bg-bg-alt text-text-muted hover:bg-surface-hover dark:bg-bg-alt dark:text-text-muted dark:hover:bg-bg-alt'
              }`}
            >
              {severity.charAt(0).toUpperCase() + severity.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Category */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-text-muted dark:text-text-muted mb-2">
          Alert Category
        </label>
        <div className="flex flex-wrap gap-2">
          {categoryChoices.map((category) => (
            <button
              key={category}
              type="button"
              onClick={() => toggleCategory(category)}
              className={`px-3 py-1 rounded-md text-sm font-medium transition-colors ${
                categoryOptions.includes(category)
                  ? 'bg-blue-600 text-white'
                  : 'bg-bg-alt text-text-muted hover:bg-surface-hover dark:bg-bg-alt dark:text-text-muted dark:hover:bg-bg-alt'
              }`}
            >
              {category.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
            </button>
          ))}
        </div>
      </div>

      {/* Source */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-text-muted dark:text-text-muted mb-2">
          Alert Source
        </label>
        <div className="flex flex-wrap gap-2">
          {sourceChoices.map((source) => (
            <button
              key={source}
              type="button"
              onClick={() => toggleSource(source)}
              className={`px-3 py-1 rounded-md text-sm font-medium transition-colors ${
                sourceOptions.includes(source)
                  ? 'bg-blue-600 text-white'
                  : 'bg-bg-alt text-text-muted hover:bg-surface-hover dark:bg-bg-alt dark:text-text-muted dark:hover:bg-bg-alt'
              }`}
            >
              {source.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
            </button>
          ))}
        </div>
      </div>

      {/* Time Window */}
      <div>
        <label className="block text-sm font-medium text-text-muted dark:text-text-muted mb-2">
          Time Window (optional)
        </label>
        <input
          type="text"
          value={timeWindow}
          onChange={(e) => handleTimeWindowChange(e.target.value)}
          placeholder="e.g., 5m, 1h, 24h"
          className="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-bg-alt dark:border-border dark:text-white"
        />
        <p className="text-xs text-text-muted dark:text-text-muted mt-1">
          Only trigger if alert is within this time window (e.g., "5m" = 5 minutes, "1h" = 1 hour)
        </p>
      </div>
    </div>
  );
}

