'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import Breadcrumbs from '@/components/ui/Breadcrumbs';
import { addTicketComment, getTicket, getTicketTabData, updateTicket } from '@/lib/api/tickets';
import TicketOverview from './components/TicketOverview';
import TabNavigation from './components/TabNavigation';
import IAMTab from './components/IAMTab';
import VMTab from './components/VMTab';
import CMDBTab from './components/CMDBTab';
import NetworkTab from './components/NetworkTab';
import TimelineTab from './components/TimelineTab';

export default function TicketDetailPage() {
  const params = useParams();
  const router = useRouter();
  const ticketId = params.id as string;
  const [tenantId, setTenantId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<string>('overview');
  const [statusUpdating, setStatusUpdating] = useState(false);
  const [assignmentUpdating, setAssignmentUpdating] = useState(false);
  const [dueDateUpdating, setDueDateUpdating] = useState(false);
  const [commentSubmitting, setCommentSubmitting] = useState(false);
  const queryClient = useQueryClient();

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const storedTenantId = localStorage.getItem('tenant_id');
      setTenantId(storedTenantId);
    }
  }, []);

  // Fetch ticket data
  const {
    data: ticket,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['ticket', ticketId, tenantId],
    queryFn: () => getTicket(ticketId, tenantId!),
    enabled: !!tenantId && !!ticketId,
  });

  // Fetch tab data when tab changes
  const {
    data: tabData,
    isLoading: tabLoading,
  } = useQuery({
    queryKey: ['ticket-tab', ticketId, activeTab, tenantId],
    queryFn: () => getTicketTabData(ticketId, activeTab, tenantId!),
    enabled: !!tenantId && !!ticketId && activeTab !== 'overview',
  });

  const handleStatusUpdate = async (newStatus: string) => {
    if (!tenantId || !ticket) return;

    try {
      setStatusUpdating(true);
      await updateTicket(ticketId, { status: newStatus }, tenantId);
      await refetch();
    } catch (error) {
      console.error('Failed to update ticket status:', error);
      throw error;
    } finally {
      setStatusUpdating(false);
    }
  };

  const handleAssignmentUpdate = async (assignedTo: string) => {
    if (!tenantId || !ticket) return;

    try {
      setAssignmentUpdating(true);
      await updateTicket(ticketId, { assigned_to: assignedTo }, tenantId);
      await refetch();
    } catch (error) {
      console.error('Failed to update ticket assignee:', error);
      throw error;
    } finally {
      setAssignmentUpdating(false);
    }
  };

  const handleDueDateUpdate = async (dueDate: string | null) => {
    if (!tenantId || !ticket) return;

    try {
      setDueDateUpdating(true);
      await updateTicket(ticketId, { due_date: dueDate || undefined }, tenantId);
      await refetch();
    } catch (error) {
      console.error('Failed to update ticket due date:', error);
      throw error;
    } finally {
      setDueDateUpdating(false);
    }
  };

  const handleCommentAdd = async (comment: string) => {
    if (!tenantId || !ticket) return;

    try {
      setCommentSubmitting(true);
      await addTicketComment(ticketId, comment, tenantId);
      await refetch();
      await queryClient.invalidateQueries({ queryKey: ['ticket-tab', ticketId, 'timeline', tenantId] });
    } catch (error) {
      console.error('Failed to add ticket comment:', error);
      throw error;
    } finally {
      setCommentSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-text-muted">Loading ticket...</p>
        </div>
      </div>
    );
  }

  if (error || !ticket) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <p className="text-red-500 mb-4">Failed to load ticket</p>
          <button
            onClick={() => router.back()}
            className="px-4 py-2 bg-primary text-bg rounded-lg"
          >
            Go Back
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-bg">
      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="mb-6">
          <Breadcrumbs />
          <button
            onClick={() => router.back()}
            className="text-text-muted hover:text-text-main mb-4"
          >
            ← Back to Tickets
          </button>
          <h1 className="text-3xl font-bold text-text-main">Ticket Details</h1>
        </div>

        {/* Overview Section */}
        <TicketOverview
          ticket={ticket}
          onStatusUpdate={handleStatusUpdate}
          onAssignmentUpdate={handleAssignmentUpdate}
          onDueDateUpdate={handleDueDateUpdate}
          onAddComment={handleCommentAdd}
          statusUpdating={statusUpdating}
          assignmentUpdating={assignmentUpdating}
          dueDateUpdating={dueDateUpdating}
          commentSubmitting={commentSubmitting}
        />

        {/* Tab Navigation */}
        <TabNavigation
          activeTab={activeTab}
          onTabChange={setActiveTab}
        />

        {/* Tab Content */}
        <div className="mt-6">
          {activeTab === 'overview' && (
            <div className="bg-[rgba(15,23,42,0.5)] rounded-lg p-6 border border-[rgba(148,163,184,0.1)]">
              <p className="text-text-muted">Select a tab above to view detailed information.</p>
            </div>
          )}
          
          {activeTab === 'iam' && (
            <IAMTab
              data={tabData?.data || ticket.iam_data}
              isLoading={tabLoading}
            />
          )}
          
          {activeTab === 'vm' && (
            <VMTab
              data={tabData?.data || ticket.vm_data}
              isLoading={tabLoading}
            />
          )}
          
          {activeTab === 'cmdb' && (
            <CMDBTab
              data={tabData?.data || ticket.cmdb_data}
              isLoading={tabLoading}
            />
          )}
          
          {activeTab === 'network' && (
            <NetworkTab
              data={tabData?.data || ticket.network_data}
              isLoading={tabLoading}
            />
          )}
          
          {activeTab === 'timeline' && (
            <TimelineTab
              data={tabData?.data || ticket.timeline_data}
              isLoading={tabLoading}
            />
          )}
        </div>
      </div>
    </div>
  );
}
