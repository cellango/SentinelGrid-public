/**
 * Terminal Node Component
 */

'use client';

import { Handle, Position } from 'reactflow';

export function TerminalNode({ data }: any) {
  const result = data.result || 'success';
  const colors = {
    success: {
      bg: 'bg-green-50 dark:bg-green-900/20',
      border: 'border-green-500 dark:border-green-400',
      text: 'text-green-700 dark:text-green-400',
      icon: '✅',
    },
    failure: {
      bg: 'bg-red-50 dark:bg-red-900/20',
      border: 'border-red-500 dark:border-red-400',
      text: 'text-red-700 dark:text-red-400',
      icon: '❌',
    },
    escalation: {
      bg: 'bg-orange-50 dark:bg-orange-900/20',
      border: 'border-orange-500 dark:border-orange-400',
      text: 'text-orange-700 dark:text-orange-400',
      icon: '⚠️',
    },
  };

  const style = colors[result as keyof typeof colors] || colors.success;

  return (
    <div
      className={`px-4 py-2 shadow-md rounded-md ${style.bg} border-2 ${style.border}`}
    >
      <Handle type="target" position={Position.Left} className={`w-3 h-3 ${style.border.replace('border-', 'bg-')}`} />
      <div className="flex items-center gap-2">
        <span className="text-xl">{style.icon}</span>
        <div>
          <div className={`font-bold ${style.text}`}>{data.label}</div>
          <div className={`text-xs ${style.text.replace('700', '600').replace('400', '300')}`}>
            {result}
          </div>
        </div>
      </div>
    </div>
  );
}

