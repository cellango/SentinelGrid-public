'use client';

import { useState } from 'react';
import { Ticket } from '@/lib/api/tickets';
import NISTBadge from '@/components/framework/NISTBadge';
import MITREBadge from '@/components/framework/MITREBadge';
import IssueOwnershipSlaPanel from '@/components/operator/IssueOwnershipSlaPanel';

interface TicketOverviewProps {
  ticket: Ticket;
  onStatusUpdate: (status: string) => Promise<void>;
  onAssignmentUpdate: (assignedTo: string) => Promise<void>;
  onDueDateUpdate: (dueDate: string | null) => Promise<void>;
  onAddComment: (comment: string) => Promise<void>;
  statusUpdating?: boolean;
  assignmentUpdating?: boolean;
  dueDateUpdating?: boolean;
  commentSubmitting?: boolean;
}

export default function TicketOverview({
  ticket,
  onStatusUpdate,
  onAssignmentUpdate,
  onDueDateUpdate,
  onAddComment,
  statusUpdating = false,
  assignmentUpdating = false,
  dueDateUpdating = false,
  commentSubmitting = false,
}: TicketOverviewProps) {
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [statusError, setStatusError] = useState<string | null>(null);
  const [commentOpen, setCommentOpen] = useState(false);
  const [commentText, setCommentText] = useState('');
  const [commentMessage, setCommentMessage] = useState<string | null>(null);
  const [commentError, setCommentError] = useState<string | null>(null);

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      open: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
      in_progress: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
      resolved: 'bg-green-500/20 text-green-400 border-green-500/30',
      closed: 'bg-surface-hover0/20 text-text-muted border-border-muted',
    };
    return colors[status] || colors.open;
  };

  const getSeverityColor = (severity?: string) => {
    const colors: Record<string, string> = {
      critical: 'bg-red-500/20 text-red-400 border-red-500/30',
      high: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
      medium: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
      low: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
    };
    return colors[severity?.toLowerCase() || 'medium'] || colors.medium;
  };

  const handleStatusChange = async (nextStatus: string) => {
    try {
      setStatusMessage(null);
      setStatusError(null);
      await onStatusUpdate(nextStatus);
      setStatusMessage(`Status updated to ${nextStatus.replace('_', ' ')}.`);
    } catch (error: any) {
      setStatusError(error?.message || 'Failed to update ticket status.');
    }
  };

  const handleCommentSubmit = async () => {
    try {
      const trimmed = commentText.trim();
      if (!trimmed) {
        setCommentError('Enter a comment before saving.');
        setCommentMessage(null);
        return;
      }
      setCommentMessage(null);
      setCommentError(null);
      await onAddComment(trimmed);
      setCommentText('');
      setCommentOpen(false);
      setCommentMessage('Comment added to the ticket timeline.');
    } catch (error: any) {
      setCommentError(error?.message || 'Failed to add ticket comment.');
    }
  };

  return (
    <div className="bg-[rgba(15,23,42,0.5)] rounded-lg p-6 border border-[rgba(148,163,184,0.1)] mb-6">
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <h2 className="text-2xl font-bold text-text-main mb-2">{ticket.title}</h2>
          {ticket.description && (
            <p className="text-text-muted mb-4">{ticket.description}</p>
          )}
        </div>
        <div className="flex gap-2">
          <span className={`px-3 py-1 rounded-full text-sm font-medium border ${getStatusColor(ticket.status)}`}>
            {ticket.status.replace('_', ' ').toUpperCase()}
          </span>
          {ticket.severity && (
            <span className={`px-3 py-1 rounded-full text-sm font-medium border ${getSeverityColor(ticket.severity)}`}>
              {ticket.severity.toUpperCase()}
            </span>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div>
          <p className="text-xs text-text-muted mb-1">Priority</p>
          <p className="text-sm font-medium text-text-main">{ticket.priority || 'N/A'}</p>
        </div>
        <div>
          <p className="text-xs text-text-muted mb-1">Category</p>
          <p className="text-sm font-medium text-text-main">{ticket.category || 'N/A'}</p>
        </div>
        <div>
          <p className="text-xs text-text-muted mb-1">Assigned To</p>
          <p className="text-sm font-medium text-text-main">{ticket.assigned_to || 'Unassigned'}</p>
        </div>
        <div>
          <p className="text-xs text-text-muted mb-1">Source</p>
          <p className="text-sm font-medium text-text-main">{ticket.source}</p>
        </div>
      </div>

      {(ticket.nist_controls || ticket.mitre_tactics || ticket.mitre_techniques) && (
        <div className="mb-6">
          <h3 className="text-sm font-semibold text-text-main mb-3">Framework Mappings</h3>
          <div className="flex flex-wrap gap-2">
            {ticket.nist_controls && Array.isArray(ticket.nist_controls) && ticket.nist_controls.map((control: any, idx: number) => (
              <NISTBadge
                key={idx}
                controlId={typeof control === 'string' ? control : control.control_id || control.id}
                title={typeof control === 'object' ? control.title : undefined}
              />
            ))}
            {ticket.mitre_tactics && Array.isArray(ticket.mitre_tactics) && ticket.mitre_tactics.map((tactic: any, idx: number) => (
              <MITREBadge
                key={idx}
                type="tactic"
                id={typeof tactic === 'string' ? tactic : tactic.tactic_id || tactic.id}
                name={typeof tactic === 'object' ? tactic.name : undefined}
              />
            ))}
            {ticket.mitre_techniques && Array.isArray(ticket.mitre_techniques) && ticket.mitre_techniques.map((technique: any, idx: number) => (
              <MITREBadge
                key={idx}
                type="technique"
                id={typeof technique === 'string' ? technique : technique.technique_id || technique.id}
                name={typeof technique === 'object' ? technique.name : undefined}
              />
            ))}
          </div>
        </div>
      )}

      <div className="rounded-xl border border-[rgba(148,163,184,0.14)] bg-[rgba(15,23,42,0.72)] p-4">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">Status</p>
        <select
          value={ticket.status}
          onChange={(event) => void handleStatusChange(event.target.value)}
          disabled={statusUpdating}
          className="mt-3 w-full px-4 py-2 bg-[rgba(15,23,42,0.8)] border border-[rgba(148,163,184,0.2)] rounded-lg text-text-main text-sm disabled:opacity-60"
        >
          <option value="open">Open</option>
          <option value="in_progress">In Progress</option>
          <option value="resolved">Resolved</option>
          <option value="closed">Closed</option>
        </select>
        {statusMessage && (
          <p className="mt-3 text-xs text-green-300">{statusMessage}</p>
        )}
        {statusError && (
          <p className="mt-3 text-xs text-red-300">{statusError}</p>
        )}
      </div>

      <div className="mt-4">
        <IssueOwnershipSlaPanel
          issueLabel="Ticket"
          currentOwner={ticket.assigned_to}
          currentDueDate={ticket.due_date}
          onOwnerSave={onAssignmentUpdate}
          onDueDateSave={onDueDateUpdate}
          ownerSaving={assignmentUpdating}
          dueDateSaving={dueDateUpdating}
          assignmentTitle="Ticket ownership"
          assignmentDescription="Search the configured downstream directory, then save the real assignee identifier on this ticket."
          assignmentSaveLabel="Save ticket owner"
        />
      </div>

      <div className="mt-4 rounded-xl border border-[rgba(148,163,184,0.14)] bg-[rgba(15,23,42,0.72)] p-4">
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">Notes</p>
            <p className="mt-1 text-sm text-text-muted">
              Add analyst notes to the ticket timeline. Linked Jira and ServiceNow tickets sync comments when supported.
            </p>
          </div>
          <button
            type="button"
            onClick={() => {
              setCommentOpen((current) => !current);
              setCommentError(null);
              setCommentMessage(null);
            }}
            className="rounded-lg border border-[rgba(148,163,184,0.2)] bg-[rgba(15,23,42,0.8)] px-4 py-2 text-sm font-medium text-text-main hover:border-primary"
          >
            {commentOpen ? 'Hide ticket note composer' : 'Add ticket comment'}
          </button>
        </div>

        {commentOpen && (
          <div className="mt-4 space-y-3">
            <textarea
              value={commentText}
              onChange={(event) => {
                setCommentText(event.target.value);
                setCommentError(null);
                setCommentMessage(null);
              }}
              rows={4}
              placeholder="Summarize analyst findings, remediation progress, or handoff context."
              className="w-full rounded-lg border border-[rgba(148,163,184,0.2)] bg-[rgba(15,23,42,0.85)] px-3 py-2 text-sm text-text-main"
            />
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={() => void handleCommentSubmit()}
                disabled={commentSubmitting}
                className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-bg disabled:opacity-60"
              >
                Add ticket note
              </button>
              <button
                type="button"
                onClick={() => {
                  setCommentOpen(false);
                  setCommentText('');
                  setCommentError(null);
                }}
                className="rounded-lg border border-[rgba(148,163,184,0.2)] px-4 py-2 text-sm font-medium text-text-main"
              >
                Discard note
              </button>
            </div>
          </div>
        )}

        {commentMessage && <p className="mt-3 text-xs text-green-300">{commentMessage}</p>}
        {commentError && <p className="mt-3 text-xs text-red-300">{commentError}</p>}
      </div>
    </div>
  );
}
