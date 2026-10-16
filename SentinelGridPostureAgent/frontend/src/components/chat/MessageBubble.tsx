'use client'

import { User, Bot } from 'lucide-react'
import type { Message } from './ChatInterface'

interface MessageBubbleProps {
  message: Message;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
      {/* Avatar */}
      <div className={`flex-shrink-0 h-10 w-10 rounded-full flex items-center justify-center ${
        isUser ? 'bg-primary text-primary-foreground' : 'bg-secondary text-secondary-foreground'
      }`}>
        {isUser ? <User className="h-5 w-5" /> : <Bot className="h-5 w-5" />}
      </div>

      {/* Message content */}
      <div className={`flex-1 max-w-[70%] ${isUser ? 'text-right' : ''}`}>
        <div className={`inline-block rounded-lg p-4 ${
          isUser 
            ? 'bg-primary text-primary-foreground' 
            : 'bg-secondary text-secondary-foreground'
        }`}>
          <div className="whitespace-pre-wrap break-words">
            {formatMessage(message.content)}
          </div>
          
          {message.mcpTool && (
            <div className="mt-2 pt-2 border-t border-current/20 text-xs opacity-70">
              🔧 Tool used: {message.mcpTool}
            </div>
          )}
        </div>
        
        <div className="text-xs text-muted-foreground mt-1 px-2">
          {message.timestamp.toLocaleTimeString()}
        </div>
      </div>
    </div>
  );
}

/**
 * Format message content with markdown-like syntax
 */
function formatMessage(content: string): React.ReactNode {
  // Simple markdown-like formatting
  const lines = content.split('\n');
  
  return lines.map((line, idx) => {
    // Bold text: **text**
    let formatted: React.ReactNode = line;
    
    if (line.includes('**')) {
      const parts = line.split('**');
      formatted = parts.map((part, partIdx) => 
        partIdx % 2 === 1 ? <strong key={partIdx}>{part}</strong> : part
      );
    }

    return (
      <span key={idx}>
        {formatted}
        {idx < lines.length - 1 && <br />}
      </span>
    );
  });
}

