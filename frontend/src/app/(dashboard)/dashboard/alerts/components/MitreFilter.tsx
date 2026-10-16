import { useEffect, useState, useRef, useCallback } from 'react';
import clsx from 'clsx';
import { Alert } from '@/lib/api/siem';

interface Props {
  alerts: Alert[];
  selectedTactics: Set<string>;
  setSelectedTactics: (s: Set<string>) => void;
  mitreFilter: string;
  setMitreFilter: (s: string) => void;
}

export default function MitreFilter({
  alerts,
  selectedTactics,
  setSelectedTactics,
  mitreFilter,
  setMitreFilter,
}: Props) {
  const [expanded, setExpanded] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);
  const [savedFilter, setSavedFilter] = useState<string | null>(() =>
    typeof window !== 'undefined' ? localStorage.getItem('mitreFilterSaved') : null
  );
  const presetTactics = [
    'Initial Access',
    'Execution',
    'Persistence',
    'Privilege Escalation',
    'Defense Evasion',
    'Credential Access',
    'Discovery',
    'Lateral Movement',
    'Collection',
    'Command and Control',
    'Exfiltration',
    'Impact',
  ];

  useEffect(() => {
    if (typeof window !== 'undefined' && savedFilter) {
      setMitreFilter(savedFilter);
    }
  }, [savedFilter, setMitreFilter]);

  // Close panel on Escape
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Escape' && expanded) {
      setExpanded(false);
    }
  }, [expanded]);

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  const tactics = Array.from(
    new Set(
      (alerts || [])
        .map((a: any) => a.mitre_tactic)
        .filter(Boolean)
    )
  );

  const toggleTactic = (tac: string) => {
    const next = new Set(selectedTactics);
    if (next.has(tac)) {
      next.delete(tac);
    } else {
      next.add(tac);
    }
    setSelectedTactics(next);
  };

  return (
    <div className="flex items-center gap-2 text-xs text-text-muted ml-auto" ref={panelRef}>
      <button
        className="px-3 py-2 min-h-[44px] rounded border border-border-faint text-text-muted hover:text-text-main transition-colors"
        onClick={() => setExpanded(!expanded)}
        aria-expanded={expanded}
        aria-controls="mitre-filter-panel"
      >
        MITRE filters
        {selectedTactics.size > 0 && (
          <span className="ml-1.5 inline-flex items-center justify-center min-w-[18px] h-[18px] rounded-full bg-primary/20 text-primary text-[10px] font-semibold px-1">
            {selectedTactics.size}
          </span>
        )}
      </button>
      {expanded && (
        <div id="mitre-filter-panel" className="flex flex-wrap items-center gap-2" role="group" aria-label="MITRE ATT&CK tactic filters">
          <div className="flex flex-wrap gap-1" role="group" aria-label="Detected tactics">
            {tactics.map((tac) => {
              const active = selectedTactics.has(tac as string);
              return (
                <button
                  key={tac as string}
                  onClick={() => toggleTactic(tac as string)}
                  aria-pressed={active}
                  className={clsx(
                    'px-2 py-1 rounded border text-[11px] transition-colors',
                    active
                      ? 'border-primary/50 text-primary bg-primary/10'
                      : 'border-border-faint text-text-muted hover:text-text-main'
                  )}
                >
                  {tac as string}
                </button>
              );
            })}
            {selectedTactics.size > 0 && (
              <button
                onClick={() => setSelectedTactics(new Set())}
                className="px-2 py-1 rounded border border-border text-[11px] text-text-muted hover:text-text-main transition-colors"
              >
                Clear
              </button>
            )}
          </div>
          <div className="flex flex-wrap gap-1" role="group" aria-label="MITRE ATT&CK preset tactics">
            {presetTactics.map((tac) => {
              const active = selectedTactics.has(tac);
              return (
                <button
                  key={tac}
                  onClick={() => toggleTactic(tac)}
                  aria-pressed={active}
                  className={clsx(
                    'px-2 py-1 rounded border text-[11px] transition-colors',
                    active
                      ? 'border-primary/50 text-primary bg-primary/10'
                      : 'border-border-faint text-text-muted hover:text-text-main'
                  )}
                >
                  {tac}
                </button>
              );
            })}
          </div>
          <label htmlFor="mitre-search" className="sr-only">Search MITRE tactic or technique</label>
          <input
            id="mitre-search"
            value={mitreFilter}
            onChange={(e) => setMitreFilter(e.target.value)}
            placeholder="search tactic/technique"
            className="bg-surface-input border border-border-faint rounded px-2 py-1 text-text-main text-xs focus:outline-none focus:border-primary/50"
          />
          <button
            className="px-2 py-1 rounded border border-primary/40 text-primary text-[11px] transition-colors hover:bg-primary/10"
            onClick={() => {
              setSavedFilter(mitreFilter);
              if (typeof window !== 'undefined') {
                localStorage.setItem('mitreFilterSaved', mitreFilter);
              }
            }}
          >
            Save filter
          </button>
        </div>
      )}
    </div>
  );
}
