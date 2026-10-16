/**
 * Dashboard Chat API Client
 * Handles AI chat for dashboard context
 */

import { apiClient } from './client';

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
  answer_type?: ChatAnswerType;
  source_kind?: ChatSourceKind;
  module?: string;
  retrieval_categories?: string[];
  sources?: Array<Record<string, any>>;
  actions?: ChatAction[];
}

export type ChatAnswerType =
  | 'knowledge_base'
  | 'live_compliance_status'
  | 'proposed_agent_action'
  | 'general';

export type ChatSourceKind = ChatAnswerType;

export interface ChatAction {
  label: string;
  action: string;
  endpoint?: string;
  requires_approval?: boolean;
  recommendation_id?: string;
}

export interface ChatRequest {
  message: string;
  active_agent?: string;
  context?: {
    page: string;
    dashboard_data?: Record<string, any>;
    selected_items?: string[];
    active_agent?: string;
  };
  conversation_id?: string;
}

export interface ChatResponse {
  reply: string;
  conversation_id: string;
  suggestions?: string[];
  actions?: ChatAction[];
  answer_type?: ChatAnswerType;
  source_kind?: ChatSourceKind;
  module?: string;
  retrieval_categories?: string[];
  sources?: Array<Record<string, any>>;
}

/**
 * Send a chat message with dashboard context
 */
export async function sendDashboardChat(
  request: ChatRequest,
  tenantId: string
): Promise<ChatResponse> {
  const response = await apiClient.post<ChatResponse>(
    `/chat/dashboard`,
    {
      tenant_id: tenantId,
      query: request.message,
      active_agent:
        request.active_agent ||
        request.context?.active_agent ||
        request.context?.dashboard_data?.active_agent,
      context: request.context,
      conversation_id: request.conversation_id,
    }
  );
  // Normalize to expected shape
  const data = response.data as any;
  return {
    reply: data.reply || data.response || '',
    conversation_id: data.conversation_id || '',
    suggestions: data.suggestions || [],
    actions: data.actions || [],
    answer_type: data.answer_type || data.source_kind || 'knowledge_base',
    source_kind: data.source_kind || data.answer_type || 'knowledge_base',
    module: data.module || 'general',
    retrieval_categories: data.retrieval_categories || [],
    sources: data.sources || [],
  };
}

/**
 * Get chat suggestions based on current dashboard state
 */
export async function getChatSuggestions(
  dashboardContext: Record<string, any>,
  tenantId: string
): Promise<string[]> {
  const response = await apiClient.post<{ suggestions: string[] }>(
    `/chat/suggestions`,
    { context: dashboardContext }
  );
  return response.data.suggestions;
}
