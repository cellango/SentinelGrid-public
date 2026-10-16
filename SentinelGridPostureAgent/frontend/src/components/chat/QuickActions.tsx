'use client'

import { Shield, AlertTriangle, Search, BarChart } from 'lucide-react'

interface QuickActionsProps {
  onSelect: (prompt: string) => void;
}

const QUICK_PROMPTS = [
  {
    icon: Shield,
    label: 'Posture Score',
    prompt: 'What is my current security posture score?',
  },
  {
    icon: AlertTriangle,
    label: 'Critical Findings',
    prompt: 'Show me all critical findings',
  },
  {
    icon: Search,
    label: 'Recent Scans',
    prompt: 'List my recent security scans',
  },
  {
    icon: BarChart,
    label: 'Asset Summary',
    prompt: 'Give me a summary of my assets',
  },
];

export function QuickActions({ onSelect }: QuickActionsProps) {
  return (
    <div className="border-t border-b bg-muted/30 p-4">
      <div className="text-xs text-muted-foreground mb-2">Quick Actions:</div>
      <div className="flex gap-2 flex-wrap">
        {QUICK_PROMPTS.map((action) => (
          <button
            key={action.label}
            onClick={() => onSelect(action.prompt)}
            className="flex items-center gap-2 px-3 py-2 text-sm border rounded-md hover:bg-accent hover:text-accent-foreground transition-colors"
          >
            <action.icon className="h-4 w-4" />
            {action.label}
          </button>
        ))}
      </div>
    </div>
  );
}

