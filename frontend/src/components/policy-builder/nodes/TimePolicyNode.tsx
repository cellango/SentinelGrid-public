/**
 * Time Policy Node Component
 * Visual representation of a time-based policy node
 */

'use client';

import { Handle, Position } from 'reactflow';
import { TimePolicyData } from '@/lib/policy/types';

interface TimePolicyNodeProps {
  data: TimePolicyData & { label: string; selected?: boolean };
  selected?: boolean;
}

const DAY_NAMES = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

function formatTime(hour: number, minute: number): string {
  const h = hour.toString().padStart(2, '0');
  const m = minute.toString().padStart(2, '0');
  return `${h}:${m}`;
}

function formatDays(daysOfWeek: number[]): string {
  if (daysOfWeek.length === 0) return 'No days';
  if (daysOfWeek.length === 7) return 'Every day';
  if (daysOfWeek.length === 5 && daysOfWeek.includes(1) && daysOfWeek.includes(5)) {
    return 'Weekdays';
  }
  return daysOfWeek.map((d) => DAY_NAMES[d]).join(', ');
}

export function TimePolicyNode({ data, selected }: TimePolicyNodeProps) {
  const timeRange = `${formatTime(data.hour, data.minute)} - ${formatTime(data.hourEnd, data.minuteEnd)}`;
  const days = formatDays(data.daysOfWeek || []);

  return (
    <div
      className={`px-4 py-3 bg-surface-card border-2 rounded-lg shadow-sm min-w-[180px] ${
        selected ? 'border-orange-500' : 'border-orange-300'
      }`}
      style={{ borderColor: selected ? '#F59E0B' : '#FCD34D' }}
    >
      <Handle type="target" position={Position.Top} className="w-3 h-3" />
      
      <div className="flex items-start gap-2">
        <div className="w-8 h-8 rounded-lg bg-orange-100 flex items-center justify-center flex-shrink-0">
          <span className="text-orange-600 text-lg">⏰</span>
        </div>
        <div className="flex-1 min-w-0">
          <div className="font-medium text-sm text-text-main">{data.label}</div>
          <div className="text-xs text-text-muted mt-1 space-y-0.5">
            <div className="truncate">{timeRange}</div>
            <div className="truncate">{days}</div>
          </div>
        </div>
      </div>

      <Handle type="source" position={Position.Bottom} className="w-3 h-3" />
    </div>
  );
}

