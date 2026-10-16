/**
 * Floating AI Chatbot Widget
 * Modern, context-aware chatbot accessible from anywhere in the dashboard
 */

'use client';

import { useState, useRef, useEffect } from 'react';
import { sendDashboardChat, getChatSuggestions, type ChatMessage } from '@/lib/api/dashboard-chat';
import { useEffectOnce } from '@/lib/hooks/useEffectOnce';
import { toast } from 'react-hot-toast';

interface FloatingChatbotProps {
  tenantId?: string;
  dashboardContext?: Record<string, any>;
}

type ChatSourceTone = 'knowledge_base' | 'live_compliance_status' | 'proposed_agent_action' | 'general';

const CHAT_SOURCE_LABELS: Record<ChatSourceTone, string> = {
  knowledge_base: 'Knowledge base',
  live_compliance_status: 'Live compliance status',
  proposed_agent_action: 'Proposed agent action',
  general: 'AI assistant',
};

const CHAT_SOURCE_CLASSNAMES: Record<ChatSourceTone, string> = {
  knowledge_base: 'border-sky-500/30 bg-sky-500/10 text-sky-200',
  live_compliance_status: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-200',
  proposed_agent_action: 'border-amber-500/30 bg-amber-500/10 text-amber-200',
  general: 'border-white/10 bg-white/5 text-slate-300',
};

export default function FloatingChatbot({ tenantId, dashboardContext = {} }: FloatingChatbotProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Default suggestions for dashboard context
  const defaultSuggestions = [
    "Give me a SOC 2 summary for our tenant.",
    "Which SOC 2 criteria are not covered?",
    "Show evidence items for logical access.",
    "Draft a SOC 2 report update.",
    "Map our playbooks to SOC 2 criteria.",
    "What incidents matter for SOC 2 right now?",
  ];

  useEffect(() => {
    if (isOpen && tenantId) {
      loadSuggestions();
    }
  }, [isOpen, tenantId]);

  useEffect(() => {
    if (isOpen) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isOpen]);

  const loadSuggestions = async () => {
    if (!tenantId) return;
    try {
      const contextSuggestions = await getChatSuggestions(dashboardContext, tenantId);
      setSuggestions(contextSuggestions.length > 0 ? contextSuggestions : defaultSuggestions);
    } catch (error) {
      console.error('Failed to load suggestions:', error);
      setSuggestions(defaultSuggestions);
    }
  };

  const handleSend = async () => {
    if (!input.trim() || isLoading || !tenantId) return;

    const userMessage: ChatMessage = {
      role: 'user',
      content: input.trim(),
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await sendDashboardChat(
        {
          message: userMessage.content,
          context: {
            page: 'dashboard',
            dashboard_data: dashboardContext,
          },
          conversation_id: conversationId || undefined,
        },
        tenantId
      );

      if (response.conversation_id && !conversationId) {
        setConversationId(response.conversation_id);
      }

      const assistantMessage: ChatMessage = {
        role: 'assistant',
        content: response.reply,
        timestamp: new Date().toISOString(),
        answer_type: response.answer_type,
        source_kind: response.source_kind,
        module: response.module,
        retrieval_categories: response.retrieval_categories,
        sources: response.sources,
        actions: response.actions,
      };

      setMessages((prev) => [...prev, assistantMessage]);

      if (response.suggestions && response.suggestions.length > 0) {
        setSuggestions(response.suggestions);
      }
    } catch (error: any) {
      console.error('Chat error:', error);
      const errorMessage: ChatMessage = {
        role: 'assistant',
        content: 'I apologize, but I encountered an error. Please try again.',
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
    if (e.key === 'Escape') {
      setIsOpen(false);
    }
  };

  return (
    <>
      {/* Floating Action Button */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full bg-gradient-to-br from-primary to-secondary shadow-lg shadow-primary/50 hover:shadow-xl hover:shadow-primary/60 transition-all duration-300 flex items-center justify-center group hover:scale-110"
          aria-label="Open AI Assistant"
        >
          <svg
            className="w-6 h-6 text-slate-950 group-hover:rotate-12 transition-transform"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
            />
          </svg>
        </button>
      )}

      {/* Chat Window */}
      {isOpen && (
        <div className="fixed bottom-6 right-6 z-50 w-96 h-[600px] flex flex-col bg-[rgba(15,23,42,0.95)] backdrop-blur-xl border border-primary/30 rounded-2xl shadow-2xl overflow-hidden animate-in slide-in-from-bottom-4 fade-in duration-300">
          {/* Header */}
          <div className="px-4 py-3 border-b border-primary/20 bg-gradient-to-r from-primary/10 to-secondary/10 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-primary to-secondary flex items-center justify-center">
                <svg className="w-5 h-5 text-slate-950" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
              </div>
              <div>
                <h3 className="font-semibold text-text-main">SOC 2 Agent</h3>
                <p className="text-xs text-text-muted">Tenant-aware answers with SOC 2 context</p>
              </div>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="text-text-muted hover:text-text-main transition-colors p-1 rounded-lg hover:bg-primary/10"
              aria-label="Close chat"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Messages Area */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.length === 0 ? (
              <div className="text-center py-8">
                <div className="text-4xl mb-4">👋</div>
                <p className="text-text-main mb-2 font-medium">How can I help you today?</p>
                <p className="text-sm text-text-muted mb-4">Try asking about your security posture, alerts, or recommendations</p>
                <div className="flex flex-wrap gap-2 justify-center">
                  {suggestions.slice(0, 3).map((suggestion, index) => (
                    <button
                      key={index}
                      onClick={() => handleSuggestionClick(suggestion)}
                      className="px-3 py-1.5 text-xs bg-primary/10 text-primary rounded-full hover:bg-primary/20 transition-colors border border-primary/20"
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
                      className={`max-w-[80%] rounded-2xl px-4 py-2.5 ${
                        message.role === 'user'
                          ? 'bg-gradient-to-br from-primary to-secondary text-slate-950'
                          : 'bg-[rgba(15,23,42,0.9)] text-text-main border border-primary/20'
                      }`}
                    >
                      {message.role === 'assistant' && message.answer_type && (
                        <div className="mb-2 flex flex-wrap items-center gap-2">
                          <span
                            className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase ${
                              CHAT_SOURCE_CLASSNAMES[(message.answer_type as ChatSourceTone) || 'general'] ||
                              CHAT_SOURCE_CLASSNAMES.general
                            }`}
                          >
                            {CHAT_SOURCE_LABELS[(message.answer_type as ChatSourceTone) || 'general'] ||
                              CHAT_SOURCE_LABELS.general}
                          </span>
                          {message.module === 'compliance' && message.retrieval_categories?.length ? (
                            <span className="text-[10px] text-slate-400">
                              {message.retrieval_categories.join(', ')}
                            </span>
                          ) : null}
                        </div>
                      )}
                      <div className="whitespace-pre-wrap text-sm">{message.content}</div>
                      {message.role === 'assistant' && message.actions?.length ? (
                        <div className="mt-3 space-y-1">
                          {message.actions.slice(0, 2).map((action) => (
                            <div
                              key={`${action.action}-${action.recommendation_id || action.label}`}
                              className="rounded-lg border border-primary/20 bg-slate-950/40 px-3 py-2 text-xs text-slate-300"
                            >
                              <span className="font-medium text-text-main">{action.label}</span>
                              {action.requires_approval ? <span className="ml-2 text-amber-300">Approval required</span> : null}
                            </div>
                          ))}
                        </div>
                      ) : null}
                    </div>
                  </div>
                ))}
                {isLoading && (
                  <div className="flex justify-start">
                    <div className="bg-[rgba(15,23,42,0.9)] border border-primary/20 rounded-2xl px-4 py-2.5">
                      <div className="flex gap-1">
                        <div className="w-2 h-2 bg-primary rounded-full animate-bounce"></div>
                        <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                        <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                      </div>
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </>
            )}
          </div>

          {/* Input Area */}
          <div className="border-t border-primary/20 p-4 bg-[rgba(15,23,42,0.5)]">
            {suggestions.length > 0 && messages.length === 0 && (
              <div className="mb-2 flex flex-wrap gap-1.5">
                {suggestions.slice(0, 2).map((suggestion, index) => (
                  <button
                    key={index}
                    onClick={() => handleSuggestionClick(suggestion)}
                    className="px-2.5 py-1 text-xs bg-primary/10 text-primary rounded-lg hover:bg-primary/20 transition-colors border border-primary/20"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            )}
            <div className="flex gap-2">
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Ask me anything..."
                className="flex-1 px-4 py-2.5 bg-[rgba(15,23,42,0.9)] border border-primary/20 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary/50 text-text-main placeholder:text-text-muted resize-none text-sm"
                rows={2}
                disabled={isLoading}
              />
              <button
                onClick={handleSend}
                disabled={!input.trim() || isLoading}
                className="px-4 py-2.5 bg-gradient-to-br from-primary to-secondary text-slate-950 rounded-xl hover:brightness-110 disabled:opacity-50 disabled:cursor-not-allowed transition-all font-medium text-sm"
              >
                {isLoading ? (
                  <div className="w-5 h-5 border-2 border-slate-950 border-t-transparent rounded-full animate-spin"></div>
                ) : (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                  </svg>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
