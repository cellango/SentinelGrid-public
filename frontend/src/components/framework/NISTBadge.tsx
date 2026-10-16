'use client';

interface NISTBadgeProps {
  controlId: string;
  title?: string;
}

export default function NISTBadge({ controlId, title }: NISTBadgeProps) {
  return (
    <span
      className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-500/20 text-blue-400 border border-blue-500/30"
      title={title || `NIST Control ${controlId}`}
    >
      NIST {controlId}
    </span>
  );
}

