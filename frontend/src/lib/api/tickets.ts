/**
 * Ticket API client
 */

import { apiClient } from './client';

export interface Ticket {
  id: string;
  title: string;
  description?: string;
  status: string;
  severity?: string;
  priority?: string;
  category?: string;
  source: string;
  external_id?: string;
  assigned_to?: string;
  created_by?: string;
  due_date?: string;
  iam_data?: any;
  vm_data?: any;
  cmdb_data?: any;
  network_data?: any;
  timeline_data?: any;
  nist_controls?: any;
  mitre_tactics?: any;
  mitre_techniques?: any;
  created_at: string;
  updated_at: string;
}

export interface TicketTabData {
  tab: string;
  data: any;
}

export interface TicketCreateInput {
  title: string;
  description?: string;
  status?: string;
  severity?: string;
  priority?: string;
  category?: string;
  source?: string;
  external_id?: string;
  alert_ids?: string[];
  cve_ids?: string[];
  exploit_indicators?: Record<string, any>;
  assigned_to?: string;
  created_by?: string;
  due_date?: string;
  incident_id?: string;
  incident_management_mode?: string;
  fix_group_id?: string;
  scan_id?: string;
}

/**
 * Create ticket
 */
export async function createTicket(
  payload: TicketCreateInput,
  tenantId?: string
): Promise<Ticket> {
  const response = await apiClient.post<Ticket>('/tickets', payload, {
    params: tenantId ? { tenant_id: tenantId } : undefined,
  });
  return response.data;
}

/**
 * Get ticket by ID
 */
export async function getTicket(ticketId: string, tenantId: string): Promise<Ticket> {
  const response = await apiClient.get<Ticket>(`/tickets/${ticketId}`, {
    params: { tenant_id: tenantId },
  });
  return response.data;
}

/**
 * Get tab-specific data for a ticket
 */
export async function getTicketTabData(
  ticketId: string,
  tabName: string,
  tenantId: string
): Promise<TicketTabData> {
  const response = await apiClient.get<TicketTabData>(
    `/tickets/${ticketId}/tabs/${tabName}`,
    {
      params: { tenant_id: tenantId },
    }
  );
  return response.data;
}

/**
 * Update ticket
 */
export async function updateTicket(
  ticketId: string,
  updates: Partial<Ticket>,
  tenantId: string
): Promise<Ticket> {
  const response = await apiClient.put<Ticket>(
    `/tickets/${ticketId}`,
    updates,
    {
      params: { tenant_id: tenantId },
    }
  );
  return response.data;
}

export async function addTicketComment(
  ticketId: string,
  comment: string,
  tenantId: string
): Promise<Ticket> {
  const response = await apiClient.post<Ticket>(
    `/tickets/${ticketId}/comments`,
    { comment },
    {
      params: { tenant_id: tenantId },
    }
  );
  return response.data;
}

/**
 * Search tickets
 */
export async function searchTickets(
  tenantId: string,
  filters?: {
    status?: string;
    severity?: string;
    category?: string;
    limit?: number;
    offset?: number;
  }
): Promise<Ticket[]> {
  const response = await apiClient.get<Ticket[]>('/tickets', {
    params: {
      tenant_id: tenantId,
      ...filters,
    },
  });
  return response.data;
}
