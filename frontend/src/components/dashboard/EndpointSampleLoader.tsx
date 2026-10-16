'use client';

import React, { useState } from 'react';

export default function EndpointSampleLoader() {
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [index, setIndex] = useState<string>('');
  const [pipeline, setPipeline] = useState<string>('');

  const triggerLoad = async () => {
    setLoading(true);
    setMessage(null);
    setError(null);
    try {
      const resp = await fetch('/api/v1/onboarding/load-endpoint-sample', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          index: index || undefined,
          pipeline: pipeline || undefined,
        }),
      });
      if (!resp.ok) {
        const data = await resp.json().catch(() => ({}));
        throw new Error(data.detail || resp.statusText);
      }
      const data = await resp.json();
      setMessage(`Sample ingested into ${data.index}${data.pipeline ? ` via pipeline ${data.pipeline}` : ''}`);
    } catch (e: any) {
      setError(e.message || 'Failed to send sample');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
      <div className="flex items-center justify-between mb-2">
        <div>
          <h4 className="text-sm font-semibold text-slate-200">Endpoint sample ingest</h4>
          <p className="text-xs text-slate-400">Send a test endpoint event to OpenSearch to validate ingest/pipeline.</p>
        </div>
        <button
          onClick={triggerLoad}
          disabled={loading}
          className="text-xs px-3 py-1 rounded-full bg-cyan-400 text-slate-950 hover:bg-cyan-300 disabled:opacity-50"
        >
          {loading ? 'Sending…' : 'Send sample'}
        </button>
      </div>
      <div className="grid md:grid-cols-2 gap-3">
        <div>
          <label className="block text-[11px] text-slate-400 mb-1">Index (optional)</label>
          <input
            value={index}
            onChange={(e) => setIndex(e.target.value)}
            placeholder="sg-<tenant>-endpoint-*"
            className="w-full rounded-lg border border-slate-700 bg-slate-950/60 px-3 py-2 text-xs text-slate-200"
          />
        </div>
        <div>
          <label className="block text-[11px] text-slate-400 mb-1">Ingest pipeline (optional)</label>
          <input
            value={pipeline}
            onChange={(e) => setPipeline(e.target.value)}
            placeholder="endpoint-pipeline"
            className="w-full rounded-lg border border-slate-700 bg-slate-950/60 px-3 py-2 text-xs text-slate-200"
          />
        </div>
      </div>
      {message && <div className="mt-3 text-xs text-green-300 bg-green-500/10 border border-green-500/30 rounded-lg p-2">{message}</div>}
      {error && <div className="mt-3 text-xs text-red-300 bg-red-500/10 border border-red-500/30 rounded-lg p-2">{error}</div>}
    </div>
  );
}
