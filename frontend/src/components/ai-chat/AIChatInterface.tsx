/**
 * AI Chat Interface Component
 * Natural language interface for IAM queries
 */

'use client';

import { useState, useRef, useEffect } from 'react';
import { aiChatApi, ChatMessage, ChatRequest, ChatResponse } from '@/lib/api/ai-chat';
import { toast } from 'react-hot-toast';

interface AIChatInterfaceProps {
  tenantId?: string;
  onPolicyCreate?: (policyData: any) => void;
}

export function AIChatInterface({ tenantId, onPolicyCreate }: AIChatInterfaceProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Load suggestions on mount
  useEffect(() => {
    loadSuggestions();
  }, []);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const loadSuggestions = async () => {
    try {
      const result = await aiChatApi.getSuggestions(undefined, tenantId);
      setSuggestions(result.suggestions);
    } catch (error) {
      console.error('Failed to load suggestions:', error);
    }
  };

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: ChatMessage = {
      role: 'user',
      content: input.trim(),
      timestamp: new Date().toISOString(),
    };

    // Add user message to UI immediately
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const request: ChatRequest = {
        query: userMessage.content,
        tenant_id: tenantId,
        conversation_id: conversationId || undefined,
      };

      const response: ChatResponse = await aiChatApi.chat(request);

      // If no conversation ID, create one
      if (!conversationId && response.timestamp) {
        // Create conversation after first exchange
        try {
          const conv = await aiChatApi.createConversation(
            userMessage.content.substring(0, 50),
            tenantId
          );
          setConversationId(conv.id);
        } catch (error) {
          console.error('Failed to create conversation:', error);
        }
      }

      const assistantMessage: ChatMessage = {
        role: 'assistant',
        content: response.answer,
        timestamp: response.timestamp,
      };

      setMessages((prev) => [...prev, assistantMessage]);

      // Check if response contains policy creation intent
      if (response.answer.toLowerCase().includes('policy') && onPolicyCreate) {
        // Could trigger policy builder if needed
        // For now, just show a toast
        toast.success('Would you like to create this policy in the Policy Builder?');
      }
    } catch (error: any) {
      toast.error(`Chat error: ${error.response?.data?.detail || error.message}`);
      const errorMessage: ChatMessage = {
        role: 'assistant',
        content: 'I apologize, but I encountered an error processing your query. Please try again.',
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSuggestionClick = (suggestion: string) => {
    setInput(suggestion);
    inputRef.current?.focus();
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-full bg-surface-card rounded-lg shadow-sm border border-surface-card-border">
      {/* Header */}
      <div className="px-4 py-3 border-b border-surface-card-border bg-gradient-to-r from-blue-50 to-indigo-50">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-blue-600 flex items-center justify-center">
            <span className="text-white text-xl">🤖</span>
          </div>
          <div>
            <h3 className="font-semibold text-text-main">IAM Assistant</h3>
            <p className="text-xs text-text-muted">Ask me about users, roles, policies, and access</p>
          </div>
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="text-center py-12">
            <div className="text-text-muted mb-4">👋</div>
            <p className="text-text-muted mb-2">Ask me anything about IAM:</p>
            <div className="flex flex-wrap gap-2 justify-center max-w-md mx-auto">
              {suggestions.map((suggestion, index) => (
                <button
                  key={index}
                  onClick={() => handleSuggestionClick(suggestion)}
                  className="px-3 py-1.5 text-sm bg-blue-50 text-blue-700 rounded-full hover:bg-blue-100 transition-colors"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <>
            {messages.map((message, index) => (
              <div
                key={index}
                className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[80%] rounded-lg px-4 py-2 ${
                    message.role === 'user'
                      ? 'bg-blue-600 text-white'
                      : 'bg-bg-alt text-text-main'
                  }`}
                >
                  <div className="whitespace-pre-wrap">{message.content}</div>
                  {message.timestamp && (
                    <div
                      className={`text-xs mt-1 ${
                        message.role === 'user' ? 'text-blue-100' : 'text-text-muted'
                      }`}
                    >
                      {new Date(message.timestamp).toLocaleTimeString()}
                    </div>
                  )}
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-bg-alt rounded-lg px-4 py-2">
                  <div className="flex gap-1">
                    <div className="w-2 h-2 bg-border-muted rounded-full animate-bounce"></div>
                    <div className="w-2 h-2 bg-border-muted rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                    <div className="w-2 h-2 bg-border-muted rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Input Area */}
      <div className="border-t border-surface-card-border p-4">
        <div className="flex gap-2">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Ask about IAM policies, users, access..."
            className="flex-1 px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
            rows={2}
            disabled={isLoading}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isLoading}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isLoading ? 'Sending...' : 'Send'}
          </button>
        </div>
        {suggestions.length > 0 && input.length === 0 && (
          <div className="mt-2 flex flex-wrap gap-2">
            {suggestions.slice(0, 3).map((suggestion, index) => (
              <button
                key={index}
                onClick={() => handleSuggestionClick(suggestion)}
                className="px-3 py-1 text-xs bg-bg-alt text-text-muted rounded-md hover:bg-surface-hover transition-colors"
              >
                {suggestion}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

