"use client";

import { useState } from "react";

export function HelpButton() {
  const [open, setOpen] = useState(false);

  return (
    <div className="fixed bottom-6 right-6 z-50">
      {open && (
        <div className="mb-3 w-72 rounded-xl border border-border bg-bg-alt p-4 shadow-xl">
          <p className="text-sm font-medium text-text-main mb-2">Need help?</p>
          <p className="text-xs text-text-muted mb-3">
            Reach out and we will get back to you within a few hours.
          </p>
          <a
            href="mailto:support@sentinelgrid.ai"
            className="block w-full rounded-lg bg-primary/10 border border-primary/20 px-3 py-2 text-center text-sm text-primary hover:bg-primary/20 transition-colors"
          >
            Email support
          </a>
        </div>
      )}
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex h-11 w-11 items-center justify-center rounded-full bg-primary text-slate-950 shadow-lg shadow-primary/25 hover:brightness-110 transition-all"
        aria-label="Get help"
      >
        <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
      </button>
    </div>
  );
}
