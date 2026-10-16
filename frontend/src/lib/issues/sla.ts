export type IssueSlaState = 'untracked' | 'on_track' | 'due_soon' | 'overdue';

export function getIssueSlaState(dueDate?: string | null, now: Date = new Date()): IssueSlaState {
  if (!dueDate) return 'untracked';
  const dueAt = new Date(dueDate);
  if (Number.isNaN(dueAt.getTime())) return 'untracked';

  const remainingMs = dueAt.getTime() - now.getTime();
  if (remainingMs <= 0) return 'overdue';
  if (remainingMs <= 4 * 60 * 60 * 1000) return 'due_soon';
  return 'on_track';
}

export function getIssueSlaLabel(dueDate?: string | null, now: Date = new Date()): string {
  if (!dueDate) return 'No SLA target';
  const dueAt = new Date(dueDate);
  if (Number.isNaN(dueAt.getTime())) return 'No SLA target';

  const remainingMs = dueAt.getTime() - now.getTime();
  const absMinutes = Math.round(Math.abs(remainingMs) / (60 * 1000));
  if (remainingMs <= 0) {
    if (absMinutes < 60) return `Overdue by ${absMinutes}m`;
    const hours = Math.round(absMinutes / 60);
    if (hours < 48) return `Overdue by ${hours}h`;
    return `Overdue since ${dueAt.toLocaleString()}`;
  }

  if (absMinutes < 60) return `Due in ${absMinutes}m`;
  const hours = Math.round(absMinutes / 60);
  if (hours < 48) return `Due in ${hours}h`;
  return `Due ${dueAt.toLocaleString()}`;
}

export function formatIssueDueDate(dueDate?: string | null): string {
  if (!dueDate) return 'Not set';
  const dueAt = new Date(dueDate);
  if (Number.isNaN(dueAt.getTime())) return 'Not set';
  return dueAt.toLocaleString();
}

export function toDateTimeLocalInputValue(dueDate?: string | null): string {
  if (!dueDate) return '';
  const date = new Date(dueDate);
  if (Number.isNaN(date.getTime())) return '';
  const pad = (value: number) => String(value).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

export function addHoursFromNow(hours: number, now: Date = new Date()): string {
  return new Date(now.getTime() + hours * 60 * 60 * 1000).toISOString();
}
