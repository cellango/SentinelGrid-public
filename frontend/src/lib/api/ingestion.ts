/**
 * Ingestion Service API Client
 * Handles event ingestion
 */

import { apiClient } from './client';

export interface RawEvent {
  event_type: string;
  source: string;
  timestamp: string;
  raw_data: Record<string, any>;
  tenant_id?: string;
  metadata?: Record<string, any>;
}

export interface IngestBatchRequest {
  events: RawEvent[];
  tenant_id?: string;
}

export interface IngestResponse {
  ingested_count: number;
  failed_count: number;
  errors: string[];
  batch_id?: string;
}

/**
 * Ingest a batch of events
 */
export async function ingestEvents(data: IngestBatchRequest): Promise<IngestResponse> {
  const response = await apiClient.post<IngestResponse>('/ingest/events', data);
  return response.data;
}

/**
 * Flush pending events for current tenant
 */
export async function flushEvents(): Promise<{ status: string; tenant_id: string }> {
  const response = await apiClient.post<{ status: string; tenant_id: string }>(
    '/ingest/events/flush'
  );
  return response.data;
}

