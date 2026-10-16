/**
 * AI Chat API Client
 * Frontend client for IAM AI chat interface
 */

import axios from 'axios';

// Create a separate client for IAM Agent (different base URL)
const iamApiClient = axios.create({
  baseURL:
    typeof window !== 'undefined'
      ? ''
      : (process.env.NEXT_PUBLIC_IAM_AGENT_URL || 'http://localhost:8005'),
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
});

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
}

export interface ChatRequest {
  query: string;
  tenant_id?: string;
  context?: Record<string, any>;
  conversation_id?: string;
  format?: 'natural' | 'json';
}

export interface ChatResponse {
  answer: string;
  entities: Array<{
    type: string;
    id?: string;
    name?: string;
  }>;
  confidence: number;
  sources: string[];
  timestamp?: string;
  error?: string;
}

export interface Conversation {
  id: string;
  title?: string;
  tenant_id?: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface ConversationWithMessages extends Conversation {
  messages: ChatMessage[];
}

const BASE_URL = '/internal/iam/chat';

export const aiChatApi = {
  /**
   * Send a chat message
   */
  async chat(request: ChatRequest): Promise<ChatResponse> {
    const response = await iamApiClient.post<ChatResponse>(BASE_URL, request);
    return response.data;
  },

  /**
   * Create a new conversation
   */
  async createConversation(title?: string, tenant_id?: string): Promise<Conversation> {
    const response = await iamApiClient.post<Conversation>(`${BASE_URL}/conversations`, {
      title,
      tenant_id,
    });
    return response.data;
  },

  /**
   * List all conversations
   */
  async listConversations(tenant_id?: string): Promise<Conversation[]> {
    const params = tenant_id ? `?tenant_id=${encodeURIComponent(tenant_id)}` : '';
    const response = await iamApiClient.get<Conversation[]>(`${BASE_URL}/conversations${params}`);
    return response.data;
  },

  /**
   * Get a conversation with messages
   */
  async getConversation(conversationId: string): Promise<ConversationWithMessages> {
    const response = await iamApiClient.get<ConversationWithMessages>(
      `${BASE_URL}/conversations/${conversationId}`
    );
    return response.data;
  },

  /**
   * Delete a conversation
   */
  async deleteConversation(conversationId: string): Promise<void> {
    await iamApiClient.delete(`${BASE_URL}/conversations/${conversationId}`);
  },

  /**
   * Get query suggestions
   */
  async getSuggestions(query?: string, tenant_id?: string): Promise<{ suggestions: string[] }> {
    const params = new URLSearchParams();
    if (query) params.append('query', query);
    if (tenant_id) params.append('tenant_id', tenant_id);
    const queryString = params.toString();
    const url = queryString ? `${BASE_URL}/suggestions?${queryString}` : `${BASE_URL}/suggestions`;
    const response = await iamApiClient.get<{ suggestions: string[] }>(url);
    return response.data;
  },
};
