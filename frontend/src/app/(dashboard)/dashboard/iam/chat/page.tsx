/**
 * IAM AI Chat Page
 * Natural language interface for IAM queries
 */

'use client';

import { AIChatInterface } from '@/components/ai-chat/AIChatInterface';

export default function IAMChatPage() {
  return (
    <div className="h-screen flex flex-col">
      <div className="flex-1 p-6">
        <div className="max-w-4xl mx-auto h-full">
          <AIChatInterface />
        </div>
      </div>
    </div>
  );
}

