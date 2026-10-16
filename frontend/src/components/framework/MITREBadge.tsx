'use client';

interface MITREBadgeProps {
  type: 'tactic' | 'technique';
  id: string;
  name?: string;
}

export default function MITREBadge({ type, id, name }: MITREBadgeProps) {
  const label = type === 'tactic' ? 'Tactic' : 'Technique';
  const colorClass = type === 'tactic' 
    ? 'bg-purple-500/20 text-purple-400 border-purple-500/30'
    : 'bg-pink-500/20 text-pink-400 border-pink-500/30';

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${colorClass}`}
      title={name || `MITRE ${label} ${id}`}
    >
      MITRE {id}
    </span>
  );
}

