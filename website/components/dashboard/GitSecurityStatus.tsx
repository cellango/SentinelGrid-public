'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { listFindings, FindingListResponse } from '@/lib/api/git-scanning';

export default function GitSecurityStatus() {
  const router = useRouter();
  const [findings, setFindings] = useState<FindingListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    total: 0,
    critical: 0,
    high: 0,
    medium: 0,
    low: 0,
  });

  useEffect(() => {
    async function loadFindings() {
      try {
        const response = await listFindings(
          { status: 'open' },
          1,
          10
        );
        setFindings(response);
        
        // Calculate stats
        const severityCounts = response.findings.reduce((acc, finding) => {
          acc[finding.severity] = (acc[finding.severity] || 0) + 1;
          return acc;
        }, {} as Record<string, number>);
        
        setStats({
          total: response.total,
          critical: severityCounts.critical || 0,
          high: severityCounts.high || 0,
          medium: severityCounts.medium || 0,
          low: severityCounts.low || 0,
        });
      } catch (error) {
        console.error('Error loading Git findings:', error);
      } finally {
        setLoading(false);
      }
    }

    loadFindings();
  }, []);

  if (loading) {
    return (
      <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-slate-700 rounded w-1/4 mb-4"></div>
          <div className="h-20 bg-slate-800 rounded"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold">Git Security</h3>
        <button
          onClick={() => router.push('/onboarding?step=4')}
          className="text-sm text-cyan-400 hover:text-cyan-300"
        >
          {stats.total > 0 ? 'View All' : 'Connect'}
        </button>
      </div>

      {/* Stats */}
      {stats.total > 0 ? (
        <>
          <div className="grid grid-cols-5 gap-2 mb-4">
            <div className="text-center">
              <div className="text-xl font-bold">{stats.total}</div>
              <div className="text-xs text-slate-400">Total</div>
            </div>
            <div className="text-center">
              <div className="text-xl font-bold text-red-400">{stats.critical}</div>
              <div className="text-xs text-slate-400">Critical</div>
            </div>
            <div className="text-center">
              <div className="text-xl font-bold text-orange-400">{stats.high}</div>
              <div className="text-xs text-slate-400">High</div>
            </div>
            <div className="text-center">
              <div className="text-xl font-bold text-yellow-400">{stats.medium}</div>
              <div className="text-xs text-slate-400">Medium</div>
            </div>
            <div className="text-center">
              <div className="text-xl font-bold text-blue-400">{stats.low}</div>
              <div className="text-xs text-slate-400">Low</div>
            </div>
          </div>

          {/* Recent Findings */}
          {findings && findings.findings.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-sm font-medium text-slate-300 mb-2">Recent Findings</h4>
              {findings.findings.slice(0, 3).map((finding) => (
                <div
                  key={finding.id}
                  className="flex items-center justify-between p-2 bg-slate-800/50 rounded border border-slate-700"
                >
                  <div className="flex items-center gap-2">
                    <span className={`text-xs px-2 py-1 rounded font-medium ${
                      finding.severity === 'critical' ? 'bg-red-500/20 text-red-400' :
                      finding.severity === 'high' ? 'bg-orange-500/20 text-orange-400' :
                      finding.severity === 'medium' ? 'bg-yellow-500/20 text-yellow-400' :
                      'bg-blue-500/20 text-blue-400'
                    }`}>
                      {finding.severity}
                    </span>
                    <span className="text-xs text-slate-300 truncate max-w-[200px]">
                      {finding.title}
                    </span>
                  </div>
                  <span className="text-xs text-slate-500">
                    {finding.scanner_tool}
                  </span>
                </div>
              ))}
            </div>
          )}
        </>
      ) : (
        <div className="text-center py-8">
          <div className="text-4xl mb-2">🔍</div>
          <p className="text-sm text-slate-400 mb-4">
            No Git repositories connected
          </p>
          <button
            onClick={() => router.push('/onboarding?step=4')}
            className="inline-flex items-center justify-center rounded-full px-4 py-2 text-sm font-medium bg-cyan-400 text-slate-950 hover:bg-cyan-300 transition-colors"
          >
            Connect Git Repository
          </button>
        </div>
      )}
    </div>
  );
}

