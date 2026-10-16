'use client';

import { clsx } from 'clsx';

// --- FilterChip ---

interface FilterChipProps {
  label: string;
  active: boolean;
  onClick: () => void;
  className?: string;
  /** Show a count badge */
  count?: number;
}

export function FilterChip({ label, active, onClick, className, count }: FilterChipProps) {
  return (
    <button
      onClick={onClick}
      className={clsx(
        'inline-flex items-center gap-1.5 px-3 py-2 min-h-[44px] rounded-full text-sm border transition-colors',
        active
          ? 'border-primary/60 text-primary bg-primary/10'
          : 'border-transparent text-text-muted hover:text-text-main hover:border-border',
        className
      )}
      aria-pressed={active}
    >
      <span>{label}</span>
      {count !== undefined && (
        <span
          className={clsx(
            'inline-flex items-center justify-center min-w-[20px] h-5 rounded-full text-[11px] font-semibold px-1.5',
            active ? 'bg-primary/20 text-primary' : 'bg-slate-700 text-text-muted'
          )}
          aria-label={`${count} items`}
        >
          {count}
        </span>
      )}
    </button>
  );
}

// --- FilterSelect ---

interface FilterSelectProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string }[];
  className?: string;
  id?: string;
}

export function FilterSelect({ label, value, onChange, options, className, id }: FilterSelectProps) {
  const selectId = id || `filter-${label.toLowerCase().replace(/\s+/g, '-')}`;

  return (
    <div className={clsx('flex flex-col gap-1', className)}>
      <label htmlFor={selectId} className="text-xs text-text-muted font-medium">
        {label}
      </label>
      <select
        id={selectId}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="px-3 py-2.5 min-h-[44px] bg-surface-input border border-border-faint rounded-md text-text-main text-sm focus:outline-none focus:ring-2 focus:ring-primary"
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  );
}

// --- FilterBar ---

interface FilterBarProps {
  children: React.ReactNode;
  className?: string;
  /** Label for the filter bar group */
  label?: string;
}

/**
 * Container for a group of filter chips or selects.
 * Provides consistent spacing and wrapping.
 */
export default function FilterBar({ children, className, label = 'Filters' }: FilterBarProps) {
  return (
    <div
      className={clsx('flex flex-wrap items-end gap-3', className)}
      role="group"
      aria-label={label}
    >
      {children}
    </div>
  );
}

// --- FilterChipGroup ---

interface FilterChipGroupProps<T extends string> {
  label: string;
  options: { value: T; label: string; count?: number }[];
  selected: T;
  onChange: (value: T) => void;
  className?: string;
}

/**
 * A labeled group of filter chips where one is active at a time.
 */
export function FilterChipGroup<T extends string>({
  label,
  options,
  selected,
  onChange,
  className,
}: FilterChipGroupProps<T>) {
  return (
    <div className={clsx('flex items-center gap-1', className)} role="group" aria-label={label}>
      <span className="text-xs text-text-muted mr-1">{label}:</span>
      {options.map((opt) => (
        <FilterChip
          key={opt.value}
          label={opt.label}
          active={selected === opt.value}
          onClick={() => onChange(opt.value)}
          count={opt.count}
        />
      ))}
    </div>
  );
}
