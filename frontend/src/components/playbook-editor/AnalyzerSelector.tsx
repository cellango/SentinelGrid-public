/**
 * Analyzer Selector Component
 * Fetches analyzers from TheHive API and displays in dropdown
 */

'use client';

import { useQuery } from '@tanstack/react-query';
import { playbooksApi } from '@/lib/api/playbooks';

interface AnalyzerSelectorProps {
  id?: string;
  value: string;
  onChange: (analyzerId: string) => void;
  observableDataType?: string;
}

export function AnalyzerSelector({ id, value, onChange, observableDataType }: AnalyzerSelectorProps) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['analyzers', observableDataType],
    queryFn: () => playbooksApi.listAnalyzers(observableDataType),
  });

  const analyzers = data?.analyzers || [];

  if (isLoading) {
    return (
      <select
        id={id}
        disabled
        className="w-full px-3 py-2 border border-border rounded-md bg-bg-alt dark:bg-bg-alt dark:border-border"
      >
        <option>Loading analyzers...</option>
      </select>
    );
  }

  if (error) {
    return (
      <div className="text-sm text-red-600 dark:text-red-400">
        Failed to load analyzers
      </div>
    );
  }

  return (
    <select
      id={id}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-bg-alt dark:border-border dark:text-white"
    >
      <option value="">Select analyzer...</option>
      {analyzers.map((analyzer: any) => (
        <option key={analyzer.id} value={analyzer.id}>
          {analyzer.name || analyzer.id}
        </option>
      ))}
    </select>
  );
}
