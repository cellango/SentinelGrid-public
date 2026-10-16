'use client'

import { useState, useRef, useEffect } from 'react'
import { Send, Loader2 } from 'lucide-react'
import { MessageBubble } from './MessageBubble'
import { ThinkingIndicator } from './ThinkingIndicator'
import { QuickActions } from './QuickActions'
import { mcpClient } from '@/lib/mcp-client'

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  mcpTool?: string;
}

export function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: 'Hello! I\'m your AI security posture assistant. Ask me anything about your cloud security, findings, or asset inventory.',
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState('');
  const [isThinking, setIsThinking] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isThinking]);

  const handleQuickAction = (prompt: string) => {
    setInput(prompt);
    handleSend(prompt);
  };

  const handleSend = async (messageText?: string) => {
    const text = messageText || input;
    if (!text.trim() || isThinking) return;

    // Add user message
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: text,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsThinking(true);

    try {
      // Parse user intent and call appropriate MCP tool
      const response = await processUserMessage(text);

      // Add assistant response
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.content,
        timestamp: new Date(),
        mcpTool: response.toolUsed,
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Error processing message:', error);
      
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: 'Sorry, I encountered an error processing your request. Please try again.',
        timestamp: new Date(),
      };

      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsThinking(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-screen max-w-4xl mx-auto">
      {/* Header */}
      <div className="border-b p-4">
        <h1 className="text-2xl font-bold">Posture AI Assistant</h1>
        <p className="text-sm text-muted-foreground">
          Ask about your security posture, findings, or assets
        </p>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map(message => (
          <MessageBubble key={message.id} message={message} />
        ))}
        
        {isThinking && <ThinkingIndicator />}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Quick Actions */}
      <QuickActions onSelect={handleQuickAction} />

      {/* Input */}
      <div className="border-t p-4">
        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Ask about your security posture..."
            className="flex-1 resize-none border rounded-md p-3 focus:outline-none focus:ring-2 focus:ring-primary"
            rows={3}
          />
          <button
            onClick={() => handleSend()}
            disabled={!input.trim() || isThinking}
            className="px-6 py-3 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isThinking ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              <Send className="h-5 w-5" />
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

/**
 * Process user message and call appropriate MCP tool
 */
async function processUserMessage(message: string): Promise<{ content: string; toolUsed?: string }> {
  const lowerMessage = message.toLowerCase();

  // Simple intent detection (in production, use better NLP)
  if (lowerMessage.includes('posture') || lowerMessage.includes('score')) {
    const response = await mcpClient.getPostureSummary('default-tenant');
    
    if (response.error) {
      return { content: `Error: ${response.error}` };
    }

    const data = response.result;
    return {
      content: `Your current security posture score is **${data.posture_score}/100** (Grade: ${data.grade}).

**Findings Summary:**
- Critical: ${data.critical_findings}
- High: ${data.high_findings}
- Medium: ${data.medium_findings}
- Low: ${data.low_findings}

${data.critical_findings > 0 ? '⚠️ You have critical findings that require immediate attention.' : '✅ No critical findings detected.'}`,
      toolUsed: 'get_posture_summary',
    };
  }

  if (lowerMessage.includes('critical') || lowerMessage.includes('findings')) {
    const response = await mcpClient.listFindings({
      tenant_id: 'default-tenant',
      severity: 'critical',
      limit: 5,
    });

    if (response.error) {
      return { content: `Error: ${response.error}` };
    }

    const findings = response.result.findings || [];
    
    if (findings.length === 0) {
      return { content: '✅ No critical findings found!', toolUsed: 'list_findings' };
    }

    let content = `Found ${findings.length} critical findings:\n\n`;
    findings.forEach((finding: any, idx: number) => {
      content += `${idx + 1}. **${finding.title}**\n   Tool: ${finding.tool} | Status: ${finding.status}\n\n`;
    });

    return { content, toolUsed: 'list_findings' };
  }

  if (lowerMessage.includes('scan') || lowerMessage.includes('analyze')) {
    return {
      content: 'To start a scan, please specify:\n- Observable type (aws_account, web_application, git_repository)\n- Value (account ID, URL, repo URL)\n\nExample: "Scan AWS account 123456789012"',
    };
  }

  // Default response
  return {
    content: `I can help you with:\n- Viewing your posture score\n- Listing findings by severity\n- Analyzing cloud accounts, web apps, or repositories\n- Searching assets\n\nWhat would you like to know?`,
  };
}

