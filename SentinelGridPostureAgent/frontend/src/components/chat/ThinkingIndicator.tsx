'use client'

import { Bot, Loader2 } from 'lucide-react'

export function ThinkingIndicator() {
  return (
    <div className="flex gap-3">
      <div className="flex-shrink-0 h-10 w-10 rounded-full bg-secondary text-secondary-foreground flex items-center justify-center">
        <Bot className="h-5 w-5" />
      </div>

      <div className="flex-1 max-w-[70%]">
        <div className="inline-block rounded-lg p-4 bg-secondary text-secondary-foreground">
          <div className="flex items-center gap-2">
            <Loader2 className="h-4 w-4 animate-spin" />
            <span className="text-sm">AI is thinking...</span>
          </div>
        </div>
      </div>
    </div>
  );
}

