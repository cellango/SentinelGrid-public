/**
 * Endpoint Coverage Component
 * Shows endpoint protection coverage and hardened image options
 */

'use client';

import { useState } from 'react';
import Link from 'next/link';

interface EndpointCoverageProps {
  coverage: {
    total: number;
    online: number;
    by_environment: {
      prod: { total: number; online: number };
      staging: { total: number; online: number };
      dev: { total: number; online: number };
    };
  };
}

export default function EndpointCoverage({ coverage }: EndpointCoverageProps) {
  const [showDownloadOptions, setShowDownloadOptions] = useState(false);

  const coveragePercent = coverage.total > 0 
    ? Math.round((coverage.online / coverage.total) * 100)
    : 0;

  const getCoverageColor = (percent: number) => {
    if (percent >= 80) return 'text-green-400';
    if (percent >= 50) return 'text-yellow-400';
    return 'text-red-400';
  };

  const getCoverageBgColor = (percent: number) => {
    if (percent >= 80) return 'bg-green-500/20 border-green-500/30';
    if (percent >= 50) return 'bg-yellow-500/20 border-yellow-500/30';
    return 'bg-red-500/20 border-red-500/30';
  };

  return (
    <div className="bg-[rgba(15,23,42,0.9)] backdrop-blur-md rounded-2xl border border-primary/20 p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-text-main mb-1">Device Protection</h3>
          <p className="text-sm text-text-muted">
            {coverage.online} / {coverage.total} servers protected ({coveragePercent}%)
          </p>
        </div>
      </div>

      {/* Coverage Progress */}
      <div className="mb-4">
        <div className="h-3 bg-[rgba(15,23,42,0.9)] rounded-full overflow-hidden">
          <div
            className={`h-full transition-all duration-500 ${getCoverageBgColor(coveragePercent)}`}
            style={{ width: `${coveragePercent}%` }}
          />
        </div>
      </div>

      {/* Breakdown by Environment */}
      <div className="space-y-2 mb-4 text-sm">
        <div className="flex items-center justify-between">
          <span className="text-text-muted">Production</span>
          <span className="text-text-main font-medium">
            {coverage.by_environment.prod.online} / {coverage.by_environment.prod.total}
          </span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-text-muted">Staging</span>
          <span className="text-text-main font-medium">
            {coverage.by_environment.staging.online} / {coverage.by_environment.staging.total}
          </span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-text-muted">Development</span>
          <span className="text-text-main font-medium">
            {coverage.by_environment.dev.online} / {coverage.by_environment.dev.total}
          </span>
        </div>
      </div>

      {/* Hardened Image Info */}
      <div className="bg-primary/10 border border-primary/20 rounded-xl p-3 mb-4">
        <p className="text-xs font-medium text-primary mb-1">Hardened Image</p>
        <p className="text-sm text-text-main mb-2">v1.2 – last updated 5 days ago</p>
        <Link
          href="/dashboard/endpoint-protection#images"
          className="text-xs text-primary hover:text-primary/80 transition-colors"
        >
          View changelog →
        </Link>
      </div>

      {/* Actions */}
      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => setShowDownloadOptions(!showDownloadOptions)}
          className="px-3 py-2 bg-primary/20 text-primary rounded-xl hover:bg-primary/30 transition-colors text-sm font-medium border border-primary/30"
        >
          Download Image
        </button>
        <Link
          href="/dashboard/endpoint-protection#install"
          className="px-3 py-2 bg-[rgba(15,23,42,0.9)] border border-primary/10 text-text-main rounded-xl hover:border-primary/30 transition-colors text-sm font-medium"
        >
          View Instructions
        </Link>
      </div>

      {/* Download Options Dropdown */}
      {showDownloadOptions && (
        <div className="mt-3 p-3 bg-[rgba(15,23,42,0.9)] border border-primary/20 rounded-xl">
          <p className="text-xs text-text-muted mb-2">Available Downloads:</p>
          <div className="space-y-1.5">
            <a
              href="#"
              className="block px-2 py-1.5 text-sm text-primary hover:bg-primary/10 rounded-lg transition-colors"
            >
              Linux (Ubuntu 22.04)
            </a>
            <a
              href="#"
              className="block px-2 py-1.5 text-sm text-primary hover:bg-primary/10 rounded-lg transition-colors"
            >
              Windows Server 2022
            </a>
            <a
              href="#"
              className="block px-2 py-1.5 text-sm text-primary hover:bg-primary/10 rounded-lg transition-colors"
            >
              Packer/Terraform Snippets
            </a>
          </div>
        </div>
      )}
    </div>
  );
}
