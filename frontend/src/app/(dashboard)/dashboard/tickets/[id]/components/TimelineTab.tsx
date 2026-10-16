'use client';

interface TimelineTabProps {
  data?: any;
  isLoading?: boolean;
}

export default function TimelineTab({ data, isLoading }: TimelineTabProps) {
  if (isLoading) {
    return (
      <div className="bg-[rgba(15,23,42,0.5)] rounded-lg p-6 border border-[rgba(148,163,184,0.1)]">
        <div className="animate-pulse">
          <div className="h-4 bg-[rgba(148,163,184,0.1)] rounded w-1/4 mb-4"></div>
          <div className="space-y-3">
            <div className="h-20 bg-[rgba(148,163,184,0.1)] rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  if (!data || (!data.events && !data.actions && !data.history)) {
    return (
      <div className="bg-[rgba(15,23,42,0.5)] rounded-lg p-6 border border-[rgba(148,163,184,0.1)]">
        <p className="text-text-muted">No timeline data available.</p>
      </div>
    );
  }

  const events = data.events || [];
  const actions = data.actions || [];
  const history = data.history || [];

  const getItemTimestamp = (item: any) =>
    item.ts || item.timestamp || item.created_at || item.at || null;

  const getItemTitle = (item: any) =>
    item.title || item.text || item.action || item.event || 'Timeline Event';

  const getItemDescription = (item: any) => {
    if (item.description) return item.description;
    const metadata = item.metadata || {};
    if (metadata.previous_assigned_to !== undefined || metadata.assigned_to !== undefined) {
      return `Assignment changed from ${metadata.previous_assigned_to || 'unassigned'} to ${metadata.assigned_to || 'unassigned'}.`;
    }
    if (metadata.previous_status !== undefined || metadata.status !== undefined) {
      return `Status changed from ${metadata.previous_status || 'unknown'} to ${metadata.status || 'unknown'}.`;
    }
    if (metadata.previous_due_date !== undefined || metadata.due_date !== undefined) {
      return `SLA target changed from ${metadata.previous_due_date || 'unset'} to ${metadata.due_date || 'unset'}.`;
    }
    return null;
  };
  
  // Combine all timeline items
  const timelineItems = [
    ...events.map((e: any) => ({ ...e, type: e.type || 'event' })),
    ...actions.map((a: any) => ({ ...a, type: a.type || 'action' })),
    ...history.map((h: any) => ({ ...h, type: h.type || 'history' })),
  ].sort((a, b) => {
    const timeA = new Date(getItemTimestamp(a) || 0).getTime();
    const timeB = new Date(getItemTimestamp(b) || 0).getTime();
    return timeB - timeA; // Most recent first
  });

  const getTypeColor = (type: string) => {
    const colors: Record<string, string> = {
      event: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
      action: 'bg-green-500/20 text-green-400 border-green-500/30',
      history: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
      comment: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30',
    };
    return colors[type] || colors.event;
  };

  return (
    <div className="bg-[rgba(15,23,42,0.5)] rounded-lg p-6 border border-[rgba(148,163,184,0.1)]">
      <h3 className="text-lg font-semibold text-text-main mb-4">Timeline</h3>
      <div className="space-y-4">
        {timelineItems.length === 0 ? (
          <p className="text-text-muted">No timeline events available.</p>
        ) : (
          timelineItems.map((item: any, idx: number) => (
            <div key={idx} className="flex gap-4">
              {/* Timeline line */}
              <div className="flex flex-col items-center">
                <div className={`w-3 h-3 rounded-full border-2 ${getTypeColor(item.type)}`}></div>
                {idx < timelineItems.length - 1 && (
                  <div className="w-0.5 h-full bg-[rgba(148,163,184,0.2)] mt-2"></div>
                )}
              </div>
              
              {/* Content */}
              <div className="flex-1 pb-4">
                <div className="flex items-center gap-2 mb-1">
                  <span className={`px-2 py-0.5 rounded text-xs border ${getTypeColor(item.type)}`}>
                    {item.type.toUpperCase()}
                  </span>
                  <span className="text-xs text-text-muted">
                    {getItemTimestamp(item)
                      ? new Date(getItemTimestamp(item)!).toLocaleString()
                      : 'Unknown time'}
                  </span>
                </div>
                <p className="font-medium text-text-main mb-1">
                  {getItemTitle(item)}
                </p>
                {getItemDescription(item) && (
                  <p className="text-sm text-text-muted mb-2">{getItemDescription(item)}</p>
                )}
                {item.result && (
                  <div className="mt-2 p-2 bg-[rgba(15,23,42,0.5)] rounded border border-[rgba(148,163,184,0.1)]">
                    <p className="text-xs text-text-muted mb-1">Result:</p>
                    <p className="text-sm text-text-main">
                      {typeof item.result === 'string' ? item.result : JSON.stringify(item.result, null, 2)}
                    </p>
                  </div>
                )}
                {item.user_id && (
                  <p className="text-xs text-text-muted mt-1">By: {item.user_id}</p>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
