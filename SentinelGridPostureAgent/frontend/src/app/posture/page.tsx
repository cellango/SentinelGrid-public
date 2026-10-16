'use client'

import { useEffect, useState } from 'react'
import { ScoreCard } from '@/components/posture/ScoreCard'
import { FindingsTable } from '@/components/posture/FindingsTable'
import { AssetInventory } from '@/components/posture/AssetInventory'
import { apiClient, type PostureSummary, type Finding, type Asset } from '@/lib/api-client'
import { AlertCircle, BarChart3, FileSearch } from 'lucide-react'
import Link from 'next/link'

export default function PosturePage() {
  const [summary, setSummary] = useState<PostureSummary | null>(null);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const tenantId = 'default-tenant'; // TODO: Get from auth context

      // Load posture summary
      const summaryData = await apiClient.getPostureSummary(tenantId);
      setSummary(summaryData);

      // Load critical and high findings
      const findingsData = await apiClient.listFindings({
        tenant_id: tenantId,
        limit: 10,
      });
      setFindings(findingsData);

      // Load assets
      const assetsData = await apiClient.listAssets(tenantId);
      setAssets(assetsData);
    } catch (error) {
      console.error('Error loading posture data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="container mx-auto p-8">
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
            <p className="text-muted-foreground">Loading posture data...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-4xl font-bold mb-2">Security Posture Dashboard</h1>
        <p className="text-muted-foreground">
          Monitor your cloud security posture and compliance status
        </p>
      </div>

      {/* Score Card */}
      {summary && (
        <div className="mb-8">
          <ScoreCard
            score={summary.posture_score}
            grade={summary.grade}
          />
        </div>
      )}

      {/* Stats Grid */}
      {summary && (
        <div className="grid md:grid-cols-4 gap-4 mb-8">
          <div className="border rounded-lg p-4 bg-red-50 dark:bg-red-950">
            <div className="text-3xl font-bold text-red-600 dark:text-red-400">
              {summary.critical_findings}
            </div>
            <div className="text-sm text-muted-foreground">Critical Findings</div>
          </div>

          <div className="border rounded-lg p-4 bg-orange-50 dark:bg-orange-950">
            <div className="text-3xl font-bold text-orange-600 dark:text-orange-400">
              {summary.high_findings}
            </div>
            <div className="text-sm text-muted-foreground">High Findings</div>
          </div>

          <div className="border rounded-lg p-4 bg-yellow-50 dark:bg-yellow-950">
            <div className="text-3xl font-bold text-yellow-600 dark:text-yellow-400">
              {summary.medium_findings}
            </div>
            <div className="text-sm text-muted-foreground">Medium Findings</div>
          </div>

          <div className="border rounded-lg p-4 bg-blue-50 dark:bg-blue-950">
            <div className="text-3xl font-bold text-blue-600 dark:text-blue-400">
              {summary.low_findings}
            </div>
            <div className="text-sm text-muted-foreground">Low Findings</div>
          </div>
        </div>
      )}

      {/* Critical Findings */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-semibold flex items-center gap-2">
            <AlertCircle className="h-6 w-6 text-red-600" />
            Priority Findings
          </h2>
          <Link
            href="/posture/findings"
            className="text-sm text-primary hover:underline"
          >
            View all →
          </Link>
        </div>
        <FindingsTable findings={findings.slice(0, 5)} />
      </div>

      {/* Quick Links */}
      <div className="grid md:grid-cols-2 gap-6">
        <Link
          href="/posture/findings"
          className="border rounded-lg p-6 hover:border-primary transition-colors group"
        >
          <FileSearch className="h-10 w-10 text-primary mb-3" />
          <h3 className="text-xl font-semibold mb-2 group-hover:text-primary">
            All Findings
          </h3>
          <p className="text-sm text-muted-foreground">
            Browse and manage all security findings
          </p>
        </Link>

        <Link
          href="/posture/assets"
          className="border rounded-lg p-6 hover:border-primary transition-colors group"
        >
          <BarChart3 className="h-10 w-10 text-primary mb-3" />
          <h3 className="text-xl font-semibold mb-2 group-hover:text-primary">
            Asset Inventory
          </h3>
          <p className="text-sm text-muted-foreground">
            View all discovered cloud resources and assets
          </p>
        </Link>
      </div>
    </div>
  );
}

